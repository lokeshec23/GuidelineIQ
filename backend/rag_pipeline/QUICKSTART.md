# RAG Pipeline - Quick Start Guide

## Installation

```bash
# Install new dependencies
pip install pdfplumber==0.11.0 qdrant-client==1.7.0 rank-bm25==0.2.2

# Ensure Qdrant is running
docker run -p 6333:6333 qdrant/qdrant
```

## Configuration

Your existing `.env` is already configured:
- ✅ `AZURE_OPENAI_EMBEDDING_DEPLOYMENT=embedding-model`
- ✅ `AZURE_OPENAI_DEPLOYMENT_NAME=extraction-model`
- ✅ `DI_endpoint` and `DI_key` (for OCR fallback)
- ✅ `QDRANT_URL=http://localhost:6333`

## Quick Test

```python
from rag_pipeline.pipeline import RAGPipeline
import asyncio

async def test():
    pipeline = RAGPipeline()
    
    results, num_chunks = await pipeline.process_dscr_guidelines(
        pdf_path="path/to/guideline.pdf",
        lender="NQMF",
        program="DSCR",
        version="1.0",
        use_ocr_fallback=True,
        enable_verification=True
    )
    
    print(f"✅ Indexed {num_chunks} chunks")
    print(f"✅ Extracted {len(results)} parameters")

asyncio.run(test())
```

## Running Tests

Unit tests are included in `backend/tests/rag_pipeline`.

```bash
# Run all tests
pytest tests/rag_pipeline

# Run specific test file
pytest tests/rag_pipeline/test_chunker.py
```

## Key Features

1. **OCR Fallback**: Automatically uses Azure OCR when pdfplumber fails
2. **Hybrid Retrieval**: BM25 + Vector search with RRF fusion
3. **Deterministic**: Temperature=0 for consistent results
4. **Citations**: Page-level tracking for all extractions
5. **Quality Assurance**: Dual-pass LLM (Extractor + Verifier)
6. **DSCR Integration**: Works with existing `DSCR_GUIDELINES` config

## File Structure

```
backend/rag_pipeline/
├── pipeline.py           # Main orchestrator
├── config.py             # Configuration
├── models.py             # Data models
├── README.md             # Full documentation
├── example_usage.py      # Interactive examples
├── ingestion/            # PDF parsing + chunking
├── indexing/             # Embeddings + Qdrant
├── retrieval/            # Hybrid search
└── extraction/           # LLM extractor + verifier
```

## Documentation

- **Full README**: `rag_pipeline/README.md`
- **Examples**: `rag_pipeline/example_usage.py`
- **Walkthrough**: See artifacts for detailed explanation

## Next Steps

1. Test with sample PDF
2. Integrate with `ingest/processor.py`
3. Update `ingest/dscr_extractor.py` to use new pipeline
