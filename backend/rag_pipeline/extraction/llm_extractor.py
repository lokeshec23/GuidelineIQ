# backend/rag_pipeline/extraction/llm_extractor.py
"""
LLM-based extraction with strict JSON output (temperature=0)
"""

import json
import asyncio
from typing import List, Dict
import logging
from openai import AzureOpenAI

from rag_pipeline.models import ExtractionResult, Citation, RetrievalResult, Chunk, ChunkType
from rag_pipeline.config import RAGConfig

logger = logging.getLogger(__name__)


class LLMExtractor:
    """
    LLM-based extractor with deterministic output (temperature=0)
    """
    
    def __init__(self):
        self.config = RAGConfig
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Azure OpenAI client"""
        try:
            self.client = AzureOpenAI(
                api_key=self.config.AZURE_OPENAI_API_KEY,
                api_version=self.config.AZURE_OPENAI_API_VERSION,
                azure_endpoint=self.config.AZURE_OPENAI_ENDPOINT
            )
            logger.info(
                f"Initialized LLM extractor with deployment: "
                f"{self.config.AZURE_OPENAI_DEPLOYMENT_NAME}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {e}")
            raise
    
    async def extract(
        self,
        parameter: str,
        evidence_chunks: List[RetrievalResult],
        context: Dict = None
    ) -> ExtractionResult:
        """
        Extract parameter value from evidence chunks
        
        Args:
            parameter: Parameter name to extract
            evidence_chunks: Retrieved chunks as evidence
            context: Additional context (category, subcategory, etc.)
        
        Returns:
            ExtractionResult with value and citations
        """
        if not evidence_chunks:
            return ExtractionResult(
                parameter=parameter,
                value="N/A",
                needs_clarification=True,
                clarification_reason="No evidence found in guidelines",
                citations=[]
            )
        
        # Build prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(parameter, evidence_chunks, context)
        
        # Call LLM with temperature=0
        try:
            response = await asyncio.to_thread(
                self._call_llm,
                system_prompt,
                user_prompt
            )
            
            # Parse JSON response
            extraction_data = self._parse_llm_response(response)
            
            # Create ExtractionResult
            result = ExtractionResult(
                parameter=parameter,
                value=extraction_data.get("value", "N/A"),
                needs_clarification=extraction_data.get("needs_clarification", False),
                clarification_reason=extraction_data.get("clarification_reason"),
                citations=[
                    Citation(
                        page=c.get("page", 0),
                        excerpt=c.get("excerpt", ""),
                        source_file=c.get("source_file")
                    )
                    for c in extraction_data.get("citations", [])
                ]
            )
            
            logger.info(f"Extracted {parameter}: {result.value[:50]}...")
            return result
        
        except Exception as e:
            logger.error(f"Extraction failed for {parameter}: {e}")
            return ExtractionResult(
                parameter=parameter,
                value="Error during extraction",
                needs_clarification=True,
                clarification_reason=str(e),
                citations=[]
            )
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for extraction"""
        return """You are a mortgage guideline extraction expert.

Your task is to extract specific parameter values from provided evidence chunks.

CRITICAL RULES:
1. Extract ONLY information explicitly stated in the evidence.
2. DO NOT use external knowledge or general mortgage standards (e.g., do not assume "0x30x12" unless stated).
3. DO NOT hallucinate or infer conditions that are not present.
4. If information is unclear or contradictory, flag for clarification.
5. Always provide citations with page numbers.
6. EXPLICITLY CAPTURE ANY RESTRICTIONS, EXCLUSIONS, OR "NOT PERMITTED" ITEMS.

OUTPUT SCHEMA:
{
    "value": "extracted value or detailed summary",
    "needs_clarification": true/false,
    "clarification_reason": "reason if clarification needed (or null)",
    "citations": [
        {
            "page": page_number,
            "excerpt": "relevant text excerpt",
            "source_file": "filename (if available)"
        }
    ]
}"""
    
    def _build_user_prompt(
        self,
        parameter: str,
        evidence_chunks: List[RetrievalResult],
        context: Dict = None
    ) -> str:
        """Build user prompt with evidence"""
        context_str = ""
        if context:
            context_str = f"""
CONTEXT:
- Category: {context.get('category', 'N/A')}
- Sub-Category: {context.get('subcategory', 'N/A')}
- Field Type: {context.get('ppe_field', 'N/A')}
"""
        
        # Format evidence chunks
        evidence_str = ""
        for idx, result in enumerate(evidence_chunks, 1):
            chunk = result.chunk
            evidence_str += f"""
--- Evidence {idx} ---
Source: {chunk.metadata.get('filename', 'Unknown')}
Pages: {chunk.page_start}-{chunk.page_end}
Section: {chunk.section_path}
Type: {chunk.chunk_type.value}

{chunk.text}

"""
        
        prompt = f"""PARAMETER TO EXTRACT: {parameter}
{context_str}
EVIDENCE FROM GUIDELINES:
{evidence_str}

TASK:
Extract the requirements, limits, and conditions for "{parameter}" from the evidence above.

INSTRUCTIONS:
1. Synthesize information from all evidence chunks
2. If evidence contains tables/matrices, extract key values
3. If requirements vary by condition (e.g., LTV, FICO), specify conditions
4. CAPTURE NEGATIVE CRITERIA: Explicitly state what is NOT permitted, ineligible, or restricted (e.g., "Texas 50(a)(6) not permitted").
5. If evidence is contradictory or unclear, set needs_clarification=true
6. Provide citations for each key piece of information
7. If no relevant information found, set value="N/A" and needs_clarification=true

OUTPUT:
Return ONLY valid JSON matching the schema. No markdown, no explanations."""
        
        return prompt
    
    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call Azure OpenAI with temperature=0
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
        
        Returns:
            LLM response text
        """
        response = self.client.chat.completions.create(
            model=self.config.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=self.config.EXTRACTION_TEMPERATURE,  # 0.0 for deterministic
            max_tokens=self.config.MAX_TOKENS,
            response_format={"type": "json_object"}  # Force JSON output
        )
        
        return response.choices[0].message.content
    
    def _parse_llm_response(self, response: str) -> Dict:
        """
        Parse and validate LLM JSON response
        
        Args:
            response: LLM response text
        
        Returns:
            Parsed dictionary
        """
        try:
            # Clean response
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Parse JSON
            data = json.loads(cleaned)
            
            # Validate required fields
            required_fields = ["value", "needs_clarification", "citations"]
            for field in required_fields:
                if field not in data:
                    logger.warning(f"Missing field in LLM response: {field}")
                    if field == "value":
                        data["value"] = "N/A"
                    elif field == "needs_clarification":
                        data["needs_clarification"] = True
                    elif field == "citations":
                        data["citations"] = []
            
            return data
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response: {response[:200]}...")
            return {
                "value": "Error: Invalid JSON response",
                "needs_clarification": True,
                "clarification_reason": "LLM returned invalid JSON",
                "citations": []
            }

    async def summarize(
        self,
        parameter: str,
        evidence_chunks: List[RetrievalResult],
        context: Dict = None
    ) -> ExtractionResult:
        """
        Generate a comprehensive paragraph summary from evidence chunks
        
        Args:
            parameter: Topic to summarize
            evidence_chunks: Retrieved chunks as evidence
            context: Additional context
        
        Returns:
            ExtractionResult with summary and citations
        """
        if not evidence_chunks:
            return ExtractionResult(
                parameter=parameter,
                value="N/A",
                needs_clarification=True,
                clarification_reason="No evidence found",
                citations=[]
            )
        
        # Map-Reduce for large chunk counts
        BATCH_SIZE = 15  # Limit chunks per call to stay safe within context window
        
        if len(evidence_chunks) <= BATCH_SIZE:
            return await self._summarize_batch(parameter, evidence_chunks, context)
        
        # MAP STEP: Summarize batches concurrently
        batches = [evidence_chunks[i:i + BATCH_SIZE] for i in range(0, len(evidence_chunks), BATCH_SIZE)]
        logger.info(f"Summarizing {len(evidence_chunks)} chunks in {len(batches)} batches...")
        
        tasks = [self._summarize_batch(parameter, batch, context) for batch in batches]
        batch_results = await asyncio.gather(*tasks)
        
        # Filter successful summaries
        intermediate_summaries = [res for res in batch_results if not res.needs_clarification and res.value != "N/A"]
        
        if not intermediate_summaries:
             return ExtractionResult(
                parameter=parameter,
                value="N/A",
                needs_clarification=True,
                clarification_reason="No valid info found in any batch",
                citations=[]
            )

        # REDUCE STEP: Summarize the summaries
        # Construct "meta-chunks" from intermediate summaries to feed into final reduction
        meta_chunks = []
        all_citations = []
        
        for idx, res in enumerate(intermediate_summaries):
            all_citations.extend(res.citations)
            meta_chunks.append(RetrievalResult(
                chunk=Chunk(
                    id=f"summary_{idx}",
                    text=res.value,
                    chunk_type=ChunkType.NARRATIVE, # Dummy
                    section_path="Summary",
                    page_start=0,
                    page_end=0,
                    metadata={"filename": "Intermediate Summary"}
                ),
                score=1.0,
                retrieval_method="summary"
            ))
            
        final_result = await self._summarize_batch(
            parameter, 
            meta_chunks, 
            context, 
            is_final_reduction=True
        )
        
        # Attach aggregated citations
        final_result.citations = all_citations
        return final_result

    async def _summarize_batch(
        self,
        parameter: str,
        evidence_chunks: List[RetrievalResult],
        context: Dict = None,
        is_final_reduction: bool = False
    ) -> ExtractionResult:
        """Internal helper to summarize a specific batch of chunks"""
        
        # Build prompt for summarization
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_summary_user_prompt(parameter, evidence_chunks, context, is_final_reduction)
        
        try:
            response = await asyncio.to_thread(
                self._call_llm,
                system_prompt,
                user_prompt
            )
            
            extraction_data = self._parse_llm_response(response)
            
            return ExtractionResult(
                parameter=parameter,
                value=extraction_data.get("value", "N/A"),
                needs_clarification=extraction_data.get("needs_clarification", False),
                clarification_reason=extraction_data.get("clarification_reason"),
                citations=[
                    Citation(
                        page=c.get("page", 0),
                        excerpt=c.get("excerpt", ""),
                        source_file=c.get("source_file")
                    )
                    for c in extraction_data.get("citations", [])
                ]
            )
            
        except Exception as e:
            logger.error(f"Batch summarization failed: {e}")
            return ExtractionResult(
                parameter=parameter,
                value=f"Error: {str(e)}",
                needs_clarification=True,
                clarification_reason=str(e),
                citations=[]
            )

    def _build_summary_user_prompt(
        self,
        parameter: str,
        evidence_chunks: List[RetrievalResult],
        context: Dict = None,
        is_final_reduction: bool = False
    ) -> str:
        """Build user prompt specifically for summarization"""
        context_str = ""
        if context:
            context_str = f"""
