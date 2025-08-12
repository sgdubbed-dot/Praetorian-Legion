from fastapi import FastAPI, APIRouter, HTTPException, Request, Response
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
import asyncio

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
COLL_THREADS = db["Threads"]
COLL_MESSAGES = db["Messages"]
COLL_FINDINGS = db["Findings"]

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

# Mission state changes
class MissionStateChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: str

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

# Guardrail (flexible structure)
class Guardrail(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class GuardrailUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")
    pass

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

from providers.selector import select_praefectus_default_model
from providers.factory import get_llm_client

SYSTEM_PROMPT = (
    "You are Praefectus, the orchestrator for Praetorian Legion. "
    "Hold a helpful, expert, collaborative tone. Respond in clear, concise prose. "
    "No JSON unless explicitly requested."
)

# ------------------ Helpers ------------------
async def ensure_legatus_idle_if_research_only_exists():
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

def map_thread_status(mission: Optional[Dict[str, Any]]) -> str:
    if not mission:
        return "Unlinked"
    st = mission.get("state")
    if st in {"scanning", "engaging", "escalating"}:
        return "Running"
    if st == "paused":
        return "Paused"
    if st == "complete":
        return "Completed"
    if st == "aborted":
        return "Aborted"
    return "Unlinked"

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
    if data.get("state") == "paused" and existing.get("state") not in {"paused","complete","aborted"}:
        data["previous_active_state"] = existing.get("state")
    await update_by_id(COLL_MISSIONS, mission_id, data)
    doc = await get_by_id(COLL_MISSIONS, mission_id)
    event = "mission_created"
    if payload.state == "paused":
        event = "mission_paused"
    elif payload.state in {"abort", "aborted"}:
        event = "mission_aborted"
    elif payload.state == "resume":
        event = "mission_resumed"
    elif payload.state == "complete":
        event = "mission_completed"
    else:
        event = "mission_updated_state"
    await log_event(event, "backend/api", {"mission_id": mission_id, **(payload.model_dump(exclude_unset=True))})
    await ensure_legatus_idle_if_research_only_exists()
    return doc

@api.post("/missions/{mission_id}/state", response_model=Mission, tags=["missions"])
async def change_mission_state(mission_id: str, payload: MissionStateChange):
    mission = await get_by_id(COLL_MISSIONS, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    new_state = payload.state
    if payload.state == "resume":
        prior = mission.get("previous_active_state") or "scanning"
        new_state = prior
        await log_event("mission_resumed", "backend/api", {"mission_id": mission_id})
    elif payload.state in {"abort", "aborted"}:
        new_state = "aborted"
        await log_event("mission_aborted", "backend/api", {"mission_id": mission_id})
    elif payload.state == "paused":
        await log_event("mission_paused", "backend/api", {"mission_id": mission_id})
    elif payload.state == "complete":
        await log_event("mission_completed", "backend/api", {"mission_id": mission_id})
    await update_by_id(COLL_MISSIONS, mission_id, {"state": new_state})
    doc = await get_by_id(COLL_MISSIONS, mission_id)
    await ensure_legatus_idle_if_research_only_exists()
    return doc

# Findings (kept minimal here for Phase 1 references)
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

# Mission Control: threads/messages
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
    doc = t.model_dump(); doc["_id"] = doc["thread_id"]
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
        gen = Thread(title="General")
        gdoc = gen.model_dump(); gdoc["_id"] = gen.thread_id
        await COLL_THREADS.insert_one(gdoc)
        threads = [gdoc]
    out = []
    for d in threads:
        mission = None
        if d.get("mission_id"):
            mission = await COLL_MISSIONS.find_one({"_id": d["mission_id"]})
            if mission:
                mission.pop("_id", None)
        status = map_thread_status(mission)
        d.pop("_id", None)
        out.append({**d, "thread_status": status})
    return out

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
    th_clean = {k: v for k, v in th.items() if k != "_id"}
    mission = None
    if th.get("mission_id"):
        mission = await COLL_MISSIONS.find_one({"_id": th.get("mission_id")})
        if mission:
            mission.pop("_id", None)
    status = map_thread_status(mission)
    await log_event("thread_loaded", "backend/mission_control", {"thread_id": thread_id})
    return {"thread": {**th_clean, "thread_status": status}, "messages": list(reversed(msgs))}

class MCChatInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    thread_id: Optional[str] = None
    text: str

@api.post("/mission_control/message", tags=["mission_control"])
async def mission_control_post_message(payload: MCChatInput):
    txt = (payload.text or "").strip()
    if not txt:
        raise HTTPException(status_code=400, detail="text is required")
    thread_id = payload.thread_id
    if not thread_id:
        gen = await COLL_THREADS.find_one({"title": "General"})
        if not gen:
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

    lowered = txt.lower().strip()
    # Trigger set: create/run/pause/stop/abort
    if lowered in {"create mission now", "approve and create mission now", "create & start mission now"}:
        # Create mission only (no auto-start here), link, and post Start/Edit actions
        objective_text = ""
        try:
            # best-effort summary to pick an objective line
            msgs = await COLL_MESSAGES.find({"thread_id": thread_id}).sort("created_at", 1).to_list(200)
            convo = "\n".join([f"{m.get('role')}: {m.get('text')}" for m in msgs])
            client = get_llm_client(); model_id = select_praefectus_default_model()
            prompt = (
                "Extract a concise objective line from this conversation. Return a single sentence.\n\n" + convo
            )
            r = client.chat(model_id=model_id, messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}], temperature=0.2, max_tokens=60)
            objective_text = r.get("text", "").strip()
        except Exception:
            objective_text = ""
        created = await create_mission(MissionCreate(**{
            "title": th.get("title", "New Mission"),
            "objective": objective_text,
            "posture": "research_only",
            "state": "scanning",
        }))
        mission_id = created["id"]
        await COLL_THREADS.update_one({"_id": thread_id}, {"$set": {"mission_id": mission_id, "updated_at": now_iso()}})
        await log_event("mission_created", "backend/mission_control", {"mission_id": mission_id, "thread_id": thread_id})
        await log_event("run_controls_used", "backend/mission_control", {"action": "run_create", "thread_id": thread_id, "mission_id": mission_id})
        text = "Mission created. Would you like to make modifications before starting?"
        assistant = Message(thread_id=thread_id, mission_id=mission_id, role="praefectus", text=text, metadata={"actions": ["start_now", "edit_draft"]})
        adoc = assistant.model_dump(); adoc["_id"] = assistant.id
        await COLL_MESSAGES.insert_one(adoc)
        await COLL_THREADS.update_one({"_id": thread_id}, {"$set": {"updated_at": now_iso()}, "$inc": {"message_count": 2}})
        return {"assistant": {"text": text, "created_at": assistant.created_at, "metadata": assistant.metadata}, "mission_id": mission_id}

    if lowered == "run mission now":
        if th.get("mission_id"):
            mission = await get_by_id(COLL_MISSIONS, th["mission_id"])
            if mission.get("state") == "paused":
                # resume
                prior = mission.get("previous_active_state") or "scanning"
                await update_by_id(COLL_MISSIONS, mission["id"], {"state": prior})
                await log_event("mission_resumed", "backend/mission_control", {"mission_id": mission["id"]})
                text = "Resumed the mission. Ready to continue."
                assistant = Message(thread_id=thread_id, mission_id=mission["id"], role="praefectus", text=text, metadata={"actions": ["start_now", "edit_draft"]})
                adoc = assistant.model_dump(); adoc["_id"] = assistant.id
                await COLL_MESSAGES.insert_one(adoc)
                await COLL_THREADS.update_one({"_id": thread_id}, {"$set": {"updated_at": now_iso()}, "$inc": {"message_count": 1}})
                await log_event("run_controls_used", "backend/mission_control", {"action": "run_resume", "thread_id": thread_id, "mission_id": mission["id"]})
                return {"assistant": {"text": text, "created_at": assistant.created_at}}
            if mission.get("state") in {"complete", "aborted"}:
                # duplicate & start new run in same chat context (system message will guide)
                dup = await duplicate_run_internal(mission_id=mission["id"], source_thread_id=thread_id, start_now=True)
                return dup
            # already running
            text = "Mission is already running."
            assistant = Message(thread_id=thread_id, mission_id=mission["id"], role="praefectus", text=text)
            adoc = assistant.model_dump(); adoc["_id"] = assistant.id
            await COLL_MESSAGES.insert_one(adoc)
            await COLL_THREADS.update_one({"_id": thread_id}, {"$set": {"updated_at": now_iso()}, "$inc": {"message_count": 1}})
            return {"assistant": {"text": text, "created_at": assistant.created_at}}
        else:
            # No mission linked; create one (same as create path)
            created = await create_mission(MissionCreate(**{
                "title": th.get("title", "New Mission"),
                "objective": "",
                "posture": "research_only",
                "state": "scanning",
            }))
            mission_id = created["id"]
            await COLL_THREADS.update_one({"_id": thread_id}, {"$set": {"mission_id": mission_id, "updated_at": now_iso()}})
            await log_event("mission_created", "backend/mission_control", {"mission_id": mission_id, "thread_id": thread_id})
            await log_event("run_controls_used", "backend/mission_control", {"action": "run_create", "thread_id": thread_id, "mission_id": mission_id})
            text = "Mission created. Would you like to make modifications before starting?"
            assistant = Message(thread_id=thread_id, mission_id=mission_id, role="praefectus", text=text, metadata={"actions": ["start_now", "edit_draft"]})
            adoc = assistant.model_dump(); adoc["_id"] = assistant.id
            await COLL_MESSAGES.insert_one(adoc)
            await COLL_THREADS.update_one({"_id": thread_id}, {"$set": {"updated_at": now_iso()}, "$inc": {"message_count": 2}})
            return {"assistant": {"text": text, "created_at": assistant.created_at, "metadata": assistant.metadata}, "mission_id": mission_id}

    if lowered == "pause mission" and th.get("mission_id"):
        await update_by_id(COLL_MISSIONS, th["mission_id"], {"state": "paused", "previous_active_state": "engaging"})
        await log_event("mission_paused", "backend/mission_control", {"mission_id": th["mission_id"]})
        text = "Mission paused."
        assistant = Message(thread_id=thread_id, mission_id=th["mission_id"], role="praefectus", text=text)
        adoc = assistant.model_dump(); adoc["_id"] = assistant.id
        await COLL_MESSAGES.insert_one(adoc)
        await COLL_THREADS.update_one({"_id": thread_id}, {"$set": {"updated_at": now_iso()}, "$inc": {"message_count": 1}})
        await log_event("run_controls_used", "backend/mission_control", {"action": "pause", "thread_id": thread_id, "mission_id": th["mission_id"]})
        return {"assistant": {"text": text, "created_at": assistant.created_at}}

    if lowered == "stop mission" and th.get("mission_id"):
        await update_by_id(COLL_MISSIONS, th["mission_id"], {"state": "complete"})
        await log_event("mission_completed", "backend/mission_control", {"mission_id": th["mission_id"]})
        text = "Mission stopped and marked complete."
        assistant = Message(thread_id=thread_id, mission_id=th["mission_id"], role="praefectus", text=text)
        adoc = assistant.model_dump(); adoc["_id"] = assistant.id
        await COLL_MESSAGES.insert_one(adoc)
        await COLL_THREADS.update_one({"_id": thread_id}, {"$set": {"updated_at": now_iso()}, "$inc": {"message_count": 1}})
        await log_event("run_controls_used", "backend/mission_control", {"action": "stop", "thread_id": thread_id, "mission_id": th["mission_id"]})
        return {"assistant": {"text": text, "created_at": assistant.created_at}}

    if lowered == "abort mission" and th.get("mission_id"):
        await update_by_id(COLL_MISSIONS, th["mission_id"], {"state": "aborted"})
        await log_event("mission_aborted", "backend/mission_control", {"mission_id": th["mission_id"]})
        text = "Mission aborted."
        assistant = Message(thread_id=thread_id, mission_id=th["mission_id"], role="praefectus", text=text)
        adoc = assistant.model_dump(); adoc["_id"] = assistant.id
        await COLL_MESSAGES.insert_one(adoc)
        await COLL_THREADS.update_one({"_id": thread_id}, {"$set": {"updated_at": now_iso()}, "$inc": {"message_count": 1}})
        await log_event("run_controls_used", "backend/mission_control", {"action": "abort", "thread_id": thread_id, "mission_id": th["mission_id"]})
        return {"assistant": {"text": text, "created_at": assistant.created_at}}

    # Default LLM reply (non-streaming)
    client = get_llm_client(); model_id = select_praefectus_default_model()
    # Compact preamble omitted for brevity here in Phase 1
    try:
        r = client.chat(model_id=model_id, messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": txt}], temperature=0.3, max_tokens=800)
        assistant_text = r.get("text", "")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")
    assistant = Message(thread_id=thread_id, mission_id=th.get("mission_id"), role="praefectus", text=assistant_text)
    adoc = assistant.model_dump(); adoc["_id"] = assistant.id
    await COLL_MESSAGES.insert_one(adoc)
    await COLL_THREADS.update_one({"_id": thread_id}, {"$set": {"updated_at": now_iso()}, "$inc": {"message_count": 2}})
    await log_event("praefectus_message_appended", "backend/mission_control", {"thread_id": thread_id})
    return {"assistant": {"text": assistant_text, "created_at": assistant.created_at}}

# Convert/Approve/Start + Duplicate run endpoint (Phase 1 support)
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
    await log_event("mission_draft_prepared", "backend/mission_control", {"thread_id": payload.thread_id, "posture": posture})
    return {"draft": draft, "warnings": warnings, "approval_blocked": approval_blocked, "timestamp": now_iso()}

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

class DuplicateRunInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mission_id: str
    source_thread_id: str
    new_thread: Optional[bool] = True
    start_now: Optional[bool] = True

async def duplicate_run_internal(mission_id: str, source_thread_id: str, start_now: bool = True):
    base = await get_by_id(COLL_MISSIONS, mission_id)
    if not base:
        raise HTTPException(status_code=404, detail="Mission not found")
    src_thread = await COLL_THREADS.find_one({"_id": source_thread_id})
    if not src_thread:
        raise HTTPException(status_code=404, detail="Source thread not found")
    created = await create_mission(MissionCreate(**{
        "title": base.get("title", src_thread.get("title", "New Mission")),
        "objective": base.get("objective", ""),
        "posture": base.get("posture", "research_only"),
        "state": "scanning",
    }))
    new_thread = Thread(title=src_thread.get("title", base.get("title", "New Run")), goal=src_thread.get("goal"), synopsis=src_thread.get("synopsis"), mission_id=created["id"])  # type: ignore
    ndoc = new_thread.model_dump(); ndoc["_id"] = new_thread.thread_id
    await COLL_THREADS.insert_one(ndoc)
    await log_event("mission_created", "backend/mission_control", {"mission_id": created["id"], "duplicated_from": mission_id})
    if start_now:
        await update_by_id(COLL_MISSIONS, created["id"], {"state": "engaging"})
        await log_event("mission_started", "backend/mission_control", {"mission_id": created["id"]})
    # System message in new thread
    text = "New run created. Any changes before starting?"
    assistant = Message(thread_id=new_thread.thread_id, mission_id=created["id"], role="praefectus", text=text, metadata={"actions": ["start_now", "edit_draft"]})
    adoc = assistant.model_dump(); adoc["_id"] = assistant.id
    await COLL_MESSAGES.insert_one(adoc)
    await COLL_THREADS.update_one({"_id": new_thread.thread_id}, {"$set": {"updated_at": now_iso()}, "$inc": {"message_count": 1}})
    await log_event("run_controls_used", "backend/mission_control", {"action": "duplicate_start", "thread_id": new_thread.thread_id, "mission_id": created["id"]})
    return {"assistant": {"text": text, "created_at": assistant.created_at, "metadata": assistant.metadata}, "mission_id": created["id"], "thread_id": new_thread.thread_id}

@api.post("/mission_control/duplicate_run", tags=["mission_control"])
async def duplicate_run(payload: DuplicateRunInput):
    return await duplicate_run_internal(mission_id=payload.mission_id, source_thread_id=payload.source_thread_id, start_now=bool(payload.start_now))

# Providers module routes are in backend/providers/routes.py (unchanged)

# Shutdown hook
@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()