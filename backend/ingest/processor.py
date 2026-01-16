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
from chat.rag_service import RAGService  # ✅ Import RAG Service
from ingest.dscr_extractor import extract_dscr_parameters_safe  # ✅ Import DSCR Extractor
from ingest.rag_extractor import run_main_rag_extraction # ✅ Import RAG Extractor

rag_service = RAGService()  # ✅ Initialize RAG Service

async def process_guideline_background(
    session_id: str,
    gridfs_file_ids: List[str],  # ✅ Now accepts list of file IDs
    filenames: List[str],  # ✅ Now accepts list of filenames
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
    
    try:
        pages_per_chunk = user_settings.get("pages_per_chunk", 1)
        num_files = len(gridfs_file_ids)
        
        print(f"\n{'='*60}")
        print(f"RAG-Based Multi-PDF Ingestion started for session {session_id[:8]}")
        print(f"Investor: {investor} | Version: {version}")
        print(f"Number of PDFs: {num_files}")
        print(f"Files: {', '.join(filenames)}")
        print(f"Model: {model_provider}/{model_name}")
        print(f"Pages per chunk: {pages_per_chunk}")
        print(f"Effective Date: {effective_date}")
        print(f"{'='*60}\n")

        # Validate prompts - Use defaults if empty
        if not user_prompt.strip():
            from config import DEFAULT_INGEST_PROMPT_USER
            user_prompt = DEFAULT_INGEST_PROMPT_USER
            print("⚠️ Using DEFAULT_INGEST_PROMPT_USER (user prompt was empty)")
        
        if not system_prompt.strip():
            from config import DEFAULT_INGEST_PROMPT_SYSTEM
            system_prompt = DEFAULT_INGEST_PROMPT_SYSTEM
            print("⚠️ Using DEFAULT_INGEST_PROMPT_SYSTEM (system prompt was empty)")

        # === STEP 1-3: Process Each PDF (Retrieve, OCR, Embed) ===
        all_text_chunks = []
        
        for idx, (file_id, filename) in enumerate(zip(gridfs_file_ids, filenames), 1):
            print(f"\n{'='*60}")
            print(f"📄 Processing PDF {idx}/{num_files}: {filename}")
            print(f"{'='*60}")
            
            # Retrieve PDF from GridFS
            update_progress(session_id, 2 + (idx-1)*20, f"Retrieving PDF {idx}/{num_files} from storage...")
            from utils.gridfs_helper import get_pdf_from_gridfs
            
            pdf_content = await get_pdf_from_gridfs(file_id)
            
            # Create temporary file for OCR processing
            temp_pdf_path = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".pdf",
                prefix=f"ocr_{session_id[:8]}_{idx}_"
            ).name
            temp_pdf_paths.append(temp_pdf_path)
            
            with open(temp_pdf_path, "wb") as f:
                f.write(pdf_content)
            
            print(f"✅ Created temporary PDF for OCR: {temp_pdf_path}")

            # OCR Extraction
            update_progress(session_id, 5 + (idx-1)*20, f"Extracting text from PDF {idx}/{num_files}...")
            ocr_client = AzureOCR()
            text_chunks = ocr_client.analyze_doc_page_by_page(
                temp_pdf_path, 
                pages_per_chunk=pages_per_chunk, 
                page_range=page_range
            )
            num_chunks = len(text_chunks)
            if num_chunks == 0:
                print(f"⚠️ OCR failed for {filename}, skipping...")
                continue

            update_progress(session_id, 15 + (idx-1)*20, f"OCR complete for PDF {idx}. Created {num_chunks} chunk(s).")
            all_text_chunks.extend(text_chunks)
            
            # Generate Embeddings for this PDF's chunks
            update_progress(session_id, 20 + (idx-1)*20, f"Generating embeddings for PDF {idx}...")
            try:
                items_to_embed = []
                
                for i, chunk_tuple in enumerate(text_chunks):
                    text, pages = chunk_tuple
                    items_to_embed.append({
                        "id": f"{file_id}_chunk_{i}",
                        "text": text,
                        "metadata": {
                            "investor": investor,
                            "version": version,
                            "page": pages,
                            "filename": filename,
                            "gridfs_file_id": file_id,
                            "type": "pdf_chunk",
                            "file_index": idx
                        }
                    })

                # Determine provider and key
                rag_provider = model_provider
                api_key = user_settings.get(f"{model_provider}_api_key")
                
                # Generate Embeddings concurrently with progress tracking
                print(f"⚡ Generating embeddings for {len(items_to_embed)} chunks from PDF {idx}...")
                
                # Track completed embeddings for progress updates
                completed_embeddings = 0
                total_embeddings = len(items_to_embed)
                embedding_lock = asyncio.Lock()
                
                async def process_embedding(item, item_idx):
                    nonlocal completed_embeddings
                    
                    emb = await rag_service.get_embedding(
                        item["text"], 
                        rag_provider, 
                        api_key,
                        azure_endpoint=user_settings.get("openai_endpoint"),
                        azure_embedding_deployment=user_settings.get("openai_embedding_deployment", "embedding-model")
                    )
                    item["embedding"] = emb
                    
                    # Update progress periodically (every 5 chunks or at completion)
                    async with embedding_lock:
                        completed_embeddings += 1
                        if completed_embeddings % 5 == 0 or completed_embeddings == total_embeddings:
                            progress_pct = 20 + (idx-1)*20 + int((completed_embeddings / total_embeddings) * 15)
                            update_progress(
                                session_id, 
                                progress_pct, 
                                f"Embedding PDF {idx}: {completed_embeddings}/{total_embeddings} chunks"
                            )
                    
                    return item

                embedded_items = await asyncio.gather(*[process_embedding(item, i) for i, item in enumerate(items_to_embed)])
                valid_docs = [d for d in embedded_items if d["embedding"]]
                
                if valid_docs:
                    # Use async version to prevent event loop blocking
                    await rag_service.add_documents_async(valid_docs, batch_size=200)
                    print(f"✅ RAG: Stored {len(valid_docs)} chunks from PDF {idx} in Vector DB.")

            except Exception as rag_err:
                print(f"⚠️ RAG Embedding Failed for PDF {idx}: {rag_err}")
                traceback.print_exc()
        
        if not all_text_chunks:
            raise ValueError("OCR process failed to extract text from any document.")

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


        # === STEP 6: DSCR Parameter Extraction (Multi-PDF Aggregation) ===
        update_progress(session_id, 90, f"Extracting DSCR Parameters from {num_files} PDF(s)...")
        try:
            from ingest.dscr_extractor import extract_dscr_parameters_multi_pdf
            
            dscr_excel_path, dscr_results = await extract_dscr_parameters_multi_pdf(
                session_id=session_id,
                gridfs_file_ids=gridfs_file_ids,
                filenames=filenames,
                rag_service=rag_service,
                llm=llm,
                investor=investor,
                version=version,
                user_settings=user_settings
            )
            print(f"✅ Multi-PDF DSCR Extraction Complete. File saved at: {dscr_excel_path}")
        except Exception as dscr_err:
            print(f"⚠️ DSCR Extraction Failed: {dscr_err}")
            traceback.print_exc()

        # === STEP 7: Convert results to Excel ===
        update_progress(session_id, 95, "Converting results to Excel...")

        excel_path = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".xlsx",
            prefix=f"extraction_{session_id[:8]}_"
        ).name

        dynamic_json_to_excel(results, excel_path)

        update_progress(session_id, 100, "Processing complete.")
        print(f"{'='*60}\nPROCESSING COMPLETE\n{'='*60}")

        # Save preview + meta
        from utils.progress import progress_store, progress_lock
        with progress_lock:
            progress_store[session_id].update({
                "excel_path": dscr_excel_path,  # Use DSCR excel as main download
                "preview_data": dscr_results,  # Use DSCR results for preview
                "filename": f"DSCR_MultiPDF_{investor}_{version}.xlsx",
                "status": "completed",
                "total_chunks": len(all_text_chunks),
                "failed_chunks": failed,
                "total_pdfs": num_files,
            })

        # Save to history after successful completion
        if user_id:
            try:
                from history.models import save_ingest_history
                # ✅ UPDATED: Store all GridFS IDs and filenames for multi-PDF
                history_id = await save_ingest_history({
                    "user_id": user_id,
                    "username": username,
                    "investor": investor,
                    "version": version,
                    "uploaded_file": ", ".join(filenames),  # Store all filenames
                    "extracted_file": f"DSCR_MultiPDF_{investor}_{version}.xlsx",
                    "preview_data": dscr_results,
                    "effective_date": effective_date,
                    "expiry_date": expiry_date,
                    "gridfs_file_id": gridfs_file_ids[0] if gridfs_file_ids else None,  # Primary file ID
                    "gridfs_file_ids": gridfs_file_ids,  # ✅ Store all file IDs
                    "page_range": page_range,
                    "guideline_type": guideline_type,
                    "program_type": program_type,
                    "total_pdfs": num_files
                })
                print(f"✅ Saved to ingest history for user: {username}")
                
                # Update progress with history ID
                with progress_lock:
                    if session_id in progress_store:
                        progress_store[session_id]["history_id"] = history_id
                        
            except Exception as hist_err:
                print(f"⚠️ Failed to save history: {hist_err}")

    except Exception as e:
        error_msg = str(e)
        print(f"\nCritical error: {error_msg}\n")
        traceback.print_exc()
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
                    print(f"🧹 Cleaned up temporary PDF: {temp_pdf_path}")
                except Exception as e:
                    print(f"⚠️ Failed to clean up temporary PDF: {e}")


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
            print(f"\n{'='*60}")
            print(f"📝 LLM RESPONSE - Chunk {idx + 1}/{total_chunks} (Pages: {page_numbers})")
            print(f"{'='*60}")
            print(response)
            print(f"{'='*60}\n")

            # ✅ Parse response and automatically inject page numbers
            parsed = parse_and_clean_llm_response(response, idx + 1, page_numbers)

            if parsed:
                async with lock:
                    results.extend(parsed)
            else:
                failed_count += 1

        except Exception as e:
            failed_count += 1
            print(f"Chunk {idx+1} FAILED: {e}")

        finally:
            completed += 1
            progress = 45 + int((completed / total_chunks) * 45)
            update_progress(
                session_id,
                progress,
                f"Processed {completed}/{total_chunks} chunk(s)"
            )

    await asyncio.gather(*(handle_chunk(i, chunk) for i, chunk in enumerate(text_chunks)))
    
    print(f"\n✅ Successfully parsed: {len(results)} rules")
    print(f"❌ Failed chunks: {failed_count}")
    
    return results, failed_count


