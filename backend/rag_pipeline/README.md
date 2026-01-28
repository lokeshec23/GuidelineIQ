# RAG Pipeline for Mortgage Guideline Extraction

Production-grade Retrieval-Augmented Generation (RAG) system for extracting structured mortgage guidelines from lender PDFs.

## Features

- **Intelligent PDF Parsing**: pdfplumber (primary) with Azure OCR fallback
- **Section-Aware Chunking**: Hierarchical section tracking with table detection
- **Hybrid Retrieval**: BM25 (keyword) + Qdrant (semantic) with Reciprocal Rank Fusion
- **Deterministic Extraction**: Azure OpenAI with temperature=0 for consistent results
- **Quality Assurance**: Dual-pass LLM (Extractor + Verifier)
- **Citation Tracking**: Page-level citations for all extracted values
- **Qdrant Integration**: Persistent vector database for `DSCR_GUIDELINES` collection

## Architecture

```
PDF → Parser (pdfplumber/OCR) → Chunker → Embedder → Qdrant
                                                          ↓
Query → Hybrid Retriever (BM25 + Vector) → LLM Extractor → LLM Verifier → Excel
```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Ensure Qdrant is running
# Option 1: Docker
docker run -p 6333:6333 qdrant/qdrant

# Option 2: Cloud (update QDRANT_URL in .env)
```

## Configuration

All configuration is managed through `.env`:

```env
# Azure OpenAI
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=embedding-model
AZURE_OPENAI_DEPLOYMENT_NAME=extraction-model

# Azure Document Intelligence (OCR Fallback)
DI_endpoint=https://your-di.cognitiveservices.azure.com/
DI_key=your_di_key_here

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Optional
```

## Usage

### Basic Usage

```python
from rag_pipeline.pipeline import RAGPipeline
from rag_pipeline.models import ProgramType
import asyncio

async def main():
    pipeline = RAGPipeline()
    
    # Process PDF and extract DSCR parameters
    results, num_chunks = await pipeline.process_dscr_guidelines(
        pdf_path="path/to/guideline.pdf",
        lender="NQMF",
        program="DSCR",
        version="1.0",
        gridfs_file_id="optional_file_id",
        use_ocr_fallback=True,  # Use OCR if pdfplumber fails
        enable_verification=True  # Enable LLM verification pass
    )
    
    print(f"Indexed {num_chunks} chunks")
    print(f"Extracted {len(results)} parameters")
    
    for result in results:
        print(f"{result['DSCR_Parameters']}: {result['NQMF Investor DSCR']}")

asyncio.run(main())
```

### Integration with Existing DSCR Workflow

```python
from rag_pipeline.pipeline import RAGPipeline
from ingest.dscr_config import DSCR_GUIDELINES

async def extract_with_rag_pipeline(
    pdf_path: str,
    investor: str,
    version: str,
    gridfs_file_id: str
):
    pipeline = RAGPipeline()
    
    # Ingest PDF
    from rag_pipeline.models import DocumentPayload, ProgramType
    
    doc_payload = DocumentPayload(
        lender=investor,
        program=ProgramType.DSCR,
        version=version,
        filename=Path(pdf_path).name,
        gridfs_file_id=gridfs_file_id
    )
    
    num_chunks = await pipeline.ingest_pdf(pdf_path, doc_payload)
    
    # Extract parameters
    filter_conditions = {
        "lender": investor,
        "program": "DSCR",
        "version": version
    }
    
    results = await pipeline.extract_parameters(
        parameters_config=DSCR_GUIDELINES,
        filter_conditions=filter_conditions,
        enable_verification=True
    )
    
    return results
```

### Manual Ingestion and Retrieval

```python
from rag_pipeline.ingestion.pdf_parser import PDFParser
from rag_pipeline.ingestion.chunker import SectionAwareChunker
from rag_pipeline.indexing.embedder import AzureEmbedder
from rag_pipeline.indexing.qdrant_manager import QdrantManager
from rag_pipeline.retrieval.hybrid_retriever import HybridRetriever

# Parse PDF
parser = PDFParser()
pages_data = parser.parse_pdf("guideline.pdf", use_ocr_fallback=True)

# Create chunks
chunker = SectionAwareChunker()
chunks = chunker.chunk_pages(pages_data, document_id="doc_123")

# Generate embeddings
embedder = AzureEmbedder()
texts = [chunk.text for chunk in chunks]
embeddings = await embedder.generate_embeddings_batch_async(texts)

for chunk, embedding in zip(chunks, embeddings):
    chunk.embedding = embedding

# Index to Qdrant
qdrant_manager = QdrantManager()
await qdrant_manager.index_chunks_async(chunks, document_payload)

# Search
retriever = HybridRetriever()
retriever.index_chunks(chunks)

