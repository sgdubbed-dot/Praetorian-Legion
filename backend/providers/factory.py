from .llm_adapter import LLMAdapter
from .openai_client import OpenAIClient


def get_llm_client() -> LLMAdapter:
    # Future: switch based on env (e.g., PROVIDER=anthropic/gemini)
    return OpenAIClient()