
import pytest
from rag_pipeline.models import Chunk, DocumentPayload, ChunkType, ExtractionResult

def test_chunk_model_validation():
    """Test Chunk model validation and default values"""
    chunk = Chunk(
        id="test_1",
        text="Sample text",
        chunk_type=ChunkType.NARRATIVE,
        section_path="Section 1",
        page_start=1,
        page_end=1
    )
    assert chunk.metadata == {}
    assert chunk.id == "test_1"

def test_document_payload_normalization():
    """Test DocumentPayload normalization of sender/lender"""
    payload = DocumentPayload(
        lender="  Test Lender  ",
        program="DSCR",
        version="1.0",
        filename="test.pdf",
        gridfs_file_id="123"
    )
    assert payload.lender == "Test Lender"  # Should be stripped
    assert payload.program.value == "DSCR"

def test_extraction_result_model():
    """Test ExtractionResult validation"""
    result = ExtractionResult(
        value="660",
        citations=[{"page": 1, "excerpt": "Min score 660", "source_file": "test.pdf"}]
    )
    assert result.value == "660"
    assert len(result.citations) == 1
    assert result.needs_clarification is False  # Default
