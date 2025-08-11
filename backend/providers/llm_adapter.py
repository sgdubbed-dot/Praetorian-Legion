from typing import List, Dict, Any

class LLMAdapter:
    def list_models(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def chat(self, model_id: str, messages: List[Dict[str, str]], temperature: float = 0.3, max_tokens: int = 800) -> Dict[str, Any]:
        # Return dict with keys: text, tokens_in, tokens_out, latency_ms, provider, model_id
        raise NotImplementedError