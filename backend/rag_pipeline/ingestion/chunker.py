# backend/rag_pipeline/ingestion/chunker.py
"""
Section-aware chunking with table detection
"""

import re
from typing import List, Dict, Tuple
import logging

from rag_pipeline.models import Chunk, ChunkType
from rag_pipeline.config import RAGConfig

logger = logging.getLogger(__name__)


class SectionAwareChunker:
    """
    Creates chunks with section hierarchy awareness
    Separates narrative text from tables
    """
    
    def __init__(self):
        self.config = RAGConfig
        self.section_stack = []  # Track section hierarchy
    
    def chunk_pages(
        self,
        pages_data: List[Dict],
        document_id: str
    ) -> List[Chunk]:
        """
        Create chunks from parsed pages
        
        Args:
            pages_data: List of page dictionaries from PDFParser
            document_id: Unique document identifier
        
        Returns:
            List of Chunk objects
        """
        all_chunks = []
        chunk_counter = 0
        
        for page_data in pages_data:
            page_num = page_data["page_number"]
            
            # Process tables first (higher priority)
            for table_idx, table in enumerate(page_data.get("tables", [])):
                chunk = self._create_table_chunk(
                    table=table,
                    page_num=page_num,
                    chunk_id=f"{document_id}_table_{page_num}_{table_idx}",
                    section_path=self._get_current_section_path()
                )
                all_chunks.append(chunk)
                chunk_counter += 1
            
            # Process narrative text
            text = page_data.get("text", "")
            if text:
                # Update section hierarchy based on headings
                headings = page_data.get("headings", [])
                if headings:
                    self._update_section_stack(headings)
                
                # Create narrative chunks
                narrative_chunks = self._create_narrative_chunks(
                    text=text,
                    page_num=page_num,
                    document_id=document_id,
                    chunk_counter=chunk_counter
                )
                all_chunks.extend(narrative_chunks)
                chunk_counter += len(narrative_chunks)
        
        logger.info(
            f"Created {len(all_chunks)} chunks "
            f"({sum(1 for c in all_chunks if c.chunk_type == ChunkType.TABLE)} tables, "
            f"{sum(1 for c in all_chunks if c.chunk_type == ChunkType.NARRATIVE)} narrative)"
        )
        
        return all_chunks
    
    def _create_table_chunk(
        self,
        table: Dict,
        page_num: int,
        chunk_id: str,
        section_path: str
    ) -> Chunk:
        """
        Create a chunk from a table
        
        Args:
            table: Table dictionary with headers and rows
            page_num: Page number
            chunk_id: Unique chunk ID
            section_path: Current section hierarchy
        
        Returns:
            Chunk object
        """
        # Format table as text
        table_text = self._format_table_as_text(table)
        
        return Chunk(
            id=chunk_id,
            text=table_text,
            chunk_type=ChunkType.TABLE,
            section_path=section_path,
            page_start=page_num,
            page_end=page_num,
            metadata={
                "has_table": True,
                "table_headers": table.get("headers", []),
                "table_row_count": len(table.get("rows", []))
            }
        )
    
    def _create_narrative_chunks(
        self,
        text: str,
        page_num: int,
        document_id: str,
        chunk_counter: int
    ) -> List[Chunk]:
        """
        Create narrative chunks from text with overlap
        
        Args:
            text: Page text
            page_num: Page number
            document_id: Document identifier
            chunk_counter: Starting chunk counter
        
        Returns:
            List of narrative chunks
        """
        chunks = []
        
        # Simple sentence-based chunking
        sentences = self._split_into_sentences(text)
        
        current_chunk_text = ""
        current_chunk_sentences = []
        
        for sentence in sentences:
            # Rough token estimate (1 token ≈ 4 characters)
            estimated_tokens = len(current_chunk_text + sentence) // 4
            
            if estimated_tokens > self.config.CHUNK_SIZE and current_chunk_text:
                # Create chunk
                chunk = Chunk(
                    id=f"{document_id}_narrative_{page_num}_{chunk_counter}",
                    text=current_chunk_text.strip(),
                    chunk_type=ChunkType.NARRATIVE,
                    section_path=self._get_current_section_path(),
                    page_start=page_num,
                    page_end=page_num,
                    metadata={"sentence_count": len(current_chunk_sentences)}
                )
                chunks.append(chunk)
                chunk_counter += 1
                
                # Overlap: keep last few sentences
                overlap_sentences = current_chunk_sentences[-2:] if len(current_chunk_sentences) > 2 else []
                current_chunk_text = " ".join(overlap_sentences) + " "
                current_chunk_sentences = overlap_sentences
            
            current_chunk_text += sentence + " "
            current_chunk_sentences.append(sentence)
        
        # Add remaining text as final chunk
        if current_chunk_text.strip():
            chunk = Chunk(
                id=f"{document_id}_narrative_{page_num}_{chunk_counter}",
                text=current_chunk_text.strip(),
                chunk_type=ChunkType.NARRATIVE,
                section_path=self._get_current_section_path(),
                page_start=page_num,
                page_end=page_num,
                metadata={"sentence_count": len(current_chunk_sentences)}
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences
        
        Args:
            text: Input text
        
        Returns:
            List of sentences
        """
        # Simple sentence splitting (can be improved with nltk)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _format_table_as_text(self, table: Dict) -> str:
        """
        Format table as readable text
        
        Args:
            table: Table dictionary
        
        Returns:
            Formatted table string
        """
        lines = []
        
        # Headers
        headers = table.get("headers", [])
        if headers:
            lines.append(" | ".join(headers))
            lines.append("-" * 50)
        
        # Rows
        for row in table.get("rows", []):
            lines.append(" | ".join(row))
        
        return "\n".join(lines)
    
    def _update_section_stack(self, headings: List[str]):
        """
        Update section hierarchy stack based on detected headings
        
        Args:
            headings: List of heading strings
        """
        for heading in headings:
            # Determine heading level (simple heuristic)
            if re.match(r'^\d+\.', heading):  # Numbered section
                # Top-level section
                self.section_stack = [heading]
            elif heading.isupper():  # ALL CAPS
                # Major section
                self.section_stack = [heading]
            else:
                # Subsection
                if len(self.section_stack) > 0:
                    self.section_stack.append(heading)
                else:
                    self.section_stack = [heading]
    
    def _get_current_section_path(self) -> str:
        """
        Get current section path as string
        
        Returns:
            Section path (e.g., "Credit > Minimum FICO")
        """
        if not self.section_stack:
            return "General"
        return " > ".join(self.section_stack)
    
    def reset_section_stack(self):
        """Reset section hierarchy (call between documents)"""
        self.section_stack = []
