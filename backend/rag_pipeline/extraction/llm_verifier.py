# backend/rag_pipeline/extraction/llm_verifier.py
"""
LLM-based verification pass (temperature=0)
"""

import json
import asyncio
from typing import List
import logging
from openai import AzureOpenAI

from rag_pipeline.models import ExtractionResult, VerificationResult, RetrievalResult
from rag_pipeline.config import RAGConfig

logger = logging.getLogger(__name__)


class LLMVerifier:
    """
    Second-pass LLM verification for quality assurance
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
            logger.info("Initialized LLM verifier")
        except Exception as e:
            logger.error(f"Failed to initialize verifier: {e}")
            raise
    
    async def verify(
        self,
        extraction_result: ExtractionResult,
        evidence_chunks: List[RetrievalResult]
    ) -> VerificationResult:
        """
        Verify extraction accuracy against evidence
        
        Args:
            extraction_result: Result from LLMExtractor
            evidence_chunks: Original evidence chunks
        
        Returns:
            VerificationResult with verification status
        """
        # Build prompts
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(extraction_result, evidence_chunks)
        
        try:
            response = await asyncio.to_thread(
                self._call_llm,
                system_prompt,
                user_prompt
            )
            
            # Parse response
            verification_data = self._parse_llm_response(response)
            
            result = VerificationResult(
                verified=verification_data.get("verified", False),
                issues=verification_data.get("issues", []),
                suggested_fix=verification_data.get("suggested_fix"),
                verification_notes=verification_data.get("verification_notes")
            )
            
            if not result.verified:
                logger.warning(
                    f"Verification failed for {extraction_result.parameter}: "
                    f"{', '.join(result.issues)}"
                )
            
            return result
        
        except Exception as e:
            logger.error(f"Verification error: {e}")
            return VerificationResult(
                verified=False,
                issues=[f"Verification process failed: {str(e)}"],
                suggested_fix=None
            )
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for verification"""
        return """You are a quality assurance expert for mortgage guideline extraction.

Your task is to verify that extracted values accurately reflect the evidence.

VERIFICATION CRITERIA:
1. Extracted value must be supported by evidence
2. No hallucination or inference beyond evidence
3. Citations must be accurate
4. Contradictions must be flagged
5. Completeness - all relevant info captured

OUTPUT SCHEMA:
{
    "verified": true/false,
    "issues": ["list of issues found"],
    "suggested_fix": "corrected value if issues found (or null)",
    "verification_notes": "additional notes (optional)"
}"""
    
    def _build_user_prompt(
        self,
        extraction_result: ExtractionResult,
        evidence_chunks: List[RetrievalResult]
    ) -> str:
        """Build verification prompt"""
        # Format evidence
        evidence_str = ""
        for idx, result in enumerate(evidence_chunks, 1):
            chunk = result.chunk
            evidence_str += f"""
--- Evidence {idx} ---
Pages: {chunk.page_start}-{chunk.page_end}
{chunk.text}
"""
        
        # Format extraction
        extraction_str = f"""
PARAMETER: {extraction_result.parameter}
EXTRACTED VALUE: {extraction_result.value}
NEEDS CLARIFICATION: {extraction_result.needs_clarification}
CLARIFICATION REASON: {extraction_result.clarification_reason or 'N/A'}
CITATIONS: {len(extraction_result.citations)} citation(s)
"""
        
        prompt = f"""EXTRACTED INFORMATION:
{extraction_str}

ORIGINAL EVIDENCE:
{evidence_str}

TASK:
Verify that the extracted value accurately reflects the evidence.

CHECK FOR:
1. Does the extracted value match what's stated in evidence?
2. Are there any hallucinations or unsupported claims?
3. Are citations accurate?
4. Is any critical information missing?
5. Are there contradictions that weren't flagged?

OUTPUT:
Return ONLY valid JSON matching the schema."""
        
        return prompt
    
    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call Azure OpenAI for verification"""
        response = self.client.chat.completions.create(
            model=self.config.AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=self.config.VERIFICATION_TEMPERATURE,  # 0.0
            max_tokens=2048,
            response_format={"type": "json_object"}
        )
        
        return response.choices[0].message.content
    
    def _parse_llm_response(self, response: str) -> dict:
        """Parse verification response"""
        try:
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            data = json.loads(cleaned.strip())
            
            # Validate
            if "verified" not in data:
                data["verified"] = False
            if "issues" not in data:
                data["issues"] = []
            
            return data
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse verification response: {e}")
            return {
                "verified": False,
                "issues": ["Verification response parsing failed"],
                "suggested_fix": None
            }
