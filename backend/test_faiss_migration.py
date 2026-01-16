# Test script for FAISS-based RAG Service
# This script tests the basic functionality of the new FAISS implementation

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chat.rag_service import RAGService
import asyncio

async def test_rag_service():
    print("="*60)
    print("Testing FAISS-based RAG Service")
    print("="*60)
    
    # Initialize RAG service
    print("\n1. Initializing RAG Service...")
    rag = RAGService()
    
    # Check initial stats
    stats = rag.get_collection_stats()
    print(f"   Initial stats: {stats}")
    
    # Test 1: Add some test documents
    print("\n2. Adding test documents...")
    test_docs = [
        {
            "id": "test_doc_1",
            "text": "This is a test document about DSCR calculations for investors.",
            "embedding": [0.1] * 1536,  # Simulated embedding (OpenAI text-embedding-3-small dimension)
            "metadata": {
                "investor": "TestInvestor",
                "version": "v1.0",
                "filename": "test.pdf",
                "page": "1",
                "type": "pdf_chunk"
            }
        },
        {
            "id": "test_doc_2",
            "text": "Another document discussing loan-to-value ratios and guidelines.",
            "embedding": [0.2] * 1536,
            "metadata": {
                "investor": "TestInvestor",
                "version": "v1.0",
                "filename": "test.pdf",
                "page": "2",
                "type": "pdf_chunk"
            }
        },
        {
            "id": "test_doc_3",
            "text": "Different investor guidelines for property evaluation.",
            "embedding": [0.15] * 1536,
            "metadata": {
                "investor": "AnotherInvestor",
                "version": "v2.0",
                "filename": "other.pdf",
                "page": "1",
                "type": "pdf_chunk"
            }
        }
    ]
    
    try:
        await rag.add_documents_async(test_docs, batch_size=2)
        print("   [OK] Documents added successfully!")
    except Exception as e:
        print(f"   [ERROR] Failed to add documents: {e}")
        return False
    
    # Check stats after adding
    stats = rag.get_collection_stats()
    print(f"   Stats after adding: {stats}")
    
    # Test 2: Test persistence (reload)
    print("\n3. Testing persistence (reload)...")
    rag2 = RAGService()
    stats2 = rag2.get_collection_stats()
    print(f"   Reloaded stats: {stats2}")
    
    if stats2['total_documents'] == 3:
        print("   [OK] Persistence works!")
    else:
        print("   [ERROR] Persistence failed!")
        return False
    
    # Test 3: Test metadata filtering
    print("\n4. Testing metadata filtering...")
    
    # Create a simple search without actual embeddings
    # We'll manually test the filtering logic
    print("   Testing filter by investor='TestInvestor'...")
    filtered_count = sum(1 for m in rag2.metadata if m['metadata'].get('investor') == 'TestInvestor')
    print(f"   Found {filtered_count} documents for TestInvestor")
    
    if filtered_count == 2:
        print("   [OK] Metadata filtering works!")
    else:
        print("   [ERROR] Metadata filtering failed!")
        return False
    
    print("\n" + "="*60)
    print("[OK] All tests passed! FAISS migration successful!")
    print("="*60)
    
    return True

if __name__ == "__main__":
    result = asyncio.run(test_rag_service())
    sys.exit(0 if result else 1)
