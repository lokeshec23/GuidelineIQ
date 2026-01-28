import sys
import os
# Add backend to sys.path so we can import modules as if we are inside backend/
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))

try:
    from rag_pipeline.config import RAGConfig
    from rag_pipeline.indexing.qdrant_manager import QdrantManager

    print(f"URL: {RAGConfig.QDRANT_URL}")
    print(f"PATH: {RAGConfig.QDRANT_PATH}")

    mgr = QdrantManager()
    print("QdrantManager initialized successfully")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
