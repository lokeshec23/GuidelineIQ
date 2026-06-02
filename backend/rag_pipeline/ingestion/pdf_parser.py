# backend/rag_pipeline/ingestion/pdf_parser.py
"""
PDF Parser with pdfplumber (primary) and Azure OCR (fallback)
"""

import re
import pdfplumber
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import logging

from utils.ocr import AzureOCR
from rag_pipeline.config import RAGConfig

logger = logging.getLogger(__name__)


class PDFParser:
    """
    PDF parser with intelligent text extraction
    - Primary: pdfplumber for native text extraction
    - Fallback: Azure OCR when pdfplumber fails
    """
    
    def __init__(self):
        self.ocr_client = None
        self.config = RAGConfig
    
    # Input validation limits
    MAX_FILE_SIZE_MB = 200
    MAX_PAGE_COUNT = 2000
    
    def parse_pdf(
        self,
        pdf_path: str,
        use_ocr_fallback: bool = True
    ) -> List[Dict]:
        """
        Parse PDF and extract structured content
        
        Args:
            pdf_path: Path to PDF file
            use_ocr_fallback: Whether to use OCR if pdfplumber fails
        
        Returns:
            List of page dictionaries with text, tables, and metadata
        
        Raises:
            ValueError: If file exceeds size/page limits
            FileNotFoundError: If file does not exist
        """
        logger.info(f"Parsing PDF: {pdf_path}")
        
        # --- Input Validation ---
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        file_size_mb = pdf_file.stat().st_size / (1024 * 1024)
        if file_size_mb > self.MAX_FILE_SIZE_MB:
            raise ValueError(
                f"PDF file too large: {file_size_mb:.1f}MB "
                f"(max {self.MAX_FILE_SIZE_MB}MB)"
            )
        
        # Quick page count check
        try:
            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)
            if page_count > self.MAX_PAGE_COUNT:
                raise ValueError(
                    f"PDF has too many pages: {page_count} "
                    f"(max {self.MAX_PAGE_COUNT})"
                )
            logger.info(f"PDF validated: {file_size_mb:.1f}MB, {page_count} pages")
        except pdfplumber.pdfminer.pdfparser.PDFSyntaxError as e:
            raise ValueError(f"Invalid PDF file: {e}")
        
        pages_data = []
        
        try:
            # Try pdfplumber first
            pages_data = self._parse_with_pdfplumber(pdf_path)
            
            # Check if extraction was successful
            total_text = sum(len(p.get("text", "")) for p in pages_data)
            
            if total_text < 100:  # Threshold for "usable text"
                logger.warning(
                    f"pdfplumber extracted only {total_text} characters. "
                    "PDF may be scanned or have extraction issues."
                )
                
                if use_ocr_fallback:
                    logger.info("Falling back to Azure OCR...")
                    pages_data = self._parse_with_ocr(pdf_path)
                else:
                    logger.warning("OCR fallback disabled. Using pdfplumber results.")
            else:
                logger.info(
                    f"pdfplumber successfully extracted {total_text} characters "
                    f"from {len(pages_data)} pages"
                )
        
        except Exception as e:
            logger.error(f"pdfplumber failed: {e}")
            
            if use_ocr_fallback:
                logger.info("Falling back to Azure OCR...")
                try:
                    pages_data = self._parse_with_ocr(pdf_path)
                except Exception as ocr_error:
                    logger.error(f"OCR fallback also failed: {ocr_error}")
                    raise ValueError(
                        f"Both pdfplumber and OCR failed to extract text from {pdf_path}"
                    )
            else:
                raise
        
        return pages_data
    
    def _parse_with_pdfplumber(self, pdf_path: str) -> List[Dict]:
        """
        Parse PDF using pdfplumber in parallel using a ThreadPoolExecutor
        
        Returns:
            List of page dictionaries with text, tables, and headings
        """
        from concurrent.futures import ThreadPoolExecutor
        
        # Open PDF to get number of pages
        with pdfplumber.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)
            
        heading_patterns = self.config.HEADING_PATTERNS
        
        def parse_page(page_num: int) -> Dict:
            page_data = {
                "page_number": page_num,
                "text": "",
                "tables": [],
                "headings": [],
                "extraction_method": "pdfplumber_parallel"
            }
            
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    if page_num <= len(pdf.pages):
                        page = pdf.pages[page_num - 1]
                        
                        # Extract text
                        text = page.extract_text()
                        if text:
                            page_data["text"] = text
                            
                            # Detect headings
                            headings = []
                            lines = text.split('\n')
                            for line in lines:
                                line = line.strip()
                                if not line:
                                    continue
                                for pattern in heading_patterns:
                                    if re.match(pattern, line):
                                        headings.append(line)
                                        break
                            page_data["headings"] = headings
                        
                        # Extract tables
                        tables = page.extract_tables()
                        if tables:
                            page_data["tables"] = [
                                self._format_table(table) for table in tables
                            ]
            except Exception as e:
                logger.error(f"Error parsing page {page_num}: {e}")
                page_data["extraction_method"] = "pdfplumber_parallel_failed"
                
            return page_data

        # Parse pages in parallel using ThreadPoolExecutor
        max_workers = min(16, num_pages) if num_pages > 0 else 1
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            pages_data = list(executor.map(parse_page, range(1, num_pages + 1)))
            
        return pages_data
    
    def _parse_with_ocr(self, pdf_path: str) -> List[Dict]:
        """
        Parse PDF using Azure OCR (fallback)
        
        Returns:
            List of page dictionaries with OCR-extracted text
        """
        if self.ocr_client is None:
            self.ocr_client = AzureOCR()
        
        logger.info(f"Running Azure OCR on {pdf_path}...")
        
        # Use existing OCR client from utils
        # analyze_doc_page_by_page returns list of (text, page_range) tuples
        ocr_results = self.ocr_client.analyze_doc_page_by_page(
            pdf_path,
            pages_per_chunk=1  # Process one page at a time for granularity
        )
        
        pages_data = []
        
        for idx, (text, page_range) in enumerate(ocr_results, start=1):
            page_data = {
                "page_number": idx,
                "text": text,
                "tables": [],  # OCR doesn't extract structured tables
                "headings": self._detect_headings(text) if text else [],
                "extraction_method": "azure_ocr"
            }
            pages_data.append(page_data)
        
        logger.info(f"OCR extracted text from {len(pages_data)} pages")
        return pages_data
    
    def _detect_headings(self, text: str) -> List[str]:
        """
        Detect headings using heuristics
        
        Args:
            text: Page text
        
        Returns:
            List of detected heading strings
        """
        headings = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check against heading patterns
            for pattern in self.config.HEADING_PATTERNS:
                if re.match(pattern, line):
                    headings.append(line)
                    break
        
        return headings
    
    def _format_table(self, table: List[List]) -> Dict:
        """
        Format extracted table into structured dict
        
        Args:
            table: Raw table from pdfplumber
        
        Returns:
            Formatted table dictionary
        """
        if not table:
            return {"headers": [], "rows": []}
        
        # First row is usually headers
        headers = table[0] if table else []
        rows = table[1:] if len(table) > 1 else []
        
        return {
            "headers": [str(h) if h else "" for h in headers],
            "rows": [
                [str(cell) if cell else "" for cell in row]
                for row in rows
            ]
        }
    
    def extract_page_range(
        self,
        pdf_path: str,
        start_page: int,
        end_page: int
    ) -> List[Dict]:
        """
        Extract specific page range from PDF
        
        Args:
            pdf_path: Path to PDF
            start_page: Starting page (1-indexed)
            end_page: Ending page (1-indexed, inclusive)
        
        Returns:
            List of page dictionaries for the specified range
        """
        all_pages = self.parse_pdf(pdf_path)
        return all_pages[start_page - 1:end_page]
