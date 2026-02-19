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
        
        # Attach embeddings to chunks (skip any that failed)
        valid_chunks = []
        for chunk, embedding in zip(chunks, embeddings):
            if embedding is not None:
                chunk.embedding = embedding
                valid_chunks.append(chunk)
            else:
                logger.warning(f"Skipping chunk {chunk.id} — embedding failed")
        
        if not valid_chunks:
            raise ValueError("All embedding generations failed")
        
        chunks = valid_chunks
        
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
        
        async def extract_one(param_config: Dict) -> List[Dict]:
            async with semaphore:
                parameter = param_config["parameter"]
                
                try:
                    # Build query
                    query = self._build_query(param_config)
                    
                    # Determine if we should prefer tables
                    prefer_tables = self.hybrid_retriever.should_prefer_tables(query)
                    
                    # Retrieve evidence with comprehensive recall
                    evidence_chunks = await self.hybrid_retriever.search(
                        query=query,
                        top_k=self.config.TOP_K_COMPREHENSIVE,  # Use much larger context
                        filter_conditions=filter_conditions,
                        prefer_tables=prefer_tables
                    )
                    
                    # Extract using NQMF-specific prompt format (with classification)
                    extraction_result = await self.extractor.extract_nqmf(
                        parameter=parameter,
                        evidence_chunks=evidence_chunks,
                        context={
                            "category": param_config.get("category"),
                            "subcategory": param_config.get("subcategory"),
                            "ppe_field": param_config.get("ppe_field")
                        }
                    )
                    
                    # Verification pass (NQMF-aware)
                    verification_result = None
                    if enable_verification:
                        verification_result = await self.verifier.verify_nqmf(
                            extraction_result,
                            evidence_chunks
                        )
                        
                        # Auto-correct if verification found hallucinations
                        if (verification_result 
                            and not verification_result.verified 
                            and verification_result.suggested_fix):
                            logger.warning(
                                f"Verification auto-correcting '{parameter}': "
                                f"{', '.join(verification_result.issues[:2])}"
                            )
                    
                    # Generate rows based on classification
                    rows = []
                    
                    # Create HARD row if hard bullets exist
                    if extraction_result.hard_value:
                        rows.append({
                            "DSCR_Parameters": parameter,
                            "Variance_Category": param_config.get("category", "General"),
                            "SubCategory": param_config.get("subcategory", "General"),
                            "PPE_Field_Type": param_config.get("ppe_field", "Text"),
                            "Hard_Soft_Classification": "HARD",
                            "NQMF Investor DSCR": extraction_result.hard_value,
                            "Classification": "Extracted",
                            "Notes": self._format_citations(extraction_result.hard_citations),
                            "_verification": verification_result.to_dict() if verification_result else None
                        })
                    
                    # Create SOFT row if soft bullets exist
                    if extraction_result.soft_value:
                        rows.append({
                            "DSCR_Parameters": parameter,
                            "Variance_Category": param_config.get("category", "General"),
                            "SubCategory": param_config.get("subcategory", "General"),
                            "PPE_Field_Type": param_config.get("ppe_field", "Text"),
                            "Hard_Soft_Classification": "SOFT",
                            "NQMF Investor DSCR": extraction_result.soft_value,
                            "Classification": "Extracted",
                            "Notes": self._format_citations(extraction_result.soft_citations),
                            "_verification": verification_result.to_dict() if verification_result else None
                        })
                    
                    # If no bullets at all, create single "NA" row
                    if not rows:
                        rows.append({
                            "DSCR_Parameters": parameter,
                            "Variance_Category": param_config.get("category", "General"),
                            "SubCategory": param_config.get("subcategory", "General"),
                            "PPE_Field_Type": param_config.get("ppe_field", "Text"),
                            "Hard_Soft_Classification": "",
                            "NQMF Investor DSCR": "NA",
                            "Classification": "Not Found",
                            "Notes": "",
                            "_verification": None
                        })
                    
                    return rows
                
                except Exception as e:
                    logger.error(f"Extraction failed for {parameter}: {e}")
                    return [{
                        "DSCR_Parameters": parameter,
                        "Variance_Category": param_config.get("category", "General"),
                        "SubCategory": param_config.get("subcategory", "General"),
                        "PPE_Field_Type": param_config.get("ppe_field", "Text"),
                        "Hard_Soft_Classification": "",
                        "NQMF Investor DSCR": "Error during extraction",
                        "Classification": "Clarification Required",
                        "Notes": f"Error: {str(e)}",
                        "_verification": None
                    }]
        
        
        # Execute all extractions
        tasks = [extract_one(config) for config in parameters_config]
        extraction_results = await asyncio.gather(*tasks)
        
        # Flatten list of lists (each parameter can return multiple rows)
        results = []
        for row_list in extraction_results:
            results.extend(row_list)
        
        logger.info(
            f"Extraction complete: {len(parameters_config)} parameters processed, "
            f"{len(results)} total rows generated"
        )
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
        Complete pipeline: Ingest PDF + Extract DSCR parameters (from DB)
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
        
        # Load DSCR parameters from database
        from sql_database import AsyncSessionLocal
        from models.sql_models import DSCRParameter
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(DSCRParameter))
            db_params = result.scalars().all()
            
            # Convert to list of dicts for the extractor
            parameters_config = [
                {
                    "parameter": p.parameter,
                    "category": p.category,
                    "subcategory": p.subcategory,
                    "ppe_field": p.ppe_field
                }
                for p in db_params
            ]

        # Fallback to static config if DB is empty (should not happen if seeded)
        if not parameters_config:
            logger.warning("No DSCR parameters found in DB, falling back to static config")
            from ingest.dscr_config import DSCR_GUIDELINES
            parameters_config = DSCR_GUIDELINES
        
        # Extract parameters
        filter_conditions = {
            "lender": lender,
            "program": program,
            "version": version
        }
        
        extraction_results = await self.extract_parameters(
            parameters_config=parameters_config,
            filter_conditions=filter_conditions,
            enable_verification=enable_verification
        )
        
        logger.info(f"Pipeline complete: {num_chunks} chunks, {len(extraction_results)} parameters")
        return extraction_results, num_chunks
