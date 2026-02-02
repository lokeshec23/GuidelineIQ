# backend/compare/dscr_template_processor.py

"""
DSCR Template-Based Comparison Processor
Uses the fixed DSCR_GUIDELINES list as a template to create structured comparison Excel
"""

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
from ingest.dscr_config import DSCR_GUIDELINES


async def process_dscr_template_comparison(
    session_id: str,
    file1_path: str,
    file2_path: str,
    file1_name: str,
    file2_name: str,
    user_settings: dict,
    model_provider: str,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    user_id: str = None,
    username: str = "Unknown",
):
    """
    Background async task to compare two DSCR guideline Excel files using the
    DSCR_GUIDELINES template as the baseline structure.
    
    Process:
    1. Load both guideline Excel files
    2. Use DSCR_GUIDELINES (46 parameters) as template
    3. For each parameter, find matching values from both guidelines
    4. Use LLM to compare and generate comparison notes
    5. Output Excel with structure:
       - DSCR_Parameters
       - Variance_Category
       - SubCategory
       - PPE_Field_Type
       - Guideline_1_Value
       - Guideline_2_Value
       - Comparison_Notes
    """
    excel_path = None

    try:
        print(f"\n{'='*60}")
        print(f"DSCR Template Comparison started for session {session_id[:8]}")
        print(f"File 1: {file1_name}")
        print(f"File 2: {file2_name}")
        print(f"Model: {model_provider}/{model_name}")
        print(f"Template: {len(DSCR_GUIDELINES)} DSCR parameters")
        print(f"{'='*60}\n")

        # Validate prompts - Use defaults if empty
        if not user_prompt.strip():
            from config import DEFAULT_COMPARISON_PROMPT_USER
            user_prompt = DEFAULT_COMPARISON_PROMPT_USER
            print("⚠️ Using DEFAULT_COMPARISON_PROMPT_USER")
        
        if not system_prompt.strip():
            from config import DEFAULT_COMPARISON_PROMPT_SYSTEM
            system_prompt = DEFAULT_COMPARISON_PROMPT_SYSTEM
            print("⚠️ Using DEFAULT_COMPARISON_PROMPT_SYSTEM")

        # STEP 1 — Load Excel Data
        update_progress(session_id, 10, "Reading guideline data...")

        data1 = await asyncio.to_thread(read_excel_to_json, file1_path, "Guideline 1")
        data2 = await asyncio.to_thread(read_excel_to_json, file2_path, "Guideline 2")

        print(f"✅ Loaded Guideline 1: {len(data1)} rows")
        print(f"✅ Loaded Guideline 2: {len(data2)} rows")

        # STEP 2 — Match data to DSCR template
        update_progress(session_id, 20, "Mapping to DSCR parameter template...")

        template_data = build_dscr_template_comparison(
            data1, data2, file1_name, file2_name
        )

        print(f"✅ Created template with {len(template_data)} DSCR parameters")

        # STEP 3 — Chunk for LLM processing
        chunk_size = user_settings.get("comparison_chunk_size", 10)
        comparison_chunks = create_comparison_chunks(template_data, chunk_size)
        num_chunks = len(comparison_chunks)

        if num_chunks == 0:
            raise ValueError("No comparison chunks created from template.")

        update_progress(session_id, 30, f"Prepared {num_chunks} comparison chunks.")

        # STEP 4 — Initialize LLM
        update_progress(session_id, 40, f"Initializing {model_provider} LLM...")
        llm = initialize_llm_provider_for_compare(user_settings, model_provider, model_name)

        # STEP 5 — Parallel LLM Processing
        update_progress(session_id, 45, f"Analyzing {num_chunks} chunks with {model_name}...")

        results, failed = await run_parallel_dscr_comparison(
            llm,
            comparison_chunks,
            system_prompt,
            user_prompt,
            session_id,
            num_chunks
        )

        if not results:
            raise ValueError("LLM returned no valid comparison data.")

        # STEP 6 — Save Excel
        update_progress(session_id, 90, "Generating DSCR comparison Excel...")

        excel_path = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".xlsx",
            prefix=f"dscr_comparison_{session_id[:8]}_"
        ).name

        # Use custom header mapping for DSCR comparison
        header_map = {
            "dscr_parameters": "DSCR PARAMETERS",
            "variance_category": "VARIANCE CATEGORIES",
            "sub_category": "SUB CATEGORY",
            "ppe_field_type": "PPE FIELD TYPE",
            "guideline_1_value": file1_name,
            "guideline_2_value": file2_name,
            "comparison_notes": "COMPARISON NOTES"
        }

        dynamic_json_to_excel(results, excel_path, header_map=header_map)

        update_progress(session_id, 100, "Comparison complete.")

        print(f"{'='*60}\nDSCR TEMPLATE COMPARISON COMPLETE\n{'='*60}")

        # Save meta & preview
        from utils.progress import progress_store, progress_lock
        with progress_lock:
            progress_store[session_id].update({
                "excel_path": excel_path,
                "preview_data": results,
                "filename": (
                    f"DSCR_Comparison_"
                    f"{os.path.splitext(file1_name)[0]}_vs_"
                    f"{os.path.splitext(file2_name)[0]}.xlsx"
                ),
                "status": "completed",
                "total_chunks": num_chunks,
                "failed_chunks": failed,
            })

        # Save to history
        if user_id:
            try:
                from history.models import save_compare_history
                await save_compare_history({
                    "user_id": user_id,
                    "username": username,
                    "uploaded_file1": file1_name,
                    "uploaded_file2": file2_name,
                    "extracted_file": (
                        f"DSCR_Comparison_{os.path.splitext(file1_name)[0]}_vs_"
                        f"{os.path.splitext(file2_name)[0]}.xlsx"
                    ),
                    "preview_data": results
                })
                print(f"✅ Saved to compare history for user: {username}")
            except Exception as hist_err:
                print(f"⚠️ Failed to save history: {hist_err}")

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
                print("Temporary file cleaned up.")


