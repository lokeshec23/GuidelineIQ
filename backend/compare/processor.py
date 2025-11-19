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
    Background async task to compare two guideline Excel files.
    Uses REAL system + user roles.
    """
    excel_path = None

    try:
        print(f"\n{'='*60}")
        print(f"Parallel comparison started for session {session_id[:8]}")
        print(f"File 1: {file1_name}")
        print(f"File 2: {file2_name}")
        print(f"Model: {model_provider}/{model_name}")
        print(f"{'='*60}\n")

        # ✅ VALIDATE PROMPTS - Use defaults if empty
        if not user_prompt.strip():
            from config import DEFAULT_COMPARISON_PROMPT_USER
            user_prompt = DEFAULT_COMPARISON_PROMPT_USER
            print("⚠️ Using DEFAULT_COMPARISON_PROMPT_USER (user prompt was empty)")
        
        if not system_prompt.strip():
            from config import DEFAULT_COMPARISON_PROMPT_SYSTEM
            system_prompt = DEFAULT_COMPARISON_PROMPT_SYSTEM
            print("⚠️ Using DEFAULT_COMPARISON_PROMPT_SYSTEM (system prompt was empty)")

        # STEP 1 — Load/Align Excel Data
        update_progress(session_id, 10, "Reading and aligning guideline data...")

        data1 = await asyncio.to_thread(read_excel_to_json, file1_path, "Guideline 1")
        data2 = await asyncio.to_thread(read_excel_to_json, file2_path, "Guideline 2")

        aligned_data = align_guideline_data(data1, data2, file1_name, file2_name)

        print(f"✅ Aligned {len(aligned_data)} rule pairs for comparison.")

        # STEP 2 — Chunk the comparison workload
        chunk_size = user_settings.get("comparison_chunk_size", 10)
        comparison_chunks = create_comparison_chunks(aligned_data, chunk_size)

        max_chunks = user_settings.get("max_comparison_chunks", 0)
        if max_chunks > 0:
            comparison_chunks = comparison_chunks[:max_chunks]
            print(f"⚠️ Limited to {max_chunks} chunks for testing")

        num_chunks = len(comparison_chunks)
        if num_chunks == 0:
            raise ValueError("No aligned comparison chunks found.")

        update_progress(session_id, 30, f"Prepared {num_chunks} comparison chunks.")

        # STEP 3 — Initialize LLM
        update_progress(session_id, 40, f"Initializing {model_provider} LLM...")
        llm = initialize_llm_provider_for_compare(user_settings, model_provider, model_name)

        # STEP 4 — Parallel LLM Processing
        update_progress(session_id, 45, f"Running {num_chunks} chunks with {model_name}...")

        results, failed = await run_parallel_comparison_with_validation(
            llm,
            comparison_chunks,
            system_prompt,
            user_prompt,
            session_id,
            num_chunks
        )

        # ✅ VALIDATE OUTPUT
        if not results:
            raise ValueError("LLM returned no valid comparison data. Check prompts and model response.")

        # STEP 5 — Save Excel
        update_progress(session_id, 90, "Generating comparison Excel...")

        excel_path = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".xlsx",
            prefix=f"comparison_{session_id[:8]}_"
        ).name

        dynamic_json_to_excel(results, excel_path)

        update_progress(session_id, 100, "Processing complete.")

        print(f"{'='*60}\nPARALLEL COMPARISON COMPLETE\n{'='*60}")

        # Save meta & preview
        from utils.progress import progress_store, progress_lock
        with progress_lock:
            progress_store[session_id].update({
                "excel_path": excel_path,
                "preview_data": results,
                "filename": (
                    f"comparison_"
                    f"{os.path.splitext(file1_name)[0]}_vs_"
                    f"{os.path.splitext(file2_name)[0]}.xlsx"
                ),
                "status": "completed",
                "total_chunks": num_chunks,
                "failed_chunks": failed,
            })

    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ Critical comparison error: {error_msg}\n")
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
        for path in [file1_path, file2_path]:
            if path and os.path.exists(path):
                os.remove(path)
                print("Temporary comparison file cleaned up.")


# ======================================================================
# ✅ PARALLEL CHUNK PROCESSING WITH VALIDATION
# ======================================================================
async def run_parallel_comparison_with_validation(
    llm: LLMProvider,
    comparison_chunks: List[List[Dict]],
    system_prompt: str,
    user_prompt: str,
    session_id: str,
    total_chunks: int
) -> Tuple[List[Dict], int]:

    chunk_results = [None] * len(comparison_chunks)
    failed_count = 0
    completed = 0

    lock = asyncio.Lock()

    async def handle_chunk(idx: int, chunk: List[Dict]):
        nonlocal chunk_results, failed_count, completed

        # Convert chunk into clean JSON for LLM
        chunk_json = json.dumps(
            [
                {
                    "guideline_1": block["guideline1"] if block["guideline1"] else {"status": "Not present in Guideline 1"},
                    "guideline_2": block["guideline2"] if block["guideline2"] else {"status": "Not present in Guideline 2"},
                }
                for block in chunk
            ],
            indent=2
        )

        # ✅ Enhanced user message with strict output enforcement
        user_content = f"""{user_prompt}

