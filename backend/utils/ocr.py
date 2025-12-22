# backend/utils/ocr.py

import os
import tempfile
import concurrent.futures
from typing import List
from PyPDF2 import PdfReader, PdfWriter
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient

# Local imports
from config import AZURE_DI_ENDPOINT, AZURE_DI_KEY

class AzureOCR:
    """
    A production-ready wrapper for Azure Document Intelligence (OCR).
    - Initializes the client with credentials from environment variables.
    - Processes PDFs in parallel chunks for speed and reliability.
    - Handles temporary file creation and cleanup.
    """

    def __init__(self):
        """Initializes the Azure Document Intelligence client."""
        if not AZURE_DI_ENDPOINT or not AZURE_DI_KEY:
            raise ValueError("Azure Document Intelligence credentials (DI_endpoint, DI_key) are not configured in the environment.")

        try:
            self.client = DocumentAnalysisClient(
                endpoint=AZURE_DI_ENDPOINT,
                credential=AzureKeyCredential(AZURE_DI_KEY),
            )
            print("✅ AzureOCR client initialized successfully.")
        except Exception as e:
            print(f"❌ Failed to initialize AzureOCR client: {e}")
            raise

    def _split_pdf_into_physical_chunks(self, pdf_path: str, pages_per_chunk: int) -> List[str]:
        """
        Splits a PDF into smaller temporary PDF files.
        This is done to manage memory and handle large documents efficiently.
        """
        print(f"📄 Splitting PDF into physical chunks of up to {pages_per_chunk} pages each...")
        temp_file_paths = []
        try:
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)

            for i in range(0, total_pages, pages_per_chunk):
                writer = PdfWriter()
                end_page = min(i + pages_per_chunk, total_pages)
                
                for j in range(i, end_page):
                    writer.add_page(reader.pages[j])

                # Create a secure temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    writer.write(tmp_file)
                    temp_file_paths.append(tmp_file.name)
                
                print(f"   - Created chunk for pages {i + 1}-{end_page}")

            print(f"✅ Created {len(temp_file_paths)} physical PDF chunks.")
            return temp_file_paths
        except Exception as e:
            print(f"❌ Error splitting PDF: {e}")
            # Clean up any files that were created before the error
            for path in temp_file_paths:
                if os.path.exists(path):
                    os.remove(path)
            raise

    def _analyze_single_chunk(self, chunk_path: str) -> str:
        """
        Runs Azure OCR on a single small PDF file chunk.
        """
        try:
            with open(chunk_path, "rb") as f:
                poller = self.client.begin_analyze_document("prebuilt-layout", f)
                result = poller.result()

            # Consolidate all text from all pages within the chunk
            # This is robust for cases where a chunk might have multiple pages
            page_texts = []
            for page in result.pages:
                # Reconstruct page text from paragraphs to maintain structure
                paragraphs_on_page = [
                    para.content for para in result.paragraphs 
                    if para.bounding_regions and para.bounding_regions[0].page_number == page.page_number
                ]
                page_texts.append("\n".join(paragraphs_on_page))
            
            return "\n\n".join(page_texts)

        except Exception as e:
            print(f"❌ OCR analysis failed for chunk {os.path.basename(chunk_path)}: {e}")
            return "" # Return empty string on failure to not break the whole process

    def analyze_doc_page_by_page(self, pdf_path: str, pages_per_chunk: int = 1) -> List[tuple]:
        """
        High-level method to orchestrate the OCR process using Azure Document Intelligence.
        It splits the PDF, processes chunks through Azure OCR, and returns text with accurate page numbers.
        
        Args:
            pdf_path: The path to the source PDF file.
            pages_per_chunk: The number of pages to group into a single text chunk for the LLM.
        
        Returns:
            A list of tuples, where each tuple is (text_content, page_numbers_string).
            Example: [("Text from page 1", "1"), ("Text from pages 2-3", "2-3")]
        """
    def _parse_page_range(self, range_str: str, max_pages: int) -> List[int]:
        """
        Parses a page range string (e.g., "1-5, 8, 11-13") into a sorted list of 1-based page numbers.
        """
        if not range_str or not range_str.strip():
            return list(range(1, max_pages + 1))
            
        pages = set()
        try:
            parts = range_str.split(',')
            for part in parts:
                part = part.strip()
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    # Clamp to valid range
                    start = max(1, start)
                    end = min(max_pages, end)
                    if start <= end:
                        pages.update(range(start, end + 1))
                else:
                    page = int(part)
                    if 1 <= page <= max_pages:
                        pages.add(page)
        except ValueError:
            print(f"⚠️ Invalid page range format: '{range_str}'. Defaulting to all pages.")
            return list(range(1, max_pages + 1))
            
        if not pages:
            print(f"⚠️ No valid pages found in range '{range_str}'. Defaulting to all pages.")
            return list(range(1, max_pages + 1))
            
        return sorted(list(pages))

    def analyze_doc_page_by_page(self, pdf_path: str, pages_per_chunk: int = 1, page_range: str = None) -> List[tuple]:
        """
        High-level method to orchestrate the OCR process using Azure Document Intelligence.
        It splits the PDF, processes chunks through Azure OCR, and returns text with accurate page numbers.
        
        Args:
            pdf_path: The path to the source PDF file.
            pages_per_chunk: The number of pages to group into a single text chunk for the LLM.
            page_range: Optional string specifying pages to process (e.g., "1-5, 8").
        
        Returns:
            A list of tuples, where each tuple is (text_content, page_numbers_string).
            Example: [("Text from page 1", "1"), ("Text from pages 2-3", "2-3")]
        """
        print(f"\n🚀 Starting Azure OCR pipeline with {pages_per_chunk} page(s) per chunk...")
        
        # Get total page count first
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        print(f"📄 Total pages in PDF: {total_pages}")

        # Determine which pages to process
        target_pages = self._parse_page_range(page_range, total_pages)
        print(f"🎯 Processing {len(target_pages)} specific pages: {target_pages}")
        
        # Split into physical chunks for Azure OCR processing (30 pages per chunk for efficiency)
        physical_chunk_size = 30
        
        # Group target pages into physical chunks
        # physical_chunks will be a list of lists, where each inner list contains page numbers for that chunk
        physical_page_groups = [target_pages[i:i + physical_chunk_size] for i in range(0, len(target_pages), physical_chunk_size)]
        
        # This will hold all OCR results with their absolute page numbers
        all_ocr_pages = []
        
        print(f"\n📋 Processing {len(physical_page_groups)} physical chunk(s) through Azure OCR...")
        
        # Process each physical chunk
        for chunk_idx, page_group in enumerate(physical_page_groups):
            print(f"\n🔍 Processing physical chunk {chunk_idx + 1}/{len(physical_page_groups)} (Pages: {page_group[0]}-{page_group[-1]})...")
            
            # Create a temporary PDF for this group of pages only
            temp_chunk_path = None
            try:
                writer = PdfWriter()
                for page_num in page_group:
                    # page_num is 1-based, PdfReader uses 0-based
                    writer.add_page(reader.pages[page_num - 1])
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    writer.write(tmp_file)
                    temp_chunk_path = tmp_file.name
                
                # Run Azure OCR on this physical chunk
                with open(temp_chunk_path, "rb") as f:
                    poller = self.client.begin_analyze_document("prebuilt-layout", f)
                    result = poller.result()
                
                # Extract text
                for page in result.pages:
                    # Azure's page.page_number is 1-based relative to the temp PDF
                    # We need to map it back to the original page number from page_group
                    temp_pdf_page_index = page.page_number - 1 # 0-based index in temp file
                    display_page_num = page_group[temp_pdf_page_index]
                    
                    paragraphs_on_page = [
                        para.content for para in result.paragraphs 
                        if para.bounding_regions and para.bounding_regions[0].page_number == page.page_number
                    ]
                    
                    page_text = "\n".join(paragraphs_on_page)
                    all_ocr_pages.append((page_text, display_page_num))
                    
                    print(f"   ✅ Extracted page {display_page_num} ({len(page_text)} chars)")
                    
            except Exception as e:
                print(f"   ❌ Azure OCR failed for chunk {chunk_idx + 1}: {e}")
                # We skip this chunk but continue processing others
                continue
                
            finally:
                if temp_chunk_path and os.path.exists(temp_chunk_path):
                    try:
                        os.remove(temp_chunk_path)
                    except:
                        pass
        
        print(f"\n✅ Azure OCR complete. Extracted {len(all_ocr_pages)} pages.")
        
        # Now group pages according to user's pages_per_chunk setting
        final_text_chunks = []
        
        print(f"\n📦 Grouping pages into chunks of {pages_per_chunk} page(s)...")
        
        for i in range(0, len(all_ocr_pages), pages_per_chunk):
            # Get the pages for this chunk
            chunk_pages = all_ocr_pages[i:i + pages_per_chunk]
            
            # Combine text from all pages in this chunk
            combined_text = "\n\n".join([page_text for page_text, _ in chunk_pages])
            
            # Get page numbers for this chunk
            page_nums = [page_num for _, page_num in chunk_pages]
            
            if len(page_nums) == 1:
                page_numbers_str = str(page_nums[0])
            else:
                # Check if pages are consecutive
                if page_nums[-1] - page_nums[0] == len(page_nums) - 1:
                    page_numbers_str = f"{page_nums[0]}-{page_nums[-1]}"
                else:
                    # Non-consecutive pages
                    page_numbers_str = ",".join(map(str, page_nums))
            
            if combined_text.strip():
                final_text_chunks.append((combined_text.strip(), page_numbers_str))
                print(f"   📄 Chunk {len(final_text_chunks)}: Pages {page_numbers_str} ({len(combined_text)} chars)")
        
        print(f"\n✅ Created {len(final_text_chunks)} text chunk(s) with accurate page numbers for LLM processing.")
        return final_text_chunks
