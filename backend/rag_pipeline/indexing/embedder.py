# backend/rag_pipeline/indexing/embedder.py
"""
Azure OpenAI Embedding Generator with content-hash cache
"""

import asyncio
import hashlib
from typing import List, Dict, Optional
import logging
from openai import AzureOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from rag_pipeline.config import RAGConfig

logger = logging.getLogger(__name__)


class AzureEmbedder:
    """
    Azure OpenAI embedding generator with retry logic
    """
    
    def __init__(self):
        self.config = RAGConfig
        self.client = None
        # Content-hash → embedding cache (avoids re-embedding identical text)
        self._cache: Dict[str, List[float]] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._initialize_client()
    
    @staticmethod
    def _content_hash(text: str) -> str:
        """SHA256 hash of text content for cache key"""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    
    def _initialize_client(self):
        """Initialize Azure OpenAI client"""
        try:
            self.client = AzureOpenAI(
                api_key=self.config.AZURE_OPENAI_API_KEY,
                api_version=self.config.AZURE_OPENAI_API_VERSION,
                azure_endpoint=self.config.AZURE_OPENAI_ENDPOINT
            )
            logger.info(
                f"Initialized Azure OpenAI client with deployment: "
                f"{self.config.AZURE_OPENAI_EMBEDDING_DEPLOYMENT}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text (with cache)
        
        Args:
            text: Input text
        
        Returns:
            Embedding vector
        """
        # Check cache first
        cache_key = self._content_hash(text)
        if cache_key in self._cache:
            self._cache_hits += 1
            return self._cache[cache_key]
        
        self._cache_misses += 1
        try:
            response = self.client.embeddings.create(
                input=[text],
                model=self.config.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
            )
            embedding = response.data[0].embedding
            self._cache[cache_key] = embedding
            return embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
    
    async def generate_embedding_async(self, text: str) -> List[float]:
        """
        Asynchronously generate embedding
        
        Args:
            text: Input text
        
        Returns:
            Embedding vector
        """
        return await asyncio.to_thread(self.generate_embedding, text)
    
    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts in batches (with cache)
        
        Args:
            texts: List of input texts
            batch_size: Number of texts per batch
        
        Returns:
            List of embedding vectors (None for failed items)
        """
        all_embeddings: List[Optional[List[float]]] = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []
        
        # Check cache for all texts first
        for i, text in enumerate(texts):
            cache_key = self._content_hash(text)
            if cache_key in self._cache:
                all_embeddings[i] = self._cache[cache_key]
                self._cache_hits += 1
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)
                self._cache_misses += 1
        
        if uncached_texts:
            logger.info(
                f"Embedding cache: {len(texts) - len(uncached_texts)} hits, "
                f"{len(uncached_texts)} misses"
            )
        else:
            logger.info(f"Embedding cache: all {len(texts)} texts cached")
            return all_embeddings
        
        # Batch embed uncached texts
        for batch_start in range(0, len(uncached_texts), batch_size):
            batch_texts = uncached_texts[batch_start:batch_start + batch_size]
            batch_indices = uncached_indices[batch_start:batch_start + batch_size]
            
            try:
                response = self.client.embeddings.create(
                    input=batch_texts,
                    model=self.config.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
                )
                for j, item in enumerate(response.data):
                    idx = batch_indices[j]
                    embedding = item.embedding
                    all_embeddings[idx] = embedding
                    # Cache the result
                    cache_key = self._content_hash(batch_texts[j])
                    self._cache[cache_key] = embedding
                
                logger.info(
                    f"Generated embeddings for batch "
                    f"({len(batch_texts)} texts)"
                )
            except Exception as e:
                logger.error(f"Batch embedding failed: {e}")
                # Fallback to individual generation
                for j, text in enumerate(batch_texts):
                    idx = batch_indices[j]
                    try:
                        emb = self.generate_embedding(text)
                        all_embeddings[idx] = emb
                    except Exception as individual_error:
                        logger.error(
                            f"Individual embedding failed, SKIPPING chunk: "
                            f"{individual_error}"
                        )
                        # Leave as None — caller must filter out
                        all_embeddings[idx] = None
        
        return all_embeddings
    
    async def generate_embeddings_batch_async(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        Asynchronously generate embeddings in batches
        
        Args:
            texts: List of input texts
            batch_size: Number of texts per batch
        
        Returns:
            List of embedding vectors
        """
        return await asyncio.to_thread(
            self.generate_embeddings_batch,
            texts,
            batch_size
        )
