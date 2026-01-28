# backend/rag_pipeline/models.py
"""
Data models for RAG pipeline
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class ChunkType(str, Enum):
    """Type of document chunk"""
    NARRATIVE = "narrative"
    TABLE = "table"
    HEADING = "heading"


class ProgramType(str, Enum):
    """Mortgage program types"""
    DSCR = "DSCR"
    FULL_ALT = "FULL_ALT"
    NQMF = "NQMF"
    GENERAL = "GENERAL"


@dataclass
class Citation:
    """Citation with page number and excerpt"""
    page: int
    excerpt: str
    source_file: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "page": self.page,
            "excerpt": self.excerpt,
            "source_file": self.source_file
        }


@dataclass
class Chunk:
    """
    Document chunk with metadata
    """
    id: str
    text: str
    chunk_type: ChunkType
    section_path: str  # e.g., "Credit > Minimum FICO > Foreign Nationals"
    page_start: int
    page_end: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "chunk_type": self.chunk_type.value,
            "section_path": self.section_path,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "metadata": self.metadata,
            "embedding": self.embedding
        }


@dataclass
class DocumentPayload:
    """
    Metadata for indexed documents
    """
    lender: str
    program: ProgramType
    version: str
    filename: str
    gridfs_file_id: Optional[str] = None
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "lender": self.lender,
            "program": self.program.value,
            "version": self.version,
            "filename": self.filename,
            "gridfs_file_id": self.gridfs_file_id,
            "effective_date": self.effective_date,
            "expiry_date": self.expiry_date
        }


@dataclass
class ExtractionResult:
    """
    Result from LLM extraction
    """
    parameter: str
    value: str
    needs_clarification: bool
    clarification_reason: Optional[str]
    citations: List[Citation]
    confidence_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter": self.parameter,
            "value": self.value,
            "needs_clarification": self.needs_clarification,
            "clarification_reason": self.clarification_reason,
            "citations": [c.to_dict() for c in self.citations],
            "confidence_score": self.confidence_score
        }


@dataclass
class VerificationResult:
    """
    Result from LLM verification pass
    """
    verified: bool
    issues: List[str]
    suggested_fix: Optional[str]
    verification_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "verified": self.verified,
            "issues": self.issues,
            "suggested_fix": self.suggested_fix,
            "verification_notes": self.verification_notes
        }


@dataclass
class RetrievalResult:
    """
    Result from hybrid retrieval
    """
    chunk: Chunk
    score: float
    retrieval_method: str  # "bm25", "vector", or "hybrid"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk": self.chunk.to_dict(),
            "score": self.score,
            "retrieval_method": self.retrieval_method
        }
