# backend/compare/processor.py

import os
import json
import tempfile
import asyncio
import traceback
from typing import List, Dict, Tuple, Optional
from utils.excel_reader import read_excel_to_json
from utils.llm_provider import LLMProvider
from utils.json_to_excel import dynamic_json_to_excel
from utils.progress import update_progress


async def process_comparison_background(
    session_id: str,
    file1_path: str,
    file2_path: str,
    file1_name: str,
    file2_name: str,
    user_settings: dict,
    model_provider: str,
    model_name: str,
    system_prompt: str,
    user_prompt: str
):
    """
    Async background task for comparing two Excel files using parallel LLM processing.
    """

    excel_path = None
    try:
        print(f"\n{'='*60}")
        print(f"Parallel comparison started for session {session_id[:8]}")
        print(f"File 1: {file1_name}")
        print(f"File 2: {file2_name}")
        print(f"Model: {model_provider}/{model_name}")
        print(f"{'='*60}\n")

        # Step 1: Read and Align Excel Data
        update_progress(session_id, 10, "Reading and aligning guideline data...")
        data1 = await asyncio.to_thread(read_excel_to_json, file1_path, "Guideline 1")
        data2 = await asyncio.to_thread(read_excel_to_json, file2_path, "Guideline 2")
        
        aligned_data = align_guideline_data(data1, data2)
        print(f"Aligned {len(aligned_data)} rule pairs for comparison.")
        
        # Step 2: Create Comparison Chunks
        chunk_size = user_settings.get("comparison_chunk_size", 10)
        comparison_chunks = create_comparison_chunks(aligned_data, chunk_size=chunk_size)
        
        max_chunks_to_process = user_settings.get("max_comparison_chunks", 15)
        if max_chunks_to_process and max_chunks_to_process > 0:
            comparison_chunks = comparison_chunks[:max_chunks_to_process]
        
        num_chunks = len(comparison_chunks)
        if num_chunks == 0:
            raise ValueError("No data available for comparison after alignment.")
        
        update_progress(session_id, 30, f"Prepared {num_chunks} comparison chunks.")

        # Step 3: Initialize LLM
        update_progress(session_id, 40, f"Initializing {model_provider} LLM...")
        llm = initialize_llm_provider_for_compare(user_settings, model_provider, model_name)

        # Build new combined prompt (system + user)
        combined_prompt_header = (
            f"### SYSTEM PROMPT\n{system_prompt or ''}\n\n"
            f"### USER PROMPT\n{user_prompt or ''}\n\n"
        )

        # Step 4: Parallel processing
        update_progress(session_id, 45, f"Running {num_chunks} chunks in full parallel with {model_name}...")
        results, failed = await run_parallel_comparison_with_rule_ids(
            llm,
            comparison_chunks,
            combined_prompt_header,
            session_id,
            num_chunks
        )

        # Step 5: Generate Excel
        update_progress(session_id, 90, "Converting comparison results to Excel...")
        excel_path = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".xlsx",
            prefix=f"comparison_{session_id[:8]}_"
        ).name

        dynamic_json_to_excel(results, excel_path)

        update_progress(session_id, 100, "Processing complete.")
        print(f"{'='*60}\nPARALLEL COMPARISON COMPLETE\n{'='*60}")

        from utils.progress import progress_store, progress_lock
        with progress_lock:
            progress_store[session_id].update({
                "excel_path": excel_path,
                "preview_data": results,
                "filename": (
                    f"comparison_"
                    f"{os.path.basename(file1_name).split('.')[0]}_vs_"
                    f"{os.path.basename(file2_name).split('.')[0]}.xlsx"
                ),
                "status": "completed",
                "total_chunks": num_chunks,
                "failed_chunks": failed,
            })

    except Exception as e:
        error_msg = str(e)
        print(f"\nCritical error: {error_msg}\n")
        traceback.print_exc()
        update_progress(session_id, -1, f"Error: {error_msg}")

        from utils.progress import progress_store, progress_lock
        with progress_lock:
            if session_id in progress_store:
                progress_store[session_id].update({"status": "failed", "error": error_msg})

    finally:
        for path in [file1_path, file2_path]:
            if path and os.path.exists(path):
                os.remove(path)
                print("Temporary comparison files cleaned up.")


