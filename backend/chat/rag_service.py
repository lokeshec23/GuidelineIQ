import chromadb
from chromadb.config import Settings
import os
from typing import List, Dict, Optional
import google.generativeai as genai
from openai import OpenAI, AzureOpenAI

# Initialize ChromaDB Client
CHROMA_DB_PATH = os.path.join(os.getcwd(), "chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Embedding Models
EMBEDDING_MODEL_OPENAI = "text-embedding-3-small"
EMBEDDING_MODEL_GEMINI = "models/text-embedding-004"

class RAGService:
    def __init__(self):
        self.collection = chroma_client.get_or_create_collection(name="guideline_chunks")

    async def get_embedding(self, text: str, provider: str, api_key: str, **kwargs) -> List[float]:
        """Generates embedding for a single text chunk (Async)."""
        import asyncio
        import functools
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

        self.collection.add(
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
        import asyncio
        import functools
        
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

        # ChromaDB query is fast enough to be sync, but good to wrap if DB grows
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata
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