CONTEXT:
- Category: {context.get('category', 'N/A')}
- Sub-Category: {context.get('subcategory', 'N/A')}
"""
        evidence_str = ""
        for idx, result in enumerate(evidence_chunks, 1):
            chunk = result.chunk
            source_info = "Intermediate Summary" if is_final_reduction else f"{chunk.metadata.get('filename', 'Unknown')} (pg {chunk.page_start})"
            
            evidence_str += f"""
--- Evidence {idx} ---
Source: {source_info}
Content:
{chunk.text}
"""
        
        task_instruction = (
            "Synthesize these intermediate summaries into one final, coherent paragraph summary."
            if is_final_reduction else
            "Write a comprehensive paragraph summary about the topic based on the evidence."
        )

        return f"""TOPIC TO SUMMARIZE: {parameter}
{context_str}
EVIDENCE:
{evidence_str}

TASK:
{task_instruction}

INSTRUCTIONS:
1. Synthesize all relevant details into a coherent paragraph.
2. Focus on requirements, limits, exceptions, and conditions.
3. If multiple sources disagree, mention the conflict.
4. Do NOT use bullet points. Write in full sentences.
5. If no relevant info is found, say "No specific guidelines found for {parameter}".
6. Provide citations.

OUTPUT:
Return JSON:
{{
    "value": "Comprehensive paragraph summary...",
    "needs_clarification": false,
    "citations": [...]
}}"""

    # ==========================================
    # NQMF-SPECIFIC EXTRACTION METHODS
    # ==========================================

    async def extract_nqmf(
        self,
        parameter: str,
        evidence_chunks: List[RetrievalResult],
        context: Dict = None
    ) -> ExtractionResult:
        """
        Extract parameter value using NQMF-specific prompt format with hard/soft classification.
        Returns classified bullet-formatted underwriting rules for Excel output.
        
        Args:
            parameter: Parameter name to extract
            evidence_chunks: Retrieved chunks as evidence
            context: Additional context (category, subcategory, ppe_field)
        
        Returns:
            ExtractionResult with classified hard_value and soft_value
        """
        if not evidence_chunks:
            return ExtractionResult(
                parameter=parameter,
                value="Not present",
                hard_value="",
                soft_value="",
                needs_clarification=False,
                clarification_reason=None,
                citations=[],
                hard_citations=[],
                soft_citations=[]
            )
        
        # Limit evidence chunks to prevent context overflow
        # Keep only the top-ranked chunks (they're already sorted by relevance score)
        MAX_CHUNKS_FOR_NQMF = 30
        if len(evidence_chunks) > MAX_CHUNKS_FOR_NQMF:
            logger.warning(
                f"Truncating evidence from {len(evidence_chunks)} to {MAX_CHUNKS_FOR_NQMF} chunks "
                f"for parameter '{parameter}' to prevent context overflow"
            )
            evidence_chunks = evidence_chunks[:MAX_CHUNKS_FOR_NQMF]
        
        # Build NQMF-specific prompts
        system_prompt = self._build_nqmf_system_prompt()
        user_prompt = self._build_nqmf_user_prompt(parameter, evidence_chunks, context)
        
        # Call LLM with temperature=0
        try:
            response = await asyncio.to_thread(
                self._call_llm,
                system_prompt,
                user_prompt
            )
            
            # Parse NQMF JSON response (now with classification)
            extraction_data = self._parse_nqmf_response(response)
            
            # Extract classified bullets
            hard_bullets = extraction_data.get("hard_bullets", [])
            soft_bullets = extraction_data.get("soft_bullets", [])
            hard_citation_indices = extraction_data.get("hard_citation_indices", [])
            soft_citation_indices = extraction_data.get("soft_citation_indices", [])
            
            # Build hard_value and soft_value strings
            hard_value = "\n".join(hard_bullets) if hard_bullets else ""
            soft_value = "\n".join(soft_bullets) if soft_bullets else ""
            
            # Build citations for hard bullets
            hard_citations = []
            for idx in hard_citation_indices:
                if 0 <= idx < len(evidence_chunks):
                    chunk = evidence_chunks[idx].chunk
                    hard_citations.append(Citation(
                        page=chunk.page_start,
                        excerpt=chunk.text[:150],  # First 150 chars
                        source_file=chunk.metadata.get('filename')
                    ))
            
            # Build citations for soft bullets
            soft_citations = []
            for idx in soft_citation_indices:
                if 0 <= idx < len(evidence_chunks):
                    chunk = evidence_chunks[idx].chunk
                    soft_citations.append(Citation(
                        page=chunk.page_start,
                        excerpt=chunk.text[:150],  # First 150 chars
                        source_file=chunk.metadata.get('filename')
                    ))
            
            # Combined value for legacy support
            combined_value = hard_value
            if soft_value:
                combined_value += ("\n" if combined_value else "") + soft_value
            if not combined_value:
                combined_value = "Not present"
            
            # Create ExtractionResult with classification
            result = ExtractionResult(
                parameter=parameter,
                value=combined_value,  # Legacy field
                hard_value=hard_value,
                soft_value=soft_value,
                needs_clarification=False,
                clarification_reason=None,
                citations=hard_citations + soft_citations,  # Combined for legacy
                hard_citations=hard_citations,
                soft_citations=soft_citations
            )
            
            logger.info(
                f"NQMF extracted {parameter}: "
                f"HARD={len(hard_bullets)} bullets, SOFT={len(soft_bullets)} bullets"
            )
            return result
        
        except Exception as e:
            logger.error(f"NQMF extraction failed for {parameter}: {e}")
            return ExtractionResult(
                parameter=parameter,
                value="Not present",
                hard_value="",
                soft_value="",
                needs_clarification=False,
                clarification_reason=None,
                citations=[],
                hard_citations=[],
                soft_citations=[]
            )

    def _build_nqmf_system_prompt(self) -> str:
        """Build NQMF-specific system prompt (Claude-hardened) with hard/soft classification"""
        return """SYSTEM ROLE (STRICT):

