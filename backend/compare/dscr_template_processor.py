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
from sql_database import AsyncSessionLocal

# Excel Export Configuration
DSCR_EXPORT_HEADER_MAP = {
    "s_no": "S.No",
    "dscr_parameters": "DSCR PARAMETERS",
    "category": "Category",
    "sub_category": "Sub Category",
    "guideline_1": "Guideline 1",
    "guideline_2": "Guideline 2",
    "comparison_notes": "Comparison Notes"
}

DSCR_EXPORT_COLUMN_ORDER = [
    "s_no",
    "dscr_parameters",
    "category",
    "sub_category",
    "guideline_1",
    "guideline_2",
    "comparison_notes"
]

DSCR_EXPORT_HIDDEN_COLUMNS = ["rule_id", "ppe_field_type"]


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

        # ✅ Add S.No to results
        for idx, item in enumerate(results, 1):
            item["s_no"] = idx

        excel_path = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".xlsx",
            prefix=f"dscr_comparison_{session_id[:8]}_"
        ).name

        # Use centralized configuration for Excel generation
        dynamic_json_to_excel(
            results,
            excel_path,
            header_map=DSCR_EXPORT_HEADER_MAP,
            hidden_columns=DSCR_EXPORT_HIDDEN_COLUMNS,
            column_order=DSCR_EXPORT_COLUMN_ORDER
        )

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
                async with AsyncSessionLocal() as db:
                    await save_compare_history(db, {
                        "user_id": user_id,
                        "username": username,
                        "session_id": session_id,  # ✅ Pass session_id so it can be looked up by chat
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


def detect_parameter_column(data: List[Dict]) -> Optional[str]:
    """
    Identify the column that likely contains DSCR parameters.
    Checks for standard names and content overlap.
    """
    if not data:
        return None

    # Get all column names from first row
    columns = list(data[0].keys())

    # 1. Check for standard names (priority order)
    standard_names = [
        "DSCR_Parameters", "DSCR Parameters", "dscr_parameters",
        "Parameter", "parameter", "Rule Name", "Rule", "Topic",
        "Guideline", "Field", "Description"
    ]

    # First pass: check if any standard name exists exactly
    for name in standard_names:
        if name in columns:
            return name

    # 2. Check content overlap with DSCR_GUIDELINES
    # We want to find a column that contains values like "Purchase", "Cash-Out Refinance"
    best_col = None
    max_overlap = 0

    # Create set of normalized template parameters
    template_params = {str(p["parameter"]).strip().lower() for p in DSCR_GUIDELINES}

    for col in columns:
        matches = 0
        # Check first 50 rows (or all if less)
        for row in data[:50]:
            val = str(row.get(col, "")).strip().lower()
            if val in template_params:
                matches += 1

        # Calculate percentage of overlap if we have data
        current_overlap = matches
        if current_overlap > max_overlap:
            max_overlap = current_overlap
            best_col = col

    if max_overlap > 0:
        return best_col

    # Fallback: if we still haven't found a column, try case-insensitive match on standard names
    for name in standard_names:
        name_lower = name.lower()
        for col in columns:
            if col.lower() == name_lower:
                return col

    return None


def build_dscr_template_comparison(
    data1: List[Dict],
    data2: List[Dict],
    file1_name: str,
    file2_name: str
) -> List[Dict]:
    """
    Build comparison data using DSCR_GUIDELINES as template.
    
    For each DSCR parameter in the template:
    1. Find matching row(s) in data1 using fuzzy matching
    2. Find matching row(s) in data2 using fuzzy matching
    3. Create a comparison entry
    """
    import difflib
    template_comparison = []
    
    def normalize(s):
        return str(s).strip().lower()

    # Helper to find the best matching row in a dataset for a given template parameter
    def find_best_match(data: List[Dict], param_name: str, col_name: str) -> Optional[Dict]:
        if not col_name or not data:
            return None

        param_norm = normalize(param_name)

        # 1. Exact Match (Fast)
        for row in data:
            val = normalize(row.get(col_name, ""))
            if val == param_norm:
                return row

        # 2. Fuzzy Match (Slower but more robust)
        best_row = None
        best_score = 0.0

        # Threshold for fuzzy matching
        FUZZY_THRESHOLD = 0.85

        for row in data:
            val = normalize(row.get(col_name, ""))
            if not val:
                continue

            ratio = difflib.SequenceMatcher(None, param_norm, val).ratio()

            # Boost for containment (if one is substring of other)
            # This helps with "Purchase" vs "Purchase Transactions"
            if len(val) > 3 and len(param_norm) > 3:
                if val in param_norm or param_norm in val:
                    # Boost ratio to at least 0.9 if contained
                    ratio = max(ratio, 0.9)

            if ratio > best_score and ratio >= FUZZY_THRESHOLD:
                best_score = ratio
                best_row = row

        return best_row

    # Detect columns
    col1 = detect_parameter_column(data1)
    col2 = detect_parameter_column(data2)
    
    print(f"📋 Detected parameter column for {file1_name}: {col1}")
    print(f"📋 Detected parameter column for {file2_name}: {col2}")
    
    # Process each DSCR template parameter
    for template_param in DSCR_GUIDELINES:
        param_name = template_param["parameter"]
        
        # Find matching data from both guidelines
        guideline1_row = find_best_match(data1, param_name, col1)
        guideline2_row = find_best_match(data2, param_name, col2)
        
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
            g1_val = llm_item.get("guideline_1_value") or llm_item.get("guideline_1") or "Not present"
            g2_val = llm_item.get("guideline_2_value") or llm_item.get("guideline_2") or "Not present"

            merged_item = {
                # ✅ Use template data for these fields to ensure consistency
                "dscr_parameters": template_item["dscr_parameters"],
                "category": template_item["variance_category"],
                "sub_category": template_item["sub_category"],
                "ppe_field_type": template_item["ppe_field_type"],
                
                # ✅ Map to 'guideline_1'/'guideline_2' for Excel/UI consistency
                "guideline_1": g1_val,
                "guideline_2": g2_val,

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
