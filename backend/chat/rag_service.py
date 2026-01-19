# backend/chat/rag_service.py

import os
import json
import faiss
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
        self.index_path = os.path.join(self.index_dir, "index.faiss")
        self.metadata_path = os.path.join(self.index_dir, "metadata.json")
        
        self.index = None
        self.metadata = []  # List of metadata dicts aligned with FAISS index
        self.dimension = None
        self._logged_embedding_model = False
        
        # Create directory if it doesn't exist
        Path(self.index_dir).mkdir(parents=True, exist_ok=True)
        
        # Load existing index or create new one
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """Load existing FAISS index and metadata, or create new ones."""
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            try:
                # Load FAISS index
                self.index = faiss.read_index(self.index_path)
                self.dimension = self.index.d
                
                # Load metadata
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                
                print(f"[OK] Loaded existing FAISS index: {self.index.ntotal} vectors, dimension={self.dimension}")
            except Exception as e:
                print(f"[WARN] Failed to load existing index: {e}")
                print("[INFO] Creating new FAISS index...")
                self.index = None
                self.metadata = []
        else:
            print("[INFO] No existing FAISS index found. Will create on first document addition.")
    
    def _save_index(self):
        """Persist FAISS index and metadata to disk."""
        try:
            if self.index is not None:
                faiss.write_index(self.index, self.index_path)
            
            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
            
            print(f"[SAVE] Saved FAISS index: {len(self.metadata)} documents")
        except Exception as e:
            print(f"[ERROR] Failed to save index: {e}")
    
    def _ensure_index_exists(self, dimension: int):
        """Create FAISS index if it doesn't exist or dimension changed."""
        if self.index is None or self.dimension != dimension:
            if self.index is not None:
                print(f"[WARN] Dimension changed from {self.dimension} to {dimension}. Creating new index.")
            
            # Use IndexFlatL2 for exact L2 distance search (best for <1M vectors)
            self.index = faiss.IndexFlatL2(dimension)
            self.dimension = dimension
            self.metadata = []  # Reset metadata when creating new index
            print(f"[OK] Created new FAISS index with dimension={dimension}")
    
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
                        api_version="2023-05-15",
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
        Add documents to FAISS index (synchronous).
        
        Args:
            documents: List of dicts with keys: id, text, embedding, metadata
            check_dimension: Legacy parameter for ChromaDB compatibility (ignored)
        """
        if not documents:
            return

        try:
            # Extract embeddings and metadata
            embeddings = [doc["embedding"] for doc in documents]
            
            # Ensure index exists with correct dimension
            dimension = len(embeddings[0])
            self._ensure_index_exists(dimension)
            
            # Convert to numpy array
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            # Add to FAISS index
            self.index.add(embeddings_array)
            
            # Store metadata (aligned with FAISS index positions)
            for doc in documents:
                metadata_entry = {
                    "id": doc["id"],
                    "text": doc["text"],
                    "metadata": doc["metadata"]
                }
                self.metadata.append(metadata_entry)
            
            # Persist to disk
            self._save_index()
            
            print(f"[OK] Added {len(documents)} documents to FAISS index. Total: {self.index.ntotal}")
            
        except Exception as e:
            print(f"[ERROR] Failed to add documents to FAISS: {e}")
            raise e
    
    async def add_documents_async(self, documents: List[Dict], batch_size: int = 200):
        """
        Asynchronously add documents to FAISS in batches.
        Offloads operations to thread pool to prevent event loop starvation.
        
        Args:
            documents: List of document dictionaries with id, text, embedding, metadata
            batch_size: Number of documents to process per batch (default: 200)
        """
        if not documents:
            return
        
        total = len(documents)
        print(f"[INFO] Adding {total} documents to FAISS in batches of {batch_size}...")

        # Add batches
        for i in range(0, total, batch_size):
            batch = documents[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size
            print(f"[INFO] Adding batch {batch_num}/{total_batches} to FAISS...")
            
            # Offload synchronous FAISS operation to thread pool
            await asyncio.to_thread(self.add_documents, batch, check_dimension=False)
            
            print(f"[OK] Batch {batch_num}/{total_batches}: Added {len(batch)} documents")
            
            # Yield control back to event loop between batches
            await asyncio.sleep(0)

    async def search(self, query: str, provider: str, api_key: str, n_results: int = 5, filter_metadata: Optional[Dict] = None, **kwargs) -> List[Dict]:
        """
        Search for relevant chunks using FAISS (Async).
        
        Args:
            query: Search query text
            provider: Embedding provider (openai/gemini)
            api_key: API key for embedding generation
            n_results: Number of results to return
            filter_metadata: Optional metadata filters (e.g., {"investor": "X", "filename": "Y"})
            **kwargs: Additional arguments for embedding generation
        
        Returns:
            List of search results with id, text, metadata, and distance
        """
        # Generate query embedding
        query_embedding = []
        try:
            if provider == "gemini":
                genai.configure(api_key=api_key)
                func = functools.partial(
                    genai.embed_content,
                    model=EMBEDDING_MODEL_GEMINI,
                    content=query,
                    task_type="retrieval_query"
                )
                result = await asyncio.to_thread(func)
                query_embedding = result['embedding']
                
            elif provider == "openai":
                # Pass through all kwargs including azure_embedding_deployment
                query_embedding = await self.get_embedding(query, provider, api_key, **kwargs)
            
        except Exception as e:
            print(f"[ERROR] Query embedding failed: {e}")
            return []

        if not query_embedding:
            return []
        
        # Check if index exists and has documents
        if self.index is None or self.index.ntotal == 0:
            print("[WARN] FAISS index is empty. No documents to search.")
            return []
        
        # Convert query to numpy array
        query_array = np.array([query_embedding], dtype=np.float32)
        
        # Perform FAISS search
        # Search for more results if filtering is needed
        search_k = n_results * 10 if filter_metadata else n_results
        search_k = min(search_k, self.index.ntotal)  # Don't search for more than available
        
        # Check for dimension mismatch
        if self.index.d != query_array.shape[1]:
            print(f"[WARN] Dimension mismatch in search: Index={self.index.d}, Query={query_array.shape[1]}")
            print("[WARN] Resetting index to match new embedding model dimension.")
            self._ensure_index_exists(query_array.shape[1])
            self._save_index()
            return []

        distances, indices = self.index.search(query_array, search_k)
        
        # Format results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:  # FAISS returns -1 for empty results
                continue
            
            metadata_entry = self.metadata[idx]
            
            # Apply metadata filtering if specified
            if filter_metadata:
                match = True
                for key, value in filter_metadata.items():
                    if metadata_entry["metadata"].get(key) != value:
                        match = False
                        break
                
                if not match:
                    continue
            
            results.append({
                "id": metadata_entry["id"],
                "text": metadata_entry["text"],
                "metadata": metadata_entry["metadata"],
                "distance": float(distances[0][i])
            })
            
            # Stop when we have enough results
            if len(results) >= n_results:
                break
        
        return results
    
    def reset_collection_if_dimension_mismatch(self, expected_dimension: int):
        """
        Legacy method for ChromaDB compatibility.
        FAISS handles dimension changes automatically by recreating the index.
        """
        if self.dimension is not None and self.dimension != expected_dimension:
            print(f"[WARN] Dimension mismatch: Current={self.dimension}, Expected={expected_dimension}")
            print(f"[INFO] Creating new FAISS index with dimension={expected_dimension}")
            self._ensure_index_exists(expected_dimension)
            return True
        return False
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the current FAISS index."""
        return {
            "total_documents": self.index.ntotal if self.index else 0,
            "dimension": self.dimension,
            "index_type": "FAISS IndexFlatL2",
            "metadata_count": len(self.metadata)
        }
