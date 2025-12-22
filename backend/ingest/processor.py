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

rag_service = RAGService()  # ✅ Initialize RAG Service

async def process_guideline_background(
    session_id: str,
    gridfs_file_id: str,  # ✅ Changed from pdf_path to gridfs_file_id
    filename: str,
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
    temp_pdf_path = None  # ✅ Track temporary PDF file
    
    try:
        pages_per_chunk = user_settings.get("pages_per_chunk", 1)
        print(f"\n{'='*60}")
        print(f"Parallel ingestion started for session {session_id[:8]}")
        print(f"Investor: {investor} | Version: {version}")
        print(f"File: {filename}")
        print(f"GridFS File ID: {gridfs_file_id}")
        print(f"Model: {model_provider}/{model_name}")
        print(f"Pages per chunk: {pages_per_chunk}")
        print(f"Effective Date: {effective_date}")
        print(f"Expiry Date: {expiry_date if expiry_date else 'N/A'}")
        print(f"Page Range: {page_range if page_range else 'All'}")
        print(f"Guideline Type: {guideline_type if guideline_type else 'N/A'}")
        print(f"Program Type: {program_type if program_type else 'N/A'}")
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

        # === STEP 1: Retrieve PDF from GridFS ===
        update_progress(session_id, 2, "Retrieving PDF from storage...")
        from utils.gridfs_helper import get_pdf_from_gridfs
        
        pdf_content = await get_pdf_from_gridfs(gridfs_file_id)
        
        # Create temporary file for OCR processing
        temp_pdf_path = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf",
            prefix=f"ocr_{session_id[:8]}_"
        ).name
        
        with open(temp_pdf_path, "wb") as f:
            f.write(pdf_content)
        
        print(f"✅ Created temporary PDF for OCR: {temp_pdf_path}")

        # === STEP 2: OCR ===
        update_progress(session_id, 5, f"Extracting text ({pages_per_chunk} page(s) per chunk)...")
        ocr_client = AzureOCR()
        text_chunks = ocr_client.analyze_doc_page_by_page(
            temp_pdf_path, 
            pages_per_chunk=pages_per_chunk, 
            page_range=page_range
        )
        num_chunks = len(text_chunks)
        if num_chunks == 0:
            raise ValueError("OCR process failed to extract text from document.")

        update_progress(session_id, 35, f"OCR complete. Created {num_chunks} text chunk(s).")

        # === STEP 3: Initialize LLM ===
        update_progress(session_id, 40, f"Initializing {model_provider} LLM...")
        llm = initialize_llm_provider(user_settings, model_provider, model_name)
        update_progress(session_id, 45, f"Running {num_chunks} chunks in full parallel...")

        # === STEP 4: Parallel LLM Calls ===
        results, failed = await run_parallel_llm_processing(
            llm, text_chunks, system_prompt, user_prompt, investor, version, session_id, num_chunks
        )

        # Validate output
        if not results:
            raise ValueError("LLM returned no valid data. Check prompts and model response.")

        # === STEP 4.5: Generate Embeddings (Chunks + Excel Rules) & Store in Vector DB ===
        update_progress(session_id, 80, "Generating embeddings for RAG (PDF + Rules)...")
        try:
            items_to_embed = []
            
            # 1. Add PDF Text Chunks
            for i, chunk_tuple in enumerate(text_chunks):
                text, pages = chunk_tuple
                items_to_embed.append({
                    "id": f"{gridfs_file_id}_chunk_{i}",
                    "text": text,
                    "metadata": {
                        "investor": investor,
                        "version": version,
                        "page": pages,
                        "filename": filename,
                        "gridfs_file_id": gridfs_file_id,
                        "type": "pdf_chunk"
                    }
                })

            # 2. Add Extracted Excel Rules
            # results is a list of dicts: {category, sub_category, guideline_summary, page_number}
            for i, rule in enumerate(results):
                # Construct a rich text representation for the rule
                rule_text = f"Category: {rule.get('category')}\nSub-Category: {rule.get('sub_category')}\nRule: {rule.get('guideline_summary')}"
                items_to_embed.append({
                    "id": f"{gridfs_file_id}_rule_{i}",
                    "text": rule_text,
                    "metadata": {
                        "investor": investor,
                        "version": version,
                        "page": rule.get('page_number', 'Unknown'),
                        "filename": filename,
                        "gridfs_file_id": gridfs_file_id,
                        "type": "excel_rule",
                        "category": rule.get('category'),
                        "sub_category": rule.get('sub_category')
                    }
                })
            
            # Determine provider and key
            rag_provider = model_provider
            api_key = user_settings.get(f"{model_provider}_api_key")
            
            # 3. Generate Embeddings concurrently
            print(f"⚡ Generating embeddings for {len(items_to_embed)} items concurrently...")
            
            async def process_embedding(item):
                emb = await rag_service.get_embedding(
                    item["text"], 
                    rag_provider, 
                    api_key,
                    azure_endpoint=user_settings.get("openai_endpoint"),
                    azure_deployment=user_settings.get("openai_deployment")
                )
                item["embedding"] = emb
                return item

            # Run all embedding calls in parallel
            embedded_items = await asyncio.gather(*[process_embedding(item) for item in items_to_embed])
            
            # Filter out failed embeddings
            valid_docs = [d for d in embedded_items if d["embedding"]]
            
            # Store in Vector DB
            if valid_docs:
                rag_service.add_documents(valid_docs)
                print(f"✅ RAG: Stored {len(valid_docs)} items (Chunks + Rules) in Vector DB.")

        except Exception as rag_err:
            print(f"⚠️ RAG Embedding Failed: {rag_err}")
            traceback.print_exc()



        # === STEP 5: Convert results to Excel ===
        update_progress(session_id, 90, "Converting results to Excel...")

        excel_path = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".xlsx",
            prefix=f"extraction_{session_id[:8]}_"
        ).name

        dynamic_json_to_excel(results, excel_path)

        update_progress(session_id, 100, "Processing complete.")
        print(f"{'='*60}\nPARALLEL PROCESSING COMPLETE\n{'='*60}")

        # Save preview + meta
        from utils.progress import progress_store, progress_lock
        with progress_lock:
            progress_store[session_id].update({
                "excel_path": excel_path,
                "preview_data": results,
                "filename": f"extraction_{investor}_{version}.xlsx",
                "status": "completed",
                "total_chunks": num_chunks,
                "failed_chunks": failed,
            })

        # Save to history after successful completion
        if user_id:
            try:
                from history.models import save_ingest_history
                # ✅ UPDATED: Pass gridfs_file_id to history
                history_id = await save_ingest_history({
                    "user_id": user_id,
                    "username": username,
                    "investor": investor,
                    "version": version,
                    "uploaded_file": filename,
                    "extracted_file": f"extraction_{investor}_{version}.xlsx",
                    "preview_data": results,
                    "effective_date": effective_date,
                    "expiry_date": expiry_date,
                    "gridfs_file_id": gridfs_file_id,  # ✅ Store GridFS ID instead of path
                    "page_range": page_range,
                    "guideline_type": guideline_type,
                    "program_type": program_type
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
        # ✅ Clean up temporary PDF file
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