# backend/rag_pipeline/indexing/embedder.py
"""
Azure OpenAI Embedding Generator
"""

import asyncio
from typing import List
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
        self._initialize_client()
    
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
        Generate embedding for a single text
        
        Args:
            text: Input text
        
        Returns:
            Embedding vector
        """
        try:
            response = self.client.embeddings.create(
                input=[text],
                model=self.config.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
            )
            return response.data[0].embedding
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
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches
        
        Args:
            texts: List of input texts
            batch_size: Number of texts per batch
        
        Returns:
            List of embedding vectors
        """
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                response = self.client.embeddings.create(
                    input=batch,
                    model=self.config.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
                )
                embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(embeddings)
                
                logger.info(
                    f"Generated embeddings for batch {i // batch_size + 1} "
                    f"({len(batch)} texts)"
                )
            except Exception as e:
                logger.error(f"Batch embedding failed: {e}")
                # Fallback to individual generation
                for text in batch:
                    try:
                        emb = self.generate_embedding(text)
                        all_embeddings.append(emb)
                    except Exception as individual_error:
                        logger.error(f"Individual embedding failed: {individual_error}")
                        # Add zero vector as placeholder
                        all_embeddings.append([0.0] * 1536)
        
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
