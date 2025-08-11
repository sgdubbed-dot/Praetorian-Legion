from fastapi import APIRouter
from .factory import get_llm_client
from .selector import select_praefectus_default_model
from typing import Dict, Any

# Import server helpers to ensure events are logged centrally
from server import now_iso, log_event  # type: ignore

router = APIRouter(prefix="/api/providers", tags=["providers"])
@router.get("/models")
async def list_models():
    client = get_llm_client()
    models = client.list_models()
    return {"models": models, "timestamp": now_iso()}

@router.get("/health")
async def health():
    model_id = select_praefectus_default_model()
    await log_event("provider_selected_default", "backend/providers", {"provider": "openai", "model_id": model_id})
    return {"provider": "openai", "praefectus_model_id": model_id, "timestamp": now_iso()}