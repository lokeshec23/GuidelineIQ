# backend/rag_pipeline/extraction/llm_verifier.py
"""
LLM-based verification pass for NQMF extraction (temperature=0)
Verifies hard/soft bullet classification and detects hallucinations.
"""

import json
import asyncio
from typing import List, Optional
import logging
from openai import AzureOpenAI

from rag_pipeline.models import ExtractionResult, VerificationResult, RetrievalResult
from rag_pipeline.config import RAGConfig

logger = logging.getLogger(__name__)


class LLMVerifier:
    """
    Second-pass LLM verification for quality assurance.
    Supports both legacy extraction and NQMF hard/soft classification.
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
    
    # ==========================================
    # NQMF-SPECIFIC VERIFICATION
    # ==========================================
    
    async def verify_nqmf(
        self,
        extraction_result: ExtractionResult,
        evidence_chunks: List[RetrievalResult]
    ) -> VerificationResult:
        """
        Verify NQMF extraction with hard/soft classification awareness.
        
        Checks:
        1. Each bullet is supported by evidence (no hallucination)
        2. Hard/soft classification is correct
        3. No critical information was missed
        4. Numeric thresholds match exactly
        
        Args:
            extraction_result: NQMF ExtractionResult with hard_value/soft_value
            evidence_chunks: Original evidence chunks
        
        Returns:
            VerificationResult with verification status and auto-corrections
        """
        if not extraction_result.hard_value and not extraction_result.soft_value:
            # Nothing to verify
            return VerificationResult(
                verified=True,
                issues=[],
                suggested_fix=None,
                verification_notes="No bullets to verify (NA result)"
            )
        
        system_prompt = self._build_nqmf_verification_prompt()
        user_prompt = self._build_nqmf_user_prompt(extraction_result, evidence_chunks)
        
        try:
            response = await asyncio.to_thread(
                self._call_llm,
                system_prompt,
                user_prompt
            )
            
            verification_data = self._parse_llm_response(response)
            
            result = VerificationResult(
                verified=verification_data.get("verified", False),
                issues=verification_data.get("issues", []),
                suggested_fix=verification_data.get("suggested_fix"),
                verification_notes=verification_data.get("verification_notes")
            )
            
            if not result.verified:
                logger.warning(
                    f"NQMF verification flagged issues for "
                    f"'{extraction_result.parameter}': "
                    f"{', '.join(result.issues[:3])}"
                )
            else:
                logger.info(
                    f"NQMF verification passed for "
                    f"'{extraction_result.parameter}'"
                )
            
            return result
        
        except Exception as e:
            logger.error(f"NQMF verification error: {e}")
            return VerificationResult(
                verified=False,
                issues=[f"Verification process failed: {str(e)}"],
                suggested_fix=None
            )
    
    def _build_nqmf_verification_prompt(self) -> str:
        """Build system prompt for NQMF verification"""
        return """You are a quality assurance expert for mortgage underwriting guideline extraction.

You are verifying NQMF extraction output that contains HARD and SOFT classified bullets.

VERIFICATION CRITERIA:

1. EVIDENCE SUPPORT
   - Every bullet MUST be supported by the provided evidence
   - If a bullet contains information NOT in the evidence → flag as hallucination
   - Numeric values (LTV, FICO, DTI, etc.) must match evidence EXACTLY

2. CLASSIFICATION ACCURACY
   - HARD bullets must contain strict requirements (must, required, prohibited, specific limits)
   - SOFT bullets must contain flexible guidelines (may, typically, subject to approval)
   - If classification is wrong, provide the correct classification

3. COMPLETENESS
   - Flag if critical requirements in the evidence were NOT extracted
   - Do NOT flag minor omissions

4. NUMERIC PRECISION
   - All percentages, scores, and limits must match evidence exactly
   - Flag any rounded or approximated values

