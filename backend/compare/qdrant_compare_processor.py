# backend/compare/qdrant_compare_processor.py
"""
Qdrant-based Excel comparison processor
Chunks Excel data, stores in Qdrant, performs hybrid search for comparison
"""

import os
import json
import tempfile
import asyncio
import traceback
import uuid
from typing import List, Dict, Optional
from utils.excel_reader import read_excel_to_json
from utils.json_to_excel import dynamic_json_to_excel
from utils.progress import update_progress
from sql_database import AsyncSessionLocal
from rag_pipeline.indexing.qdrant_manager import QdrantManager
from rag_pipeline.indexing.embedder import AzureEmbedder
from rag_pipeline.models import Chunk, ChunkType, DocumentPayload
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def process_qdrant_comparison_background(
    session_id: str,
    file1_path: str,
    file2_path: str,
    file1_name: str,
    file2_name: str,
    investor: str = "Unknown Investor",
    version: str = "v1",
    user_id: str = None,
    username: str = "Unknown",
):
    """
    Background async task to compare two Excel files using Qdrant.
    
    Process:
    1. Read both Excel files
    2. Chunk the data (each row becomes a chunk)
    3. Store chunks in Qdrant with metadata
    4. Perform hybrid search to find matches
    5. Generate comparison Excel
    """
    excel_path = None

    try:
        logger.info(f"{'='*60}")
        logger.info(f"Qdrant comparison started for session {session_id[:8]}")
        logger.info(f"Investor: {investor} | Version: {version}")
        logger.info(f"File 1: {file1_name}")
        logger.info(f"File 2: {file2_name}")
        logger.info(f"{'='*60}")

        # STEP 1 — Load Excel Data
        update_progress(session_id, 10, "Reading Excel files...")
        
        data1 = await asyncio.to_thread(read_excel_to_json, file1_path, file1_name)
        data2 = await asyncio.to_thread(read_excel_to_json, file2_path, file2_name)
        
        if not data1 or not data2:
            raise ValueError("One or both Excel files are empty")
        
        logger.info(f"✅ Loaded {len(data1)} rows from File 1, {len(data2)} rows from File 2")

        # STEP 2 — Initialize Qdrant and Embedder
        update_progress(session_id, 20, "Initializing Qdrant...")
        
        qdrant_manager = QdrantManager()
        embedder = AzureEmbedder()
        
        # STEP 3 — Chunk and Store File 1
        update_progress(session_id, 30, "Processing and storing File 1...")
        
        chunks1 = await create_excel_chunks(
            data1, 
            file1_name, 
            session_id, 
            file_label="file1",
            embedder=embedder
        )
        
        doc_payload1 = DocumentPayload(
            filename=file1_name,
            lender=file1_name.split("_")[0] if "_" in file1_name else "Unknown",
            program="Excel Comparison",
            version="v1",
            gridfs_file_id=f"{session_id}_file1"
        )
        
        await qdrant_manager.index_chunks_async(chunks1, doc_payload1)
        logger.info(f"✅ Indexed {len(chunks1)} chunks from File 1")

        # STEP 4 — Chunk and Store File 2
        update_progress(session_id, 50, "Processing and storing File 2...")
        
        chunks2 = await create_excel_chunks(
            data2, 
            file2_name, 
            session_id, 
            file_label="file2",
            embedder=embedder
        )
        
        doc_payload2 = DocumentPayload(
            filename=file2_name,
            lender=file2_name.split("_")[0] if "_" in file2_name else "Unknown",
            program="Excel Comparison",
            version="v2",
            gridfs_file_id=f"{session_id}_file2"
        )
        
        await qdrant_manager.index_chunks_async(chunks2, doc_payload2)
        logger.info(f"✅ Indexed {len(chunks2)} chunks from File 2")

        # STEP 5 — Perform Comparison via Search
        update_progress(session_id, 70, "Comparing data using hybrid search...")
        
        comparison_results = await perform_comparison_search(
            qdrant_manager,
            chunks1,
            chunks2,
            data1,
            data2,
            session_id
        )
        
        logger.info(f"✅ Generated {len(comparison_results)} comparison rows")

        # STEP 6 — Generate Excel
        update_progress(session_id, 90, "Generating comparison Excel...")
        
        excel_path = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".xlsx",
            prefix=f"qdrant_comparison_{session_id[:8]}_"
        ).name
        
        # Use header map to rename columns for Excel export
        header_map = {
            "dscr_parameters": "Parameters"
        }
        dynamic_json_to_excel(comparison_results, excel_path, header_map=header_map)
        
        update_progress(session_id, 100, "Comparison complete!")
        
        logger.info(f"{'='*60}")
        logger.info("QDRANT COMPARISON COMPLETE")
        logger.info(f"{'='*60}")

        # Save meta & preview
        from utils.progress import progress_store, progress_lock
        with progress_lock:
            progress_store[session_id].update({
                "excel_path": excel_path,
                "preview_data": comparison_results,
                "filename": (
                    f"qdrant_comparison_"
                    f"{os.path.splitext(file1_name)[0]}_vs_"
                    f"{os.path.splitext(file2_name)[0]}.xlsx"
                ),
                "file1_name": file1_name,
                "file2_name": file2_name,
                "status": "completed",
                "total_rows": len(comparison_results),
            })

        # Save to history
        if user_id:
            try:
                from history.models import save_compare_history
                async with AsyncSessionLocal() as db:
                    await save_compare_history(db, {
                        "user_id": user_id,
                        "username": username,
                        "session_id": session_id,
                        "investor": investor,
                        "version": version,
                        "uploaded_file1": file1_name,
                        "uploaded_file2": file2_name,
                        "extracted_file": (
                            f"qdrant_comparison_{os.path.splitext(file1_name)[0]}_vs_"
                            f"{os.path.splitext(file2_name)[0]}.xlsx"
                        ),
                        "preview_data": comparison_results
                    })
                logger.info(f"✅ Saved to compare history for user: {username}")
            except Exception as hist_err:
                logger.warning(f"⚠️ Failed to save history: {hist_err}")

        # STEP 7 — Cleanup Qdrant (remove temporary chunks)
        try:
            qdrant_manager.delete_by_document(f"{session_id}_file1")
            qdrant_manager.delete_by_document(f"{session_id}_file2")
            logger.info("✅ Cleaned up temporary Qdrant chunks")
        except Exception as cleanup_err:
            logger.warning(f"⚠️ Failed to cleanup Qdrant: {cleanup_err}")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Critical comparison error: {error_msg}")
        traceback.print_exc()

        update_progress(session_id, -1, f"Error: {error_msg}")

        from utils.progress import progress_store, progress_lock
        with progress_lock:
            if session_id in progress_store:
                progress_store[session_id].update({
                    "status": "failed",
                    "error": error_msg
                })

    finally:
        # Cleanup temp files
        for path in [file1_path, file2_path]:
            if path and os.path.exists(path):
                os.remove(path)
                logger.info(f"Cleaned up temp file: {path}")


