# backend/rag_pipeline/indexing/qdrant_manager.py
"""
Qdrant vector database manager for DSCR_GUIDELINES collection
"""

import asyncio
from typing import List, Dict, Optional
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)

from rag_pipeline.models import Chunk, DocumentPayload
from rag_pipeline.config import RAGConfig

logger = logging.getLogger(__name__)


class QdrantManager:
    """
    Manages Qdrant collection for mortgage guidelines
    """
    
    def __init__(self):
        self.config = RAGConfig
        self.client = None
        self.collection_name = self.config.QDRANT_COLLECTION
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Qdrant client"""
        try:
            self.client = QdrantClient(
                url=self.config.QDRANT_URL,
                api_key=self.config.QDRANT_API_KEY
            )
            logger.info(f"Connected to Qdrant at {self.config.QDRANT_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise
    
    def create_collection(self, vector_size: int = 1536, force_recreate: bool = False):
        """
        Create or recreate Qdrant collection
        
        Args:
            vector_size: Dimension of embedding vectors (1536 for text-embedding-3-large)
            force_recreate: If True, delete existing collection and recreate
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_exists = any(c.name == self.collection_name for c in collections)
            
            if collection_exists:
                if force_recreate:
                    logger.warning(f"Deleting existing collection: {self.collection_name}")
                    self.client.delete_collection(self.collection_name)
                else:
                    logger.info(f"Collection {self.collection_name} already exists")
                    return
            
            # Create collection
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )
            logger.info(
                f"Created collection {self.collection_name} "
                f"with vector size {vector_size}"
            )
        
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise
    
    def index_chunks(
        self,
        chunks: List[Chunk],
        document_payload: DocumentPayload,
        batch_size: int = 100
    ):
        """
        Index chunks to Qdrant
        
        Args:
            chunks: List of Chunk objects with embeddings
            document_payload: Document metadata
            batch_size: Number of chunks per batch
        """
        if not chunks:
            logger.warning("No chunks to index")
            return
        
        # Ensure collection exists
        vector_size = len(chunks[0].embedding) if chunks[0].embedding else 1536
        self.create_collection(vector_size=vector_size, force_recreate=False)
        
        # Prepare points
        points = []
        for chunk in chunks:
            if not chunk.embedding:
                logger.warning(f"Chunk {chunk.id} has no embedding, skipping")
                continue
            
            # Merge document metadata with chunk metadata
            payload = {
                **document_payload.to_dict(),
                "chunk_id": chunk.id,
                "chunk_type": chunk.chunk_type.value,
                "section_path": chunk.section_path,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "text": chunk.text,
                **chunk.metadata
            }
            
            point = PointStruct(
                id=hash(chunk.id) % (2**63),  # Convert string ID to int
                vector=chunk.embedding,
                payload=payload
            )
            points.append(point)
        
        # Upload in batches
        total_points = len(points)
        for i in range(0, total_points, batch_size):
            batch = points[i:i + batch_size]
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch
                )
                logger.info(
                    f"Indexed batch {i // batch_size + 1} "
                    f"({len(batch)} chunks)"
                )
            except Exception as e:
                logger.error(f"Failed to index batch: {e}")
                raise
        
        logger.info(f"Successfully indexed {total_points} chunks to Qdrant")
    
    async def index_chunks_async(
        self,
        chunks: List[Chunk],
        document_payload: DocumentPayload,
        batch_size: int = 100
    ):
        """
        Asynchronously index chunks to Qdrant
        
        Args:
            chunks: List of Chunk objects with embeddings
            document_payload: Document metadata
            batch_size: Number of chunks per batch
        """
        await asyncio.to_thread(
            self.index_chunks,
            chunks,
            document_payload,
            batch_size
        )
    
    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_conditions: Optional[Dict[str, str]] = None
    ) -> List[Dict]:
        """
        Search for similar chunks
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filter_conditions: Metadata filters (e.g., {"lender": "NQMF", "program": "DSCR"})
        
        Returns:
            List of search results with score and payload
        """
        try:
            # Build filter
            query_filter = None
            if filter_conditions:
                must_conditions = [
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                    for key, value in filter_conditions.items()
                ]
                query_filter = Filter(must=must_conditions)
            
            # Search
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=query_filter
            )
            
            # Format results
            results = []
            for hit in search_results:
                results.append({
                    "id": hit.payload.get("chunk_id"),
                    "text": hit.payload.get("text"),
                    "score": hit.score,
                    "metadata": {
                        "lender": hit.payload.get("lender"),
                        "program": hit.payload.get("program"),
                        "version": hit.payload.get("version"),
                        "section_path": hit.payload.get("section_path"),
                        "chunk_type": hit.payload.get("chunk_type"),
                        "page_start": hit.payload.get("page_start"),
                        "page_end": hit.payload.get("page_end"),
                        "filename": hit.payload.get("filename")
                    }
                })
            
            return results
        
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def search_async(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_conditions: Optional[Dict[str, str]] = None
    ) -> List[Dict]:
        """
        Asynchronously search for similar chunks
        """
        return await asyncio.to_thread(
            self.search,
            query_vector,
            top_k,
            filter_conditions
        )
    
    def delete_by_document(self, gridfs_file_id: str):
        """
        Delete all chunks for a specific document
        
        Args:
            gridfs_file_id: GridFS file ID to delete
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="gridfs_file_id",
                            match=MatchValue(value=gridfs_file_id)
                        )
                    ]
                )
            )
            logger.info(f"Deleted chunks for document: {gridfs_file_id}")
        except Exception as e:
            logger.error(f"Failed to delete document chunks: {e}")
            raise
    
    def get_collection_info(self) -> Dict:
        """
        Get collection statistics
        
        Returns:
            Dictionary with collection info
        """
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {}
