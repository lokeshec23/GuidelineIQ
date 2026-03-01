# backend/rag_pipeline/retrieval/bm25_retriever.py
"""
BM25 keyword-based retrieval with proper tokenization
"""

import re
from typing import List, Dict, Set
import logging
from rank_bm25 import BM25Okapi

from rag_pipeline.models import Chunk

logger = logging.getLogger(__name__)

# Mortgage-domain stopwords (superset of common English stopwords)
_STOPWORDS: Set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "just", "because", "but", "and", "or", "if", "while", "about",
    "this", "that", "these", "those", "it", "its", "i", "we", "you",
    "he", "she", "they", "me", "him", "her", "us", "them", "my", "your",
    "his", "our", "their", "what", "which", "who", "whom",
}


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
        Production-grade tokenization for mortgage documents:
        - Lowercase
        - Remove punctuation (preserve hyphens in terms like '50(a)(6)')
        - Filter stopwords
        - Basic suffix stemming
        
        Args:
            text: Input text
        
        Returns:
            List of cleaned, filtered tokens
        """
        # Lowercase and split on whitespace + punctuation boundaries
        # Preserve parenthesized terms and hyphens for mortgage terms
        tokens = re.findall(r'[a-z0-9]+(?:[\-()][a-z0-9]+)*', text.lower())
        
        # Filter stopwords and very short tokens
        tokens = [t for t in tokens if t not in _STOPWORDS and len(t) > 1]
        
        # Basic suffix stemming (lightweight, no NLTK dependency)
        stemmed = []
        for token in tokens:
            if token.endswith("tion") or token.endswith("sion"):
                stemmed.append(token[:-3])  # requirement -> requir
            elif token.endswith("ment"):
                stemmed.append(token[:-4] if len(token) > 5 else token)
            elif token.endswith("ing") and len(token) > 4:
                stemmed.append(token[:-3])
            elif token.endswith("ed") and len(token) > 3:
                stemmed.append(token[:-2])
            elif token.endswith("ly") and len(token) > 3:
                stemmed.append(token[:-2])
            elif token.endswith("ies"):
                stemmed.append(token[:-3] + "y")
            elif token.endswith("es") and len(token) > 3:
                stemmed.append(token[:-2])
            elif token.endswith("s") and not token.endswith("ss") and len(token) > 2:
                stemmed.append(token[:-1])
            else:
                stemmed.append(token)
        
        return stemmed