You are generating underwriting guideline text
that will be written directly into an Excel cell
for NQMF comparison worksheets.

You are NOT a summarizer.
You are NOT an explainer.
You are NOT allowed to generalize policy.

Your output must visually and linguistically match
NQMF Excel Column-5 content.

================================================
EXCEL CONTEXT (READ-ONLY)
================================================

This output corresponds to:

• Sheet 2: NQMF Flex Select
• Sheet 3: NQMF Investor DSCR (1-4 Units)
• Column 5 only

Headers, rows, and PPE classification already exist.
You generate ONLY the cell value.

================================================
ROW SCOPE (CRITICAL)
================================================

You are processing EXACTLY ONE parameter (one row).

You must NOT:
• Create new rows
• Merge with other parameters
• Reference other parameters
• Change PPE type

================================================
OUTPUT STYLE (MATCH EXCEL)
================================================

Column-5 text MUST:

• Use bullet points starting with: "• "
• Match Excel tone: underwriting / compliance language
• Be lightly cleaned for clarity ONLY
• Preserve structure similar to NQMF sheets
• Avoid conversational or AI-style phrasing

================================================
CONTENT RULES (NON-NEGOTIABLE)
================================================

1. Bullet Structure
   • Extract ALL relevant rules and conditions as separate bullets
   • Each bullet = one enforceable rule or condition
   • No paragraphs outside bullets
   • Each bullet on a new line

