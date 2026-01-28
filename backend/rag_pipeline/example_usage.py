# backend/rag_pipeline/example_usage.py
"""
Example usage of RAG Pipeline
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from rag_pipeline.pipeline import RAGPipeline
from rag_pipeline.models import DocumentPayload, ProgramType
from ingest.dscr_config import DSCR_GUIDELINES


async def example_full_pipeline():
    """
    Example: Complete pipeline from PDF to extraction
    """
    print("="*60)
    print("RAG Pipeline - Full Example")
    print("="*60)
    
    pipeline = RAGPipeline()
    
    # Example PDF path (replace with actual path)
    pdf_path = "path/to/your/guideline.pdf"
    
    # Process DSCR guidelines
    results, num_chunks = await pipeline.process_dscr_guidelines(
        pdf_path=pdf_path,
        lender="NQMF",
        program="DSCR",
        version="1.0",
        gridfs_file_id="example_file_id",
        use_ocr_fallback=True,
        enable_verification=True
    )
    
    print(f"\n✅ Pipeline Complete!")
    print(f"   - Indexed: {num_chunks} chunks")
    print(f"   - Extracted: {len(results)} parameters")
    
    # Show sample results
    print("\nSample Extractions:")
    for result in results[:5]:
        print(f"\n  Parameter: {result['DSCR_Parameters']}")
        print(f"  Value: {result['NQMF Investor DSCR'][:100]}...")
        print(f"  Classification: {result['Classification']}")
        if result.get('Notes'):
            print(f"  Citations: {result['Notes'][:100]}...")


async def example_ingest_only():
    """
    Example: Ingest PDF without extraction
    """
    print("="*60)
    print("RAG Pipeline - Ingestion Only")
    print("="*60)
    
    pipeline = RAGPipeline()
    
    # Create document payload
    doc_payload = DocumentPayload(
        lender="NQMF",
        program=ProgramType.DSCR,
        version="1.0",
        filename="example_guideline.pdf",
        gridfs_file_id="example_123"
    )
    
    # Ingest PDF
    pdf_path = "path/to/your/guideline.pdf"
    num_chunks = await pipeline.ingest_pdf(
        pdf_path=pdf_path,
        document_payload=doc_payload,
        use_ocr_fallback=True
    )
    
    print(f"\n✅ Ingestion Complete!")
    print(f"   - Indexed: {num_chunks} chunks to Qdrant")
    print(f"   - Collection: DSCR_GUIDELINES")


async def example_extract_only():
    """
    Example: Extract from already-indexed documents
    """
    print("="*60)
    print("RAG Pipeline - Extraction Only")
    print("="*60)
    
    pipeline = RAGPipeline()
    
    # Filter conditions for retrieval
    filter_conditions = {
        "lender": "NQMF",
        "program": "DSCR",
        "version": "1.0"
    }
    
    # Extract parameters
    results = await pipeline.extract_parameters(
        parameters_config=DSCR_GUIDELINES,
        filter_conditions=filter_conditions,
        enable_verification=True
    )
    
    print(f"\n✅ Extraction Complete!")
    print(f"   - Extracted: {len(results)} parameters")
    
    # Count classifications
    extracted = sum(1 for r in results if r['Classification'] == 'Extracted')
    clarification = sum(1 for r in results if r['Classification'] == 'Clarification Required')
    
    print(f"   - Successfully Extracted: {extracted}")
    print(f"   - Needs Clarification: {clarification}")


async def example_hybrid_retrieval():
    """
    Example: Test hybrid retrieval
    """
    print("="*60)
    print("RAG Pipeline - Hybrid Retrieval Test")
    print("="*60)
    
    from rag_pipeline.retrieval.hybrid_retriever import HybridRetriever
    
    retriever = HybridRetriever()
    
    # Search query
    query = "What is the minimum FICO score for DSCR loans?"
    
    # Determine if we should prefer tables
    prefer_tables = retriever.should_prefer_tables(query)
    print(f"\nQuery: {query}")
    print(f"Prefer Tables: {prefer_tables}")
    
    # Search
    results = await retriever.search(
        query=query,
        top_k=5,
        filter_conditions={"lender": "NQMF", "program": "DSCR"},
        prefer_tables=prefer_tables
    )
    
    print(f"\n✅ Retrieved {len(results)} chunks:")
    for idx, result in enumerate(results, 1):
        chunk = result.chunk
        print(f"\n  {idx}. Score: {result.score:.4f}")
        print(f"     Type: {chunk.chunk_type.value}")
        print(f"     Section: {chunk.section_path}")
        print(f"     Pages: {chunk.page_start}-{chunk.page_end}")
        print(f"     Text: {chunk.text[:100]}...")


async def example_check_qdrant():
    """
    Example: Check Qdrant collection status
    """
    print("="*60)
    print("RAG Pipeline - Qdrant Status")
    print("="*60)
    
    from rag_pipeline.indexing.qdrant_manager import QdrantManager
    
    qdrant = QdrantManager()
    
    # Get collection info
    info = qdrant.get_collection_info()
    
    print(f"\nCollection: {info.get('name', 'N/A')}")
    print(f"Points: {info.get('points_count', 0)}")
    print(f"Vectors: {info.get('vectors_count', 0)}")
    print(f"Status: {info.get('status', 'Unknown')}")


def main():
    """
    Main entry point - run all examples
    """
    print("\n" + "="*60)
    print("RAG Pipeline - Example Usage")
    print("="*60 + "\n")
    
    print("Available examples:")
    print("1. Full Pipeline (Ingest + Extract)")
    print("2. Ingestion Only")
    print("3. Extraction Only")
    print("4. Hybrid Retrieval Test")
    print("5. Check Qdrant Status")
    print("6. Run All Examples")
    
    choice = input("\nSelect example (1-6): ").strip()
    
    if choice == "1":
        asyncio.run(example_full_pipeline())
    elif choice == "2":
        asyncio.run(example_ingest_only())
    elif choice == "3":
        asyncio.run(example_extract_only())
    elif choice == "4":
        asyncio.run(example_hybrid_retrieval())
    elif choice == "5":
        asyncio.run(example_check_qdrant())
    elif choice == "6":
        print("\nRunning all examples...\n")
        asyncio.run(example_check_qdrant())
        # Add more as needed
    else:
        print("Invalid choice. Exiting.")


if __name__ == "__main__":
    main()
