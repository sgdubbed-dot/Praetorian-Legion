from fastapi import FastAPI, APIRouter, HTTPException, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
import os
import uuid
import logging
import csv
import io

# Load env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# MongoDB connection (must use env variables only)
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

# App and router (all backend routes must be under /api)
app = FastAPI()
api = APIRouter(prefix="/api")

# Timezone helpers (Phase 1 requires America/Phoenix timestamps)
PHOENIX_TZ = ZoneInfo("America/Phoenix")

def now_iso() -> str:
    return datetime.now(tz=PHOENIX_TZ).isoformat()

def to_phoenix(ts: Optional[str]) -> Optional[str]:
    if not ts:
        return ts
    try:
        s = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.astimezone(PHOENIX_TZ).isoformat()
    except Exception:
        return now_iso()

def phoenix_time_line(ts: str) -> str:
    try:
        return to_phoenix(ts) or ts
    except Exception:
        return ts

# ID helper
# Flake8 E731: do not assign a lambda expression; define a function instead

def new_id() -> str:
    return str(uuid.uuid4())

# Collections (TitleCase matching tabs where applicable)
COLL_MISSIONS = db["Missions"]
COLL_FORUMS = db["Forums"]
COLL_ROLODEX = db["Rolodex"]
COLL_HOT_LEADS = db["Hot Leads"]  # space allowed; accessed via dict-style
COLL_EXPORTS = db["Exports"]
COLL_AGENTS = db["Agents"]
COLL_GUARDRAILS = db["Guardrails"]
COLL_EVENTS = db["Events"]

# Mongo helpers (avoid ObjectID, use UUID string as _id)
async def insert_with_id(coll, doc: Dict[str, Any]) -> Dict[str, Any]:
    if "id" not in doc:
        doc["id"] = new_id()
    created = doc.get("created_at", now_iso())
    doc["created_at"] = created
    doc["updated_at"] = doc.get("updated_at", created)
    doc["_id"] = doc["id"]
    await coll.insert_one(doc)
    doc.pop("_id", None)
    return doc

async def update_by_id(coll, _id: str, fields: Dict[str, Any]) -> int:
    # Support explicit field clearing when value is None (use $unset)
    set_fields = {k: v for k, v in fields.items() if v is not None}
    unset_fields = {k: "" for k, v in fields.items() if v is None}
    set_fields["updated_at"] = now_iso()
    update_doc: Dict[str, Any] = {}
    if set_fields:
        update_doc["$set"] = set_fields
    if unset_fields:
        update_doc["$unset"] = unset_fields
    res = await coll.update_one({"_id": _id}, update_doc)
    return res.modified_count

async def get_by_id(coll, _id: str) -> Optional[Dict[str, Any]]:
    doc = await coll.find_one({"_id": _id})
    if doc:
        doc.pop("_id", None)
    return doc

# Event logging per taxonomy
class Event(BaseModel):
    id: str = Field(default_factory=new_id)
    event_name: str
    source: str
    timestamp: str = Field(default_factory=now_iso)
    payload: Dict[str, Any] = Field(default_factory=dict)

async def log_event(event_name: str, source: str, payload: Optional[Dict[str, Any]] = None):
    event = Event(event_name=event_name, source=source, payload=payload or {})
    await insert_with_id(COLL_EVENTS, event.model_dump())

# ------------------ Data Contracts (Pydantic) ------------------
# Mission
class Mission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=new_id)
    title: str
    objective: str
    posture: str  # help_only | help_plus_soft_marketing | research_only
    state: str  # draft|scanning|engaging|escalating|paused|complete|aborted
    agents_assigned: List[str] = Field(default_factory=list)
    counters: Dict[str, int] = Field(default_factory=lambda: {
        "forums_found": 0,
        "prospects_added": 0,
        "hot_leads": 0,
    })
    insights: List[str] = Field(default_factory=list)
    insights_rich: List[Dict[str, str]] = Field(default_factory=list)
    previous_active_state: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class MissionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    objective: str
    posture: str
    state: str = "draft"
    agents_assigned: List[str] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)

class MissionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = None
    objective: Optional[str] = None
    posture: Optional[str] = None
    state: Optional[str] = None
    agents_assigned: Optional[List[str]] = None
    counters: Optional[Dict[str, int]] = None
    insights: Optional[List[str]] = None
    insights_rich: Optional[List[Dict[str, str]]] = None
    previous_active_state: Optional[str] = None

# Forum
class Forum(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=new_id)
    platform: str
    name: str
    url: str
    rule_profile: str  # strict_help_only | open_soft_marketing
    topic_tags: List[str] = Field(default_factory=list)
    size_velocity: Optional[str] = None
    relevance_notes: Optional[str] = None
    last_seen_at: Optional[str] = None
    # UX-10: link validation
    link_status: Optional[str] = None  # ok | not_found | blocked
    last_checked_at: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class ForumCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    platform: str
    name: str
    url: str
    rule_profile: str
    topic_tags: List[str] = Field(default_factory=list)
    size_velocity: Optional[str] = None
    relevance_notes: Optional[str] = None
    last_seen_at: Optional[str] = None

class ForumUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    platform: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None
    rule_profile: Optional[str] = None
    topic_tags: Optional[List[str]] = None
    size_velocity: Optional[str] = None
    relevance_notes: Optional[str] = None
    last_seen_at: Optional[str] = None

# Prospect (Rolodex)
class Signal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str
    quote: str
    link: Optional[str] = None
    timestamp: str = Field(default_factory=now_iso)

class EngagementEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    channel: Optional[str] = None
    content: Optional[str] = None
    timestamp: str = Field(default_factory=now_iso)
    outcome: Optional[str] = None

class Prospect(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=new_id)
    name_or_alias: str
    handles: Dict[str, str] = Field(default_factory=dict)
    company: Optional[str] = None
    role: Optional[str] = None
    location_public: Optional[str] = None
    signals: List[Signal] = Field(default_factory=list)
    priority_state: str = "cold"  # hot|warm|cold
    reason_tags: List[str] = Field(default_factory=list)
    engagement_history: List[EngagementEntry] = Field(default_factory=list)
    mission_tags: List[str] = Field(default_factory=list)
    platform_tags: List[str] = Field(default_factory=list)
    contact_public: Dict[str, Optional[str]] = Field(default_factory=dict)
    source_type: str = "manual"  # seeded|discovered|manual
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class ProspectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name_or_alias: str
    handles: Dict[str, str] = Field(default_factory=dict)
    company: Optional[str] = None
    role: Optional[str] = None
    location_public: Optional[str] = None
    signals: List[Signal] = Field(default_factory=list)
    priority_state: str = "cold"
    reason_tags: List[str] = Field(default_factory=list)
    engagement_history: List[EngagementEntry] = Field(default_factory=list)
    mission_tags: List[str] = Field(default_factory=list)
    platform_tags: List[str] = Field(default_factory=list)
    contact_public: Dict[str, Optional[str]] = Field(default_factory=dict)
    source_type: Optional[str] = None  # seeded|discovered|manual

class ProspectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name_or_alias: Optional[str] = None
    handles: Optional[Dict[str, str]] = None
    company: Optional[str] = None
    role: Optional[str] = None
    location_public: Optional[str] = None
    signals: Optional[List[Signal]] = None
    priority_state: Optional[str] = None
    reason_tags: Optional[List[str]] = None
    engagement_history: Optional[List[EngagementEntry]] = None
    mission_tags: Optional[List[str]] = None
    platform_tags: Optional[List[str]] = None
    contact_public: Optional[Dict[str, Optional[str]]] = None
    source_type: Optional[str] = None