OUTPUT SCHEMA (JSON only):
{
    "verified": true/false,
    "issues": ["list of specific issues found"],
    "suggested_fix": "corrected bullets if needed, or null",
    "reclassifications": [
        {"bullet": "• original bullet", "from": "HARD", "to": "SOFT"}
    ],
    "hallucinated_bullets": ["• any bullets not supported by evidence"],
    "verification_notes": "summary of verification"
}"""
    
    def _build_nqmf_user_prompt(
        self,
        extraction_result: ExtractionResult,
        evidence_chunks: List[RetrievalResult]
    ) -> str:
        """Build user prompt for NQMF verification"""
        # Format evidence (limit to prevent context overflow)
        evidence_str = ""
        max_chunks = min(len(evidence_chunks), self.config.MAX_CHUNKS_FOR_NQMF)
        for idx, result in enumerate(evidence_chunks[:max_chunks], 1):
            chunk = result.chunk
            text = chunk.text[:1500] if len(chunk.text) > 1500 else chunk.text
            evidence_str += f"""
--- Evidence {idx} ---
Pages: {chunk.page_start}-{chunk.page_end}
Section: {chunk.section_path}
{text}
"""
        
        return f"""PARAMETER: {extraction_result.parameter}

EXTRACTED HARD BULLETS:
{extraction_result.hard_value or '(none)'}

EXTRACTED SOFT BULLETS:
{extraction_result.soft_value or '(none)'}

ORIGINAL EVIDENCE:
{evidence_str}

VERIFY:
1. Is every bullet supported by the evidence above?
2. Are hard/soft classifications correct?
3. Are numeric values exact?
4. Was any critical requirement missed?

Return ONLY valid JSON."""
    
    # ==========================================
    # LEGACY VERIFICATION (backward compat)
    # ==========================================
    
    async def verify(
        self,
        extraction_result: ExtractionResult,
        evidence_chunks: List[RetrievalResult]
    ) -> VerificationResult:
        """
        Legacy verify method — delegates to NQMF verifier if
        hard_value/soft_value present, else uses original logic.
        """
        if extraction_result.hard_value or extraction_result.soft_value:
            return await self.verify_nqmf(extraction_result, evidence_chunks)
        
        # Original legacy path
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(extraction_result, evidence_chunks)
        
        try:
            response = await asyncio.to_thread(
                self._call_llm,
                system_prompt,
                user_prompt
            )
            
            verification_data = self._parse_llm_response(response)
            
            result = VerificationResult(
                verified=verification_data.get("verified", False),
                issues=verification_data.get("issues", []),
                suggested_fix=verification_data.get("suggested_fix"),
                verification_notes=verification_data.get("verification_notes")
            )
            
            if not result.verified:
                logger.info(
                    f"Verification flagged issues for {extraction_result.parameter}: "
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
        """Build system prompt for legacy verification"""
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
    "suggested_fix": "corrected value. IF HALLUCINATION/UNSUPPORTED: you MUST provide 'N/A' or the correct supported value.",
    "verification_notes": "additional notes (optional)"
}"""
    
    def _build_user_prompt(
        self,
        extraction_result: ExtractionResult,
        evidence_chunks: List[RetrievalResult]
    ) -> str:
        """Build verification prompt"""
        evidence_str = ""
        for idx, result in enumerate(evidence_chunks, 1):
            chunk = result.chunk
            evidence_str += f"""
--- Evidence {idx} ---
Pages: {chunk.page_start}-{chunk.page_end}
{chunk.text}
"""
        
        extraction_str = f"""
PARAMETER: {extraction_result.parameter}
EXTRACTED VALUE: {extraction_result.value}
NEEDS CLARIFICATION: {extraction_result.needs_clarification}
CLARIFICATION REASON: {extraction_result.clarification_reason or 'N/A'}
CITATIONS: {len(extraction_result.citations)} citation(s)
"""
        
        return f"""EXTRACTED INFORMATION:
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
