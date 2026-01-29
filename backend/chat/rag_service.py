# backend/chat/rag_service.py

import os
import json
import numpy as np
from typing import List, Dict, Optional
import google.generativeai as genai
import random
from openai import OpenAI, AzureOpenAI
import asyncio
import functools
from pathlib import Path

# Embedding Models
EMBEDDING_MODEL_OPENAI = "text-embedding-3-small"
EMBEDDING_MODEL_GEMINI = "models/text-embedding-004"

class RAGService:
    def __init__(self):
        self.index_dir = os.path.join(os.getcwd(), "faiss_db")
        # Legacy paths - kept preventing errors if accessed
        self.index_path = os.path.join(self.index_dir, "index.faiss")
        self.metadata_path = os.path.join(self.index_dir, "metadata.json")
        
        # FAISS removed - these are placeholders
        self.index = None
        self.metadata = [] 
        self.dimension = None
        self._logged_embedding_model = False
        
        # Create directory if it doesn't exist
        Path(self.index_dir).mkdir(parents=True, exist_ok=True)
        
        print("[INFO] RAG Service initialized.")

    
    def _save_index(self):
        """No-op: FAISS removed"""
        pass
    
    def _ensure_index_exists(self, dimension: int):
        """No-op: FAISS removed"""
        pass
    
    async def get_embedding(self, text: str, provider: str, api_key: str, **kwargs) -> List[float]:
        """Generates embedding for a single text chunk (Async)."""
        try:
            if provider == "openai":
                client = None
                if kwargs.get("azure_endpoint"):
                    # For Azure OpenAI, use a separate embedding deployment
                    embedding_deployment = kwargs.get("azure_embedding_deployment", "embedding-model")
                    
                    # Only log once per session
                    if not self._logged_embedding_model:
                        print(f"[INFO] Using Azure OpenAI Embedding Deployment: {embedding_deployment}")
                        self._logged_embedding_model = True
                    
                    client = AzureOpenAI(
                        api_key=api_key,
                        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
                        azure_endpoint=kwargs.get("azure_endpoint")
                    )
                    # Use the embedding deployment name as the model parameter
                    func = functools.partial(client.embeddings.create, input=[text], model=embedding_deployment)
                else:
                    client = OpenAI(api_key=api_key)
                    
                    # Only log once per session
                    if not self._logged_embedding_model:
                        print(f"[INFO] Using OpenAI Embedding Model: {EMBEDDING_MODEL_OPENAI}")
                        self._logged_embedding_model = True
                    
                    # For standard OpenAI, use the embedding model constant
                    func = functools.partial(client.embeddings.create, input=[text], model=EMBEDDING_MODEL_OPENAI)
                
                # Run sync call in thread
                response = await asyncio.to_thread(func)
                return response.data[0].embedding

            elif provider == "gemini":
                genai.configure(api_key=api_key)
                
                # Only log once per session
                if not self._logged_embedding_model:
                    print(f"[INFO] Using Gemini Embedding Model: {EMBEDDING_MODEL_GEMINI}")
                    self._logged_embedding_model = True
                
                # Retry logic for Gemini embedding
                max_retries = 5
                base_delay = 1
                
                for attempt in range(max_retries):
                    try:
                        # Run sync call in thread
                        func = functools.partial(
                            genai.embed_content,
                            model=EMBEDDING_MODEL_GEMINI,
                            content=text,
                            task_type="retrieval_document",
                            title="Guideline Chunk" 
                        )
                        result = await asyncio.to_thread(func)
                        return result['embedding']
                    except Exception as e:
                        if attempt == max_retries - 1:
                            print(f"[ERROR] Gemini embedding failed after {max_retries} attempts: {e}")
                            raise e
                        
                        sleep_time = (base_delay * (2 ** attempt)) + (random.random() * 0.5)
                        print(f"[WARN] Gemini embedding failed (Attempt {attempt+1}/{max_retries}). Retrying in {sleep_time:.2f}s... Error: {e}")
                        await asyncio.sleep(sleep_time)
            
            else:
                raise ValueError(f"Unsupported provider for embeddings: {provider}")
        except Exception as e:
            print(f"[ERROR] Embedding generation failed: {e}")
            return []

    def add_documents(self, documents: List[Dict], check_dimension: bool = True):
        """
        No-op: FAISS removed.
        Prior code added documents to FAISS index.
        """
        if not documents:
            return
        
        # Log that we are skipping indexing
        # print(f"[INFO] Skipping FAISS indexing for {len(documents)} documents (FAISS disabled).")
        pass
    
    async def add_documents_async(self, documents: List[Dict], batch_size: int = 200):
        """
        No-op: FAISS removed.
        """
        if not documents:
            return
        
        # print(f"[INFO] Skipping FAISS indexing (Async) for {len(documents)} documents.")
        pass

    async def search(self, query: str, provider: str, api_key: str, n_results: int = 5, filter_metadata: Optional[Dict] = None, **kwargs) -> List[Dict]:
        """
        Legacy search method. Returns empty list as FAISS is removed.
        Use RAGPipeline (Qdrant) for search instead.
        """
        # print("[WARN] RAGService.search called but FAISS is disabled. Returning empty results.")
        return []
    
    def reset_collection_if_dimension_mismatch(self, expected_dimension: int):
        """No-op"""
        return False
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the current index (Stubbed)."""
        return {
            "total_documents": 0,
            "dimension": 0,
            "index_type": "FAISS Removed",
            "metadata_count": 0
        }
