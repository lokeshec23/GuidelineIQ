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
        self._logged_embedding_model = False  # Flag to prevent excessive logging

    def _get_collection(self):
        if self.collection is None:
            if self.client is None:
                self.client = chromadb.PersistentClient(path=self.chroma_path)
            
            collection_name = "guideline_chunks"
            
            # Try to get existing collection
            try:
                self.collection = self.client.get_collection(name=collection_name)
                print(f"✅ Using existing ChromaDB collection: {collection_name}")
            except Exception as e:
                # Collection doesn't exist, create it
                print(f"📦 Creating new ChromaDB collection: {collection_name}")
                self.collection = self.client.create_collection(name=collection_name)
                
        return self.collection
    
    def reset_collection_if_dimension_mismatch(self, expected_dimension: int):
        """
        Reset the collection if there's a dimension mismatch.
        This is needed when switching between different embedding models.
        """
        if self.client is None:
            self.client = chromadb.PersistentClient(path=self.chroma_path)
        
        collection_name = "guideline_chunks"
        
        try:
            # Try to get existing collection
            existing_collection = self.client.get_collection(name=collection_name)
            
            # Check if collection has any documents
            count = existing_collection.count()
            
            if count > 0:
                # Get a sample document to check dimension
                sample = existing_collection.peek(limit=1)
                if sample and sample.get('embeddings') and len(sample['embeddings']) > 0:
                    actual_dimension = len(sample['embeddings'][0])
                    
                    if actual_dimension != expected_dimension:
                        print(f"⚠️ Dimension mismatch detected: Collection has {actual_dimension}D embeddings, but model produces {expected_dimension}D")
                        print(f"🔄 Deleting and recreating collection...")
                        
                        # Delete old collection
                        self.client.delete_collection(name=collection_name)
                        
                        # Create new collection
                        self.collection = self.client.create_collection(name=collection_name)
                        print(f"✅ Created new collection with {expected_dimension}D embeddings")
                        return True
            
            self.collection = existing_collection
            return False
            
        except Exception as e:
            # Collection doesn't exist, create it
            print(f"📦 Creating new ChromaDB collection: {collection_name}")
            self.collection = self.client.create_collection(name=collection_name)
            return False

    async def get_embedding(self, text: str, provider: str, api_key: str, **kwargs) -> List[float]:
        """Generates embedding for a single text chunk (Async)."""
        try:
            if provider == "openai":
                # ... existing client setup ...
                client = None
                if kwargs.get("azure_endpoint"):
                     # For Azure OpenAI, use a separate embedding deployment
                     embedding_deployment = kwargs.get("azure_embedding_deployment", "embedding-model")
                     
                     # Only log once per session
                     if not self._logged_embedding_model:
                         print(f"🔍 Using Azure OpenAI Embedding Deployment: {embedding_deployment}")
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
                        print(f"🔍 Using OpenAI Embedding Model: {EMBEDDING_MODEL_OPENAI}")
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
                    print(f"🔍 Using Gemini Embedding Model: {EMBEDDING_MODEL_GEMINI}")
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

        # Check embedding dimension and reset collection if needed
        if embeddings and len(embeddings) > 0:
            embedding_dimension = len(embeddings[0])
            self.reset_collection_if_dimension_mismatch(embedding_dimension)
        
        collection = self._get_collection()
        
        try:
            collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents_text
            )
            print(f"✅ Added {len(documents)} chunks to ChromaDB.")
        except Exception as e:
            if "dimension" in str(e).lower():
                print(f"⚠️ Dimension error detected: {e}")
                print(f"🔄 Recreating collection with correct dimension...")
                
                # Force reset the collection
                if embeddings and len(embeddings) > 0:
                    embedding_dimension = len(embeddings[0])
                    self.reset_collection_if_dimension_mismatch(embedding_dimension)
                    
                    # Retry adding documents
                    collection = self._get_collection()
                    collection.add(
                        ids=ids,
                        embeddings=embeddings,
                        metadatas=metadatas,
                        documents=documents_text
                    )
                    print(f"✅ Added {len(documents)} chunks to ChromaDB after reset.")
            else:
                raise e

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
                 # Pass through all kwargs including azure_embedding_deployment
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
