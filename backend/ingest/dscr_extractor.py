# backend/ingest/dscr_extractor.py

import os
import asyncio
import tempfile
from typing import List, Dict
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from ingest.dscr_config import DSCR_Parameters
from chat.rag_service import RAGService
from utils.llm_provider import LLMProvider

async def extract_dscr_parameters(
    session_id: str,
    gridfs_file_id: str,
    rag_service: RAGService,
    llm: LLMProvider,
    investor: str,
    version: str,
    user_settings: dict
) -> str:
    """
    Extracts DSCR parameters using RAG and LLM, and saves them to an Excel file.
    
    Returns:
        The path to the generated Excel file.
    """
    print(f"\n{'='*60}")
    print(f"🚀 Starting DSCR Parameter Extraction for Session: {session_id[:8]}")
    print(f"{'='*60}\n")
    
    results = []
    
    # Concurrency control
    semaphore = asyncio.Semaphore(10)  # Verify 10 parallel tasks
    
    async def process_parameter(param: str):
        async with semaphore:
            try:
                # 1. RAG Search
                # We filter by the specific file/investor/version context
                filter_metadata = {
                    "gridfs_file_id": gridfs_file_id
                }
                
                rag_provider = user_settings.get("rag_model_provider", "gemini") # Default or from settings
                # If rag_model_provider not explicitly set, imply from general provider or default to openai if not found?
                # Actually processor.py uses 'model_provider' for both LLM and RAG usually, 
                # but let's stick to what's available. 
                # In processor.py: 
                # rag_provider = model_provider
                # api_key = user_settings.get(f"{model_provider}_api_key")
                
                # We'll use the same provider as the LLM if not specified, 
                # but we need the API key for that provider.
                
                # Better approach: Use the LLM's provider as the RAG provider 
                # since we know we have that configured.
                provider = llm.provider 
                api_key = llm.api_key
                
                # Search for context
                # "2-1 Buydown" -> Search query
                search_results = await rag_service.search(
                    query=param,
                    provider=provider,
                    api_key=api_key,
                    n_results=5,
                    filter_metadata=filter_metadata,
                    azure_endpoint=user_settings.get("openai_endpoint"),
                    azure_deployment=user_settings.get("openai_deployment")
                )
                
                context_text = ""
                if search_results:
                    context_text = "\n\n".join([f"Source (Page {r['metadata'].get('page', '?')}): {r['text']}" for r in search_results])
                
                if not context_text:
                    print(f"⚠️ No context found for parameter: {param}")
                    results.append({"DSCR_Parameters": param, "NQMF Investor DSCR": "Not Found"})
                    return

                # 2. LLM Extraction
                system_prompt = "You are an expert mortgage underwriter. Your goal is to extract specific DSCR guidelines from the provided context."
                
                user_msg = f"""
### CONTEXT
{context_text}

### INSTRUCTION
Extract the specific guideline requirements for the parameter: "{param}".
If the requirements are found, list them as bullet points or a concise summary.
If no relevant information is found in the context for this specific parameter, reply with "Not Found".

### OUTPUT FORMAT
Return ONLY the extracted text (bullet points are fine). Do not include "Here is the summary" or other conversational filler.
"""
                
                response = await asyncio.to_thread(
                    llm.generate,
                    system_prompt,
                    user_msg
                )
                
                extracted_value = response.strip()
                
                # Cleanup if LLM is too chatty (though prompt says return only text)
                if extracted_value.lower().startswith("not found"):
                    extracted_value = "Not Found"
                
                results.append({"DSCR_Parameters": param, "NQMF Investor DSCR": extracted_value})
                print(f"✅ Extracted: {param}")
                
            except Exception as e:
                print(f"❌ Failed to extract {param}: {e}")
                results.append({"DSCR_Parameters": param, "NQMF Investor DSCR": "Error during extraction"})

    # Run all tasks
    tasks = [process_parameter(p) for p in DSCR_Parameters]
    await asyncio.gather(*tasks)
    
    # Sort results to match original order (asyncio.gather returns in order of *completion*? No, gather returns in order of *submission* if we awaited the result of gather directly, but here we are appending to a list inside the async function, so the list order is indeterminate. We should re-sort or map results.)
    
    # Better: modify process_parameter to return the result, then gather will preserve order.
    # Let's refactor slightly to be safer with order.
    
    # Refactored Runner Logic below
    pass

