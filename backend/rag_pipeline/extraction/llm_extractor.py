# backend/rag_pipeline/extraction/llm_extractor.py
"""
LLM-based extraction with strict JSON output (temperature=0)
"""

import json
import asyncio
from typing import List, Dict
import logging
from openai import AzureOpenAI

from rag_pipeline.models import ExtractionResult, Citation, RetrievalResult
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
1. Extract ONLY information explicitly stated in the evidence
2. If information is unclear or contradictory, flag for clarification
3. Always provide citations with page numbers
4. Output MUST be valid JSON matching the schema
5. Be deterministic - same input should always produce same output

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
4. If evidence is contradictory or unclear, set needs_clarification=true
5. Provide citations for each key piece of information
6. If no relevant information found, set value="N/A" and needs_clarification=true

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