async def run_parallel_comparison_with_rule_ids(
    llm: LLMProvider,
    comparison_chunks: List[List[Dict]],
    combined_prompt_header: str,
    session_id: str,
    total_chunks: int
) -> Tuple[List[Dict], int]:

    chunk_results = [None] * len(comparison_chunks)
    failed_count = 0
    completed = 0
    lock = asyncio.Lock()

    async def handle_chunk(idx: int, chunk: List[Dict]):
        nonlocal chunk_results, failed_count, completed

        chunk_text = format_chunk_for_prompt(chunk)

        # Build full prompt
        full_prompt = (
            f"{combined_prompt_header}"
            f"### COMPARISON DATA CHUNK ###\n{chunk_text}"
        )

        try:
            response = await asyncio.to_thread(llm.generate, full_prompt)
            parsed = parse_comparison_response(response, idx + 1)

            if parsed:
                async with lock:
                    chunk_results[idx] = parsed

        except Exception as e:
            failed_count += 1
            print(f"Chunk {idx+1} failed: {e}")
            async with lock:
                chunk_results[idx] = []

        finally:
            completed += 1
            progress = 45 + int((completed / total_chunks) * 45)
            update_progress(session_id, progress, f"Processed {completed}/{total_chunks} chunk(s)")

    await asyncio.gather(*(handle_chunk(i, c) for i, c in enumerate(comparison_chunks)))

    # Aggregate results + assign rule IDs
    final_results = []
    rule_counter = 1

    for block in chunk_results:
        if block:
            for item in block:
                item["rule_id"] = rule_counter
                rule_counter += 1
                final_results.append(item)

    return final_results, failed_count


def initialize_llm_provider_for_compare(user_settings: dict, provider: str, model: str) -> LLMProvider:
    params = {
        "temperature": user_settings.get("temperature", 0.3),
        "max_tokens": user_settings.get("max_output_tokens", 8192),
        "top_p": user_settings.get("top_p", 0.95),
        "stop_sequences": user_settings.get("stop_sequences", []),
    }

    if provider == "openai":
        return LLMProvider(
            provider="openai",
            api_key=user_settings.get("openai_api_key"),
            model=model,
            azure_endpoint=user_settings.get("openai_endpoint"),
            azure_deployment=user_settings.get("openai_deployment"),
            **params
        )

    if provider == "gemini":
        return LLMProvider(
            provider="gemini",
            api_key=user_settings.get("gemini_api_key"),
            model=model,
            **params
        )

    raise ValueError("Unsupported provider")


def parse_comparison_response(response: str, chunk_num: int) -> List[Dict]:
    import re
    cleaned = response.strip()
    match = re.search(r"(\[.*\])", cleaned, re.DOTALL)
    if not match:
        print(f"No JSON array found in chunk {chunk_num}")
        return []

    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, list) else []

    except json.JSONDecodeError as e:
        print(f"JSON parse error in chunk {chunk_num}: {e}")
        return []


def align_guideline_data(data1: List[Dict], data2: List[Dict]) -> List[Dict]:
    aligned = []
    map2 = {
        (
            item.get("Category", "").strip().lower(),
            item.get("Attribute", "").strip().lower()
        ): item
        for item in data2
    }

    for item1 in data1:
        key = (
            item1.get("Category", "").strip().lower(),
            item1.get("Attribute", "").strip().lower()
        )
        item2 = map2.pop(key, None)
        aligned.append({
            "guideline1": item1,
            "guideline2": item2
        })

    for item2 in map2.values():
        aligned.append({
            "guideline1": None,
            "guideline2": item2
        })

    return aligned


def create_comparison_chunks(aligned_data: List[Dict], chunk_size: int = 10) -> List[List[Dict]]:
    chunks = []
    for i in range(0, len(aligned_data), chunk_size):
        chunk = aligned_data[i:i+chunk_size]
        if chunk:
            chunks.append(chunk)
    return chunks


def format_chunk_for_prompt(chunk: List[Dict]) -> str:
    cleaned = []
    for idx, pair in enumerate(chunk, 1):
        cleaned.append({
            "comparison_id": idx,
            "guideline_1": pair["guideline1"] or {"status": "Not present in Guideline 1"},
            "guideline_2": pair["guideline2"] or {"status": "Not present in Guideline 2"},
        })
    return json.dumps(cleaned, indent=2)
