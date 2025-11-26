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


async def process_guideline_background(
    session_id: str,
    pdf_path: str,
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
):
    excel_path = None
    try:
        pages_per_chunk = user_settings.get("pages_per_chunk", 1)
        print(f"\n{'='*60}")
        print(f"Parallel ingestion started for session {session_id[:8]}")
        print(f"Investor: {investor} | Version: {version}")
        print(f"File: {filename}")
        print(f"Model: {model_provider}/{model_name}")
        print(f"Pages per chunk: {pages_per_chunk}")
        print(f"Effective Date: {effective_date}")
        print(f"Expiry Date: {expiry_date if expiry_date else 'N/A'}")
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

        # === STEP 1: OCR ===
        update_progress(session_id, 5, f"Extracting text ({pages_per_chunk} page(s) per chunk)...")
        ocr_client = AzureOCR()
        text_chunks = ocr_client.analyze_doc_page_by_page(pdf_path, pages_per_chunk=pages_per_chunk)
        num_chunks = len(text_chunks)
        if num_chunks == 0:
            raise ValueError("OCR process failed to extract text from document.")

        update_progress(session_id, 35, f"OCR complete. Created {num_chunks} text chunk(s).")

        # === STEP 2: Initialize LLM ===
        update_progress(session_id, 40, f"Initializing {model_provider} LLM...")
        llm = initialize_llm_provider(user_settings, model_provider, model_name)
        update_progress(session_id, 45, f"Running {num_chunks} chunks in full parallel with {model_name}...")

        # === STEP 3: Parallel LLM Calls ===
        results, failed = await run_parallel_llm_processing(
            llm, text_chunks, system_prompt, user_prompt, investor, version, session_id, num_chunks
        )

        # Validate output
        if not results:
            raise ValueError("LLM returned no valid data. Check prompts and model response.")

        # === STEP 4: Convert results to Excel ===
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
                # ✅ UPDATED: Pass file_path to history
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
                    "file_path": pdf_path 
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

    # ✅ REMOVED: Do not delete the PDF file, we need it for chat
    # finally:
    #     if os.path.exists(pdf_path):
    #         os.remove(pdf_path)
    #         print("Temporary PDF file cleaned up.")


async def run_parallel_llm_processing(
    llm: LLMProvider,
    text_chunks: List[str],
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

    async def handle_chunk(idx: int, chunk_text: str):
        nonlocal results, failed_count, completed

        user_msg = f"""{user_prompt}

### METADATA
- Investor: {investor}
- Version: {version}

### TEXT TO PROCESS
{chunk_text}

### REMINDER: OUTPUT FORMAT
You MUST respond with a valid JSON array only. Each object must have exactly these keys:
- "category" (string)
- "attribute" (string)  
- "guideline_summary" (string)

Start with '[' and end with ']'. No markdown, no explanations."""

        try:
            response = await asyncio.to_thread(
                llm.generate,
                system_prompt,
                user_msg
            )

            parsed = parse_and_clean_llm_response(response, idx + 1)

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


def parse_and_clean_llm_response(response: str, chunk_num: int) -> List[Dict]:
    import re
    
    cleaned = re.sub(r'```json\s*|\s*```', '', response.strip())
    
    start = cleaned.find("[")
    end = cleaned.rfind("]")

    if start == -1 or end == -1:
        return []

    try:
        data = json.loads(cleaned[start:end + 1])

        if not isinstance(data, list):
            return []
        
        valid_items = []
        required_keys = {"category", "attribute", "guideline_summary"}
        
        for item in data:
            if not isinstance(item, dict):
                continue
            
            if required_keys.issubset(item.keys()):
                valid_items.append(item)
        
        return valid_items

    except json.JSONDecodeError:
        return []