# backend/rag_pipeline/pipeline.py
"""
Main RAG Pipeline Orchestrator
Integrates with existing DSCR_GUIDELINES workflow
"""

import asyncio
from typing import List, Dict, Tuple
import logging
from pathlib import Path

from rag_pipeline.models import (
    Chunk, DocumentPayload, ProgramType,
    ExtractionResult, VerificationResult
)
from rag_pipeline.config import RAGConfig
from rag_pipeline.ingestion.pdf_parser import PDFParser
from rag_pipeline.ingestion.chunker import SectionAwareChunker
from rag_pipeline.indexing.embedder import AzureEmbedder
from rag_pipeline.indexing.qdrant_manager import QdrantManager
from rag_pipeline.retrieval.hybrid_retriever import HybridRetriever
from rag_pipeline.extraction.llm_extractor import LLMExtractor
from rag_pipeline.extraction.llm_verifier import LLMVerifier

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Production-grade RAG pipeline for mortgage guideline extraction
    """
    
    def __init__(self):
        self.config = RAGConfig
        self.pdf_parser = PDFParser()
        self.chunker = SectionAwareChunker()
        self.embedder = AzureEmbedder()
        self.qdrant_manager = QdrantManager()
        self.hybrid_retriever = HybridRetriever()
        self.extractor = LLMExtractor()
        self.verifier = LLMVerifier()
    
    async def ingest_pdf(
        self,
        pdf_path: str,
        document_payload: DocumentPayload,
        use_ocr_fallback: bool = True
    ) -> int:
        """
        Ingest PDF: Parse → Chunk → Embed → Index to Qdrant
        
        Args:
            pdf_path: Path to PDF file
            document_payload: Document metadata
            use_ocr_fallback: Whether to use OCR if pdfplumber fails
        
        Returns:
            Number of chunks indexed
        """
        logger.info(f"Starting ingestion for: {pdf_path}")
        
        # Step 1: Parse PDF
        logger.info("Step 1/4: Parsing PDF...")
        pages_data = self.pdf_parser.parse_pdf(pdf_path, use_ocr_fallback)
        
        # Step 2: Create chunks
        logger.info("Step 2/4: Creating chunks...")
        document_id = document_payload.gridfs_file_id or Path(pdf_path).stem
        chunks = self.chunker.chunk_pages(pages_data, document_id)
        
        if not chunks:
            raise ValueError("No chunks created from PDF")
        
        # Step 3: Generate embeddings
        logger.info(f"Step 3/4: Generating embeddings for {len(chunks)} chunks...")
        texts = [chunk.text for chunk in chunks]
        embeddings = await self.embedder.generate_embeddings_batch_async(
            texts,
            batch_size=100
        )
        
        # Attach embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
        
        # Step 4: Index to Qdrant
        logger.info("Step 4/4: Indexing to Qdrant...")
        await self.qdrant_manager.index_chunks_async(
            chunks,
            document_payload,
            batch_size=100
        )
        
        # Also index for BM25
        self.hybrid_retriever.index_chunks(chunks)
        
        logger.info(f"Ingestion complete: {len(chunks)} chunks indexed")
        return len(chunks)
    
    async def extract_parameters(
        self,
        parameters_config: List[Dict],
        filter_conditions: Dict[str, str],
        enable_verification: bool = True
    ) -> List[Dict]:
        """
        Extract parameters using hybrid retrieval + LLM
        
        Args:
            parameters_config: List of parameter configurations from DSCR_GUIDELINES
            filter_conditions: Metadata filters (lender, program, version)
            enable_verification: Whether to run verification pass
        
        Returns:
            List of extraction results
        """
        logger.info(f"Extracting {len(parameters_config)} parameters...")
        
        results = []
        
        # Process parameters concurrently (with semaphore for rate limiting)
        semaphore = asyncio.Semaphore(5)
        
        async def extract_one(param_config: Dict) -> Dict:
            async with semaphore:
                parameter = param_config["parameter"]
                
                try:
                    # Build query
                    query = self._build_query(param_config)
                    
                    # Determine if we should prefer tables
                    prefer_tables = self.hybrid_retriever.should_prefer_tables(query)
                    
                    # Retrieve evidence
                    evidence_chunks = await self.hybrid_retriever.search(
                        query=query,
                        top_k=5,
                        filter_conditions=filter_conditions,
                        prefer_tables=prefer_tables
                    )
                    
                    # Extract
                    extraction_result = await self.extractor.extract(
                        parameter=parameter,
                        evidence_chunks=evidence_chunks,
                        context={
                            "category": param_config.get("category"),
                            "subcategory": param_config.get("subcategory"),
                            "ppe_field": param_config.get("ppe_field")
                        }
                    )
                    
                    # Verify (optional)
                    verification_result = None
                    if enable_verification and not extraction_result.needs_clarification:
                        verification_result = await self.verifier.verify(
                            extraction_result,
                            evidence_chunks
                        )
                        
                        # Apply fix if verification failed
                        if not verification_result.verified and verification_result.suggested_fix:
                            logger.info(f"Applying verification fix for {parameter}")
                            extraction_result.value = verification_result.suggested_fix
                    
                    # Format result
                    return {
                        "DSCR_Parameters": parameter,
                        "Variance_Category": param_config.get("category", "General"),
                        "SubCategory": param_config.get("subcategory", "General"),
                        "PPE_Field_Type": param_config.get("ppe_field", "Text"),
                        "NQMF Investor DSCR": extraction_result.value,
                        "Classification": (
                            "Clarification Required" if extraction_result.needs_clarification
                            else "Extracted"
                        ),
                        "Notes": self._format_citations(extraction_result.citations),
                        "_verification": verification_result.to_dict() if verification_result else None
                    }
                
                except Exception as e:
                    logger.error(f"Extraction failed for {parameter}: {e}")
                    return {
                        "DSCR_Parameters": parameter,
                        "Variance_Category": param_config.get("category", "General"),
                        "SubCategory": param_config.get("subcategory", "General"),
                        "PPE_Field_Type": param_config.get("ppe_field", "Text"),
                        "NQMF Investor DSCR": "Error during extraction",
                        "Classification": "Clarification Required",
                        "Notes": f"Error: {str(e)}"
                    }
        
        # Execute all extractions
        tasks = [extract_one(config) for config in parameters_config]
        results = await asyncio.gather(*tasks)
        
        logger.info(f"Extraction complete: {len(results)} parameters processed")
        return results
    
    def _build_query(self, param_config: Dict) -> str:
        """
        Build search query from parameter configuration
        
        Args:
            param_config: Parameter configuration dict
        
        Returns:
            Search query string
        """
        parameter = param_config["parameter"]
        aliases = param_config.get("aliases", [])
        
        # Combine parameter with aliases
        if aliases:
            query = f"{parameter} {' '.join(aliases)}"
        else:
            query = f"What are the requirements for {parameter}?"
        
        return query
    
    def _format_citations(self, citations: List) -> str:
        """
        Format citations for Excel Notes column
        
        Args:
            citations: List of Citation objects
        
        Returns:
            Formatted citation string
        """
        if not citations:
            return ""
        
        citation_strs = []
        for citation in citations:
            source = citation.source_file or "Document"
            citation_strs.append(
                f"Page {citation.page} ({source}): \"{citation.excerpt[:100]}...\""
            )
        
        return " | ".join(citation_strs)
    
    async def process_dscr_guidelines(
        self,
        pdf_path: str,
        lender: str,
        program: str,
        version: str,
        gridfs_file_id: str = None,
        use_ocr_fallback: bool = True,
        enable_verification: bool = True
    ) -> Tuple[List[Dict], int]:
        """
        Complete pipeline: Ingest PDF + Extract DSCR parameters
        
        Args:
            pdf_path: Path to PDF file
            lender: Lender name
            program: Program type (DSCR, FULL_ALT, etc.)
            version: Version identifier
            gridfs_file_id: Optional GridFS file ID
            use_ocr_fallback: Whether to use OCR fallback
            enable_verification: Whether to run verification pass
        
        Returns:
            Tuple of (extraction_results, num_chunks_indexed)
        """
        logger.info(f"Processing DSCR guidelines for {lender} - {program} v{version}")
        
        # Create document payload
        document_payload = DocumentPayload(
            lender=lender,
            program=ProgramType(program) if program in [p.value for p in ProgramType] else ProgramType.GENERAL,
            version=version,
            filename=Path(pdf_path).name,
            gridfs_file_id=gridfs_file_id
        )
        
        # Ingest PDF
        num_chunks = await self.ingest_pdf(
            pdf_path,
            document_payload,
            use_ocr_fallback
        )
        
        # Load DSCR_GUIDELINES configuration
        from ingest.dscr_config import DSCR_GUIDELINES
        
        # Extract parameters
        filter_conditions = {
            "lender": lender,
            "program": program,
            "version": version
        }
        
        extraction_results = await self.extract_parameters(
            parameters_config=DSCR_GUIDELINES,
            filter_conditions=filter_conditions,
            enable_verification=enable_verification
        )
        
        logger.info(f"Pipeline complete: {num_chunks} chunks, {len(extraction_results)} parameters")
        return extraction_results, num_chunks