# HotLead
class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quote: str
    link: Optional[str] = None
    timestamp: str = Field(default_factory=now_iso)

class HotLead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=new_id)
    prospect_id: str
    evidence: List[Evidence] = Field(default_factory=list)
    proposed_script: Optional[str] = None
    suggested_actions: List[str] = Field(default_factory=list)
    status: str = "pending_approval"  # pending_approval|approved|deferred|removed
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class HotLeadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prospect_id: str
    evidence: List[Evidence]
    proposed_script: Optional[str] = None
    suggested_actions: List[str] = Field(default_factory=list)

class HotLeadStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str  # approved|deferred|removed

class HotLeadPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proposed_script: Optional[str] = None

# Export
class Export(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=new_id)
    recipe_name: str
    filter_spec: Dict[str, Any] = Field(default_factory=dict)
    file_url: Optional[str] = None
    row_count: int = 0
    generated_at: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class ExportRecipeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipe_name: str
    filter_spec: Dict[str, Any] = Field(default_factory=dict)

class ExportGenerate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipe_name: str

# Agent Status
class AgentStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=new_id)
    agent_name: str  # Praefectus|Explorator|Legatus
    status_light: str  # green|yellow|red
    last_activity: Optional[str] = None
    activity_stream: List[Dict[str, Any]] = Field(default_factory=list)
    error_state: Optional[str] = None
    next_retry_at: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class AgentStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status_light: Optional[str] = None
    last_activity: Optional[str] = None
    activity_stream: Optional[List[Dict[str, Any]]] = None
    error_state: Optional[str] = None

