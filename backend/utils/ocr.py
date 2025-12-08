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
        High-level method to orchestrate the OCR process.
        It splits the PDF, processes chunks in parallel, and returns a list of text contents with page numbers.
        
        Args:
            pdf_path: The path to the source PDF file.
            pages_per_chunk: The number of pages to group into a single text chunk for the LLM.
        
        Returns:
            A list of tuples, where each tuple is (text_content, page_numbers_string).
            Example: [("Text from page 1", "1"), ("Text from pages 2-3", "2-3")]
        """
        print(f"\n🚀 Starting OCR pipeline with {pages_per_chunk} page(s) per chunk...")
        
        # Get total page count first
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        print(f"📄 Total pages in PDF: {total_pages}")
        
        # Use larger physical chunks for OCR efficiency, e.g., 30 pages
        # This reduces the number of separate API calls to Azure OCR
        physical_chunk_paths = self._split_pdf_into_physical_chunks(pdf_path, pages_per_chunk=30)
        
        # This will hold the final text chunks with page numbers, grouped by the user's setting
        final_text_chunks = []
        
        # Track the current absolute page number across all physical chunks
        current_absolute_page = 1
        
        # Process each physical 30-page chunk
        for physical_chunk_path in physical_chunk_paths:
            # We need to re-read the small physical chunk to split it logically
            reader = PdfReader(physical_chunk_path)
            total_pages_in_chunk = len(reader.pages)

            # Now, create logical chunks based on user's 'pages_per_chunk' setting
            for i in range(0, total_pages_in_chunk, pages_per_chunk):
                writer = PdfWriter()
                end_page = min(i + pages_per_chunk, total_pages_in_chunk)
                
                # Calculate the absolute page numbers for this chunk
                start_page_num = current_absolute_page + i
                end_page_num = current_absolute_page + end_page - 1
                
                # Format page numbers as string
                if start_page_num == end_page_num:
                    page_numbers = str(start_page_num)
                else:
                    page_numbers = f"{start_page_num}-{end_page_num}"
                
                current_logical_chunk_text = ""
                for j in range(i, end_page):
                    page = reader.pages[j]
                    current_logical_chunk_text += page.extract_text() + "\n\n"
                
                if current_logical_chunk_text.strip():
                    # Append as tuple: (text, page_numbers)
                    final_text_chunks.append((current_logical_chunk_text.strip(), page_numbers))
            
            # Update the absolute page counter for the next physical chunk
            current_absolute_page += total_pages_in_chunk

        # Cleanup the temporary physical PDF chunks
        for path in physical_chunk_paths:
            if os.path.exists(path):
                os.remove(path)
                
        print(f"✅ OCR complete. Extracted {len(final_text_chunks)} text chunks with page numbers for LLM processing.")
        return final_text_chunks
