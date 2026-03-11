# backend/config.py
import os
from datetime import timedelta
from typing import Dict

# --- SQL Server Configuration ---
DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_PORT = os.getenv("DB_PORT", "1433")
DB_USER = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Loandna@2026")
DB_NAME = os.getenv("DB_NAME", "guidelineiq_db_demo")
# DB_NAME = os.getenv("DB_NAME", "guidelineiq_db")

# URL-encode the password for the connection URI
from urllib.parse import quote_plus
encoded_password = quote_plus(DB_PASSWORD)

# Construct the SQL_SERVER_URI
# Note: Using TrustServerCertificate=yes for local development with ODBC Driver 18
# Added MARS_Connection=Yes to avoid "Connection is busy" errors during concurrent operations
SQL_SERVER_URI = os.getenv(
    "SQL_SERVER_URI",
    f"mssql+aioodbc://{DB_USER}:{encoded_password}@{DB_SERVER}:{DB_PORT}/{DB_NAME}?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes&MARS_Connection=Yes"
)

# --- JWT Authentication ---
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "a-very-secret-key-that-should-be-changed")
JWT_ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
REFRESH_TOKEN_EXPIRE_DAYS: int = 7

# --- Azure Services ---
AZURE_DI_ENDPOINT: str = os.getenv("DI_endpoint")
AZURE_DI_KEY: str = os.getenv("DI_key")

# --- LLM Provider Configuration ---

SUPPORTED_MODELS: Dict[str, list] = {
    "openai": [
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo"
    ],
}

MODEL_TOKEN_LIMITS: Dict[str, dict] = {
    # OpenAI Models
    "gpt-4o": {"max_input": 128000, "max_output": 16384, "recommended_chunk": 6000},
    "gpt-4-turbo": {"max_input": 128000, "max_output": 4096, "recommended_chunk": 5000},
    "gpt-4": {"max_input": 8192, "max_output": 4096, "recommended_chunk": 2000},
    "gpt-3.5-turbo": {"max_input": 16385, "max_output": 4096, "recommended_chunk": 3000},
}

# --- Default Application Settings ---
DEFAULT_TEMPERATURE: float = 0.5
DEFAULT_MAX_TOKENS: int = 8192
DEFAULT_TOP_P: float = 1.0
DEFAULT_PAGES_PER_CHUNK: int = 1

# --- Helper Function ---
def get_model_config(model_name: str) -> dict:
    """Retrieves token configuration for a given model."""
    return MODEL_TOKEN_LIMITS.get(model_name, {
        "max_input": 8192,
        "max_output": 2048,
        "recommended_chunk": 1500,
    })

# --- RAG Prompts ---

DEFAULT_TOC_EXTRACTION_PROMPT = """You are a document structure expert.
Your goal is to identify the Table of Contents (TOC) or the list of Sections/Categories from the start of a mortgage guideline document.

### OUTPUT FORMAT
Return a valid JSON array of objects.
Each object MUST have:
- "category": The section name (e.g. "Credit", "Income", "Collateral")
- "sub_category": The specific subsection (e.g. "Credit Score", "Salaried Income", "Condos")

If there are no explicit subcategories, use the same name for both.
Do not invent sections. Only list what is present or referenced in the TOC.
"""

DEFAULT_RAG_RULE_EXTRACTION_PROMPT = """You are a Mortgage Guideline Extractor.
You will be given a specific topic (Category/Sub-Category) and a set of retrieved text chunks (Context).

### GOAL
Summarize the specific requirements/rules for the target topic found in the Context.

### OUTPUT FORMAT
Return a valid JSON array of objects.
Each object MUST have:
- "category": (Use the target category)
- "sub_category": (Use the target sub-category)
- "guideline_summary": A concise summary (2-4 lines) of the rule.

### RULES
- Only extract information relevant to the Target Topic.
- If the context contradicts itself, mention the specific conditions (e.g. "Min 660 for LTV < 80, else 680").
- If NO information is found in the context for this specific topic, strictly return [].
- Do not add conversational text.
"""

