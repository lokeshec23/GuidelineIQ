import chromadb
from chromadb.config import Settings
import os
from typing import List, Dict, Optional
import google.generativeai as genai
import random
from openai import OpenAI, AzureOpenAI
import asyncio
import functools

# Embedding Models
EMBEDDING_MODEL_OPENAI = "text-embedding-3-small"
EMBEDDING_MODEL_GEMINI = "models/text-embedding-004"

class RAGService:
    def __init__(self):
        self.chroma_path = os.path.join(os.getcwd(), "chroma_db")
        self.client = None
        self.collection = None

    def _get_collection(self):
        if self.collection is None:
            if self.client is None:
                self.client = chromadb.PersistentClient(path=self.chroma_path)
            self.collection = self.client.get_or_create_collection(name="guideline_chunks")
        return self.collection

    async def get_embedding(self, text: str, provider: str, api_key: str, **kwargs) -> List[float]:
        """Generates embedding for a single text chunk (Async)."""
        try:
            if provider == "openai":
                # ... existing client setup ...
                client = None
                if kwargs.get("azure_endpoint"):
                     client = AzureOpenAI(
                        api_key=api_key,
                        api_version="2023-05-15",
                        azure_endpoint=kwargs.get("azure_endpoint"),
                        azure_deployment=kwargs.get("azure_deployment")
                    )
                else:
                    client = OpenAI(api_key=api_key)
                
                # Run sync call in thread
                func = functools.partial(client.embeddings.create, input=[text], model=EMBEDDING_MODEL_OPENAI)
                response = await asyncio.to_thread(func)
                return response.data[0].embedding

            elif provider == "gemini":
                genai.configure(api_key=api_key)
                
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
                            print(f"❌ Gemini embedding failed after {max_retries} attempts: {e}")
                            raise e
                        
                        sleep_time = (base_delay * (2 ** attempt)) + (random.random() * 0.5)
                        print(f"⚠️ Gemini embedding failed (Attempt {attempt+1}/{max_retries}). Retrying in {sleep_time:.2f}s... Error: {e}")
                        await asyncio.sleep(sleep_time)
            
            else:
                raise ValueError(f"Unsupported provider for embeddings: {provider}")
        except Exception as e:
            print(f"❌ Embedding generation failed: {e}")
            return []

    def add_documents(self, documents: List[Dict]):
        # ... existing sync add_documents is fine (local DB) ...
        # (Same implementation as before)
        if not documents:
            return

        ids = [doc["id"] for doc in documents]
        embeddings = [doc["embedding"] for doc in documents]
        metadatas = [doc["metadata"] for doc in documents]
        documents_text = [doc["text"] for doc in documents]

        collection = self._get_collection()
        collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents_text
        )
        print(f"✅ Added {len(documents)} chunks to ChromaDB.")

    async def search(self, query: str, provider: str, api_key: str, n_results: int = 5, filter_metadata: Optional[Dict] = None, **kwargs) -> List[Dict]:
        """
        Searches for relevant chunks (Async).
        """
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
                 query_embedding = await self.get_embedding(query, provider, api_key, **kwargs)
            
        except Exception as e:
             print(f"❌ Query embedding failed: {e}")
             return []

        if not query_embedding:
            return []

        # Prepare filter
        where_clause = None
        if filter_metadata:
            if len(filter_metadata) > 1:
                # Use explicit $and for multiple conditions
                where_clause = {"$and": [{k: v} for k, v in filter_metadata.items()]}
            else:
                where_clause = filter_metadata

        # ChromaDB query is fast enough to be sync, but good to wrap if DB grows
        collection = self._get_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause
        )
        
        # Format results (same as before)
        formatted_results = []
        if results['ids']:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    "id": results['ids'][0][i],
                    "text": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if results['distances'] else None
                })
        
        return formatted_results