def build_dscr_template_comparison(
    data1: List[Dict],
    data2: List[Dict],
    file1_name: str,
    file2_name: str
) -> List[Dict]:
    """
    Build comparison data using DSCR_GUIDELINES as template.
    
    For each DSCR parameter in the template:
    1. Find matching row(s) in data1
    2. Find matching row(s) in data2
    3. Create a comparison entry
    
    Returns:
        List of dicts with structure:
        {
            "dscr_parameters": "Purchase",
            "variance_category": "Eligible Transactions",
            "sub_category": "Feature Eligibility",
            "ppe_field_type": "Hard",
            "guideline_1_data": {...},
            "guideline_2_data": {...}
        }
    """
    template_comparison = []
    
    # Normalize function for fuzzy matching
    def normalize(s):
        return str(s).strip().lower()
    
    # Build lookup maps for both guidelines
    # Key: normalized parameter name
    def build_lookup(data: List[Dict]) -> Dict[str, Dict]:
        lookup = {}
        for row in data:
            # Try multiple possible column names for parameter
            param = (
                row.get("DSCR_Parameters") or 
                row.get("DSCR Parameters") or 
                row.get("dscr_parameters") or 
                row.get("Parameter") or 
                row.get("parameter") or
                ""
            )
            if param:
                key = normalize(param)
                # Store the full row data
                lookup[key] = row
        return lookup
    
    lookup1 = build_lookup(data1)
    lookup2 = build_lookup(data2)
    
    print(f"📋 Guideline 1 parameter map: {len(lookup1)} entries")
    print(f"📋 Guideline 2 parameter map: {len(lookup2)} entries")
    
    # Process each DSCR template parameter
    for template_param in DSCR_GUIDELINES:
        param_name = template_param["parameter"]
        param_key = normalize(param_name)
        
        # Find matching data from both guidelines
        guideline1_row = lookup1.get(param_key)
        guideline2_row = lookup2.get(param_key)
        
        # Create comparison entry
        comparison_entry = {
            "dscr_parameters": param_name,
            "variance_category": template_param["category"],
            "sub_category": template_param["subcategory"],
            "ppe_field_type": template_param["ppe_field"],
            "guideline_1_data": guideline1_row if guideline1_row else {"status": "Not present"},
            "guideline_2_data": guideline2_row if guideline2_row else {"status": "Not present"},
        }
        
        template_comparison.append(comparison_entry)
    
    return template_comparison