2. Language Discipline
   • Use declarative underwriting language
   • Preserve numeric thresholds exactly
   • Preserve conditions and exceptions
   • Avoid vague terms: generally, typically, may vary

3. Tables
   • If limits appear in tables, extract exact values
   • Do NOT explain the table
   • Do NOT restate table layout

4. Multi-PDF Conflicts
   • If multiple values exist for the same parameter, list all values as separate bullets
   • Do NOT append source filenames or file references

   Example:
   • Maximum LTV is limited to 70%.
   • Maximum LTV is limited to 75%.

5. Missing Evidence
   • If the parameter is not explicitly stated → output:
     Not present

   (Exactly "Not present", no bullets, no explanation.)

================================================
CLASSIFICATION RULES (CRITICAL)
================================================

After extracting bullets, classify EACH bullet as either:

**HARD** = Strict requirement that MUST be followed
   Indicators:
   • Keywords: must, required, not permitted, prohibited, not allowed, shall, cannot
   • Contains specific numeric limits (maximum, minimum, exact values)
   • Absolute statements without qualifiers
   • Definitive restrictions or exclusions
   
   Examples:
   • Maximum LTV is limited to 70%.
   • Texas 50(a)(6) loans are not permitted.
   • Minimum FICO score required is 680.

**SOFT** = Flexible guideline with potential exceptions
   Indicators:
   • Keywords: may, typically, generally, usually, can
   • Phrases: exceptions, subject to approval, at lender's discretion, case-by-case
   • Manual review or underwriter approval required
   • Conditional or flexible statements
   
   Examples:
   • Exceptions may be considered with approval.
   • Subject to underwriter review.
   • Additional documentation may be requested.

