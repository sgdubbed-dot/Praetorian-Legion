from fastapi import APIRouter
from .factory import get_llm_client
from .selector import select_praefectus_default_model
from typing import Dict, Any

# These will be replaced by project helpers when included from server
router = APIRouter(prefix="/api/providers", tags=["providers"])

# Fallback Phoenix time helper (server will override by dependency)

def now_iso():
    import datetime, zoneinfo
    tz = zoneinfo.ZoneInfo("America/Phoenix")
    return datetime.datetime.now(tz).isoformat()

async def log_event(name: str, source: str, payload: Dict[str, Any]):
    return True

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