async def create_excel_chunks(
    data: List[Dict],
    filename: str,
    session_id: str,
    file_label: str,
    embedder: AzureEmbedder
) -> List[Chunk]:
    """
    Convert Excel rows to Chunk objects with embeddings
    
    Args:
        data: List of row dictionaries from Excel
        filename: Original filename
        session_id: Comparison session ID
        file_label: "file1" or "file2"
        embedder: Embedder instance
    
    Returns:
        List of Chunk objects with embeddings
    """
    chunks = []
    
    for idx, row in enumerate(data):
        # Create text representation of the row
        text_parts = []
        category = row.get("category", row.get("Category", ""))
        sub_category = row.get("sub_category", row.get("Sub Category", ""))
        
        # Build searchable text
        if category:
            text_parts.append(f"Category: {category}")
        if sub_category:
            text_parts.append(f"Sub Category: {sub_category}")
        
        # Add all other fields
        for key, value in row.items():
            if key.lower() not in ["category", "sub_category", "sub category"] and value:
                text_parts.append(f"{key}: {value}")
        
        text = " | ".join(text_parts)
        
        # Create chunk
        chunk = Chunk(
            id=f"{session_id}_{file_label}_{idx}",
            text=text,
            chunk_type=ChunkType.EXCEL_ROW,
            section_path=f"{category} > {sub_category}" if category and sub_category else "",
            page_start=idx + 1,  # Row number
            page_end=idx + 1,
            metadata={
                "category": category,
                "sub_category": sub_category,
                "row_index": idx,
                "comparison_session_id": session_id,
                "file_label": file_label,
                "original_row": row  # Store original row data
            }
        )
        
        chunks.append(chunk)
    
    # Generate embeddings in batch
    logger.info(f"Generating embeddings for {len(chunks)} chunks from {file_label}...")
    texts = [chunk.text for chunk in chunks]
    embeddings = await asyncio.to_thread(embedder.generate_embeddings_batch, texts)
    
    # Assign embeddings
    for chunk, embedding in zip(chunks, embeddings):
        chunk.embedding = embedding
    
    return chunks


