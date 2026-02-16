# backend/utils/llm_provider.py

import time
from typing import List, Optional
from openai import AzureOpenAI
from config import get_model_config
from utils.logger import setup_logger

logger = setup_logger(__name__)


class LLMProvider:
    """
    Unified LLM client for Azure OpenAI.
    Supports system + user message roles.
    """

    def __init__(
        self,
        provider: str,
        api_key: str,
        model: str,
        temperature: float = 0.5,
        max_tokens: int = 8192,
        top_p: float = 1.0,
        stop_sequences: Optional[List[str]] = None,
        azure_endpoint: Optional[str] = None,
        azure_deployment: Optional[str] = None,
        max_retries: int = 3,
        backoff_base: float = 2.0,
    ):
        self.provider = provider.lower()
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.stop_sequences = stop_sequences or []
        self.max_retries = max_retries
        self.backoff_base = backoff_base

        if self.provider != "openai":
            raise ValueError(
                f"Unsupported LLM provider: '{self.provider}'. Only 'openai' (Azure OpenAI) is supported."
            )

        if not all([azure_endpoint, azure_deployment, api_key]):
            raise ValueError(
                "Azure OpenAI requires API key, endpoint, and deployment name."
            )

        self.client = AzureOpenAI(
            api_key=self.api_key,
            api_version="2024-02-01",
            azure_endpoint=azure_endpoint,
        )
        
        self.deployment = azure_deployment
        logger.info(f"[INIT] Azure OpenAI ready (deployment: {self.deployment})")

    def generate(self, system_prompt: str, user_content: str) -> str:
        """
        Generates text using system + user roles.
        system_prompt → high-level instructions
        user_content  → chunk data + user prompt
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.deployment,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    top_p=self.top_p,
                    stop=self.stop_sequences or None,
                )

                content = response.choices[0].message.content
                logger.info(f"[OpenAI] Response OK ({len(content)} chars)")
                return content

            except Exception as e:
                logger.warning(f"[OpenAI] Attempt {attempt} failed: {e}")

                if attempt < self.max_retries:
                    time.sleep(self.backoff_base ** attempt)
                    continue

                # Fallback to gpt-4o if not already using it
                if "gpt-4o" not in self.deployment:
                    try:
                        logger.warning("[OpenAI] Switching to fallback model: gpt-4o")
                        original_deployment = self.deployment
                        self.deployment = "gpt-4o"

                        response = self.client.chat.completions.create(
                            model=self.deployment,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_content},
                            ],
                        )
                        content = response.choices[0].message.content
                        logger.info(f"[OpenAI] Fallback OK ({len(content)} chars)")
                        # Restore original deployment for future calls
                        self.deployment = original_deployment
                        return content
                    except Exception as e2:
                        self.deployment = original_deployment
                        logger.error(f"[OpenAI] Fallback failed: {e2}")

                raise Exception(f"Azure OpenAI failed after retries: {e}")