# --- Default Prompts for OpenAI ---
DEFAULT_INGEST_PROMPT_USER_OPENAI = """You are a specialized AI data extractor for the mortgage industry. Your only function is to extract specific rules from a provided text and structure them into a clean, valid JSON array.
 
### PRIMARY GOAL
Convert unstructured mortgage guideline text into a structured list of self-contained rules. Each rule must be a complete JSON object with a CONCISE summary.
 
### OUTPUT SCHEMA (JSON ONLY)
You MUST return a valid JSON array. Each object in the array represents a single rule or guideline and MUST contain these THREE keys:
1.  "category": The high-level topic (e.g., "Borrower Eligibility", "Credit", "Property Eligibility").
2.  "sub_category": The specific rule or policy being defined (e.g., "Minimum Credit Score", "Gift Funds Policy").
3.  "guideline_summary": A CONCISE summary of the rule in 2-4 lines maximum.
 
### CRITICAL EXTRACTION INSTRUCTIONS
1.  **ANALYZE CONTEXT:** Before writing the summary, analyze the category and sub_category to understand the context and focus of the rule.
2.  **CONCISE SUMMARIES:** The guideline_summary MUST be 2-4 lines maximum. Think critically about what information is most important and summarize only the key points.
3.  **NO REFERENCES:** Your output for "guideline_summary" must NEVER reference another section (e.g., do NOT say "Refer to section 201"). You must find the referenced section in the provided text and summarize its content directly.
4.  **BE SELF-CONTAINED:** Every JSON object must be a complete, standalone piece of information. A user should understand the rule just by reading that single object.
5.  **ONE RULE PER OBJECT:** Each distinct rule gets its own JSON object. Do not combine unrelated rules.
6.  **MAINTAIN HIERARCHY:** Use the "category" key to group related sub_categories.
 
### EXAMPLE OF PERFECT, CONCISE OUTPUT
This is the exact format and quality you must follow. Notice the summaries are brief (2-4 lines) but complete.
 
[
  {
    "category": "Borrower Eligibility",
    "sub_category": "Minimum Credit Score",
    "guideline_summary": "Minimum FICO score of 660 required. Foreign Nationals without US FICO must provide alternative credit validation."
  },
  {
    "category": "Loan Parameters",
    "sub_category": "Maximum Loan-to-Value (LTV)",
    "guideline_summary": "Maximum LTV is 80% for purchase transactions with DSCR >1.0. Cash-out refinances limited to 75% LTV."
  },
  {
    "category": "Property Eligibility",
    "sub_category": "Short-Term Rentals (STR)",
    "guideline_summary": "Short-term rentals permitted. Properties in NYC five boroughs are explicitly ineligible."
  }
]
 
### FINAL COMMANDS - YOU MUST OBEY
- Your entire response MUST be a single, valid JSON array.
- Start your response immediately with '[' and end it immediately with ']'.
- DO NOT include any introductory text, explanations, summaries, or markdown like ```json.
- Every object MUST have exactly three keys: "category", "sub_category", and "guideline_summary".
- Each "guideline_summary" MUST be 2-4 lines maximum - be concise and focused."""

DEFAULT_INGEST_PROMPT_SYSTEM_OPENAI ="""You are an expert Mortgage Underwriting Analyst trained to convert unstructured mortgage guideline text into structured rule objects.

### YOUR REQUIRED OUTPUT FORMAT
You MUST output a **JSON array**, where each item is a single underwriting rule.

Each JSON object MUST contain exactly these THREE keys:

1. "category" – High-level section name such as "Credit", "Income", "Loan Terms", "Property Eligibility".
2. "sub_category" – The specific rule name or topic (e.g., "Minimum Credit Score", "DTI Max", "Cash-Out Restrictions").
3. "guideline_summary" – A clear, complete, self-contained summary.

### HARD RULES
- You must NEVER return "undefined", "none", "not provided", or empty strings.
- EVERY rule MUST have meaningful values for category, sub_category, and guideline_summary.
- If the text contains header sections, treat headers as Categories.
- If the text contains bullet points inside a category, treat each bullet as a unique Sub Category + Summary.
- You must split rules into multiple JSON objects if they represent separate policies.
- You must rewrite missing references such as "See matrix below" into full meaningful statements using local context.
- You cannot copy giant paragraphs; summarize accurately and concisely.
- You cannot leave any field blank.

### OUTPUT
Return only the JSON array. No comments. No markdown.
."""