async def perform_comparison_search(
    qdrant_manager: QdrantManager,
    chunks1: List[Chunk],
    chunks2: List[Chunk],
    data1: List[Dict],
    data2: List[Dict],
    session_id: str
) -> List[Dict]:
    """
    Perform comparison by searching for matches between chunks
    
    For each chunk in file1, search for the best match in file2
    """
    comparison_results = []
    matched_indices_file2 = set()
    
    # Search for matches for each chunk in file1
    for chunk1 in chunks1:
        # Search in Qdrant for similar chunks from file2
        filter_conditions = {
            "comparison_session_id": session_id,
            "file_label": "file2"
        }
        
        search_results = await qdrant_manager.search_async(
            query_vector=chunk1.embedding,
            top_k=1,  # Get best match
            filter_conditions=filter_conditions
        )
        
        # Get original row data
        row1 = chunk1.metadata.get("original_row", {})
        
        if search_results and search_results[0]["score"] > 0.7:  # Similarity threshold
            # Found a match
            best_match = search_results[0]
            match_chunk_id = best_match["id"]
            
            # Find the corresponding chunk2
            chunk2 = next((c for c in chunks2 if c.id == match_chunk_id), None)
            
            if chunk2:
                row2 = chunk2.metadata.get("original_row", {})
                matched_indices_file2.add(chunk2.metadata.get("row_index"))
                
                comparison_results.append({
                    "dscr_parameters": row1.get("DSCR_Parameters", row1.get("DSCR Parameters", "")),
                    "category": row1.get("category", row1.get("Category", "")),
                    "sub_category": row1.get("sub_category", row1.get("Sub Category", "")),
                    "guideline_1": json.dumps(row1, ensure_ascii=False),
                    "guideline_2": json.dumps(row2, ensure_ascii=False),
                    "comparison_notes": f"Match found (similarity: {best_match['score']:.2f})",
                    "match_score": best_match['score']
                })
        else:
            # No match found
            comparison_results.append({
                "dscr_parameters": row1.get("DSCR_Parameters", row1.get("DSCR Parameters", "")),
                "category": row1.get("category", row1.get("Category", "")),
                "sub_category": row1.get("sub_category", row1.get("Sub Category", "")),
                "guideline_1": json.dumps(row1, ensure_ascii=False),
                "guideline_2": "Not present in File 2",
                "comparison_notes": "No matching row found in File 2",
                "match_score": 0.0
            })
    
    # Add unmatched rows from file2
    for chunk2 in chunks2:
        row_index = chunk2.metadata.get("row_index")
        if row_index not in matched_indices_file2:
            row2 = chunk2.metadata.get("original_row", {})
            comparison_results.append({
                "dscr_parameters": row2.get("DSCR_Parameters", row2.get("DSCR Parameters", "")),
                "category": row2.get("category", row2.get("Category", "")),
                "sub_category": row2.get("sub_category", row2.get("Sub Category", "")),
                "guideline_1": "Not present in File 1",
                "guideline_2": json.dumps(row2, ensure_ascii=False),
                "comparison_notes": "Only present in File 2",
                "match_score": 0.0
            })
    
    return comparison_results