### DATA CHUNK TO COMPARE
{chunk_json}

### REMINDER: OUTPUT FORMAT
You MUST respond with a valid JSON array only. Each object must have exactly these keys:
- "category" (string)
- "attribute" (string)
- "guideline_1" (string)
- "guideline_2" (string)
- "comparison_notes" (string)

Start with '[' and end with ']'. No markdown, no explanations. DO NOT include "rule_id"."""

        try:
            response = await asyncio.to_thread(
                llm.generate,
                system_prompt,
                user_content
            )

            parsed = parse_and_validate_comparison_response(response, idx + 1)

            if parsed:
                async with lock:
                    chunk_results[idx] = parsed
            else:
                # ✅ Log the actual response for debugging
                print(f"❌ Chunk {idx+1} returned invalid JSON. Response preview:")
                print(response[:500])
                failed_count += 1
                async with lock:
                    chunk_results[idx] = []

        except Exception as e:
            failed_count += 1
            print(f"❌ Chunk {idx+1} failed: {e}")
            async with lock:
                chunk_results[idx] = []

        finally:
            completed += 1
            progress = 45 + int((completed / total_chunks) * 45)
            update_progress(session_id, progress, f"Processed {completed}/{total_chunks} chunk(s)")

    await asyncio.gather(*(handle_chunk(i, c) for i, c in enumerate(comparison_chunks)))

    # ✅ Merge results + assign sequential rule IDs
    final = []
    rule_id = 1

    for item_list in chunk_results:
        if not item_list:
            continue
        for obj in item_list:
            obj["rule_id"] = rule_id
            rule_id += 1
            final.append(obj)

    print(f"\n✅ Successfully compared: {len(final)} rules")
    print(f"❌ Failed chunks: {failed_count}")

    return final, failed_count


# ======================================================================
# ✅ ENHANCED JSON PARSER WITH SCHEMA VALIDATION
# ======================================================================
def parse_and_validate_comparison_response(response: str, chunk_num: int) -> List[Dict]:
    import re
    
    # Remove markdown code blocks if present
    cleaned = re.sub(r'```json\s*|\s*```', '', response.strip())
    
    # Find JSON array
    start = cleaned.find("[")
    end = cleaned.rfind("]")

    if start == -1 or end == -1:
        print(f"⚠️ Chunk {chunk_num}: No JSON array found in response")
        return []

    try:
        data = json.loads(cleaned[start:end + 1])

        if not isinstance(data, list):
            print(f"⚠️ Chunk {chunk_num}: JSON is not a list")
            return []
        
        # ✅ VALIDATE SCHEMA
        valid_items = []
        required_keys = {"category", "attribute", "guideline_1", "guideline_2", "comparison_notes"}
        
        for item in data:
            if not isinstance(item, dict):
                continue
                
            # Remove rule_id if LLM added it
            if "rule_id" in item:
                del item["rule_id"]
            
            # Check if all required keys are present
            if required_keys.issubset(item.keys()):
                valid_items.append(item)
            else:
                missing = required_keys - set(item.keys())
                print(f"⚠️ Chunk {chunk_num}: Missing keys {missing} in item: {list(item.keys())}")
        
        if not valid_items:
            print(f"⚠️ Chunk {chunk_num}: No valid items after schema validation")
        
        return valid_items

    except json.JSONDecodeError as e:
        print(f"❌ Chunk {chunk_num}: JSON parse error: {e}")
        print(f"Attempted to parse: {cleaned[start:start+200]}...")
        return []


# ======================================================================
# HELPERS
# ======================================================================
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

    raise ValueError(f"Unsupported provider: {provider}")


def align_guideline_data(data1: List[Dict], data2: List[Dict], file1_name: str, file2_name: str) -> List[Dict]:
    """
    Align two guidelines based on category + attribute.
    Assumes the Excel has columns: category, attribute, guideline_summary
    """
    aligned = []
    
    # Create lookup map for guideline 2
    map2 = {}
    for item in data2:
        key = (
            item.get("category", "").strip().lower(),
            item.get("attribute", "").strip().lower(),
        )
        map2[key] = item

    # Match guideline 1 items
    for item1 in data1:
        key = (
            item1.get("category", "").strip().lower(),
            item1.get("attribute", "").strip().lower(),
        )
        item2 = map2.pop(key, None)

        aligned.append({
            "guideline1": item1,
            "guideline2": item2
        })

    # Add remaining unmatched guideline 2 rules
    for item2 in map2.values():
        aligned.append({
            "guideline1": None,
            "guideline2": item2
        })

    return aligned


def create_comparison_chunks(aligned_data: List[Dict], chunk_size: int = 10) -> List[List[Dict]]:
    """Split aligned data into chunks for parallel processing"""
    return [
        aligned_data[i:i + chunk_size]
        for i in range(0, len(aligned_data), chunk_size)
    ]