# Guardrail (flexible structure but must include created_at/updated_at)
class Guardrail(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class GuardrailUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")
    # free-form, we will set updated_at server-side
    pass

# ------------------ Helpers ------------------
async def _check_url_status(url: str) -> Dict[str, Any]:
    import aiohttp
    status = "blocked"
    try:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.head(url, allow_redirects=True, timeout=10) as resp:
                    code = resp.status
            except Exception:
                async with session.get(url, allow_redirects=True, timeout=10) as resp:
                    code = resp.status
        if 200 <= code < 400:
            status = "ok"
        elif code == 404:
            status = "not_found"
        else:
            status = "blocked"
    except Exception:
        status = "blocked"
    return {"link_status": status, "last_checked_at": now_iso()}

async def ensure_legatus_idle_if_research_only_exists():
    # If any non-complete, non-paused mission with research_only posture exists, set Legatus to yellow
    active = await COLL_MISSIONS.count_documents({
        "posture": "research_only",
        "state": {"$in": ["draft", "scanning", "engaging", "escalating"]},
    })
    if active > 0:
        existing = await COLL_AGENTS.find_one({"agent_name": "Legatus"})
        if existing:
            await update_by_id(COLL_AGENTS, existing["_id"], {"status_light": "yellow", "last_activity": now_iso()})
        else:
            await insert_with_id(COLL_AGENTS, AgentStatus(agent_name="Legatus", status_light="yellow", last_activity=now_iso()).model_dump())

async def append_agent_activity(agent_name: str, entry: Dict[str, Any]):
    existing = await COLL_AGENTS.find_one({"agent_name": agent_name})
    if existing:
        stream = existing.get("activity_stream", [])
        stream.append(entry)
        await update_by_id(COLL_AGENTS, existing["_id"], {"activity_stream": stream, "last_activity": now_iso(), "status_light": existing.get("status_light", "green")})
    else:
        base = AgentStatus(agent_name=agent_name, status_light="green", last_activity=now_iso(), activity_stream=[entry])
        await insert_with_id(COLL_AGENTS, base.model_dump())

# ------------------ Routes ------------------
@api.get("/", tags=["meta"])
async def root():
    return {"message": "Praetorian Legion API ready"}

@api.get("/health", tags=["meta"])
async def health():
    return {"ok": True, "timestamp": now_iso()}

# Missions
@api.post("/missions", response_model=Mission, tags=["missions"])
async def create_mission(payload: MissionCreate):
    mission = Mission(**payload.model_dump())
    # Initialize insights_rich from insights if provided
    if mission.insights and not mission.insights_rich:
        mission.insights_rich = [{"text": t, "timestamp": now_iso()} for t in mission.insights]
    doc = await insert_with_id(COLL_MISSIONS, mission.model_dump())
    await log_event("mission_created", "backend/api", {"mission_id": doc["id"]})
    await ensure_legatus_idle_if_research_only_exists()
    return doc

@api.get("/missions", response_model=List[Mission], tags=["missions"])
async def list_missions():
    docs = await COLL_MISSIONS.find().sort("updated_at", -1).to_list(1000)
    return [{k: v for k, v in d.items() if k != "_id"} for d in docs]

@api.get("/missions/{mission_id}", response_model=Mission, tags=["missions"])
async def get_mission(mission_id: str):
    doc = await get_by_id(COLL_MISSIONS, mission_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Mission not found")
    # Migration: if insights_rich empty but legacy insights exist, convert once
    if (not doc.get("insights_rich")) and doc.get("insights"):
        rich = [{"text": t, "timestamp": now_iso()} for t in (doc.get("insights") or [])]
        await update_by_id(COLL_MISSIONS, mission_id, {"insights_rich": rich})
        doc = await get_by_id(COLL_MISSIONS, mission_id)
    return doc

@api.patch("/missions/{mission_id}", response_model=Mission, tags=["missions"])
async def update_mission(mission_id: str, payload: MissionUpdate):
    existing = await get_by_id(COLL_MISSIONS, mission_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Mission not found")
    data = payload.model_dump(exclude_unset=True)
    # Track previous_active_state when pausing from an active state
    if data.get("state") == "paused" and existing.get("state") not in {"paused","complete","aborted"}:
        data["previous_active_state"] = existing.get("state")
    updated = await update_by_id(COLL_MISSIONS, mission_id, data)
    doc = await get_by_id(COLL_MISSIONS, mission_id)
    await log_event("mission_updated_state" if payload.state else "mission_created", "backend/api", {"mission_id": mission_id, **data})
    await ensure_legatus_idle_if_research_only_exists()
    return doc

class MissionStateChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: str

@api.post("/missions/{mission_id}/state", response_model=Mission, tags=["missions"])
async def change_mission_state(mission_id: str, payload: MissionStateChange):
    mission = await get_by_id(COLL_MISSIONS, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    new_state = payload.state
    event = "mission_updated_state"

    if payload.state == "resume":
        # Resume to previous_active_state or scanning if unknown
        prior = mission.get("previous_active_state") or "scanning"
        new_state = prior
        event = "mission_resumed"
    elif payload.state == "abort" or payload.state == "aborted":
        new_state = "aborted"
        event = "mission_aborted"
    elif payload.state == "paused":
        event = "mission_paused"

    # When pausing, store previous_active_state
    update_fields: Dict[str, Any] = {"state": new_state}
    if new_state == "paused" and mission.get("state") not in {"paused","complete","aborted"}:
        update_fields["previous_active_state"] = mission.get("state")

    await update_by_id(COLL_MISSIONS, mission_id, update_fields)
    doc = await get_by_id(COLL_MISSIONS, mission_id)
    await log_event(event, "backend/api", {"mission_id": mission_id, "state": new_state})
    await ensure_legatus_idle_if_research_only_exists()
    return doc

# Forums
@api.post("/forums", response_model=Forum, tags=["forums"])
async def create_forum(payload: ForumCreate):
    forum = Forum(**payload.model_dump())
    # LEGION-UX-10: validate link
    link_meta = await _check_url_status(forum.url)
    forum.link_status = link_meta["link_status"]
    forum.last_checked_at = link_meta["last_checked_at"]
    doc = await insert_with_id(COLL_FORUMS, forum.model_dump())
    await log_event("forum_discovered", "backend/api", {"forum_id": doc["id"], **link_meta})
    return doc

@api.get("/forums", response_model=List[Forum], tags=["forums"])
async def list_forums():
    docs = await COLL_FORUMS.find().sort("updated_at", -1).to_list(1000)
    return [{k: v for k, v in d.items() if k != "_id"} for d in docs]

@api.get("/forums/{forum_id}", response_model=Forum, tags=["forums"])
async def get_forum(forum_id: str):
    doc = await get_by_id(COLL_FORUMS, forum_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Forum not found")
    return doc

@api.post("/forums/{forum_id}/check_link", tags=["forums"])
async def forum_check_link(forum_id: str):
    doc = await get_by_id(COLL_FORUMS, forum_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Forum not found")
    meta = await _check_url_status(doc["url"])
    await update_by_id(COLL_FORUMS, forum_id, meta)
    out = await get_by_id(COLL_FORUMS, forum_id)
    await log_event("forum_link_checked", "backend/api", {"forum_id": forum_id, **meta})
    return out

@api.patch("/forums/{forum_id}", response_model=Forum, tags=["forums"])
async def update_forum(forum_id: str, payload: ForumUpdate):
    existing = await get_by_id(COLL_FORUMS, forum_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Forum not found")
    data = payload.model_dump(exclude_unset=True)
    # If URL changed, re-check link
    if "url" in data and data["url"]:
        link_meta = await _check_url_status(data["url"])
        data.update(link_meta)
    await update_by_id(COLL_FORUMS, forum_id, data)
    doc = await get_by_id(COLL_FORUMS, forum_id)
    if "rule_profile" in data and existing.get("rule_profile") != doc.get("rule_profile"):
        await log_event("forum_rule_profile_changed", "backend/api", {"forum_id": forum_id, "rule_profile": doc.get("rule_profile")})
    else:
        await log_event("forum_updated", "backend/api", {"forum_id": forum_id})
    return doc

# Prospects (Rolodex)
@api.post("/prospects", response_model=Prospect, tags=["prospects"])
async def create_prospect(payload: ProspectCreate):
    data = payload.model_dump()
    if not data.get("source_type"):
        data["source_type"] = "manual"
    prospect = Prospect(**data)
    doc = await insert_with_id(COLL_ROLODEX, prospect.model_dump())
    await log_event("prospect_added", "backend/api", {"prospect_id": doc["id"], "source_type": doc.get("source_type")})
    return doc

@api.get("/prospects", response_model=List[Prospect], tags=["prospects"])
async def list_prospects():
    docs = await COLL_ROLODEX.find().sort("updated_at", -1).to_list(2000)
    return [{k: v for k, v in d.items() if k != "_id"} for d in docs]

@api.get("/prospects/{prospect_id}", response_model=Prospect, tags=["prospects"])
async def get_prospect(prospect_id: str):
    doc = await get_by_id(COLL_ROLODEX, prospect_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Prospect not found")
    return doc

@api.patch("/prospects/{prospect_id}", response_model=Prospect, tags=["prospects"])
async def update_prospect(prospect_id: str, payload: ProspectUpdate):
    existing = await get_by_id(COLL_ROLODEX, prospect_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Prospect not found")
    data = payload.model_dump(exclude_unset=True)
    updated = await update_by_id(COLL_ROLODEX, prospect_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Prospect not modified")
    doc = await get_by_id(COLL_ROLODEX, prospect_id)
    if "priority_state" in data and data["priority_state"] != existing.get("priority_state"):
        await log_event("prospect_state_changed", "backend/api", {"prospect_id": prospect_id, "priority_state": doc.get("priority_state")})
    else:
        await log_event("prospect_enriched", "backend/api", {"prospect_id": prospect_id})
    return doc

# Hot Leads
@api.post("/hotleads", response_model=HotLead, tags=["hotleads"])
async def create_hot_lead(payload: HotLeadCreate):
    p = await get_by_id(COLL_ROLODEX, payload.prospect_id)
    if not p:
        raise HTTPException(status_code=400, detail="prospect_id not found")
    hl = HotLead(**payload.model_dump())
    doc = await insert_with_id(COLL_HOT_LEADS, hl.model_dump())
    await log_event("hotlead_flagged", "backend/api", {"hotlead_id": doc["id"], "prospect_id": payload.prospect_id})
    await log_event("hotlead_packet_prepared", "backend/api", {"hotlead_id": doc["id"]})
    return doc

@api.get("/hotleads", response_model=List[HotLead], tags=["hotleads"])
async def list_hot_leads():
    docs = await COLL_HOT_LEADS.find().sort("updated_at", -1).to_list(500)
    return [{k: v for k, v in d.items() if k != "_id"} for d in docs]

@api.get("/hotleads/{hotlead_id}", response_model=HotLead, tags=["hotleads"])
async def get_hot_lead(hotlead_id: str):
    doc = await get_by_id(COLL_HOT_LEADS, hotlead_id)
    if not doc:
        raise HTTPException(status_code=404, detail="HotLead not found")
    return doc

@api.post("/hotleads/{hotlead_id}/status", response_model=HotLead, tags=["hotleads"])
async def update_hot_lead_status(hotlead_id: str, payload: HotLeadStatusUpdate):
    if payload.status not in {"approved", "deferred", "removed"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    updated = await update_by_id(COLL_HOT_LEADS, hotlead_id, {"status": payload.status})
    if not updated:
        raise HTTPException(status_code=404, detail="HotLead not found")
    doc = await get_by_id(COLL_HOT_LEADS, hotlead_id)
    event_map = {
        "approved": "hotlead_approved",
        "deferred": "hotlead_deferred",
        "removed": "hotlead_removed",
    }
    await log_event(event_map[payload.status], "backend/api", {"hotlead_id": hotlead_id})

    if payload.status == "approved":
        p = await get_by_id(COLL_ROLODEX, doc["prospect_id"])  # type: ignore
        if p:
            history = p.get("engagement_history", [])
            history.append({
                "event": "closing_approved",
                "by_agent": "Praefectus",
                "details": "Hot lead approved – Legatus may proceed",
                "timestamp": now_iso(),
            })
            await update_by_id(COLL_ROLODEX, p["id"], {"engagement_history": history})
    return doc

@api.patch("/hotleads/{hotlead_id}", response_model=HotLead, tags=["hotleads"])
async def patch_hot_lead(hotlead_id: str, payload: HotLeadPatch):
    existing = await get_by_id(COLL_HOT_LEADS, hotlead_id)
    if not existing:
        raise HTTPException(status_code=404, detail="HotLead not found")
    data = payload.model_dump(exclude_unset=True)
    await update_by_id(COLL_HOT_LEADS, hotlead_id, data)
    doc = await get_by_id(COLL_HOT_LEADS, hotlead_id)
    if "proposed_script" in data:
        await log_event("hotlead_script_edited", "backend/api", {"hotlead_id": hotlead_id})
    return doc

# Mission Control — Threads and Messages
class Thread(BaseModel):
    model_config = ConfigDict(extra="forbid")
    thread_id: str = Field(default_factory=new_id)
    title: str
    mission_id: Optional[str] = None
    goal: Optional[str] = None
    stage: str = "brainstorm"  # brainstorm | consolidate | execute
    synopsis: Optional[str] = None
    pinned_message_ids: List[str] = Field(default_factory=list)
    stage_history: List[Dict[str, Any]] = Field(default_factory=list)
    message_count: int = 0
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class ThreadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    mission_id: Optional[str] = None

class ThreadUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = None
    mission_id: Optional[str] = None
    goal: Optional[str] = None
    stage: Optional[str] = None
    synopsis: Optional[str] = None

class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=new_id)
    thread_id: str
    mission_id: Optional[str] = None
    role: str  # human | praefectus
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=now_iso)

COLL_THREADS = db["Threads"]
COLL_MESSAGES = db["Messages"]

from providers.selector import select_praefectus_default_model
from providers.factory import get_llm_client

SYSTEM_PROMPT = (
    "You are Praefectus, the orchestrator for Praetorian Legion. "
    "Hold a helpful, expert, collaborative tone. Respond in clear, concise prose. "
    "No JSON unless explicitly requested."
)

@api.patch("/mission_control/threads/{thread_id}", tags=["mission_control"])
async def update_thread(thread_id: str, payload: ThreadUpdate):
    th = await COLL_THREADS.find_one({"_id": thread_id})
    if not th:
        raise HTTPException(status_code=404, detail="Thread not found")
    data = payload.model_dump(exclude_unset=True)
    updates: Dict[str, Any] = {}
    if "stage" in data and data["stage"] and data["stage"] != th.get("stage", "brainstorm"):
        history = th.get("stage_history", [])
        history.append({"stage": data["stage"], "timestamp": now_iso()})
        updates["stage_history"] = history
    for k, v in data.items():
        if k != "stage_history":
            updates[k] = v
    updates["updated_at"] = now_iso()
    await COLL_THREADS.update_one({"_id": thread_id}, {"$set": updates})
    out = await COLL_THREADS.find_one({"_id": thread_id})
    out.pop("_id", None)
    return out

@api.post("/mission_control/threads", tags=["mission_control"])
async def create_thread(payload: ThreadCreate):
    t = Thread(title=payload.title, mission_id=payload.mission_id)
    doc = t.model_dump()
    doc["_id"] = doc["thread_id"]
    await COLL_THREADS.insert_one(doc)
    await log_event("thread_created", "backend/mission_control", {"thread_id": t.thread_id})
    return {"thread_id": t.thread_id}

@api.get("/mission_control/threads", tags=["mission_control"])
async def list_threads(mission_id: Optional[str] = None):
    q: Dict[str, Any] = {}
    if mission_id:
        q["mission_id"] = mission_id
    threads = await COLL_THREADS.find(q).sort("updated_at", -1).to_list(100)
    if not threads:
        # Auto-create General on first load
        gen = Thread(title="General")
        gdoc = gen.model_dump(); gdoc["_id"] = gen.thread_id
        await COLL_THREADS.insert_one(gdoc)
        threads = [gdoc]
    for d in threads:
        d.pop("_id", None)
    return threads

@api.get("/mission_control/thread/{thread_id}", tags=["mission_control"])
async def get_thread(thread_id: str, limit: int = 50, before: Optional[str] = None):
    th = await COLL_THREADS.find_one({"_id": thread_id})
    if not th:
        raise HTTPException(status_code=404, detail="Thread not found")
    before_time = None
    if before:
        m = await COLL_MESSAGES.find_one({"_id": before})
        if m:
            before_time = m.get("created_at")
    mq: Dict[str, Any] = {"thread_id": thread_id}
    if before_time:
        mq["created_at"] = {"$lt": before_time}
    msgs = await COLL_MESSAGES.find(mq).sort("created_at", -1).limit(limit).to_list(limit)
    for d in msgs:
        d.pop("_id", None)
    th.pop("_id", None)
    return {"thread": th, "messages": list(reversed(msgs))}

class MCChatInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    thread_id: Optional[str] = None
    text: str
    approve: Optional[bool] = False
    draft: Optional[Dict[str, Any]] = None

@api.post("/mission_control/message", tags=["mission_control"])
async def mission_control_post_message(payload: MCChatInput):
    txt = (payload.text or "").strip()
    if not txt:
        raise HTTPException(status_code=400, detail="text is required")
    # Default to General thread if none provided
    thread_id = payload.thread_id
    if not thread_id:
        gen = await COLL_THREADS.find_one({"title": "General"})
        if not gen:
            # create General
            gen_t = Thread(title="General")
            gdoc = gen_t.model_dump(); gdoc["_id"] = gen_t.thread_id
            await COLL_THREADS.insert_one(gdoc)
            gen = gdoc
        thread_id = gen.get("_id") or gen.get("thread_id")
    th = await COLL_THREADS.find_one({"_id": thread_id})
    if not th:
        raise HTTPException(status_code=404, detail="Thread not found")
    # Append human
    human = Message(thread_id=thread_id, mission_id=th.get("mission_id"), role="human", text=txt)
    hdoc = human.model_dump(); hdoc["_id"] = human.id
    await COLL_MESSAGES.insert_one(hdoc)
    # LLM call
    client = get_llm_client()
    model_id = select_praefectus_default_model()
    # Build context preamble from product_brief guardrail
    product = await COLL_GUARDRAILS.find_one({"type": "product_brief"})
    product_brief = ""
    if product and isinstance(product.get("value"), dict):
        v = product.get("value")
        # Compose short bullet lines
        def join_list(key):
            arr = v.get(key) or []
            return "; ".join(arr) if isinstance(arr, list) else str(arr)
        product_brief = (
            f"Product: {v.get('title','')} — {v.get('one_liner','')}\n"
            f"Category: {v.get('category','')}\n"
            f"Value props: {join_list('value_props')}\n"
            f"Features: {join_list('key_features')}\n"
            f"Differentiators: {join_list('differentiators')}\n"
            f"Forbidden tone: {join_list('forbidden_tone')}\n"
        ).strip()
    thread_preamble = (
        f"Goal: {th.get('goal','(unset)')}\n"
        f"Stage: {th.get('stage','brainstorm')}\n"
        f"Synopsis: {th.get('synopsis','')}\n"
        f"Mission posture: {('research_only' if False else (await COLL_MISSIONS.find_one({'_id': th.get('mission_id')})).get('posture') if th.get('mission_id') else 'n/a')}\n"
    )
    stage_behavior = {
        "brainstorm": "Generate several viable options. Ask 1-2 concise clarifiers. Avoid committing.",
        "consolidate": "Compare shortlisted options, converge to one cohesive plan, and show trade-offs.",
        "execute": "Report progress, next actions, and missing inputs. Prepare updates and findings.",
    }
    anti_drift = (
        "Stay strictly aligned to this thread's goal. If user is ambiguous, ask one brief clarifier or reframe to the goal. "
        "Do not change domains or metaphors that break the mission context."
    )
    system = "\n\n".join(filter(None, [SYSTEM_PROMPT, product_brief, thread_preamble, stage_behavior.get(th.get('stage','brainstorm'), ''), anti_drift]))

    # Include last ~6 messages for context
    recent_msgs = await COLL_MESSAGES.find({"thread_id": thread_id}).sort("created_at", -1).limit(6).to_list(6)
    recent_msgs = list(reversed(recent_msgs))
    messages = [{"role": "system", "content": system}] + [
        {"role": ("user" if m.get("role") == "human" else "assistant"), "content": m.get("text","")}
        for m in recent_msgs
    ] + [{"role": "user", "content": txt}]

    await log_event("context_preamble_used", "backend/mission_control", {"thread_id": thread_id, "model_id": model_id})
    try:
        resp = client.chat(model_id=model_id, messages=messages, temperature=0.3, max_tokens=800)
        assistant_text = resp.get("text", "")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")
    # Append assistant
    # Drift guard keywords
    drift_terms = ["UAV","enemy","kinetic","overwatch","SIGINT","munition","airstrike","platoon","terrain"]
    lower = assistant_text.lower()
    offending = [k for k in drift_terms if k.lower() in lower]
    reframed = False
    if offending:
        await log_event("assistant_redraft_due_to_drift", "backend/mission_control", {"thread_id": thread_id, "offending_terms": offending})
        # Redraft
        redraft_prompt = "You drifted off the mission. Rewrite strictly aligned to the thread goal and current stage."
        try:
            r2 = client.chat(model_id=model_id, messages=[{"role": "system", "content": system}, {"role": "user", "content": redraft_prompt}], temperature=0.2, max_tokens=800)
            assistant_text = r2.get("text", assistant_text)
            reframed = True
        except Exception:
            pass

    # Append assistant
    assistant = Message(thread_id=thread_id, mission_id=th.get("mission_id"), role="praefectus", text=assistant_text, metadata={"reframed": reframed})
    adoc = assistant.model_dump(); adoc["_id"] = assistant.id
    await COLL_MESSAGES.insert_one(adoc)
    # Update thread counters
    await COLL_THREADS.update_one({"_id": thread_id}, {"$set": {"updated_at": now_iso()}, "$inc": {"message_count": 2}})
    await log_event("praefectus_message_appended", "backend/mission_control", {"thread_id": thread_id, "model_id": model_id, "reframed": reframed})
    return {"assistant": {"text": assistant_text, "created_at": assistant.created_at, "reframed": reframed}}

class SummarizeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    thread_id: str

@api.post("/mission_control/summarize", tags=["mission_control"])
async def mission_control_summarize(payload: SummarizeInput):
    th = await COLL_THREADS.find_one({"_id": payload.thread_id})
    if not th:
        raise HTTPException(status_code=404, detail="Thread not found")
    msgs = await COLL_MESSAGES.find({"thread_id": payload.thread_id}).sort("created_at", 1).to_list(200)
    convo = "\n".join([f"{m.get('role')}: {m.get('text')}" for m in msgs])
    prompt = (
        "Summarize the conversation into a mission draft. Return fields as plain bullet prose (no JSON):\n"
        "Title, Objective, Posture (help_only/help_plus_soft_marketing/research_only), Audience, Success Criteria (list), Risks (list), Approvals Needed (list), Notes.\n\n" + convo
    )
    client = get_llm_client(); model_id = select_praefectus_default_model()
    r = client.chat(model_id=model_id, messages=[{"role":"system","content":SYSTEM_PROMPT}, {"role":"user","content": prompt}], temperature=0.3, max_tokens=800)
    # Append short assistant note
    note = Message(thread_id=payload.thread_id, role="praefectus", text="Summary ready. Open Draft panel.")
    ndoc = note.model_dump(); ndoc["_id"] = note.id
    await COLL_MESSAGES.insert_one(ndoc)
    await COLL_THREADS.update_one({"_id": payload.thread_id}, {"$set": {"updated_at": now_iso()}, "$inc": {"message_count": 1}})
    await log_event("mission_summary_prepared", "backend/mission_control", {"thread_id": payload.thread_id})
    # For Phase 1, return the raw assistant text split into fields client-side
    return {"structured_text": r.get("text", ""), "timestamp": now_iso()}

class ConvertToDraftInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    thread_id: str
    fields_override: Optional[Dict[str, Any]] = None

@api.post("/mission_control/convert_to_draft", tags=["mission_control"])
async def mission_control_convert_to_draft(payload: ConvertToDraftInput):
    warnings: List[str] = []
    approval_blocked = False
    draft = payload.fields_override or {}
    posture = draft.get("posture") or "help_only"
    # Simple guardrail check
    guards = await COLL_GUARDRAILS.find().to_list(200)
    has_research_only = any((g.get("default_posture") == "research_only") or (g.get("type") == "posture" and g.get("value") == "research_only") for g in guards)
    if posture == "help_plus_soft_marketing" and has_research_only:
        warnings.append("Guardrail requires research_only; marketing disabled.")
        approval_blocked = True
    await log_event("mission_draft_prepared", "backend/mission_control", {"thread_id": payload.thread_id, "posture": posture})
    return {"draft": draft, "warnings": warnings, "approval_blocked": approval_blocked, "timestamp": now_iso()}

class ApproveDraftInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    thread_id: str
    draft: Dict[str, Any]
    confirm_override: Optional[bool] = False

@api.post("/mission_control/approve_draft", tags=["mission_control"])
async def mission_control_approve_draft(payload: ApproveDraftInput):
    # Re-check guardrails
    warnings: List[str] = []
    approval_blocked = False
    posture = payload.draft.get("posture") or "help_only"
    guards = await COLL_GUARDRAILS.find().to_list(200)
    has_research_only = any((g.get("default_posture") == "research_only") or (g.get("type") == "posture" and g.get("value") == "research_only") for g in guards)
    if posture == "help_plus_soft_marketing" and has_research_only and not payload.confirm_override:
        warnings.append("Guardrail requires research_only; marketing disabled.")
        approval_blocked = True
        return {"warnings": warnings, "approval_blocked": approval_blocked}
    created = await create_mission(MissionCreate(**{
        "title": payload.draft.get("title", "New Mission"),
        "objective": payload.draft.get("objective", "Explore and summarize findings"),
        "posture": posture,
        "state": "scanning",
    }))
    # Link thread to mission
    await COLL_THREADS.update_one({"_id": payload.thread_id}, {"$set": {"mission_id": created["id"], "updated_at": now_iso()}})
    await log_event("mission_created", "backend/mission_control", {"mission_id": created["id"], "thread_id": payload.thread_id})
    return {"mission_id": created["id"], "timestamp": now_iso()}

class StartMissionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mission_id: str

@api.post("/mission_control/start_mission", tags=["mission_control"])
async def mission_control_start_mission(payload: StartMissionInput):
    doc = await get_by_id(COLL_MISSIONS, payload.mission_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Mission not found")
    await update_by_id(COLL_MISSIONS, payload.mission_id, {"state": "engaging"})
    await log_event("mission_started", "backend/mission_control", {"mission_id": payload.mission_id})
    return {"ok": True, "mission_id": payload.mission_id, "timestamp": now_iso()}

# Exports (CSV generation + download)
async def filter_prospects_for_export(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    docs = await COLL_ROLODEX.find().to_list(5000)
    rows = []
    for d in docs:
        d.pop("_id", None)
        ok = True
        if "priority_state" in spec:
            if d.get("priority_state") not in set(spec["priority_state"]):
                ok = False
        if ok and spec.get("has_linkedin"):
            if "linkedin" not in (d.get("handles") or {}):
                ok = False
        if ok and spec.get("platforms"):
            pt = set(d.get("platform_tags") or [])
            if pt.isdisjoint(set(spec["platforms"])):
                ok = False
        if ok and spec.get("tags"):
            mt = set(d.get("mission_tags") or [])
            if mt.isdisjoint(set(spec["tags"])):
                ok = False
        if ok:
            rows.append(d)
    return rows

@api.post("/exports/recipe", response_model=Export, tags=["exports"])
async def create_export_recipe(payload: ExportRecipeCreate):
    exp = Export(recipe_name=payload.recipe_name, filter_spec=payload.filter_spec)
    doc = await insert_with_id(COLL_EXPORTS, exp.model_dump())
    await log_event("export_recipe_created", "backend/api", {"export_id": doc["id"], "recipe_name": payload.recipe_name})
    return doc

@api.post("/exports/generate", response_model=Export, tags=["exports"])
async def generate_export(payload: ExportGenerate):
    recipe = await COLL_EXPORTS.find_one({"recipe_name": payload.recipe_name})
    if not recipe:
        exp = Export(recipe_name=payload.recipe_name)
        recipe = await insert_with_id(COLL_EXPORTS, exp.model_dump())
    else:
        recipe.pop("_id", None)
    rows = await filter_prospects_for_export(recipe.get("filter_spec", {}))
    output = io.StringIO()
    writer = csv.writer(output)
    headers = [
        "id","name_or_alias","priority_state","company","role","handles.linkedin","platform_tags","mission_tags","created_at","updated_at"
    ]
    writer.writerow(headers)
    for r in rows:
        writer.writerow([
            r.get("id"), r.get("name_or_alias"), r.get("priority_state"), r.get("company"), r.get("role"),
            (r.get("handles") or {}).get("linkedin",""),
            ";".join(r.get("platform_tags") or []),
            ";".join(r.get("mission_tags") or []),
            r.get("created_at"), r.get("updated_at"),
        ])
    csv_data = output.getvalue()
    update = {
        "row_count": len(rows),
        "file_url": f"/api/exports/{recipe['id']}/download",
        "generated_at": now_iso(),
        "csv_data": csv_data,
    }
    await update_by_id(COLL_EXPORTS, recipe["id"], update)
    doc = await get_by_id(COLL_EXPORTS, recipe["id"])
    await log_event("export_generated", "backend/api", {"export_id": doc["id"], "row_count": doc["row_count"]})
    return doc

@api.get("/exports", response_model=List[Export], tags=["exports"])
async def list_exports():
    docs = await COLL_EXPORTS.find().sort("generated_at", -1).to_list(200)
    cleaned = []
    for d in docs:
        d.pop("_id", None)
        d.pop("csv_data", None)
        cleaned.append(d)
    return cleaned

@api.get("/exports/{export_id}/download", tags=["exports"])
async def download_export(export_id: str):
    doc = await COLL_EXPORTS.find_one({"_id": export_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Export not found")
    csv_data = doc.get("csv_data", "")
    headers = {"Content-Disposition": f"attachment; filename=export_{export_id}.csv"}
    return Response(content=csv_data, media_type="text/csv", headers=headers)

# Findings
class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=new_id)
    mission_id: str
    thread_id: str
    title: str
    body_markdown: str = ""
    highlights: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class FindingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mission_id: str
    thread_id: str
    title: str
    body_markdown: Optional[str] = ""
    highlights: Optional[List[str]] = None
    metrics: Optional[Dict[str, Any]] = None
    attachments: Optional[List[Dict[str, Any]]] = None

class FindingPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = None
    body_markdown: Optional[str] = None
    highlights: Optional[List[str]] = None
    metrics: Optional[Dict[str, Any]] = None
    attachments: Optional[List[Dict[str, Any]]] = None

COLL_FINDINGS = db["Findings"]

@api.post("/findings", tags=["findings"])
async def create_finding(payload: FindingCreate):
    base = Finding(
        mission_id=payload.mission_id,
        thread_id=payload.thread_id,
        title=payload.title,
        body_markdown=payload.body_markdown or "",
        highlights=payload.highlights or [],
        metrics=payload.metrics or {},
        attachments=payload.attachments or [],
    )
    doc = await insert_with_id(COLL_FINDINGS, base.model_dump())
    await log_event("findings_created", "backend/findings", {"finding_id": doc["id"], "mission_id": doc["mission_id"], "thread_id": doc["thread_id"]})
    return doc

@api.get("/findings", tags=["findings"])
async def list_findings(mission_id: Optional[str] = None, limit: int = 200):
    q: Dict[str, Any] = {}
    if mission_id:
        q["mission_id"] = mission_id
    cursor = COLL_FINDINGS.find(q).sort("updated_at", -1).limit(limit)
    docs = await cursor.to_list(limit)
    return [{k: v for k, v in d.items() if k != "_id"} for d in docs]

@api.get("/findings/{finding_id}", tags=["findings"])
async def get_finding(finding_id: str):
    doc = await get_by_id(COLL_FINDINGS, finding_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Finding not found")
    return doc

@api.patch("/findings/{finding_id}", tags=["findings"])
async def patch_finding(finding_id: str, payload: FindingPatch):
    data = payload.model_dump(exclude_unset=True)
    updated = await update_by_id(COLL_FINDINGS, finding_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Finding not found")
    doc = await get_by_id(COLL_FINDINGS, finding_id)
    await log_event("findings_updated", "backend/findings", {"finding_id": finding_id})
    return doc

@api.post("/findings/{finding_id}/export", tags=["findings"])
async def export_finding(finding_id: str, format: str = "md"):
    d = await COLL_FINDINGS.find_one({"_id": finding_id})
    if not d:
        raise HTTPException(status_code=404, detail="Finding not found")
    d.pop("_id", None)
    filename = f"finding_{finding_id}.{ 'md' if format=='md' else 'csv' }"
    if format == "md":
        content = f"# {d.get('title','')}\n\n" + (d.get("body_markdown", "") or "")
        media = "text/markdown"
    else:
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["id","mission_id","thread_id","title","updated_at"])
        writer.writerow([d.get("id"), d.get("mission_id"), d.get("thread_id"), d.get("title"), d.get("updated_at")])
        content = out.getvalue()
        media = "text/csv"
    await log_event("findings_exported", "backend/findings", {"finding_id": finding_id, "format": format})
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return Response(content=content, media_type=media, headers=headers)

class SnapshotFindingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    thread_id: str

@api.post("/mission_control/snapshot_findings", tags=["mission_control"])
async def snapshot_findings(payload: SnapshotFindingInput):
    th = await COLL_THREADS.find_one({"_id": payload.thread_id})
    if not th:
        raise HTTPException(status_code=404, detail="Thread not found")
    if not th.get("mission_id"):
        raise HTTPException(status_code=400, detail="Thread not linked to a mission")
    msgs = await COLL_MESSAGES.find({"thread_id": payload.thread_id}).sort("created_at", -1).limit(6).to_list(6)
    msgs = list(reversed(msgs))
    lines = [
        f"Goal: {th.get('goal','')}",
        f"Stage: {th.get('stage','brainstorm')}",
        f"Synopsis: {th.get('synopsis','')}",
        "",
        "Last 6 turns:",
    ]
    for m in msgs:
        ts = to_phoenix(m.get("created_at")) or m.get("created_at")
        lines.append(f"- {ts} {m.get('role')}: {m.get('text')}")
    body = "\n".join(lines)
    title = f"Findings - {th.get('title','Thread')} {now_iso()}"
    fdoc = Finding(mission_id=th.get("mission_id"), thread_id=payload.thread_id, title=title, body_markdown=body)
    doc = await insert_with_id(COLL_FINDINGS, fdoc.model_dump())
    await log_event("findings_created", "backend/findings", {"finding_id": doc['id'], "mission_id": doc['mission_id'], "thread_id": doc['thread_id']})
    return doc

# Agents
@api.post("/agents/status", response_model=AgentStatus, tags=["agents"])
async def upsert_agent_status(payload: AgentStatus):
    # Normalize any inbound timestamps to Phoenix for storage consistency
    norm = payload.model_dump()
    for k in ("last_activity", "created_at", "updated_at", "next_retry_at"):
        if k in norm and norm[k]:
            norm[k] = to_phoenix(norm[k])
    # Normalize nested activity_stream timestamps if present
    if isinstance(norm.get("activity_stream"), list):
        fixed_stream = []
        for entry in norm["activity_stream"]:
            if isinstance(entry, dict) and entry.get("timestamp"):
                entry = {**entry, "timestamp": to_phoenix(entry["timestamp"]) }
            fixed_stream.append(entry)
        norm["activity_stream"] = fixed_stream

    existing = await COLL_AGENTS.find_one({"agent_name": payload.agent_name})
    if existing:
        await update_by_id(COLL_AGENTS, existing["_id"], {k: v for k, v in norm.items() if k != "id"})
        doc = await get_by_id(COLL_AGENTS, existing["_id"])
    else:
        doc = await insert_with_id(COLL_AGENTS, norm)
    await log_event("agent_status_changed", "backend/api", {"agent_name": doc["agent_name"], "status_light": doc.get("status_light")})
    return doc

class AgentError(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_name: str
    error_state: str
    next_retry_at: Optional[str] = None

@api.post("/agents/error", response_model=AgentStatus, tags=["agents"])
async def report_agent_error(payload: AgentError):
    existing = await COLL_AGENTS.find_one({"agent_name": payload.agent_name})
    if not existing:
        base = AgentStatus(agent_name=payload.agent_name, status_light="red", error_state=payload.error_state, last_activity=now_iso(), next_retry_at=payload.next_retry_at)
        doc = await insert_with_id(COLL_AGENTS, base.model_dump())
    else:
        await update_by_id(COLL_AGENTS, existing["_id"], {"status_light": "red", "error_state": payload.error_state, "last_activity": now_iso(), "next_retry_at": payload.next_retry_at})
        doc = await get_by_id(COLL_AGENTS, existing["_id"])
    await log_event("agent_error_detected", "backend/api", {"agent_name": payload.agent_name, "error_state": payload.error_state})
    if payload.next_retry_at:
        await log_event("agent_retry_scheduled", "backend/api", {"agent_name": payload.agent_name, "next_retry_at": payload.next_retry_at})
    return doc

@api.get("/agents", response_model=List[AgentStatus], tags=["agents"])
async def list_agents():
    # Ensure all three agent rows exist
    required = [
        ("Praefectus", "green"),
        ("Explorator", "green"),
        ("Legatus", "green"),
    ]
    existing = await COLL_AGENTS.find().to_list(10)
    index = {d.get("agent_name"): d for d in existing}
    for name, default_color in required:
        if name not in index:
            await insert_with_id(COLL_AGENTS, AgentStatus(agent_name=name, status_light=("yellow" if name=="Legatus" else default_color), last_activity=now_iso()).model_dump())

    # Auto-reset Explorator error state if retry time has passed
    now_dt = datetime.now(tz=PHOENIX_TZ)
    expl = await COLL_AGENTS.find_one({"agent_name": "Explorator"})
    if expl and expl.get("next_retry_at"):
        try:
            retry_dt = datetime.fromisoformat(expl["next_retry_at"].replace("Z", "+00:00"))
            if retry_dt <= now_dt:
                # Determine new status based on active missions
                active_missions = await COLL_MISSIONS.count_documents({"state": {"$in": ["scanning","engaging","escalating"]}})
                desired_status = "green" if active_missions > 0 else "yellow"
                update_fields: Dict[str, Any] = {"last_activity": now_iso(), "error_state": None, "next_retry_at": None}
                # If currently red, also flip to desired status
                if expl.get("status_light") == "red":
                    update_fields["status_light"] = desired_status
                await update_by_id(COLL_AGENTS, expl["_id"], update_fields)
                await log_event("agent_error_cleared", "backend/api", {"agent_name": "Explorator"})
                # Emit status_changed only if we actually changed status color
                if expl.get("status_light") == "red":
                    await log_event("agent_status_changed", "backend/api", {"agent_name": "Explorator", "status_light": desired_status})
        except Exception:
            # If parsing fails, ignore
            pass

    # Apply research_only posture rule and general Legatus posture logic
    # 1) If any active research_only mission exists, Legatus must be yellow (idle)
    await ensure_legatus_idle_if_research_only_exists()
    # 2) If no research_only mission is active, set Legatus reflecting outreach status: green if any approved hot lead exists, else yellow
    active_research_only = await COLL_MISSIONS.count_documents({
        "posture": "research_only",
        "state": {"$in": ["draft", "scanning", "engaging", "escalating"]},
    })
    if active_research_only == 0:
        leg = await COLL_AGENTS.find_one({"agent_name": "Legatus"})
        if leg:
            approved_hl = await COLL_HOT_LEADS.count_documents({"status": "approved"})
            leg_status = "green" if approved_hl > 0 else "yellow"
            if leg.get("status_light") != leg_status:
                await update_by_id(COLL_AGENTS, leg["_id"], {"status_light": leg_status, "last_activity": now_iso()})
                await log_event("agent_status_changed", "backend/api", {"agent_name": "Legatus", "status_light": leg_status})

    docs = await COLL_AGENTS.find().sort("agent_name", 1).to_list(50)
    # Normalize outgoing timestamps to Phoenix (including nested activity_stream timestamps)
    cleaned = []
    for d in docs:
        d.pop("_id", None)
        for k in ("last_activity", "created_at", "updated_at", "next_retry_at"):
            if d.get(k):
                d[k] = to_phoenix(d[k])
        if isinstance(d.get("activity_stream"), list):
            new_stream = []
            for entry in d["activity_stream"]:
                if isinstance(entry, dict) and entry.get("timestamp"):
                    entry = {**entry, "timestamp": to_phoenix(entry["timestamp"]) }
                new_stream.append(entry)
            d["activity_stream"] = new_stream
        cleaned.append(d)
    return cleaned

# Guardrails
@api.get("/guardrails", tags=["guardrails"])
async def list_guardrails():
    docs = await COLL_GUARDRAILS.find().sort("updated_at", -1).to_list(200)
    return [{k: v for k, v in d.items() if k != "_id"} for d in docs]

@api.post("/guardrails", tags=["guardrails"])
async def create_guardrail(payload: Dict[str, Any]):
    payload = {**payload}
    payload.setdefault("created_at", now_iso())
    payload.setdefault("updated_at", payload["created_at"])
    doc = await insert_with_id(COLL_GUARDRAILS, payload)
    await log_event("guardrail_updated", "backend/api", {"guardrail_id": doc["id"]})
    return doc

@api.get("/guardrails/{guardrail_id}", tags=["guardrails"])
async def get_guardrail(guardrail_id: str):
    doc = await get_by_id(COLL_GUARDRAILS, guardrail_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Guardrail not found")
    return doc

@api.put("/guardrails/{guardrail_id}", tags=["guardrails"])
async def update_guardrail(guardrail_id: str, payload: Dict[str, Any]):
    existing = await get_by_id(COLL_GUARDRAILS, guardrail_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Guardrail not found")
    payload = {k: v for k, v in payload.items()}
    await update_by_id(COLL_GUARDRAILS, guardrail_id, payload)
    doc = await get_by_id(COLL_GUARDRAILS, guardrail_id)
    await log_event("guardrail_updated", "backend/api", {"guardrail_id": guardrail_id})
    return doc

# Events (for auditing/logging)
@api.get("/events", tags=["events"]) 
async def list_events(limit: int = 200, mission_id: Optional[str] = None, hotlead_id: Optional[str] = None, prospect_id: Optional[str] = None, agent_name: Optional[str] = None, source: Optional[str] = None):
    q: Dict[str, Any] = {}
    if mission_id:
        q["payload.mission_id"] = mission_id
    if hotlead_id:
        q["payload.hotlead_id"] = hotlead_id
    if prospect_id:
        q["payload.prospect_id"] = prospect_id
    if agent_name:
        q["payload.agent_name"] = agent_name
    if source:
        q["source"] = source
    cursor = COLL_EVENTS.find(q).sort("timestamp", -1).limit(limit)
    docs = await cursor.to_list(limit)
    return [{k: v for k, v in d.items() if k != "_id"} for d in docs]

# ---------- Scenario Helper Endpoints (Milestone C) ----------
class ScenarioResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    ok: bool = True
    message: str
    mission_id: Optional[str] = None

@api.post("/scenarios/strict_rule_mission", response_model=ScenarioResult, tags=["scenarios"])
async def scenario_strict_rule_mission():
    # Create a strict-help mission, seed forums (>=5) and some prospects
    m = await create_mission(MissionCreate(
        title="Map senior agent-ops engineers in strict forums",
        objective="Discover and profile at least five strict-help forums; add initial prospects",
        posture="help_only",
        state="scanning",
    ))
    forum_specs = [
        ("StackOverflow", "agentops", "https://stackoverflow.com/tags/agentops", ["agentops","observability"]),
        ("Reddit", "r/agentops", "https://reddit.com/r/agentops", ["agents","ops"]),
        ("Discord", "AgentOps Guild", "https://discord.gg/agentops", ["guild"]),
        ("GitHub", "AgentOps Discussions", "https://github.com/topics/agentops", ["discussions"]),
        ("Hacker News", "AgentOps", "https://news.ycombinator.com", ["hn"]) ,
    ]
    count_forums = 0
    for plat, name, url, tags in forum_specs:
        await create_forum(ForumCreate(platform=plat, name=name, url=url, rule_profile="strict_help_only", topic_tags=tags))
        count_forums += 1
    # Add a couple prospects
    p1 = await create_prospect(ProspectCreate(name_or_alias="Alex Doe", handles={"linkedin": "alexdoe"}, priority_state="warm", source_type="seeded"))
    p2 = await create_prospect(ProspectCreate(name_or_alias="Sam Lee", handles={"github": "samlee"}, priority_state="cold", source_type="seeded"))
    # Update mission counters
    counters = m["counters"]
    counters["forums_found"] += count_forums
    counters["prospects_added"] += 2
    await update_by_id(COLL_MISSIONS, m["id"], {"counters": counters})
    return ScenarioResult(ok=True, message="Strict-rule mission seeded with forums and prospects", mission_id=m["id"]).model_dump()

@api.post("/scenarios/open_forum_plan", response_model=ScenarioResult, tags=["scenarios"])
async def scenario_open_forum_plan():
    m = await create_mission(MissionCreate(
        title="Explore agent observability chatter",
        objective="Scan X/LinkedIn for agent observability and draft engagement plan",
        posture="help_plus_soft_marketing",
        state="scanning",
        insights=["Risks: platform policy changes, perception of marketing"],
    ))
    # Seed open forums
    await create_forum(ForumCreate(platform="X", name="#agentobservability", url="https://x.com/search?q=agent%20observability", rule_profile="open_soft_marketing", topic_tags=["agents","observability"]))
    await create_forum(ForumCreate(platform="LinkedIn", name="Agent Observability", url="https://www.linkedin.com/search/results/content/?keywords=agent%20observability", rule_profile="open_soft_marketing", topic_tags=["agents","observability"]))
    counters = m["counters"]
    counters["forums_found"] += 2
    await update_by_id(COLL_MISSIONS, m["id"], {"counters": counters, "insights": m.get("insights", []) + ["Initial platforms prioritized: X & LinkedIn"]})
    await log_event("approval_requested", "Praefectus", {"mission_id": m["id"], "posture": "help_plus_soft_marketing"})
    return ScenarioResult(ok=True, message="Open-forum plan drafted and forums added", mission_id=m["id"]).model_dump()

@api.post("/scenarios/generate_hotlead", tags=["scenarios"])
async def scenario_generate_hotlead():
    # Find or create a prospect with a buying signal
    prospects = await COLL_ROLODEX.find().to_list(10)
    pid = None
    if prospects:
        pid = prospects[0].get("_id") or prospects[0].get("id")
    else:
        p = await create_prospect(ProspectCreate(name_or_alias="Jordan Kim", handles={"linkedin":"jordank"}, priority_state="hot", signals=[Signal(type="post", quote="We need agent observability now", link="https://example.com").model_dump()], source_type="seeded"))
        pid = p["id"]
    hl = await create_hot_lead(HotLeadCreate(
        prospect_id=str(pid),
        evidence=[Evidence(quote="Strong buying signal", link="https://example.com/thread")],
        proposed_script="Hi! It sounds like you're evaluating observability for agents. Happy to share a short checklist and a 10‑min call if helpful.",
        suggested_actions=["prepare brief case study", "offer trial"],
    ))
    return {"ok": True, "hotlead_id": hl["id"]}

@api.post("/scenarios/export_shortcut", tags=["scenarios"])
async def scenario_export_shortcut():
    name = "Warm+Hot last 7 days with LinkedIn handle"
    await create_export_recipe(ExportRecipeCreate(recipe_name=name, filter_spec={"priority_state":["warm","hot"], "has_linkedin": True}))
    doc = await generate_export(ExportGenerate(recipe_name=name))
    return {"ok": True, "export_id": doc["id"], "file_url": doc.get("file_url")}

class RetryWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    minutes: Optional[int] = 5

@api.post("/scenarios/agent_error_retry", tags=["scenarios"])
async def scenario_agent_error_retry(payload: RetryWindow | None = None):
    minutes = (payload.minutes if payload and payload.minutes is not None else 5)
    next_retry = (datetime.now(tz=PHOENIX_TZ) + timedelta(minutes=minutes)).isoformat()
    doc = await report_agent_error(AgentError(agent_name="Explorator", error_state="crawl_timeout", next_retry_at=next_retry))
    return {"ok": True, "agent": doc}

# Mount router
from providers.routes import router as providers_router
app.include_router(api)
app.include_router(providers_router)

# CORS (origins from env)
_cors_origins_raw = os.environ.get("CORS_ORIGINS", "*")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
_allow_credentials = True
if "*" in _cors_origins:
    _allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_credentials=_allow_credentials,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()