async def run_parallel_dscr_comparison(
    llm: LLMProvider,
    comparison_chunks: List[List[Dict]],
    system_prompt: str,
    user_prompt: str,
    session_id: str,
    total_chunks: int
) -> Tuple[List[Dict], int]:
    """
    Run LLM comparison in parallel for DSCR template chunks.
    """
    chunk_results = [None] * len(comparison_chunks)
    failed_count = 0
    completed = 0

    lock = asyncio.Lock()

    async def handle_chunk(idx: int, chunk: List[Dict]):
        nonlocal chunk_results, failed_count, completed

        # Prepare chunk data for LLM
        chunk_json = json.dumps(
            [
                {
                    "dscr_parameter": item["dscr_parameters"],
                    "category": item["variance_category"],
                    "sub_category": item["sub_category"],
                    "ppe_field_type": item["ppe_field_type"],
                    "guideline_1": item["guideline_1_data"],
                    "guideline_2": item["guideline_2_data"],
                }
                for item in chunk
            ],
            indent=2
        )

        user_content = f"""{user_prompt}

### DATA CHUNK TO COMPARE
{chunk_json}

### REMINDER: OUTPUT FORMAT
You MUST respond with a valid JSON array only. Each object must have exactly these keys:
- "guideline_1_value" (or "guideline_1"): Extract the key rule/value/summary from the guideline_1 object. If not found, use "Not present".
- "guideline_2_value" (or "guideline_2"): Extract the key rule/value/summary from the guideline_2 object. If not found, use "Not present".
- "comparison_notes": Analyze and explain differences, updates, or similarities in a detailed string.

Start with '[' and end with ']'. No markdown, no explanations."""

        try:
            response = await asyncio.to_thread(
                llm.generate,
                system_prompt,
                user_content
            )

            parsed = parse_and_validate_dscr_response(response, idx + 1, chunk)

            if parsed:
                async with lock:
                    chunk_results[idx] = parsed
            else:
                print(f"❌ Chunk {idx+1} returned invalid JSON.")
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

    final = []
    for item_list in chunk_results:
        if not item_list:
            continue
        for obj in item_list:
            final.append(obj)

    print(f"\n✅ Successfully compared: {len(final)} DSCR parameters")
    print(f"❌ Failed chunks: {failed_count}")

    return final, failed_count


def parse_and_validate_dscr_response(response: str, chunk_num: int, original_chunk: List[Dict]) -> List[Dict]:
    """
    Parse and validate LLM response for DSCR comparison.
    IMPORTANT: Merges LLM output with original template data to ensure parameter names are preserved.
    """
    import re
    
    cleaned = re.sub(r'```json\s*|\s*```', '', response.strip())
    
    start = cleaned.find("[")
    end = cleaned.rfind("]")

    if start == -1 or end == -1:
        print(f"⚠️ Chunk {chunk_num}: No JSON array found")
        return []

    try:
        data = json.loads(cleaned[start:end + 1])

        if not isinstance(data, list):
            return []
        
        valid_items = []
        
        # LLM should return same number of items as in original chunk
        if len(data) != len(original_chunk):
            print(f"⚠️ Chunk {chunk_num}: LLM returned {len(data)} items, expected {len(original_chunk)}")
            # Pad with empty items if needed
            while len(data) < len(original_chunk):
                data.append({
                    "guideline_1_value": "Error: LLM did not return value",
                    "guideline_2_value": "Error: LLM did not return value",
                    "comparison_notes": "Error during processing"
                })
        
        # Merge LLM output with original template data
        for i, (llm_item, template_item) in enumerate(zip(data, original_chunk)):
            if not isinstance(llm_item, dict):
                continue
            
            # Build final item with template data (guaranteed to be correct) + LLM analysis
            merged_item = {
                # ✅ Always use template data for these fields (never trust LLM to copy them)
                "dscr_parameters": template_item["dscr_parameters"],
                "variance_category": template_item["variance_category"],
                "sub_category": template_item["sub_category"],
                "ppe_field_type": template_item["ppe_field_type"],
                
                # ✅ Get LLM-generated values (with fallbacks for key variations)
                "guideline_1_value": llm_item.get("guideline_1_value") or llm_item.get("guideline_1") or "Not present",
                "guideline_2_value": llm_item.get("guideline_2_value") or llm_item.get("guideline_2") or "Not present",
                "comparison_notes": llm_item.get("comparison_notes", "No analysis available")
            }
            
            valid_items.append(merged_item)
        
        return valid_items

    except json.JSONDecodeError as e:
        print(f"⚠️ Chunk {chunk_num}: JSON decode error: {e}")
        return []



def initialize_llm_provider_for_compare(user_settings: dict, provider: str, model: str) -> LLMProvider:
    """Initialize LLM provider for comparison."""
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


def create_comparison_chunks(template_data: List[Dict], chunk_size: int = 10) -> List[List[Dict]]:
    """Split template data into chunks for parallel processing."""
    return [
        template_data[i:i + chunk_size]
        for i in range(0, len(template_data), chunk_size)
    ]
