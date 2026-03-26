
import logging
import time
import json
import os
from openai import OpenAI
from .base import LLM, Schema, ToolDef

logger = logging.getLogger(__name__)

# Retry config
_MAX_RETRIES = 6
_RETRY_BASE_DELAY = 5

class GeminiLLM(LLM):
    """
    Mocked GeminiLLM that actually uses OpenAI-compatible API (api.apiyi.com).
    This bypasses the need for the google-genai package which was causing import errors.
    """
    def __init__(self, model: str = "gemini-2.0-flash-lite-preview-02-05"):
        # Use env vars or defaults
        api_key = os.getenv("OPENAI_API_KEY", "sk-xxx")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.apiyi.com/v1")
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=30.0)
        self._model = model

    @property
    def model_id(self) -> str:
        return f"nexus_compat:{self._model}"

    def generate(self, prompt: str, schema: Schema) -> dict:
        """
        Uses OpenAI-compatible model to fulfill the Schema requirement.
        """
        system_prompt = (
            "You are a helpful assistant. You MUST return your response in valid JSON format. "
            f"The JSON must exactly match this structure: {json.dumps(schema.properties)}. "
            f"Required fields: {json.dumps(schema.required)}."
        )
        
        delay = _RETRY_BASE_DELAY
        for attempt in range(_MAX_RETRIES):
            try:
                print(f"      [LLM-CALC] Calling {self._model} (Attempt {attempt+1})...", end="", flush=True)
                t_start = time.perf_counter()
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ]
                )
                t_elapsed = time.perf_counter() - t_start
                print(f" Done ({t_elapsed:.1f}s)")
                
                raw_content = response.choices[0].message.content
                parsed = json.loads(raw_content)
                # Validation
                if all(k in parsed for k in schema.required):
                    return parsed
                logger.warning("[nexus_compat] Missing required fields in attempt %d", attempt)
            except Exception as e:
                logger.warning("[nexus_compat] Error in attempt %d: %s", attempt, str(e))
            
            if attempt < _MAX_RETRIES - 1:
                time.sleep(delay)
                delay *= 2
                
        raise RuntimeError(f"Nexus/Gemini compat failed after {_MAX_RETRIES} retries")

    def tool_loop(self, prompt: str, tools: list[ToolDef], max_tool_calls: int = 10) -> str:
        """
        Simple chat completion if tool loop is needed for RAG judge.
        """
        # Note: For LoCoMo benchmark, judge usually uses simple generate.
        # This is a fallback.
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("[nexus_compat] Tool loop error: %s", e)
            return ""

    def _generate_raw(self, contents, **kwargs):
        # Compatibility method if others call it directly
        return self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": str(contents)}]
        )
