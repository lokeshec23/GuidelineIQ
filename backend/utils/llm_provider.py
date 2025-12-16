# backend/utils/llm_provider.py

import time
import requests
from typing import List, Optional
from openai import AzureOpenAI
from config import get_model_config, GEMINI_API_BASE_URL


class LLMProvider:
    """
    Unified LLM client for Azure OpenAI and Google Gemini.
    Supports REAL system + user messages (Option B).
    """

    _gemini_session = None  # Shared HTTP session

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

        # -------- Azure OpenAI --------
        if self.provider == "openai":
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
            print(f"[INIT] Azure OpenAI ready (deployment: {self.deployment})")

        # -------- Gemini --------
        elif self.provider == "gemini":
            if not api_key:
                raise ValueError("Gemini requires an API key.")

            if not LLMProvider._gemini_session:
                LLMProvider._gemini_session = requests.Session()

            print(f"[INIT] Gemini ready (model: {self.model})")

        else:
            raise ValueError(f"Unsupported LLM provider: '{self.provider}'")

    # -----------------------------------------------------------
    # Public API
    # -----------------------------------------------------------
    def generate(self, system_prompt: str, user_content: str) -> dict:
        """
        Generates text using REAL system + user roles.
        system_prompt → high-level instructions
        user_content  → chunk data + user prompt
        
        Returns:
            Dictionary with:
                - response: Generated text
                - usage: Token usage dict with prompt_tokens, completion_tokens, total_tokens
        """
        if self.provider == "openai":
            return self._generate_azure_openai(system_prompt, user_content)

        if self.provider == "gemini":
            return self._generate_gemini(system_prompt, user_content)

        raise NotImplementedError(f"Provider '{self.provider}' not implemented.")

    # -----------------------------------------------------------
    # Azure OpenAI — REAL system & user roles
    # -----------------------------------------------------------
    def _generate_azure_openai(self, system_prompt: str, user_content: str) -> dict:
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
                
                # Extract token usage
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
                
                print(f"[OpenAI] Response OK ({len(content)} chars, {usage['total_tokens']} tokens)")
                return {"response": content, "usage": usage}

            except Exception as e:
                print(f"[OpenAI] Attempt {attempt} failed: {e}")

                if attempt < self.max_retries:
                    time.sleep(self.backoff_base ** attempt)
                    continue

                # Fallback to gpt-4o
                if "gpt-4o" not in self.deployment:
                    try:
                        print("[OpenAI] Switching to fallback model: gpt-4o")
                        self.deployment = "gpt-4o"
                        response = self.client.chat.completions.create(
                            model=self.deployment,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_content},
                            ],
                        )
                        content = response.choices[0].message.content
                        usage = {
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens
                        }
                        print(f"[OpenAI] Fallback OK ({len(content)} chars, {usage['total_tokens']} tokens)")
                        return {"response": content, "usage": usage}
                    except Exception as e2:
                        print(f"[OpenAI] Fallback failed: {e2}")

                raise Exception(f"Azure OpenAI failed after retries: {e}")

    # -----------------------------------------------------------
    # Gemini — REAL system & user roles
    # -----------------------------------------------------------
    def _generate_gemini(self, system_prompt: str, user_content: str) -> dict:
        """
        Gemini 1.5 / 2.0+ now supports system messages via "system_instruction".
        We will use recommended structure from Google PaLM → Gemini upgrade docs.
        """

        model_config = get_model_config(self.model)

        api_url = (
            f"{GEMINI_API_BASE_URL}/{self.model}:generateContent?key={self.api_key}"
        )

        payload = {
            "system_instruction": {
                "role": "system",
                "parts": [{"text": system_prompt}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_content}],
                }
            ],
            "generationConfig": {
                "temperature": self.temperature,
                # "maxOutputTokens": model_config.get("max_output", 8192),
                "topP": self.top_p,
                "stopSequences": self.stop_sequences,
            },
        }

        headers = {"Content-Type": "application/json"}
        session = LLMProvider._gemini_session or requests.Session()

        for attempt in range(1, self.max_retries + 1):
            try:
                response = session.post(api_url, headers=headers, json=payload, timeout=180)

                if response.status_code == 503:
                    print(f"[Gemini] 503 overload (attempt {attempt}), retrying...")
                    time.sleep(self.backoff_base ** attempt)
                    continue

                response.raise_for_status()
                result = response.json()

                candidates = result.get("candidates", [])
                if not candidates:
                    reason = result.get("promptFeedback", {}).get("blockReason", "Unknown")
                    raise ValueError(f"Gemini blocked request: {reason}")

                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
                
                # Extract token usage from usageMetadata
                usage_metadata = result.get("usageMetadata", {})
                usage = {
                    "prompt_tokens": usage_metadata.get("promptTokenCount", 0),
                    "completion_tokens": usage_metadata.get("candidatesTokenCount", 0),
                    "total_tokens": usage_metadata.get("totalTokenCount", 0)
                }

                print(f"[Gemini] Response OK ({len(text)} chars, {usage['total_tokens']} tokens)")
                return {"response": text, "usage": usage}

            except Exception as e:
                print(f"[Gemini] Attempt {attempt} failed: {e}")

                if attempt < self.max_retries:
                    time.sleep(self.backoff_base ** attempt)
                    continue

                # Fallback to Flash model
                if self.model == "gemini-2.5-pro":
                    print("[Gemini] Switching to fallback: gemini-2.5-flash")
                    self.model = "gemini-2.5-flash"
                    return self._generate_gemini(system_prompt, user_content)

                raise Exception(f"Gemini failed after retries: {e}")