results = await retriever.search(
    query="What is the minimum FICO score?",
    top_k=5,
    filter_conditions={"lender": "NQMF"},
    prefer_tables=False
)
```

## Key Components

### 1. PDF Parser (`ingestion/pdf_parser.py`)
- **Primary**: pdfplumber for native text extraction
- **Fallback**: Azure OCR when pdfplumber yields < 100 characters
- **Features**: Table detection, heading extraction, page-level metadata

### 2. Section-Aware Chunker (`ingestion/chunker.py`)
- **Chunk Types**: Narrative (text) and Table (structured data)
- **Section Hierarchy**: Tracks section path (e.g., "Credit > Minimum FICO")
- **Overlap**: 50-token overlap between narrative chunks
- **Max Size**: 500 tokens per chunk (configurable)

### 3. Qdrant Manager (`indexing/qdrant_manager.py`)
- **Collection**: `DSCR_GUIDELINES`
- **Vector Size**: 1536 (text-embedding-3-large)
- **Metadata**: lender, program, version, section_path, chunk_type, pages
- **Operations**: Create, index, search, delete by document

### 4. Hybrid Retriever (`retrieval/hybrid_retriever.py`)
- **BM25**: Keyword-based retrieval (30% weight)
- **Vector**: Semantic search via Qdrant (70% weight)
- **Fusion**: Reciprocal Rank Fusion (RRF)
- **Table Preference**: 50% boost for table chunks when query suggests matrix data

### 5. LLM Extractor (`extraction/llm_extractor.py`)
- **Model**: Azure OpenAI (deployment from .env)
- **Temperature**: 0.0 (deterministic)
- **Output**: Strict JSON schema with value, citations, clarification flags
- **Retry**: Automatic retry on JSON parsing errors

### 6. LLM Verifier (`extraction/llm_verifier.py`)
- **Purpose**: Quality assurance pass
- **Checks**: Hallucination detection, citation accuracy, completeness
- **Output**: Verification status, issues list, suggested fixes

## Data Models

### Chunk
```python
@dataclass
class Chunk:
    id: str
    text: str
    chunk_type: ChunkType  # NARRATIVE | TABLE
    section_path: str  # "Credit > Minimum FICO"
    page_start: int
    page_end: int
    metadata: Dict[str, Any]
    embedding: Optional[List[float]]
```

### ExtractionResult
```python
@dataclass
class ExtractionResult:
    parameter: str
    value: str
    needs_clarification: bool
    clarification_reason: Optional[str]
    citations: List[Citation]  # Page + excerpt
    confidence_score: float
```

## Configuration

### RAGConfig (`config.py`)
- **Chunking**: `CHUNK_SIZE=500`, `CHUNK_OVERLAP=50`
- **Retrieval**: `TOP_K_BM25=10`, `TOP_K_VECTOR=10`, `TOP_K_FINAL=5`
- **Weights**: `BM25_WEIGHT=0.3`, `VECTOR_WEIGHT=0.7`
- **LLM**: `EXTRACTION_TEMPERATURE=0.0`, `MAX_TOKENS=4096`

## Logging

Logs are written to `logs/rag_pipeline/`:
- `ingestion.log`: PDF parsing and chunking
- `indexing.log`: Embedding generation and Qdrant operations
- `retrieval.log`: Search queries and results
- `extraction.log`: LLM calls and responses

## Testing

```bash
# Run tests
pytest tests/rag_pipeline/

# Test specific module
pytest tests/rag_pipeline/test_pdf_parser.py -v
```

## Troubleshooting

### OCR Fallback Not Triggering
- Check `DI_endpoint` and `DI_key` in `.env`
- Verify Azure Document Intelligence resource is active
- Check logs for pdfplumber character count

### Qdrant Connection Failed
- Ensure Qdrant is running: `docker ps | grep qdrant`
- Check `QDRANT_URL` in `.env`
- Verify network connectivity

### Embedding Generation Slow
- Reduce batch size in `embedder.generate_embeddings_batch_async()`
- Check Azure OpenAI rate limits
- Consider using async batching

### Low Retrieval Quality
- Adjust `BM25_WEIGHT` and `VECTOR_WEIGHT` in `config.py`
- Increase `TOP_K_VECTOR` for more candidates
- Enable `prefer_tables=True` for matrix-heavy queries

## Performance

- **Ingestion**: ~500 chunks/minute (with embeddings)
- **Retrieval**: ~50ms per query (hybrid)
- **Extraction**: ~2-3 seconds per parameter (with verification)
- **End-to-End**: ~5-10 minutes for full DSCR guideline (200+ parameters)

## Production Considerations

1. **Rate Limiting**: Implement semaphores for Azure OpenAI API calls
2. **Caching**: Cache embeddings for frequently accessed chunks
3. **Monitoring**: Track extraction accuracy and verification failure rates
4. **Versioning**: Use `version` field in metadata for guideline updates
5. **Backup**: Regular Qdrant collection snapshots

## License

Proprietary - Internal Use Only