**DEFAULT RULE:**
If classification is ambiguous, default to HARD.

================================================
PROHIBITED OUTPUT
================================================

You MUST NOT:
• Write summaries
• Combine multiple parameters
• Add interpretations or recommendations
• Explain rationale
• Add headings
• Add markdown (except in bullet content)
• Add extra keys beyond what's specified
• Add chain-of-thought

================================================
OUTPUT FORMAT (ABSOLUTE)
================================================

Return ONLY valid JSON:

{
  "hard_bullets": ["• Bullet 1", "• Bullet 2"],
  "soft_bullets": ["• Bullet 1"],
  "hard_citation_indices": [0, 1, 2],
  "soft_citation_indices": [3]
}

OR if no bullets found:

{
  "hard_bullets": [],
  "soft_bullets": []
}

Rules:
• Bullets must start with "• "
• New lines separated by \\n within each bullet if needed
• citation_indices refer to the evidence chunk numbers (0-indexed)
• If all bullets are one type, the other array can be empty
• No trailing commentary
• If NO evidence found, return empty arrays (not "Not present" in this format)

================================================
FINAL ENFORCEMENT
================================================

If evidence is weak → fewer bullets.
If evidence is absent → empty arrays.
If evidence conflicts → classify each conflicting value.
If ambiguous classification → default to HARD.

