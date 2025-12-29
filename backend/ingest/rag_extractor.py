# backend/ingest/rag_extractor.py

import json
import asyncio
from typing import List, Dict
from chat.rag_service import RAGService
from utils.llm_provider import LLMProvider
from config import DEFAULT_TOC_EXTRACTION_PROMPT, DEFAULT_RAG_RULE_EXTRACTION_PROMPT
from utils.progress import update_progress

async def run_main_rag_extraction(
    session_id: str,
    gridfs_file_id: str,
    rag_service: RAGService,
    llm: LLMProvider,
    investor: str,
    version: str,
    user_settings: dict,
    text_chunks: List[tuple], # (text, pages)
    system_prompt: str = None, # Optional override
    user_prompt: str = None    # Optional override
) -> List[Dict]:
    """
    Orchestrates the RAG-based extraction process:
    1. Extract TOC/Categories (using LLM on the first chunk or summary)
    2. For each category, search vector DB for relevant context
    3. Extract specific rules using LLM + Context
    """
    
    print(f"🚀 Starting RAG-based Extraction for Session: {session_id[:8]}")
    
    # --- Step 1: Extract Table of Contents / Categories ---
    update_progress(session_id, 45, "Extracting Guide Structure (TOC)...")
    
    # We'll use the first few pages (likely containing TOC) or a compilation of headers
    # For efficiency, let's try to pass the first 10 pages (arbitrary limit)
    toc_context = ""
    for text, pages in text_chunks[:10]:
        toc_context += f"\n--- Page {pages} ---\n{text}"
    
    toc_structure = await extract_toc(llm, toc_context)
    
    if not toc_structure:
        # Fallback: If TOC extraction fails, maybe define some default generic categories?
        # Or try to process the whole document in very large chunks (expensive)
        print("⚠️ TOC Extraction failed. Using fallback default categories.")
        toc_structure = [
            {"category": "Credit", "sub_category": "Credit Score"},
            {"category": "Credit", "sub_category": "Credit History"},
            {"category": "Income", "sub_category": "Documentation"},
            {"category": "Income", "sub_category": "DTI"},
            {"category": "Assets", "sub_category": "Funds to Close"},
            {"category": "Property", "sub_category": "Appraisal"},
            {"category": "Property", "sub_category": "Property Types"},
            {"category": "Loan Terms", "sub_category": "LTV / CLTV"},
        ]
        
    print(f"✅ Extracted {len(toc_structure)} items for processing.")
    
    # --- Step 2: RAG Extraction per Item ---
    update_progress(session_id, 50, f"Extracting rules for {len(toc_structure)} sections...")
    
    results = []
    failed_count = 0
    completed = 0
    total_items = len(toc_structure)
    
    # Concurrency control
    semaphore = asyncio.Semaphore(5) # 5 Parallel LLM calls
    
    async def process_item(item: Dict):
        nonlocal results, failed_count, completed
        async with semaphore:
            try:
                category = item.get("category", "General")
                sub_category = item.get("sub_category", category)
                
                # 1. Search Context
                query = f"{category} - {sub_category}"
                
                # Use LLM's key/provider
                provider = llm.provider
                api_key = llm.api_key
                
                search_results = await rag_service.search(
                    query=query,
                    provider=provider,
                    api_key=api_key,
                    n_results=7, # Fetch detailed context
                    filter_metadata={"gridfs_file_id": gridfs_file_id},
                    azure_endpoint=user_settings.get("openai_endpoint"),
                    azure_deployment=user_settings.get("openai_deployment")
                )
                
                if not search_results:
                    print(f"⚠️ No context found for {query}")
                    return

                context_text = "\n\n".join([f"Source (Page {r['metadata'].get('page', '?')}): {r['text']}" for r in search_results])
                
                # 2. Extract Rule
                extracted = await extract_rule_via_rag(llm, context_text, category, sub_category)
                
                if extracted:
                    # Clean up: If extracted is a list, extend. If dict, append.
                    if isinstance(extracted, list):
                        results.extend(extracted)
                    elif isinstance(extracted, dict):
                        results.append(extracted)
                
            except Exception as e:
                print(f"❌ Failed to extract {category}/{sub_category}: {e}")
                failed_count += 1
            finally:
                completed += 1
                # Progress ranges from 50 to 90
                prog = 50 + int((completed / total_items) * 40)
                update_progress(session_id, prog, f"Processed {completed}/{total_items} sections")

    await asyncio.gather(*(process_item(item) for item in toc_structure))
    
    return results

async def extract_toc(llm: LLMProvider, context_text: str) -> List[Dict]:
    """
    Extracts high-level categories/subcategories to guide the RAG process.
    """
    prompt = DEFAULT_TOC_EXTRACTION_PROMPT
    user_msg = f"""
### DOCUMENT START (First 10~ pages)
{context_text[:50000]} # Limit char count to avoid context overflow

### INSTRUCTION
Identify the Table of Contents or the main Section Headers from the text above.
Return a JSON array of objects with "category" and "sub_category".
    """
    
    try:
        response = await asyncio.to_thread(llm.generate, "You are a document structure analyzer.", user_msg)
        return parse_json_response(response)
    except Exception as e:
        print(f"TOC Extraction Error: {e}")
        return []

async def extract_rule_via_rag(llm: LLMProvider, context: str, category: str, sub_category: str) -> List[Dict]:
    """
    Extracts the rule summary for a specific topic using retrieved context.
    """
    system_prompt = DEFAULT_RAG_RULE_EXTRACTION_PROMPT
    
    user_msg = f"""
### CONTEXT
{context}

### TARGET TOPIC
Category: {category}
Sub-Category: {sub_category}

### INSTRUCTION
Based strictly on the provided context, summarize the guidelines/rules for "{sub_category}" under "{category}".
If the context contains multiple distinct rules for this topic, create multiple objects.
If no relevant info is found, return an empty array [].
    """
    
    try:
        response = await asyncio.to_thread(llm.generate, system_prompt, user_msg)
        return parse_json_response(response)
    except Exception as e:
        print(f"Rule Extraction Error ({sub_category}): {e}")
        return []

def parse_json_response(response: str) -> List[Dict]:
    import re
    cleaned = re.sub(r'```json\s*|\s*```', '', response.strip())
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1: return []
    try:
        data = json.loads(cleaned[start:end+1])
        if isinstance(data, list): return data
        return []
    except: return []
