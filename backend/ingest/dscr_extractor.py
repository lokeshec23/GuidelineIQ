# backend/ingest/dscr_extractor.py

import os
import asyncio
import json
import datetime
from typing import List, Dict, Tuple
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from ingest.dscr_config import DSCR_Parameters, DSCR_Parameter_Aliases
from chat.rag_service import RAGService
from utils.llm_provider import LLMProvider

async def extract_dscr_parameters_safe(
    session_id: str,
    gridfs_file_id: str,
    rag_service: RAGService,
    llm: LLMProvider,
    investor: str,
    version: str,
    user_settings: dict
) -> Tuple[str, List[Dict]]:
    """
    Extracts DSCR parameters using RAG and LLM, and saves them to an Excel file.
    Returns:
        Tuple[str, List[Dict]]: (The path to the generated Excel file, The data list)
    """
    print(f"\n{'='*60}")
    print(f"🚀 Starting RAG-Based DSCR Extraction for Session: {session_id[:8]}")
    print(f"{'='*60}\n")
    
    # Concurrency control
    semaphore = asyncio.Semaphore(10)
    
    async def process_one(param: str) -> Dict:
        async with semaphore:
            try:
                # Setup provider/key (reusing logic from thought process)
                provider = llm.provider 
                api_key = llm.api_key # The LLMProvider has the key stored
                
                filter_metadata = {"gridfs_file_id": gridfs_file_id}
                
                # Check for aliases
                base_query = f"What are the requirements for {param}?"
                search_query = base_query
                if param in DSCR_Parameter_Aliases:
                    aliases = DSCR_Parameter_Aliases[param]
                    search_query = f"{param} {' '.join(aliases)}"

                search_results = await rag_service.search(
                    query=search_query,
                    provider=provider,
                    api_key=api_key,
                    n_results=5,
                    filter_metadata=filter_metadata,
                    azure_endpoint=user_settings.get("openai_endpoint"),
                    azure_deployment=user_settings.get("openai_deployment")
                )
                
                context_text = ""
                if search_results:
                    context_text = "\n\n".join([f"- {r['text']}" for r in search_results])
                
                if not context_text:
                    return {
                        "DSCR_Parameters": param, 
                        "NQMF Investor DSCR": "Not Found",
                        "rag_variance": "Not Found",
                        "rag_subcat": "Not Found"
                    }
                
                # Enhanced Prompt for Detailed Extraction
                system_prompt = "You are a Mortgage Policy Summarizer."
                user_msg = f"""
                Initial Request: {base_query}
                
                Context from Guidelines:
                {context_text}
                
                Task:
                1. Extract the specific "Variance Category" and "SubCategory" that this guideline belongs to based strictly on the context.
                2. Create a bulleted list of the specific requirements, limits, and conditions for "{param}" based strictly on the context.
                
                Format your response as a JSON object with the following keys:
                - "variance_category": (string)
                - "subcategory": (string)
                - "summary": (string, clean list with "• " bullets)

                Be concise. If the context doesn't explicitly mention something, state "Not found in context".
                """
                
                response_text = await asyncio.to_thread(
                    llm.generate,
                    "You are a helpful mortgage expert assistant. Always return valid JSON.",
                    user_msg
                )
                
                try:
                    # Basic JSON cleaning
                    json_str = response_text.strip()
                    if json_str.startswith("```json"):
                        json_str = json_str[7:]
                    if json_str.endswith("```"):
                        json_str = json_str[:-3]
                    
                    data_json = json.loads(json_str.strip())
                    return {
                        "DSCR_Parameters": param,
                        "rag_variance": data_json.get("variance_category", "Not found"),
                        "rag_subcat": data_json.get("subcategory", "Not found"),
                        "NQMF Investor DSCR": data_json.get("summary", "No summary provided.")
                    }
                except Exception as json_err:
                    print(f"JSON Parse Error for {param}: {json_err}")
                    return {
                        "DSCR_Parameters": param,
                        "rag_variance": "Error parsing",
                        "rag_subcat": "Error parsing",
                        "NQMF Investor DSCR": response_text.strip()
                    }
                
            except Exception as e:
                print(f"Error on {param}: {e}")
                return {
                    "DSCR_Parameters": param,
                    "rag_variance": "Error",
                    "rag_subcat": "Error", 
                    "NQMF Investor DSCR": "Error extraction"
                }

    # Execute
    tasks = [process_one(p) for p in DSCR_Parameters]
    results = await asyncio.gather(*tasks)
    
    # Generate Excel
    filepath = create_dscr_excel(results, session_id, investor, version)
    return filepath, results

def create_dscr_excel(data: List[Dict], session_id: str, investor: str, version: str) -> str:
    wb = Workbook()
    ws = wb.active
    ws.title = "DSCR 1-4 RAG Output"

    # Exact 5 headers 
    headers = [
        "DSCR Parameters\n(Investor / Business Purpose Loans)", 
        "Variance Categories", 
        "SubCategories", 
        "PPE Field Type", 
        f"NQMF Investor DSCR (1-4 Units) Generated {datetime.date.today()}"
    ]
    
    ws.append(headers)

    # Styles
    header_font = Font(bold=True, size=11)
    header_fill_blue = PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid") # Light Blue
    header_fill_orange = PatternFill(start_color="F8CBAD", end_color="F8CBAD", fill_type="solid") # Peach/Orange
    
    # Apply Header Styles
    for col_num, cell in enumerate(ws[1], 1):
        cell.font = header_font
        cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
        # Apply colors based on column index
        if col_num == 1:
            cell.fill = header_fill_blue
        elif col_num in [2, 3, 4]:
            cell.fill = header_fill_orange
        else: # Content column
            cell.fill = header_fill_blue

    # Sort results
    # We want to preserve the order of DSCR_Parameters if possible
    # Create a map of param -> index
    param_order = {p: i for i, p in enumerate(DSCR_Parameters)}
    data.sort(key=lambda x: param_order.get(x['DSCR_Parameters'], 999))

    thin_border = Border(left=Side(style='thin'), 
                         right=Side(style='thin'), 
                         top=Side(style='thin'), 
                         bottom=Side(style='thin'))
    
    fill_light_yellow = PatternFill(start_color="FFFFCC", end_color="FFFFCC", fill_type="solid")
    fill_light_green = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")

    for item in data:
        row = [
            item['DSCR_Parameters'],       # Column A
            item.get('rag_variance', ''),  # Column B
            item.get('rag_subcat', ''),    # Column C
            item.get('rule', {}).get('policy_type', ''), # Column D - Placeholder if we had rule object
            item['NQMF Investor DSCR']     # Column E
        ]
        ws.append(row)
        
        # Apply row styles
        current_row = ws.max_row
        for col_idx, cell in enumerate(ws[current_row], 1):
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = thin_border
            
            # Fill colors based on column
            if col_idx in [1, 2, 3]:
                cell.fill = fill_light_green 
            elif col_idx == 4:
                pass
            elif col_idx == 5:
                cell.fill = fill_light_yellow 

    # Column Widths
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 25
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 80
    
    # File Path
    filename = f"DSCR_Extraction_{investor}_{version}_{session_id[:8]}.xlsx"
    
    # Save to 'results' folder in backend
    base_dir = os.getcwd()
    results_dir = os.path.join(base_dir, "results")
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
        
    filepath = os.path.join(results_dir, filename)
    
    try:
        wb.save(filepath)
        print(f"✅ DSCR Excel saved at: {filepath}")
        return filepath
    except Exception as e:
        print(f"Error saving Excel: {e}")
        # Fallback to temp if results dir fails
        return f"Error: {e}"