Execute with maximum restraint."""


    def _build_nqmf_user_prompt(
        self,
        parameter: str,
        evidence_chunks: List[RetrievalResult],
        context: Dict = None
    ) -> str:
        """Build NQMF-specific user prompt with evidence"""
        # Context information
        context_str = ""
        if context:
            context_str = f"""
================================================
PARAMETER CONTEXT
================================================

Parameter: {parameter}
Category: {context.get('category', 'N/A')}
Subcategory: {context.get('subcategory', 'N/A')}
PPE Field Type: {context.get('ppe_field', 'N/A')} (already fixed)
"""
        
        # Format evidence chunks with truncation to prevent context overflow
        evidence_str = ""
        max_chunk_length = self.config.MAX_EVIDENCE_CHUNK_LENGTH
        
        for idx, result in enumerate(evidence_chunks, 1):
            chunk = result.chunk
            source_file = chunk.metadata.get('filename', 'Unknown')
            
            # Truncate chunk text if it exceeds max length
            chunk_text = chunk.text
            if len(chunk_text) > max_chunk_length:
                chunk_text = chunk_text[:max_chunk_length] + "... [truncated]"
            
            evidence_str += f"""
--- Evidence {idx} ---
Source: {source_file}
Pages: {chunk.page_start}-{chunk.page_end}
Section: {chunk.section_path}

{chunk_text}

"""
        
        prompt = f"""{context_str}

================================================
RETRIEVED GUIDELINE EVIDENCE
================================================
{evidence_str}

================================================
TASK
================================================

Extract the underwriting rules for "{parameter}" from the evidence above.

Classify each extracted bullet as HARD or SOFT based on the classification rules.

Output ONLY the JSON with these keys:
• "hard_bullets": array of HARD requirement bullets
• "soft_bullets": array of SOFT guideline bullets
• "hard_citation_indices": array of evidence indices (0-based) for hard bullets
• "soft_citation_indices": array of evidence indices (0-based) for soft bullets

If no evidence found, return empty arrays.
No explanations. No extra keys. No commentary. No source filenames."""
        
        return prompt

    def _parse_nqmf_response(self, response: str) -> Dict:
        """
        Parse and validate NQMF-specific JSON response with hard/soft classification
        
        Args:
            response: LLM response text
        
        Returns:
            Parsed dictionary with hard_bullets and soft_bullets arrays
        """
        try:
            # Clean response
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Parse JSON
            data = json.loads(cleaned)
            
            # Validate new classification format
            if "hard_bullets" not in data or "soft_bullets" not in data:
                logger.warning("Missing hard_bullets or soft_bullets in LLM response")
                # Default to empty arrays if not found
                return {
                    "hard_bullets": [],
                    "soft_bullets": [],
                    "hard_citation_indices": [],
                    "soft_citation_indices": []
                }
            
            # Ensure arrays exist
            hard_bullets = data.get("hard_bullets", [])
            soft_bullets = data.get("soft_bullets", [])
            hard_citation_indices = data.get("hard_citation_indices", [])
            soft_citation_indices = data.get("soft_citation_indices", [])
            
            # Validate arrays are actually lists
            if not isinstance(hard_bullets, list):
                hard_bullets = []
            if not isinstance(soft_bullets, list):
                soft_bullets = []
            if not isinstance(hard_citation_indices, list):
                hard_citation_indices = []
            if not isinstance(soft_citation_indices, list):
                soft_citation_indices = []
            
            return {
                "hard_bullets": hard_bullets,
                "soft_bullets": soft_bullets,
                "hard_citation_indices": hard_citation_indices,
                "soft_citation_indices": soft_citation_indices
            }
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse NQMF LLM response as JSON: {e}")
            logger.error(f"Response: {response[:200]}...")
            return {
                "hard_bullets": [],
                "soft_bullets": [],
                "hard_citation_indices": [],
                "soft_citation_indices": []
            }
