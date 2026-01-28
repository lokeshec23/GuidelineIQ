# backend/rag_pipeline/retrieval/bm25_retriever.py
"""
BM25 keyword-based retrieval
"""

from typing import List, Dict
import logging
from rank_bm25 import BM25Okapi

from rag_pipeline.models import Chunk

logger = logging.getLogger(__name__)


class BM25Retriever:
    """
    BM25 retriever for keyword-based search
    """
    
    def __init__(self):
        self.bm25 = None
        self.chunks = []
        self.tokenized_corpus = []
    
    def index_chunks(self, chunks: List[Chunk]):
        """
        Build BM25 index from chunks
        
        Args:
            chunks: List of Chunk objects
        """
        self.chunks = chunks
        
        # Tokenize corpus
        self.tokenized_corpus = [
            self._tokenize(chunk.text) for chunk in chunks
        ]
        
        # Build BM25 index
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        
        logger.info(f"Built BM25 index with {len(chunks)} chunks")
    
    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        Search using BM25
        
        Args:
            query: Search query
            top_k: Number of results to return
        
        Returns:
            List of results with chunk and score
        """
        if not self.bm25:
            logger.warning("BM25 index not built. Call index_chunks first.")
            return []
        
        # Tokenize query
        tokenized_query = self._tokenize(query)
        
        # Get BM25 scores
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top-k indices
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:top_k]
        
        # Format results
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include non-zero scores
                results.append({
                    "chunk": self.chunks[idx],
                    "score": float(scores[idx]),
                    "retrieval_method": "bm25"
                })
        
        logger.info(f"BM25 search returned {len(results)} results")
        return results
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Simple tokenization (lowercase + split)
        
        Args:
            text: Input text
        
        Returns:
            List of tokens
        """
        return text.lower().split()