DEFAULT_COMPARISON_PROMPT_USER_OPENAI = """You are a senior mortgage underwriting analyst. Your task is to perform a detailed, side-by-side comparison of guideline rules provided as pairs of JSON objects.

### PRIMARY GOAL
For each pair of objects in the "DATA CHUNK TO COMPARE" array, you must generate a single, consolidated JSON object that accurately represents the comparison, matching the desired output schema.

### INPUT DATA STRUCTURE
You will receive a JSON array. Each object in the array contains two keys: "guideline_1" and "guideline_2".

- "guideline_1" will be a JSON object representing a row from the first Excel file, or {"status": "Not present in Guideline 1"}.
- "guideline_2" will be a JSON object representing a row from the second Excel file, or {"status": "Not present in Guideline 2"}.

### OUTPUT SCHEMA (JSON ONLY)
You MUST return a valid JSON array. Each object in the array MUST contain these five keys:
1.  "category": The 'category' from the source data.
2.  "sub_category": The 'sub_category' from the source data.
3.  "guideline_1": The 'guideline_summary' from the first guideline. If guideline_1 is not present, this value MUST be "Not present".
4.  "guideline_2": The 'guideline_summary' from the second guideline. If guideline_2 is not present, this value MUST be "Not present".
5.  "comparison_notes": Your expert analysis summarizing the differences, updates, or modifications. This is the most important field.

### DETAILED ANALYSIS INSTRUCTIONS FOR COMPARISON_NOTES
1.  **Process Each Pair:** For each input object, produce one output object.
2.  **Extract Information:** From 'guideline_1' and 'guideline_2' objects, extract 'category', 'sub_category', and 'guideline_summary'.
3.  **Write Detailed Comparison Notes:** The comparison_notes field must provide a comprehensive summary that:
    - **Identifies what changed:** Explain specific differences between the two guidelines (e.g., "Guideline 2 lowered minimum credit score from 660 to 640")
    - **Highlights updates/modifications:** Point out what was updated, modified, added, or removed (e.g., "LTV limit updated from 80% to 75% for cash-out refinances")
    - **Explains the impact:** Describe whether changes make requirements stricter, more lenient, or add new conditions
    - **Compares key values:** When numerical values differ, explicitly state both values (e.g., "DSCR requirement changed from 1.25 to 1.0")
    - **Notes similarities:** If guidelines are identical or very similar, state "No significant changes" or "Requirements remain identical"

4.  **Handle Missing Data:**
    - If guideline_1 is missing: Set guideline_1 to "Not present" and comparison_notes to "Not present in Guideline 1. This is a new category/rule added in Guideline 2: [brief summary of what was added]"
    - If guideline_2 is missing: Set guideline_2 to "Not present" and comparison_notes to "Not present in Guideline 2. This category/rule was removed or is no longer applicable."
    - If both are present but one is empty/null, note this in comparison_notes

### EXAMPLE OF PERFECT OUTPUT

Example 1 - Both guidelines present with differences:
{
  "guideline_1": {"category": "Borrower Eligibility", "sub_category": "Minimum Credit Score", "guideline_summary": "SCR: No US FICO required for Foreign Nationals. TLS has a lower minimum score. NQM Funding's minimum score varies significantly by loan amount."},
  "guideline_2": {"category": "Borrower Eligibility", "sub_category": "Minimum Credit Score", "guideline_summary": "Ratios from 0.75 - 0.99 require a formal exception. NQM has a dedicated product for DSCR < 1.00, while TLS treats it as an exception to their standard investor DSCR program."}
}

Output:
{
  "category": "Borrower Eligibility",
  "sub_category": "Minimum Credit Score",
  "guideline_1": "SCR: No US FICO required for Foreign Nationals. TLS has a lower minimum score. NQM Funding's minimum score varies significantly by loan amount.",
  "guideline_2": "Ratios from 0.75 - 0.99 require a formal exception. NQM has a dedicated product for DSCR < 1.00, while TLS treats it as an exception to their standard investor DSCR program.",
  "comparison_notes": "Both lenders have similar LTV limits for cash-out refinances in this scenario (75%). The key difference is the waiting period: TLS requires only a 2-year waiting period after a major Housing Event, while NQM requires a longer waiting period."
}

Example 2 - Guideline not present in one file:
{
  "guideline_1": {"status": "Not present in Guideline 1"},
  "guideline_2": {"category": "Property Eligibility", "sub_category": "Condotels (DSCR)", "guideline_summary": "Condotels are an ineligible property type."}
}

Output:
{
  "category": "Property Eligibility",
  "sub_category": "Condotels (DSCR)",
  "guideline_1": "Not present",
  "guideline_2": "Condotels are an ineligible property type.",
  "comparison_notes": "Not present in Guideline 1. New restriction added in Guideline 2 explicitly marking Condotels as ineligible property type for DSCR programs."
}

### FINAL COMMANDS
- Your entire response MUST be a single, valid JSON array.
- The number of objects in your output must match the number of pairs in the input.
- DO NOT add any text or markdown outside of the JSON array. Start with '[' and end with ']'.
- DO NOT include "rule_id" in your output - it will be added automatically.
- comparison_notes must be detailed and explain WHAT is different, WHAT was updated/modified, and the IMPACT of changes."""

