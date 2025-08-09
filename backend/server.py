from fastapi import FastAPI, APIRouter, HTTPException, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime
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

# ID helper
new_id = lambda: str(uuid.uuid4())

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
    # timestamps (Phoenix)
    created = doc.get("created_at", now_iso())
    doc["created_at"] = created
    doc["updated_at"] = doc.get("updated_at", created)
    # avoid ObjectId by setting _id
    doc["_id"] = doc["id"]
    await coll.insert_one(doc)
    # remove _id for API output
    doc.pop("_id", None)
    return doc

async def update_by_id(coll, _id: str, fields: Dict[str, Any]) -> int:
    fields = {k: v for k, v in fields.items() if v is not None}
    fields["updated_at"] = now_iso()
    res = await coll.update_one({"_id": _id}, {"$set": fields})
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
    state: str  # draft|scanning|engaging|escalating|paused|complete
    agents_assigned: List[str] = Field(default_factory=list)
    counters: Dict[str, int] = Field(default_factory=lambda: {
        "forums_found": 0,
        "prospects_added": 0,
        "hot_leads": 0,
    })
    insights: List[str] = Field(default_factory=list)
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
    return doc

@api.patch("/missions/{mission_id}", response_model=Mission, tags=["missions"])
async def update_mission(mission_id: str, payload: MissionUpdate):
    updated = await update_by_id(COLL_MISSIONS, mission_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Mission not found or not modified")
    doc = await get_by_id(COLL_MISSIONS, mission_id)
    await log_event("mission_updated_state" if payload.state else "mission_created", "backend/api", {"mission_id": mission_id, **payload.model_dump(exclude_unset=True)})
    await ensure_legatus_idle_if_research_only_exists()
    return doc

class MissionStateChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: str

@api.post("/missions/{mission_id}/state", response_model=Mission, tags=["missions"])
async def change_mission_state(mission_id: str, payload: MissionStateChange):
    updated = await update_by_id(COLL_MISSIONS, mission_id, {"state": payload.state})
    if not updated:
        raise HTTPException(status_code=404, detail="Mission not found")
    doc = await get_by_id(COLL_MISSIONS, mission_id)
    # Emit specific events
    state_event = {
        "paused": "mission_paused",
        "complete": "mission_completed",
    }.get(payload.state, "mission_updated_state")
    await log_event(state_event, "backend/api", {"mission_id": mission_id, "state": payload.state})
    await ensure_legatus_idle_if_research_only_exists()
    return doc

# Forums
@api.post("/forums", response_model=Forum, tags=["forums"])
async def create_forum(payload: ForumCreate):
    forum = Forum(**payload.model_dump())
    doc = await insert_with_id(COLL_FORUMS, forum.model_dump())
    await log_event("forum_discovered", "backend/api", {"forum_id": doc["id"]})
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

@api.patch("/forums/{forum_id}", response_model=Forum, tags=["forums"])
async def update_forum(forum_id: str, payload: ForumUpdate):
    # Determine if rule_profile changed to log specific event
    existing = await get_by_id(COLL_FORUMS, forum_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Forum not found")
    updated = await update_by_id(COLL_FORUMS, forum_id, payload.model_dump(exclude_unset=True))
    doc = await get_by_id(COLL_FORUMS, forum_id)
    if "rule_profile" in payload.model_dump(exclude_unset=True) and existing.get("rule_profile") != doc.get("rule_profile"):
        await log_event("forum_rule_profile_changed", "backend/api", {"forum_id": forum_id, "rule_profile": doc.get("rule_profile")})
    else:
        await log_event("forum_updated", "backend/api", {"forum_id": forum_id})
    return doc

# Prospects (Rolodex)
@api.post("/prospects", response_model=Prospect, tags=["prospects"])
async def create_prospect(payload: ProspectCreate):
    prospect = Prospect(**payload.model_dump())
    doc = await insert_with_id(COLL_ROLODEX, prospect.model_dump())
    await log_event("prospect_added", "backend/api", {"prospect_id": doc["id"]})
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
    # Ensure prospect exists
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
    return doc

# Mission Control Chat
class MCMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    approve: Optional[bool] = False
    reject: Optional[bool] = False
    draft: Optional[Dict[str, Any]] = None

class MCReply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    understanding: str
    critique_options: List[str]
    recommended_mission_draft: Dict[str, Any]
    open_questions: List[str]

@api.post("/mission_control/message", response_model=MCReply, tags=["mission_control"])
async def mission_control_message(payload: MCMessage):
    text = payload.text.strip()
    # naive parsing
    wants_research = any(k in text.lower() for k in ["research", "map", "discover"])
    posture = "research_only" if wants_research else "help_only"
    draft = payload.draft or {
        "title": (text[:48] + "...") if len(text) > 48 else (text or "New Mission"),
        "objective": text or "Explore and summarize findings",
        "posture": posture,
        "state": "draft",
    }
    reply = MCReply(
        understanding=f"You asked to {'research/map' if wants_research else 'assist'}: {text[:180]}",
        critique_options=[
            "Scope clarity: define target persona precisely",
            "Success criteria: specify measurable outcomes",
            "Guardrails: confirm per-forum posture & etiquette",
        ],
        recommended_mission_draft=draft,
        open_questions=[
            "Which platforms are highest priority?",
            "Any sensitive topics to avoid?",
        ],
    )
    # log events
    await log_event("mission_draft_submitted", "Praefectus", {"draft": draft})
    await log_event("approval_requested", "Praefectus", {"draft": draft})

    # append activity for Praefectus (human + ai)
    await append_agent_activity("Praefectus", {"who": "human", "content": text, "timestamp": now_iso()})
    await append_agent_activity("Praefectus", {"who": "Praefectus", "content": f"Draft proposed: {draft['title']}", "timestamp": now_iso()})

    # optional auto-actions
    if payload.reject:
        await log_event("approval_rejected", "backend/api", {"draft": draft})
        return reply

    if payload.approve:
        # create mission
        created = await create_mission(MissionCreate(**{
            "title": draft.get("title", "New Mission"),
            "objective": draft.get("objective", text or "Explore"),
            "posture": draft.get("posture", posture),
            "state": "draft",
        }))
        await log_event("approval_granted", "backend/api", {"mission_id": created["id"]})
        # If research_only, auto-discover a couple forums (Explorator behavior)
        if created.get("posture") == "research_only":
            samples = [
                ForumCreate(platform="Reddit", name="r/agentops", url="https://reddit.com/r/agentops", rule_profile="strict_help_only", topic_tags=["agents","ops"]),
                ForumCreate(platform="StackOverflow", name="agentops tag", url="https://stackoverflow.com/questions/tagged/agentops", rule_profile="strict_help_only", topic_tags=["agentops"]),
            ]
            for f in samples:
                try:
                    await create_forum(f)
                except Exception:
                    pass
        # Ensure Legatus idle when research_only exists
        await ensure_legatus_idle_if_research_only_exists()
    return reply

# Exports (CSV generation + download)
async def filter_prospects_for_export(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    # naive filtering in Python for Phase 1
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
    # Find or create recipe
    recipe = await COLL_EXPORTS.find_one({"recipe_name": payload.recipe_name})
    if not recipe:
        exp = Export(recipe_name=payload.recipe_name)
        recipe = await insert_with_id(COLL_EXPORTS, exp.model_dump())
    else:
        recipe.pop("_id", None)
    rows = await filter_prospects_for_export(recipe.get("filter_spec", {}))
    # build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    headers = [
        "id","name_or_alias","priority_state","company","role","handles.linkedin","platform_tags","mission_tags","created_at","updated_at"
    ]
    writer.writerow(headers)
    for r in rows:
        writer.writerow([
            r.get("id"),
            r.get("name_or_alias"),
            r.get("priority_state"),
            r.get("company"),
            r.get("role"),
            (r.get("handles") or {}).get("linkedin",""),
            ";".join(r.get("platform_tags") or []),
            ";".join(r.get("mission_tags") or []),
            r.get("created_at"),
            r.get("updated_at"),
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
    # strip csv_data from listing
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
    headers = {
        "Content-Disposition": f"attachment; filename=export_{export_id}.csv"
    }
    return Response(content=csv_data, media_type="text/csv", headers=headers)

# Agents
@api.post("/agents/status", response_model=AgentStatus, tags=["agents"])
async def upsert_agent_status(payload: AgentStatus):
    # Upsert on agent_name
    existing = await COLL_AGENTS.find_one({"agent_name": payload.agent_name})
    if existing:
        await update_by_id(COLL_AGENTS, existing["_id"], payload.model_dump(exclude={"id"}))
        doc = await get_by_id(COLL_AGENTS, existing["_id"])
    else:
        doc = await insert_with_id(COLL_AGENTS, payload.model_dump())
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
        # initialize record
        base = AgentStatus(agent_name=payload.agent_name, status_light="red", error_state=payload.error_state, last_activity=now_iso())
        doc = await insert_with_id(COLL_AGENTS, base.model_dump())
    else:
        await update_by_id(COLL_AGENTS, existing["_id"], {"status_light": "red", "error_state": payload.error_state, "last_activity": now_iso()})
        doc = await get_by_id(COLL_AGENTS, existing["_id"])
    await log_event("agent_error_detected", "backend/api", {"agent_name": payload.agent_name, "error_state": payload.error_state})
    if payload.next_retry_at:
        await log_event("agent_retry_scheduled", "backend/api", {"agent_name": payload.agent_name, "next_retry_at": payload.next_retry_at})
    return doc

@api.get("/agents", response_model=List[AgentStatus], tags=["agents"])
async def list_agents():
    docs = await COLL_AGENTS.find().sort("updated_at", -1).to_list(50)
    return [{k: v for k, v in d.items() if k != "_id"} for d in docs]

# Guardrails
@api.get("/guardrails", tags=["guardrails"])
async def list_guardrails():
    docs = await COLL_GUARDRAILS.find().sort("updated_at", -1).to_list(200)
    return [{k: v for k, v in d.items() if k != "_id"} for d in docs]

@api.post("/guardrails", tags=["guardrails"])
async def create_guardrail(payload: Dict[str, Any]):
    # Ensure timestamps
    payload = {**payload}
    payload.setdefault("created_at", now_iso())
    payload.setdefault("updated_at", payload["created_at"])
    doc = await insert_with_id(COLL_GUARDRAILS, payload)
    await log_event("guardrail_updated", "backend/api", {"guardrail_id": doc["id"]})
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
async def list_events(limit: int = 200, mission_id: Optional[str] = None, hotlead_id: Optional[str] = None, prospect_id: Optional[str] = None, agent_name: Optional[str] = None):
    q: Dict[str, Any] = {}
    # we stored identifiers inside payload keys in our log_event usage
    if mission_id:
        q["payload.mission_id"] = mission_id
    if hotlead_id:
        q["payload.hotlead_id"] = hotlead_id
    if prospect_id:
        q["payload.prospect_id"] = prospect_id
    if agent_name:
        q["payload.agent_name"] = agent_name
    cursor = COLL_EVENTS.find(q).sort("timestamp", -1).limit(limit)
    docs = await cursor.to_list(limit)
    return [{k: v for k, v in d.items() if k != "_id"} for d in docs]

# Mount router
app.include_router(api)

# CORS (origins from env)
# CORS configuration with safe wildcard handling
_cors_origins_raw = os.environ.get("CORS_ORIGINS", "*")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
_allow_credentials = True
if "*" in _cors_origins:
    # Starlette disallows '*' with credentials. To ensure CORS works in dev with
    # wildcard origins (e.g., localhost:3000 -> preview domain), disable credentials.
    _allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_credentials=_allow_credentials,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Shutdown hook
@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()