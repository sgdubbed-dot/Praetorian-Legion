import os
import time
from typing import Optional
from .factory import get_llm_client

_DEFAULT_MODEL_CACHE: Optional[str] = None
_LAST_SELECT_AT = 0


def select_praefectus_default_model() -> str:
    global _DEFAULT_MODEL_CACHE, _LAST_SELECT_AT
    if _DEFAULT_MODEL_CACHE and (time.time() - _LAST_SELECT_AT) < 3600:
        return _DEFAULT_MODEL_CACHE

    client = get_llm_client()
    cfg = os.getenv("PRAEFECTUS_MODEL_ID", "auto")
    if cfg and cfg != "auto":
        _DEFAULT_MODEL_CACHE = cfg
        _LAST_SELECT_AT = time.time()
        return cfg

    # Auto-select: prefer GPT-5 reasoning/thinking chat models; else best GPT-5 chat
    best = None
    models = client.list_models()
    # Prefer reasoning/thinking variants
    for m in models:
        mid = str(m.get("id", "")).lower()
        if "gpt-5" in mid and ("reason" in mid or "think" in mid):
            best = m.get("id")
            break
    # Next, pick GPT-5 chat
    if not best:
        for m in models:
            mid = str(m.get("id", "")).lower()
            if "gpt-5" in mid and "chat" in mid:
                best = m.get("id")
                break
    # Fallback to first available
    if not best and models:
        best = models[0].get("id")

    _DEFAULT_MODEL_CACHE = best or "gpt-5"
    _LAST_SELECT_AT = time.time()
    return _DEFAULT_MODEL_CACHE