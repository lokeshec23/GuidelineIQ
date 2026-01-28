# backend/rag_pipeline/retrieval/hybrid_retriever.py
"""
Hybrid retrieval combining BM25 and vector search
"""

import asyncio
from typing import List, Dict, Optional
import logging

from rag_pipeline.models import Chunk, RetrievalResult
from rag_pipeline.config import RAGConfig
from rag_pipeline.retrieval.bm25_retriever import BM25Retriever
from rag_pipeline.indexing.qdrant_manager import QdrantManager
from rag_pipeline.indexing.embedder import AzureEmbedder

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Hybrid retrieval using Reciprocal Rank Fusion (RRF)
    Combines BM25 (keyword) and vector (semantic) search
    """
    
    def __init__(self):
        self.config = RAGConfig
        self.bm25_retriever = BM25Retriever()
        self.qdrant_manager = QdrantManager()
        self.embedder = AzureEmbedder()
    
    def index_chunks(self, chunks: List[Chunk]):
        """
        Index chunks for both BM25 and vector search
        
        Args:
            chunks: List of Chunk objects (must have embeddings)
        """
        # Index for BM25
        self.bm25_retriever.index_chunks(chunks)
        
        logger.info("Chunks indexed for hybrid retrieval")
    
    async def search(
        self,
        query: str,
        top_k: int = None,
        filter_conditions: Optional[Dict[str, str]] = None,
        prefer_tables: bool = False
    ) -> List[RetrievalResult]:
        """
        Hybrid search with RRF fusion
        
        Args:
            query: Search query
            top_k: Number of final results (default from config)
            filter_conditions: Metadata filters for vector search
            prefer_tables: Boost table chunks in results
        
        Returns:
            List of RetrievalResult objects
        """
        if top_k is None:
            top_k = self.config.TOP_K_FINAL
        
        # Generate query embedding
        query_vector = await self.embedder.generate_embedding_async(query)
        
        # BM25 search
        bm25_results = self.bm25_retriever.search(
            query=query,
            top_k=self.config.TOP_K_BM25
        )
        
        # Vector search
        vector_results = await self.qdrant_manager.search_async(
            query_vector=query_vector,
            top_k=self.config.TOP_K_VECTOR,
            filter_conditions=filter_conditions
        )
        
        # Convert vector results to common format
        vector_results_formatted = [
            {
                "chunk": self._dict_to_chunk(r),
                "score": r["score"],
                "retrieval_method": "vector"
            }
            for r in vector_results
        ]
        
        # Fuse results using RRF
        fused_results = self._reciprocal_rank_fusion(
            bm25_results=bm25_results,
            vector_results=vector_results_formatted,
            top_k=top_k,
            prefer_tables=prefer_tables
        )
        
        logger.info(
            f"Hybrid search returned {len(fused_results)} results "
            f"(BM25: {len(bm25_results)}, Vector: {len(vector_results)})"
        )
        
        return fused_results
    
    def _reciprocal_rank_fusion(
        self,
        bm25_results: List[Dict],
        vector_results: List[Dict],
        top_k: int,
        prefer_tables: bool = False,
        k: int = 60
    ) -> List[RetrievalResult]:
        """
        Reciprocal Rank Fusion algorithm
        
        Args:
            bm25_results: BM25 search results
            vector_results: Vector search results
            top_k: Number of results to return
            prefer_tables: Boost table chunks
            k: RRF constant (default 60)
        
        Returns:
            Fused and ranked results
        """
        # Calculate RRF scores
        rrf_scores = {}
        
        # BM25 contribution
        for rank, result in enumerate(bm25_results, start=1):
            chunk_id = result["chunk"].id
            score = self.config.BM25_WEIGHT / (k + rank)
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + score
        
        # Vector contribution
        for rank, result in enumerate(vector_results, start=1):
            chunk_id = result["chunk"].id
            score = self.config.VECTOR_WEIGHT / (k + rank)
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + score
        
        # Collect all unique chunks
        all_chunks = {}
        for result in bm25_results + vector_results:
            chunk = result["chunk"]
            if chunk.id not in all_chunks:
                all_chunks[chunk.id] = chunk
        
        # Apply table preference boost
        if prefer_tables:
            for chunk_id, chunk in all_chunks.items():
                if chunk.chunk_type.value == "table":
                    rrf_scores[chunk_id] *= 1.5  # 50% boost for tables
        
        # Sort by RRF score
        sorted_chunk_ids = sorted(
            rrf_scores.keys(),
            key=lambda cid: rrf_scores[cid],
            reverse=True
        )[:top_k]
        
        # Create RetrievalResult objects
        results = [
            RetrievalResult(
                chunk=all_chunks[chunk_id],
                score=rrf_scores[chunk_id],
                retrieval_method="hybrid"
            )
            for chunk_id in sorted_chunk_ids
        ]
        
        return results
    
    def _dict_to_chunk(self, result_dict: Dict) -> Chunk:
        """
        Convert Qdrant result dict to Chunk object
        
        Args:
            result_dict: Result dictionary from Qdrant
        
        Returns:
            Chunk object
        """
        from rag_pipeline.models import ChunkType
        
        metadata = result_dict.get("metadata", {})
        
        return Chunk(
            id=result_dict.get("id", ""),
            text=result_dict.get("text", ""),
            chunk_type=ChunkType(metadata.get("chunk_type", "narrative")),
            section_path=metadata.get("section_path", "General"),
            page_start=metadata.get("page_start", 0),
            page_end=metadata.get("page_end", 0),
            metadata=metadata
        )
    
    def should_prefer_tables(self, query: str) -> bool:
        """
        Determine if query suggests table/matrix data
        
        Args:
            query: Search query
        
        Returns:
            True if query suggests tables
        """
        query_lower = query.lower()
        return any(
            keyword in query_lower
            for keyword in self.config.TABLE_KEYWORDS
        )
