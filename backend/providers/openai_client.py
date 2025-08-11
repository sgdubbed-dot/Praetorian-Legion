import os
import time
from typing import List, Dict, Any
from openai import OpenAI
from .llm_adapter import LLMAdapter

class OpenAIClient(LLMAdapter):
    def __init__(self):
        key = os.getenv("EMERGENT_LLM_KEY")
        if not key:
            raise RuntimeError("EMERGENT_LLM_KEY is not set")
        # OpenAI client will read api_key parameter
        self._client = OpenAI(api_key=key)

    def list_models(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        models = self._client.models.list().data
        for m in models:
            out.append({
                "id": getattr(m, "id", None),
                "provider": "openai",
                # OpenAI python objects may not expose context_window; leave None if missing
                "context_window": getattr(m, "context_window", None),
                "capabilities": ["chat"],
            })
        return out

    def chat(self, model_id: str, messages: List[Dict[str, str]], temperature: float = 0.3, max_tokens: int = 800) -> Dict[str, Any]:
        t0 = time.time()
        resp = self._client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        t1 = time.time()
        choice = resp.choices[0].message
        usage = getattr(resp, "usage", None)
        return {
            "text": getattr(choice, "content", ""),
            "tokens_in": getattr(usage, "prompt_tokens", None) if usage else None,
            "tokens_out": getattr(usage, "completion_tokens", None) if usage else None,
            "latency_ms": int((t1 - t0) * 1000),
            "provider": "openai",
            "model_id": model_id,
        }