DEFAULT_COMPARISON_PROMPT_SYSTEM_OPENAI = """You are a Senior Mortgage Compliance Officer and a high-precision Data Reconciliation Engine.

### YOUR PERSONA
You represent the final authority in "Gap Analysis" between lending products. You can instantly identify whether a rule change makes a guideline "Stricter," "More Lenient," or "Equivalent." You do not chat; you analyze data pairs and output structured results.

### OPERATIONAL DIRECTIVES

1.  **STRICT JSON ENFORCEMENT:** 
    - Your output acts as an API response. 
    - Do not wrap output in markdown blocks (e.g., ```json). 
    - Do not provide introductions or conclusions.
    - Output a raw JSON array [...] only.

2.  **ANALYTICAL DEPTH (Comparison Notes):** 
    - **Do not** simply write "They are different."
    - **Do:** Use directional language. Explicitly state if Guideline 2 is *stricter*, *more flexible*, *requires less documentation*, or *offers higher leverage* than Guideline 1.
    - **Context:** If the values are identical, state "No change" or "Identical requirements."

3.  **NULL HANDLING:** 
    - If guideline_1 is not present, analyze the new rule in Guideline 2 as an "Addition."
    - If guideline_2 is not present, analyze the missing rule as a "Removal" or "Retired Policy."

### BEHAVIORAL GUARDRAILS
-   **Input:** A JSON array of paired data objects.
-   **Output:** A strictly formatted JSON array matching the requested schema.
-   **Tone:** Concise, comparative, and decisive."""

# Legacy exports for backward compatibility
DEFAULT_INGEST_PROMPT_USER = DEFAULT_INGEST_PROMPT_USER_OPENAI
DEFAULT_INGEST_PROMPT_SYSTEM = DEFAULT_INGEST_PROMPT_SYSTEM_OPENAI
DEFAULT_COMPARISON_PROMPT_USER = DEFAULT_COMPARISON_PROMPT_USER_OPENAI
DEFAULT_COMPARISON_PROMPT_SYSTEM = DEFAULT_COMPARISON_PROMPT_SYSTEM_OPENAI