def initialize_llm_provider(user_settings: dict, provider: str, model: str) -> LLMProvider:
    params = {
        "temperature": user_settings.get("temperature", 0.5),
        "max_tokens": user_settings.get("max_output_tokens", 8192),
        "top_p": user_settings.get("top_p", 1.0),
        "stop_sequences": user_settings.get("stop_sequences", []),
    }

    if provider == "openai":
        return LLMProvider(
            provider="openai",
            api_key=user_settings.get("openai_api_key"),
            model=model,
            azure_endpoint=user_settings.get("openai_endpoint"),
            azure_deployment=user_settings.get("openai_deployment"),
            **params,
        )

    if provider == "gemini":
        return LLMProvider(
            provider="gemini",
            api_key=user_settings.get("gemini_api_key"),
            model=model,
            **params,
        )

    raise ValueError(f"Unsupported provider: {provider}")


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
        print(f"⚠️ Chunk {chunk_num}: No JSON array found in response")
        return []

    try:
        data = json.loads(cleaned[start:end + 1])

        if not isinstance(data, list):
            print(f"⚠️ Chunk {chunk_num}: Response is not a JSON array")
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
        
        print(f"✅ Chunk {chunk_num}: Parsed {len(valid_items)} items and injected page_number '{page_numbers}'")
        return valid_items

    except json.JSONDecodeError as e:
        print(f"❌ Chunk {chunk_num}: JSON decode error - {str(e)}")
        return []