async def extract_dscr_parameters_safe(
    session_id: str,
    gridfs_file_id: str,
    rag_service: RAGService,
    llm: LLMProvider,
    investor: str,
    version: str,
    user_settings: dict
) -> str:
    """
    Wrapper to ensure order and error handling.
    """
    print(f"📊 Extraction started for {len(DSCR_Parameters)} parameters...")
    
    semaphore = asyncio.Semaphore(10)
    
    async def process_one(param: str) -> Dict:
        async with semaphore:
            try:
                # Setup provider/key (reusing logic from thought process)
                provider = llm.provider 
                api_key = llm.api_key # The LLMProvider has the key stored
                
                filter_metadata = {"gridfs_file_id": gridfs_file_id}
                
                search_results = await rag_service.search(
                    query=param,
                    provider=provider,
                    api_key=api_key,
                    n_results=5,
                    filter_metadata=filter_metadata,
                    azure_endpoint=user_settings.get("openai_endpoint"),
                    azure_deployment=user_settings.get("openai_deployment")
                )
                
                context_text = "\n\n".join([f"- {r['text']}" for r in search_results])
                
                if not context_text:
                    return {"DSCR_Parameters": param, "NQMF Investor DSCR": "Not Found"}
                
                system_prompt = "You are an expert mortgage underwriter."
                user_msg = f"""
Context:
{context_text}

Task:
Extract key requirements for "{param}" based on the context.
Return ONLY the specific rules/limits. Formatting: Use bullet points (•).
If not mentioned, return "Not Found".
"""
                response = await asyncio.to_thread(llm.generate, system_prompt, user_msg)
                return {"DSCR_Parameters": param, "NQMF Investor DSCR": response.strip()}
                
            except Exception as e:
                print(f"Error on {param}: {e}")
                return {"DSCR_Parameters": param, "NQMF Investor DSCR": "Error"}

    # Execute
    tasks = [process_one(p) for p in DSCR_Parameters]
    results = await asyncio.gather(*tasks)
    
    # Generate Excel
    return create_dscr_excel(results, session_id, investor, version)

def create_dscr_excel(data: List[Dict], session_id: str, investor: str, version: str) -> str:
    wb = Workbook()
    ws = wb.active
    ws.title = "DSCR Parameters"
    
    # Headers
    headers = ["DSCR_Parameters", "NQMF Investor DSCR"]
    
    # Styles
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    border_thin = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    alignment_wrap = Alignment(wrap_text=True, vertical='top', horizontal='left')
    
    # Write Headers
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        
    # Write Data
    for row_num, item in enumerate(data, 2):
        # Column 1: Parameter Name
        cell1 = ws.cell(row=row_num, column=1)
        cell1.value = item["DSCR_Parameters"]
        cell1.border = border_thin
        cell1.alignment = alignment_wrap
        
        # Column 2: Value
        cell2 = ws.cell(row=row_num, column=2)
        cell2.value = item["NQMF Investor DSCR"]
        cell2.border = border_thin
        cell2.alignment = alignment_wrap

    # Dimensions
    ws.column_dimensions['A'].width = 40
    ws.column_dimensions['B'].width = 80
    
    # File Path
    filename = f"DSCR_Extraction_{investor}_{version}_{session_id[:8]}.xlsx"
    
    # Save to 'results' folder in backend
    base_dir = os.getcwd()
    results_dir = os.path.join(base_dir, "results")
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
        
    filepath = os.path.join(results_dir, filename)
    
    wb.save(filepath)
    print(f"✅ DSCR Excel saved at: {filepath}")
    return filepath
