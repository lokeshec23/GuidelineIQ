import sys
import os
# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.rag_pipeline.config import RAGConfig
from backend.rag_pipeline.indexing.qdrant_manager import QdrantManager

print(f"URL: {RAGConfig.QDRANT_URL}")
print(f"PATH: {RAGConfig.QDRANT_PATH}")

try:
    mgr = QdrantManager()
    print("QdrantManager initialized successfully")
    # info = mgr.get_collection_info()
    # print(f"Collection Info: {info}") 
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
