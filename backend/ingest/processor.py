# backend/ingest/processor.py

import os
import json
import time
import tempfile
import asyncio
import traceback
from typing import List, Dict, Tuple
from utils.ocr import AzureOCR
from utils.llm_provider import LLMProvider
from utils.json_to_excel import dynamic_json_to_excel
from utils.progress import update_progress

from ingest.dscr_extractor import extract_dscr_parameters_safe  # ✅ Import DSCR Extractor
from ingest.rag_extractor import run_main_rag_extraction # ✅ Import RAG Extractor
from utils.logger import setup_logger
from sql_database import AsyncSessionLocal # Import session factory

logger = setup_logger(__name__)




async def process_guideline_background(
    session_id: str,
    gridfs_file_ids: List[str],  # ✅ Now accepts list of file IDs
    filenames: List[str],  # ✅ Now accepts list of filenames
    investor_id: str,
    investor: str,
    version: str,
    user_settings: dict,
    model_provider: str,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    user_id: str = None,
    username: str = "Unknown",
    effective_date: str = None,
    expiry_date: str = None,
    page_range: str = None,
    guideline_type: str = None,
    program_type: str = None,
):
    excel_path = None
    temp_pdf_paths = []  # ✅ Track all temporary PDF files
    
    # Create a DB session for this background task
    async with AsyncSessionLocal() as db:
        try:
            pages_per_chunk = user_settings.get("pages_per_chunk", 1)
            num_files = len(gridfs_file_ids)
            
            logger.info(f"RAG-Based Multi-PDF Ingestion started for session {session_id[:8]}")
            logger.info(f"Investor: {investor} | Version: {version} | Files: {num_files}")

            # Parse guideline_type into a list (comes as comma-separated string from frontend)
            guideline_types_list = None
            if guideline_type:
                guideline_types_list = [t.strip() for t in guideline_type.split(",") if t.strip()]
                logger.info(f"Selected guideline types: {guideline_types_list}")


            # Validate prompts - Use defaults if empty
            if not user_prompt.strip():
                from config import DEFAULT_INGEST_PROMPT_USER
                user_prompt = DEFAULT_INGEST_PROMPT_USER
                logger.warning("Using DEFAULT_INGEST_PROMPT_USER (user prompt was empty)")

            
            if not system_prompt.strip():
                from config import DEFAULT_INGEST_PROMPT_SYSTEM
                system_prompt = DEFAULT_INGEST_PROMPT_SYSTEM
                logger.warning("Using DEFAULT_INGEST_PROMPT_SYSTEM (system prompt was empty)")


            # === STEP 1: Process Each PDF with RAG Pipeline ===
            from rag_pipeline.pipeline import RAGPipeline
            from rag_pipeline.models import DocumentPayload, ProgramType, Chunk, ChunkType
            
            # Initialize Pipeline
            pipeline = RAGPipeline()
            
            # Concurrency control
            semaphore = asyncio.Semaphore(5)
            files_completed = 0
            files_lock = asyncio.Lock()
            
            # Track indexed documents for later cleanup/extraction
            indexed_documents = []

            async def process_single_pdf(idx: int, gridfs_id: str, filename: str):
                nonlocal files_completed
                
                async with semaphore:
                    try:
                        logger.info(f"Processing PDF {idx}/{num_files}: {filename}")
                        
                        # 1. Retrieve PDF from GridFS - Use a dedicated session for each concurrent file retrieval
                        # This prevents "Connection is busy" errors on SQL Server when processing multiple files.
                        from utils.gridfs_helper import get_pdf_from_gridfs
                        async with AsyncSessionLocal() as sub_db:
                            pdf_content = await get_pdf_from_gridfs(sub_db, gridfs_id)
                        
                        # 2. Save to temp file
                        def write_temp():
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix=f"rag_{session_id[:8]}_{idx}_") as temp_file:
                                temp_file.write(pdf_content)
                                return temp_file.name
                                
                        temp_pdf_path = await asyncio.to_thread(write_temp)
                        temp_pdf_paths.append(temp_pdf_path)
                        
                        # 3. Create Document Payload
                        # Map program_type string to Enum, default to DSCR if not specified or invalid
                        program_enum = ProgramType.DSCR
                        if program_type and program_type.upper() in [p.value for p in ProgramType]:
                            program_enum = ProgramType(program_type.upper())
                        
                        doc_payload = DocumentPayload(
                            lender=investor,
                            program=program_enum,
                            version=version,
                            filename=filename,
                            gridfs_file_id=gridfs_id,
                            effective_date=effective_date,
                            expiry_date=expiry_date
                        )
                        
                        # 4. Ingest using RAG Pipeline (Parse -> Chunk -> Embed -> Index)
                        # use_ocr_fallback=True is default and handled by pipeline
                        num_chunks = await pipeline.ingest_pdf(
                            pdf_path=temp_pdf_path,
                            document_payload=doc_payload,
                            use_ocr_fallback=True
                        )
                        
                        logger.info(f"Successfully indexed {num_chunks} chunks for {filename}")
                        
                        # Update progress
                        async with files_lock:
                            files_completed += 1
                            pct = int((files_completed / num_files) * 45)
                            update_progress(session_id, pct, f"Processed PDF {files_completed}/{num_files}: {filename}")
                        
                        return {
                            "filename": filename,
                            "gridfs_id": gridfs_id,
                            "chunks": num_chunks,
                            "status": "success"
                        }

                    except Exception as e:
                        logger.error(f"Failed to process PDF {filename}: {str(e)}", exc_info=True)
                        return {
                            "filename": filename,
                            "gridfs_id": gridfs_id,
                            "error": str(e),
                            "status": "failed"
                        }

            # Gather all tasks
            tasks = [
                process_single_pdf(idx, file_id, filename)
                for idx, (file_id, filename) in enumerate(zip(gridfs_file_ids, filenames), 1)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Check results
            failed_files = [r for r in results if r["status"] == "failed"]
            if len(failed_files) == len(results):
                 raise ValueError("All files failed to process via RAG Pipeline.")
                 
            logger.info(f"Ingestion complete. Success: {len(results) - len(failed_files)}, Failed: {len(failed_files)}")

            # Initialize LLM for downstream tasks (legacy support if needed)
            llm = initialize_llm_provider(user_settings, model_provider, model_name)

            # === STEP 5: RAG-Based Extraction (Optional - Commented for Multi-PDF) ===
            # Note: This section was designed for single PDF workflow
            # For multi-PDF, we focus on DSCR parameter extraction which uses RAG internally
            """
            update_progress(session_id, 45, "Running RAG-based extraction...")
            
            results = await run_main_rag_extraction(
                session_id=session_id,
                gridfs_file_id=gridfs_file_ids[0],  # Would need to handle multiple files
                rag_service=rag_service,
                llm=llm,
                investor=investor,
                version=version,
                user_settings=user_settings,
                text_chunks=all_text_chunks,
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            """
            results = []  # Skip general RAG extraction for multi-PDF workflow
            failed = 0

            # === STEP 5.5: Embed Extracted Rules (Optional - Skipped for Multi-PDF) ===
            # Commented out - not needed for multi-PDF DSCR extraction workflow
            """
            update_progress(session_id, 85, "Indexing extracted rules for Chat...")
            try:
                 rule_items = []
                 for i, rule in enumerate(results):
                    rule_text = f\"Category: {rule.get('category')}\\nSub-Category: {rule.get('sub_category')}\\nRule: {rule.get('guideline_summary')}\"
                    rule_items.append({
                        \"id\": f\"{gridfs_file_ids[0]}_rule_{i}\",
                        \"text\": rule_text,
                        \"metadata\": {
                            \"investor\": investor,
                            \"version\": version,
                            \"page\": \"Derived\",
                            \"filename\": filenames[0],
                            \"gridfs_file_id\": gridfs_file_ids[0],
                            \"type\": \"excel_rule\",
                            \"category\": rule.get('category'),
                            \"sub_category\": rule.get('sub_category')
                        }
                    })
                 
                 # Embed rules
                 embedded_rules = await asyncio.gather(*[process_embedding(item) for item in rule_items])
                 valid_rules = [d for d in embedded_rules if d[\"embedding\"]]
                 if valid_rules:
                    rag_service.add_documents(valid_rules)
                    print(f\"✅ RAG: Stored {len(valid_rules)} derived rules in Vector DB.\")
    
            except Exception as e:
                print(f\"⚠️ Failed to index extracted rules: {e}\")
            """


            # === STEP 6: Multi-Type Parameter Extraction (Parallel) ===
            all_preview_data = {}
            all_excel_paths = {}
            total_extracted_chunks = 0
            
            async def process_type_extraction(g_type):
                nonlocal total_extracted_chunks
                update_progress(session_id, 90, f"Extracting {g_type} Parameters...")
                try:
                    from ingest.dscr_extractor import extract_dscr_parameters_multi_pdf
                    
                    path, results = await extract_dscr_parameters_multi_pdf(
                        session_id=session_id,
                        gridfs_file_ids=gridfs_file_ids,
                        filenames=filenames,
                        llm=llm,
                        investor_id=investor_id,
                        investor=investor,
                        version=version,
                        user_settings=user_settings,
                        pipeline=pipeline,
                        guideline_types=[g_type]  # Process one type at a time
                    )
                    return g_type, path, results
                except Exception as e:
                    logger.error(f"Extraction failed for {g_type}: {e}")
                    return g_type, None, []

            # Determine extraction order: Alt Doc first, but run in parallel as requested
            # We can start Alt Doc slightly earlier or just gather all
            extraction_tasks = [process_type_extraction(t) for t in guideline_types_list]
            extraction_results = await asyncio.gather(*extraction_tasks)

            for g_type, path, results in extraction_results:
                if results:
                    all_preview_data[g_type] = results
                    all_excel_paths[g_type] = path
                    total_extracted_chunks += len(results)
            
            logger.info(f"Multi-Type Extraction Complete. Types: {list(all_preview_data.keys())}")

            # === STEP 6.5: Index Extracted Parameters for Chat (Excel Mode) ===
            all_extracted_results = []
            for g_type, results in all_preview_data.items():
                if results:
                    all_extracted_results.extend(results)
                    
            if all_extracted_results:
                update_progress(session_id, 96, "Indexing extracted DSCR rules...")
                try:
                    rule_docs = []
                    rag_provider = model_provider
                    api_key = user_settings.get(f"{model_provider}_api_key")

                    # Prepare documents for embedding
                    items_to_embed = []
                    # Ensure investor and version use underscores
                    safe_investor = investor.replace(" ", "_")
                    safe_version = version.replace(" ", "_")
                    dynamic_col_name = f"{safe_investor}_{safe_version}"
                    
                    for idx, item in enumerate(all_extracted_results):
                        # Skip items with no useful info
                        summary = item.get(dynamic_col_name, item.get('NQMF Investor DSCR', ''))
                        if not summary or summary in ["Not present", "NA", "N/A", "Error extraction", "No summary provided."]:
                            continue
                            
                        # keys in extract results: DSCR_Parameters, Variance_Category, SubCategory, PPE_Field_Type, {investor}_{version}
                        text_content = f"Parameter: {item['DSCR_Parameters']}\n" \
                                       f"Category: {item.get('Variance_Category', '')} - {item.get('SubCategory', '')}\n" \
                                       f"Rule/Guideline: {summary}"
                        
                        items_to_embed.append({
                            "id": f"{gridfs_file_ids[0]}_dscr_{idx}", # Anchor to first file
                            "text": text_content,
                            "metadata": {
                                "investor": investor,
                                "version": version,
                                "page": "DSCR Extract", 
                                "filename": "Extracted Excel Data", 
                                "gridfs_file_id": gridfs_file_ids[0],
                                "type": "excel_rule", # CRITICAL: This enables 'Excel' mode search
                                "parameter": item['DSCR_Parameters']
                            }
                        })

                    logger.info(f"📋 Found {len(all_extracted_results)} total parameters")
                    logger.info(f"📋 Prepared {len(items_to_embed)} rules for indexing (skipped NA/empty entries)")

                    # Generate embeddings in parallel batches
                    logger.info(f"🔄 Generating embeddings in batches for {len(items_to_embed)} DSCR rules...")
                    texts_to_embed = [item["text"] for item in items_to_embed]
                    embeddings = await pipeline.embedder.generate_embeddings_batch_async(texts_to_embed, batch_size=100)
                    
                    # Associate embeddings back to items and filter failures
                    valid_rules = []
                    for item, emb in zip(items_to_embed, embeddings):
                        if emb:
                            item["embedding"] = emb
                            valid_rules.append(item)
                        else:
                            logger.error(f"Failed to embed rule: {item['metadata'].get('parameter')}")
                    
                    if valid_rules:
                        # Convert to Chunk objects for Qdrant/Hybrid indexing
                        chunks_for_indexing = []
                        for r in valid_rules:
                            chunks_for_indexing.append(Chunk(
                                id=r["id"],
                                text=r["text"],
                                chunk_type=ChunkType.EXCEL_ROW,
                                section_path=f"{r['metadata'].get('investor')} > {r['metadata'].get('version')} > {r['metadata'].get('parameter')}",
                                page_start=0,
                                page_end=0,
                                metadata=r["metadata"],
                                embedding=r["embedding"]
                            ))

                        # Prepare doc payload for Qdrant indexing
                        rule_payload = DocumentPayload(
                            lender=investor,
                            program=ProgramType.DSCR,
                            version=version,
                            filename="Extracted_Rules.xlsx",
                            gridfs_file_id=gridfs_file_ids[0]
                        )
                        
                        logger.info(f"💾 Storing {len(chunks_for_indexing)} rules to Qdrant vector database...")
                        await pipeline.qdrant_manager.index_chunks_async(
                            chunks_for_indexing,
                            rule_payload,
                            batch_size=100
                        )
                        
                        # Also index for BM25 within the current pipeline instance
                        pipeline.hybrid_retriever.index_chunks(chunks_for_indexing)
                        
                        logger.info(f"✅ RAG: Stored {len(chunks_for_indexing)} derived rules in Qdrant.")
                        logger.info("✅ Excel mode search is now ENABLED for this session!")
                    else:
                        logger.warning("⚠️ No valid rules to index.")

                except Exception as idx_err:
                     logger.error(f"⚠️ Failed to index extracted rules: {idx_err}")



            # === STEP 7: Convert results to Excel ===
            update_progress(session_id, 95, "Converting results to Excel...")

            # Use the first available result for legacy download support if needed
            primary_excel_path = next(iter(all_excel_paths.values()), None)
            primary_results = next(iter(all_preview_data.values()), [])

            update_progress(session_id, 100, "Processing complete.")
            logger.info("PROCESSING COMPLETE")


            # Save preview + meta
            from utils.progress import progress_store, progress_lock
            with progress_lock:
                progress_store[session_id].update({
                    "excel_path": primary_excel_path,  # Main download (Legacy)
                    "all_excel_paths": all_excel_paths, # New multi-download
                    "preview_data": all_preview_data,  # New categorized preview
                    "filename": f"{investor.replace(' ', '_')}_{version.replace(' ', '_')}.xlsx",
                    "status": "completed",
                    "total_chunks": total_extracted_chunks,
                    "failed_chunks": 0,
                    "total_pdfs": num_files,
                })

            # Save to history after successful completion
            if user_id:
                try:
                    from history.models import save_ingest_history
                    
                    # ✅ NEW: Format pdf_files array with proper structure
                    pdf_files = [
                        {
                            "file_index": idx,
                            "filename": filename,
                            "gridfs_file_id": file_id
                        }
                        for idx, (file_id, filename) in enumerate(zip(gridfs_file_ids, filenames))
                    ]
                    
                    # Store history IDs to update progress later if needed
                    history_ids = []
                    
                    # If multiple types were selected, save them as individual records
                    types_to_save = guideline_types_list if guideline_types_list else [None]
                    
                    for g_type in types_to_save:
                        # Format version to include type as requested: AB_1_fulldoc
                        # We append it to the version field to keep investor field clean
                        # but ensure they are distinct records.
                        type_suffix = f"_{g_type.lower().replace(' ', '')}" if g_type else ""
                        individual_version = f"{version}{type_suffix}"
                        
                        # Get preview data for this specific type if available
                        individual_preview = all_preview_data.get(g_type, []) if g_type else all_preview_data
                        
                        history_id = await save_ingest_history(db, {
                            "user_id": user_id,
                            "username": username,
                            "investor": investor,
                            "version": individual_version,
                            "uploaded_file": ", ".join(filenames),
                            "extracted_file": f"{investor.replace(' ', '_')}_{individual_version.replace(' ', '_')}.xlsx",
                            "preview_data": individual_preview,
                            "effective_date": effective_date,
                            "expiry_date": expiry_date,
                            "gridfs_file_id": gridfs_file_ids[0] if gridfs_file_ids else None,
                            "pdf_files": pdf_files,
                            "page_range": page_range,
                            "guideline_type": g_type or guideline_type, # Use specific type
                            "program_type": program_type,
                        })
                        history_ids.append(history_id)
                        logger.info(f"✅ Saved to ingest history for type '{g_type}': {history_id}")

                    # Update progress with the last history ID (or could send list)
                    with progress_lock:
                        if session_id in progress_store:
                            progress_store[session_id]["history_id"] = history_ids[-1]
                            
                except Exception as hist_err:
                    logger.error(f"Failed to save history: {hist_err}")


        except Exception as e:
            error_msg = str(e)
            logger.critical(f"Critical error: {error_msg}", exc_info=True)
            update_progress(session_id, -1, f"Error: {error_msg}")


            from utils.progress import progress_store, progress_lock
            with progress_lock:
                if session_id in progress_store:
                    progress_store[session_id].update({"status": "failed", "error": error_msg})
            
            # Cleanup Excel if failed
            if excel_path and os.path.exists(excel_path):
                os.remove(excel_path)
        
        finally:
            # ✅ Clean up all temporary PDF files
            for temp_pdf_path in temp_pdf_paths:
                if temp_pdf_path and os.path.exists(temp_pdf_path):
                    try:
                        os.remove(temp_pdf_path)
                        logger.debug(f"Cleaned up temporary PDF: {temp_pdf_path}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up temporary PDF: {e}")



async def run_parallel_llm_processing(
    llm: LLMProvider,
    text_chunks: List[tuple],  # ✅ Now expects list of tuples (text, page_numbers)
    system_prompt: str,
    user_prompt: str,
    investor: str,
    version: str,
    session_id: str,
    total_chunks: int
):
    results = []
    failed_count = 0
    completed = 0
    lock = asyncio.Lock()

    async def handle_chunk(idx: int, chunk_data: tuple):
        nonlocal results, failed_count, completed
        
        # Unpack the tuple: (text, page_numbers)
        chunk_text, page_numbers = chunk_data

        # ✅ Simplified prompt - LLM doesn't need to worry about page_number anymore
        user_msg = f"""{user_prompt}

### METADATA
- Investor: {investor}
- Version: {version}

### TEXT TO PROCESS
{chunk_text}

### REMINDER: OUTPUT FORMAT
You MUST respond with a valid JSON array only. Each object must have these keys:
- "category" (string)
- "sub_category" (string)
- "guideline_summary" (string)

Start with '[' and end with ']'. No markdown, no explanations."""

        try:
            response = await asyncio.to_thread(
                llm.generate,
                system_prompt,
                user_msg
            )

            # ✅ Log LLM response for verification
            # logger.debug(f"LLM RESPONSE - Chunk {idx + 1}/{total_chunks} (Pages: {page_numbers}): {response[:100]}...") 
            
            # ✅ Parse response and automatically inject page numbers

            parsed = parse_and_clean_llm_response(response, idx + 1, page_numbers)

            if parsed:
                async with lock:
                    results.extend(parsed)
            else:
                failed_count += 1

        except Exception as e:
            failed_count += 1
            logger.error(f"Chunk {idx+1} FAILED: {e}")


        finally:
            completed += 1
            progress = 45 + int((completed / total_chunks) * 45)
            update_progress(
                session_id,
                progress,
                f"Processed {completed}/{total_chunks} chunk(s)"
            )

    await asyncio.gather(*(handle_chunk(i, chunk) for i, chunk in enumerate(text_chunks)))
    
    logger.info(f"Successfully parsed: {len(results)} rules | Failed chunks: {failed_count}")

    
    return results, failed_count


def initialize_llm_provider(user_settings: dict, provider: str, model: str) -> LLMProvider:
    import os

    params = {
        "temperature": user_settings.get("temperature", 0.5),
        "max_tokens": user_settings.get("max_output_tokens", 8192),
        "top_p": user_settings.get("top_p", 1.0),
        "stop_sequences": user_settings.get("stop_sequences", []),
    }

    if provider == "openai":
        # Prefer DB-stored user settings; fall back to .env values if missing.
        api_key = (
            user_settings.get("openai_api_key")
            or os.getenv("AZURE_OPENAI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        endpoint = (
            user_settings.get("openai_endpoint")
            or os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        deployment = (
            user_settings.get("openai_deployment")
            or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
            or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        )

        if not all([api_key, endpoint, deployment]):
            missing = [
                k for k, v in {
                    "api_key": api_key,
                    "endpoint": endpoint,
                    "deployment": deployment,
                }.items() if not v
            ]
            raise ValueError(
                f"Azure OpenAI requires api_key, endpoint, and deployment. "
                f"Missing: {missing}. Set them in the user settings or .env file."
            )

        logger.info(
            "[LLM] Azure OpenAI initializing — endpoint: %s, deployment: %s",
            endpoint,
            deployment,
        )

        return LLMProvider(
            provider="openai",
            api_key=api_key,
            model=model,
            azure_endpoint=endpoint,
            azure_deployment=deployment,
            **params,
        )

    raise ValueError(f"Unsupported provider: {provider}. Only 'openai' (Azure OpenAI) is supported.")


def parse_and_clean_llm_response(response: str, chunk_num: int, page_numbers: str) -> List[Dict]:
    """
    Parse LLM response and automatically inject page numbers from chunk metadata.
    
    Args:
        response: Raw LLM response text
        chunk_num: Chunk number (for logging)
        page_numbers: Page number(s) for this chunk (e.g., "5" or "5-7")
    
    Returns:
        List of validated dictionaries with page_number automatically injected
    """
    import re
    
    cleaned = re.sub(r'```json\s*|\s*```', '', response.strip())
    
    start = cleaned.find("[")
    end = cleaned.rfind("]")

    if start == -1 or end == -1:
        logger.warning(f"Chunk {chunk_num}: No JSON array found in response")
        return []


    try:
        data = json.loads(cleaned[start:end + 1])

        if not isinstance(data, list):
            logger.warning(f"Chunk {chunk_num}: Response is not a JSON array")
            return []

        
        valid_items = []
        
        # ✅ Only require the 3 core fields - we'll inject page_number automatically
        required_keys = {"category", "sub_category", "guideline_summary"}
        old_format_keys = {"category", "attribute", "guideline_summary"}
        
        for item in data:
            if not isinstance(item, dict):
                continue
            
            # Check if it matches new format (category, sub_category, guideline_summary)
            if required_keys.issubset(item.keys()):
                # ✅ Automatically inject page number from chunk metadata
                item["page_number"] = page_numbers
                valid_items.append(item)
            # Check if it matches old format (attribute) - normalize to sub_category
            elif old_format_keys.issubset(item.keys()):
                # Normalize to new format by renaming attribute to sub_category
                normalized_item = {
                    "category": item["category"],
                    "sub_category": item["attribute"],
                    "guideline_summary": item["guideline_summary"],
                    "page_number": page_numbers  # ✅ Auto-inject from metadata
                }
                valid_items.append(normalized_item)
        
        # logger.debug(f"Chunk {chunk_num}: Parsed {len(valid_items)} items and injected page_number '{page_numbers}'")
        return valid_items


    except json.JSONDecodeError as e:
        logger.error(f"Chunk {chunk_num}: JSON decode error - {str(e)}")
        return []
