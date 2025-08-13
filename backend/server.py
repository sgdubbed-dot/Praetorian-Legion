from fastapi import FastAPI, APIRouter, HTTPException, Request, Response
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
import csv
import io
import asyncio

# Load env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# MongoDB
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI()
api = APIRouter(prefix="/api")

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
            # assume UTC if missing tz
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.astimezone(PHOENIX_TZ).isoformat()
    except Exception:
        return now_iso()

# UUID

def new_id() -> str:
    return str(uuid.uuid4())

# Collections
COLL_OPERATIONS = db["Missions"]
COLL_EVENTS = db["Events"]
COLL_THREADS = db["Threads"]
COLL_MESSAGES = db["Messages"]
COLL_FINDINGS = db["Findings"]
COLL_GUARDRAILS = db["Guardrails"]
COLL_AGENTS = db["Agents"]
COLL_EXPORTS = db["Exports"]
COLL_FORUMS = db["Forums"]
COLL_ROLODEX = db["Rolodex"]
COLL_HOT_LEADS = db["Hot Leads"]

# DB helpers (UUID only)
async def insert_with_id(coll, doc: Dict[str, Any]) -> Dict[str, Any]:
    if "id" not in doc and "thread_id" not in doc:
        doc["id"] = new_id()
    created = doc.get("created_at", now_iso())
    doc["created_at"] = created
    doc["updated_at"] = doc.get("updated_at", created)
    if "_id" not in doc:
        doc["_id"] = doc.get("id") or doc.get("thread_id")
    await coll.insert_one(doc)
    doc.pop("_id", None)
    return doc

async def update_by_id(coll, _id: str, fields: Dict[str, Any]) -> int:
    set_fields = {k: v for k, v in fields.items() if v is not None}
    unset_fields = {k: "" for k, v in fields.items() if v is None}
    set_fields["updated_at"] = now_iso()
    upd: Dict[str, Any] = {}
    if set_fields:
        upd["$set"] = set_fields
    if unset_fields:
        upd["$unset"] = unset_fields
    res = await coll.update_one({"_id": _id}, upd)
    return res.modified_count

async def get_by_id(coll, _id: str) -> Optional[Dict[str, Any]]:
    doc = await coll.find_one({"_id": _id})
    if doc:
        doc.pop("_id", None)
    return doc

# Events
class Event(BaseModel):
    id: str = Field(default_factory=new_id)
    event_name: str
    source: str
    timestamp: str = Field(default_factory=now_iso)
    payload: Dict[str, Any] = Field(default_factory=dict)

async def log_event(event_name: str, source: str, payload: Optional[Dict[str, Any]] = None):
    ev = Event(event_name=event_name, source=source, payload=payload or {})
    await insert_with_id(COLL_EVENTS, ev.model_dump())

@api.get("/events")
async def list_events(source: Optional[str] = None, mission_id: Optional[str] = None, thread_id: Optional[str] = None, limit: int = 100):
    q: Dict[str, Any] = {}
    if source: q["source"] = source
    if mission_id: q["payload.mission_id"] = mission_id
    if thread_id: q["payload.thread_id"] = thread_id
    docs = await COLL_EVENTS.find(q).sort("timestamp", -1).limit(limit).to_list(limit)
    return [{k: (to_phoenix(v) if k == "timestamp" else v) for k, v in d.items() if k != "_id"} for d in docs]

@api.post("/events")
async def create_event(payload: Dict[str, Any]):
    # used by FE error boundary
    name = payload.get("event_name") or "fe_error"
    src = payload.get("source") or "frontend"
    await log_event(name, src, payload.get("payload") or {k: v for k, v in payload.items() if k not in {"event_name", "source"}})
    return {"ok": True, "timestamp": now_iso()}

# Missions
class Mission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=new_id)
    title: str
    objective: str
    posture: str
    state: str
    agents_assigned: List[str] = Field(default_factory=list)
    counters: Dict[str, int] = Field(default_factory=lambda: {"forums_found":0, "prospects_added":0, "hot_leads":0})
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

@api.post("/missions")
async def create_mission(payload: MissionCreate):
    mission = Mission(**payload.model_dump())
    if mission.insights and not mission.insights_rich:
        mission.insights_rich = [{"text": t, "timestamp": now_iso()} for t in mission.insights]
    doc = await insert_with_id(COLL_OPERATIONS, mission.model_dump())
    await log_event("mission_created", "backend/api", {"mission_id": doc["id"]})
    return doc

@api.get("/missions")
async def list_missions():
    docs = await COLL_OPERATIONS.find().sort("updated_at", -1).to_list(1000)
    out = []
    for d in docs:
        d.pop("_id", None)
        # migrate-on-read defaults
        d.setdefault("counters", {"forums_found":0, "prospects_added":0, "hot_leads":0})
        d.setdefault("insights", [])
        d.setdefault("insights_rich", [])
        d.setdefault("previous_active_state", None)
        d.setdefault("state", "draft")
        d.setdefault("created_at", now_iso())
        d.setdefault("updated_at", now_iso())
        out.append(d)
    return out

@api.get("/missions/{mission_id}")
async def get_mission(mission_id: str):
    d = await get_by_id(COLL_OPERATIONS, mission_id)
    if not d:
        raise HTTPException(status_code=404, detail="Mission not found")
    # migrate-on-read
    changed = False
    if "counters" not in d: d["counters"] = {"forums_found":0, "prospects_added":0, "hot_leads":0}; changed = True
    if "insights" not in d: d["insights"] = []; changed = True
    if "insights_rich" not in d: d["insights_rich"] = []; changed = True
    if "previous_active_state" not in d: d["previous_active_state"] = None; changed = True
    if changed:
        await update_by_id(COLL_OPERATIONS, mission_id, {k: d[k] for k in ["counters","insights","insights_rich","previous_active_state"]})
    return d

@api.post("/missions/{mission_id}/state")
async def change_mission_state(mission_id: str, payload: Dict[str, Any]):
    doc = await get_by_id(COLL_OPERATIONS, mission_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Mission not found")
    state = payload.get("state")
    if state == "resume":
        state = doc.get("previous_active_state") or "scanning"
        await log_event("mission_resumed", "backend/api", {"mission_id": mission_id})
    elif state in {"abort", "aborted"}:
        state = "aborted"
        await log_event("mission_aborted", "backend/api", {"mission_id": mission_id})
    elif state == "paused":
        await log_event("mission_paused", "backend/api", {"mission_id": mission_id})
    elif state == "complete":
        await log_event("mission_completed", "backend/api", {"mission_id": mission_id})
    await update_by_id(COLL_OPERATIONS, mission_id, {"state": state})
    return await get_by_id(COLL_OPERATIONS, mission_id)

# Findings
class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=new_id)
    mission_id: Optional[str] = None
    thread_id: Optional[str] = None
    title: str = ""
    body_markdown: str = ""
    highlights: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class FindingPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = None
    body_markdown: Optional[str] = None
    highlights: Optional[List[str]] = None
    metrics: Optional[Dict[str, Any]] = None
    attachments: Optional[List[Dict[str, Any]]] = None

@api.get("/findings")
async def list_findings(mission_id: Optional[str] = None, limit: int = 200):
    q: Dict[str, Any] = {}
    if mission_id:
        q["mission_id"] = mission_id
    docs = await COLL_FINDINGS.find(q).sort("updated_at", -1).limit(limit).to_list(limit)
    out = []
    for d in docs:
        d.pop("_id", None)
        d.setdefault("title", "")
        d.setdefault("body_markdown", "")
        d.setdefault("highlights", [])
        d.setdefault("metrics", {})
        d.setdefault("mission_id", None)
        d.setdefault("created_at", now_iso())
        d.setdefault("updated_at", now_iso())
        out.append(d)
    return out

@api.get("/findings/{finding_id}")
async def get_finding(finding_id: str):
    d = await get_by_id(COLL_FINDINGS, finding_id)
    if not d:
        raise HTTPException(status_code=404, detail="Finding not found")
    changed = False
    for k, v in {"title":"", "body_markdown":"", "highlights":[], "metrics":{}, "mission_id":None}.items():
        if k not in d:
            d[k] = v
            changed = True
    if changed:
        await update_by_id(COLL_FINDINGS, finding_id, {k: d[k] for k in ["title","body_markdown","highlights","metrics","mission_id"]})
    return d

@api.patch("/findings/{finding_id}")
async def patch_finding(finding_id: str, payload: FindingPatch):
    data = payload.model_dump(exclude_unset=True)
    await update_by_id(COLL_FINDINGS, finding_id, data)
    return await get_by_id(COLL_FINDINGS, finding_id)

@api.post("/findings/{finding_id}/export")
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
        out = io.StringIO(); writer = csv.writer(out)
        writer.writerow(["id","mission_id","thread_id","title","updated_at"])
        writer.writerow([d.get("id"), d.get("mission_id"), d.get("thread_id"), d.get("title"), d.get("updated_at")])
        content = out.getvalue(); media = "text/csv"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    await log_event("findings_exported", "backend/findings", {"finding_id": finding_id, "format": format})
    return Response(content=content, media_type=media, headers=headers)

# Snapshot Findings
class SnapshotFindingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    thread_id: str

@api.post("/mission_control/snapshot_findings")
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

# Mission Control threads/messages
class Thread(BaseModel):
    model_config = ConfigDict(extra="forbid")
    thread_id: str = Field(default_factory=new_id)
    title: str
    mission_id: Optional[str] = None
    goal: Optional[str] = None
    stage: str = "brainstorm"
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
    role: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=now_iso)

from providers.selector import select_praefectus_default_model
from providers.factory import get_llm_client

SYSTEM_PROMPT = (
    "You are Praefectus, the strategic AI commander for Augustus. "
    
    "ABOUT PRAETORIA:\n"
    "Praetoria is a visibility and control layer for the agent economy—a unified command center for monitoring, validating, and coordinating autonomous AI agents across cloud, chain, and code. "
    "It evolves through 3 stages: (1) Agent Observability (live now), (2) Platform & Registry (2-4 months), (3) Control Infrastructure (6-12 months).\n"
    
    "PRAETORIA'S MISSION:\n"
    "• Stage 1: Mission Control for live agent fleets with real-time observability, trace logs, and debugging\n"
    "• Stage 2: Registry of registries with verified agent identity, reputation, and compliance\n"
    "• Stage 3: Internet-grade control infrastructure with routing, payments, and security for autonomous software\n"
    
    "TARGET MARKET & PERSONAS:\n"
    "• Developers/Agent Teams: Need observability, fast debugging, reproducible traces, verified identity\n"
    "• Startups: Monitor live agents post-launch, clear performance views for investors\n"
    "• Enterprises: Multi-vendor visibility, governance, audit logs, risk scores across internal/partner agents\n"
    "• Security & Compliance: Anomaly detection, provenance, policy enforcement on agent behavior\n"
    "• Investors & Analysts: Real-time view of the agent economy—who's operating, where, how well\n"
    
    "CURRENT PRODUCT (Stage 1):\n"
    "Mission Control with global agent activity, Agent Trace Logs for forensics-grade debugging, Organization Views per customer, "
    "real-time alerts with root-cause analysis and fix suggestions. Built for agents (not generic apps), captures prompt/response traces.\n"
    
    "COMPETITIVE ADVANTAGES:\n"
    "• Framework-agnostic (LangChain, CrewAI, AutoGen, LangGraph, on-chain agents)\n"
    "• Privacy-by-design with tiered visibility\n"
    "• Agent-native (captures multi-step reasoning, prompt/response traces)\n"
    "• Evolution path: tool → platform → infrastructure\n"
    
    "YOUR ROLE AS PRAEFECTUS:\n"
    "You orchestrate Augustus's intelligence, marketing, and sales operations to help Praetoria reach its target market. "
    "You understand the agent economy, the pain points of agent builders, and how Praetoria solves visibility/control challenges. "
    "Focus on engaging developers, startups, enterprises dealing with agent proliferation, monitoring needs, and governance challenges.\n"
    
    "COMMUNICATION STYLE:\n"
    "Hold a helpful, expert, collaborative tone. Speak with authority about agent observability, debugging challenges, "
    "and the need for agent identity/registry solutions. Respond in clear, concise prose. No JSON unless explicitly requested."
)

def map_thread_status(mission: Optional[Dict[str, Any]]) -> str:
    if not mission:
        return "Unlinked"
    st = mission.get("state")
    if st in {"scanning", "engaging", "escalating"}: return "Running"
    if st == "paused": return "Paused"
    if st == "complete": return "Completed"
    if st == "aborted": return "Aborted"
    return "Unlinked"

@api.post("/mission_control/threads")
async def create_thread(payload: ThreadCreate):
    t = Thread(title=payload.title, mission_id=payload.mission_id)
    doc = t.model_dump(); doc["_id"] = t.thread_id
    await COLL_THREADS.insert_one(doc)
    await log_event("thread_created", "backend/mission_control", {"thread_id": t.thread_id})
    return {"thread_id": t.thread_id}

@api.get("/mission_control/threads")
async def list_threads(mission_id: Optional[str] = None):
    q: Dict[str, Any] = {}
    if mission_id: q["mission_id"] = mission_id
    threads = await COLL_THREADS.find(q).sort("updated_at", -1).to_list(200)
    if not threads:
        gen = Thread(title="General")
        gdoc = gen.model_dump(); gdoc["_id"] = gen.thread_id
        await COLL_THREADS.insert_one(gdoc)
        threads = [gdoc]
    out = []
    for d in threads:
        mission = None
        if d.get("mission_id"):
            mission = await COLL_OPERATIONS.find_one({"_id": d["mission_id"]})
            if mission: mission.pop("_id", None)
        status = map_thread_status(mission)
        d.pop("_id", None)
        out.append({**d, "thread_status": status})
    return out

@api.get("/mission_control/thread/{thread_id}")
async def get_thread(thread_id: str, limit: int = 50, before: Optional[str] = None):
    th = await COLL_THREADS.find_one({"_id": thread_id})
    if not th: raise HTTPException(status_code=404, detail="Thread not found")
    before_time = None
    if before:
        m = await COLL_MESSAGES.find_one({"_id": before})
        if m: before_time = m.get("created_at")
    mq: Dict[str, Any] = {"thread_id": thread_id}
    if before_time: mq["created_at"] = {"$lt": before_time}
    msgs = await COLL_MESSAGES.find(mq).sort("created_at", -1).limit(limit).to_list(limit)
    for d in msgs: d.pop("_id", None)
    mission = None
    if th.get("mission_id"):
        mission = await COLL_OPERATIONS.find_one({"_id": th.get("mission_id")})
        if mission: mission.pop("_id", None)
    status = map_thread_status(mission)
    await log_event("thread_loaded", "backend/mission_control", {"thread_id": thread_id})
    th_clean = {k: v for k, v in th.items() if k != "_id"}
    return {"thread": {**th_clean, "thread_status": status}, "messages": list(reversed(msgs))}

class MCChatInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    thread_id: Optional[str] = None
    text: str

@api.post("/mission_control/message")
async def mission_control_message(payload: MCChatInput):
    txt = (payload.text or "").strip()
    if not txt: raise HTTPException(status_code=400, detail="text is required")
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
    if not th: raise HTTPException(status_code=404, detail="Thread not found")

    # append human
    human = Message(thread_id=thread_id, mission_id=th.get("mission_id"), role="human", text=txt)
    hdoc = human.model_dump(); hdoc["_id"] = human.id
    await COLL_MESSAGES.insert_one(hdoc)

    lowered = txt.lower().strip()
    # triggers
    if lowered in {"create mission now", "approve and create mission now", "create & start mission now"}:
        created = await create_mission(MissionCreate(**{
            "title": th.get("title", "New Mission"),
            "objective": "",
            "posture": "research_only",
            "state": "scanning",
        }))
        mission_id = created["id"]
        await update_by_id(COLL_THREADS, thread_id, {"mission_id": mission_id})
        await log_event("run_controls_used", "backend/mission_control", {"action": "run_create", "thread_id": thread_id, "mission_id": mission_id})
        text = "Mission created. Would you like to make modifications before starting?"
        assistant = Message(thread_id=thread_id, mission_id=mission_id, role="praefectus", text=text, metadata={"actions": ["start_now", "edit_draft"]})
        adoc = assistant.model_dump(); adoc["_id"] = assistant.id
        await COLL_MESSAGES.insert_one(adoc)
        await update_by_id(COLL_THREADS, thread_id, {})
        return {"assistant": {"text": text, "created_at": assistant.created_at, "metadata": assistant.metadata}, "mission_id": mission_id}

    if lowered == "run mission now":
        if th.get("mission_id"):
            mission = await get_by_id(COLL_OPERATIONS, th["mission_id"])
            if mission.get("state") == "paused":
                prior = mission.get("previous_active_state") or "scanning"
                await update_by_id(COLL_OPERATIONS, mission["id"], {"state": prior})
                await log_event("mission_resumed", "backend/mission_control", {"mission_id": mission["id"]})
                text = "Resumed the mission. Ready to continue."
                assistant = Message(thread_id=thread_id, mission_id=mission["id"], role="praefectus", text=text, metadata={"actions": ["start_now", "edit_draft"]})
                adoc = assistant.model_dump(); adoc["_id"] = assistant.id
                await COLL_MESSAGES.insert_one(adoc)
                await update_by_id(COLL_THREADS, thread_id, {})
                await log_event("run_controls_used", "backend/mission_control", {"action": "run_resume", "thread_id": thread_id, "mission_id": mission["id"]})
                return {"assistant": {"text": text, "created_at": assistant.created_at}}
            if mission.get("state") in {"complete", "aborted"}:
                # duplicate
                dup = await duplicate_run_internal(mission_id=mission["id"], source_thread_id=thread_id, start_now=True)
                return dup
            text = "Mission is already running."
            assistant = Message(thread_id=thread_id, mission_id=mission["id"], role="praefectus", text=text)
            adoc = assistant.model_dump(); adoc["_id"] = assistant.id
            await COLL_MESSAGES.insert_one(adoc)
            await update_by_id(COLL_THREADS, thread_id, {})
            return {"assistant": {"text": text, "created_at": assistant.created_at}}
        else:
            created = await create_mission(MissionCreate(**{
                "title": th.get("title", "New Mission"),
                "objective": "",
                "posture": "research_only",
                "state": "scanning",
            }))
            mission_id = created["id"]
            await update_by_id(COLL_THREADS, thread_id, {"mission_id": mission_id})
            await log_event("mission_created", "backend/mission_control", {"mission_id": mission_id, "thread_id": thread_id})
            await log_event("run_controls_used", "backend/mission_control", {"action": "run_create", "thread_id": thread_id, "mission_id": mission_id})
            text = "Mission created. Would you like to make modifications before starting?"
            assistant = Message(thread_id=thread_id, mission_id=mission_id, role="praefectus", text=text, metadata={"actions": ["start_now", "edit_draft"]})
            adoc = assistant.model_dump(); adoc["_id"] = assistant.id
            await COLL_MESSAGES.insert_one(adoc)
            await update_by_id(COLL_THREADS, thread_id, {})
            return {"assistant": {"text": text, "created_at": assistant.created_at, "metadata": assistant.metadata}, "mission_id": mission_id}

    if lowered == "pause mission" and th.get("mission_id"):
        await update_by_id(COLL_OPERATIONS, th["mission_id"], {"state": "paused", "previous_active_state": "engaging"})
        await log_event("mission_paused", "backend/mission_control", {"mission_id": th["mission_id"]})
        text = "Mission paused."
        assistant = Message(thread_id=thread_id, mission_id=th["mission_id"], role="praefectus", text=text)
        adoc = assistant.model_dump(); adoc["_id"] = assistant.id
        await COLL_MESSAGES.insert_one(adoc)
        await update_by_id(COLL_THREADS, thread_id, {})
        await log_event("run_controls_used", "backend/mission_control", {"action": "pause", "thread_id": thread_id, "mission_id": th["mission_id"]})
        return {"assistant": {"text": text, "created_at": assistant.created_at}}

    if lowered == "stop mission" and th.get("mission_id"):
        await update_by_id(COLL_OPERATIONS, th["mission_id"], {"state": "complete"})
        await log_event("mission_completed", "backend/mission_control", {"mission_id": th["mission_id"]})
        text = "Mission stopped and marked complete."
        assistant = Message(thread_id=thread_id, mission_id=th["mission_id"], role="praefectus", text=text)
        adoc = assistant.model_dump(); adoc["_id"] = assistant.id
        await COLL_MESSAGES.insert_one(adoc)
        await update_by_id(COLL_THREADS, thread_id, {})
        await log_event("run_controls_used", "backend/mission_control", {"action": "stop", "thread_id": thread_id, "mission_id": th["mission_id"]})
        return {"assistant": {"text": text, "created_at": assistant.created_at}}

    if lowered == "abort mission" and th.get("mission_id"):
        await update_by_id(COLL_OPERATIONS, th["mission_id"], {"state": "aborted"})
        await log_event("mission_aborted", "backend/mission_control", {"mission_id": th["mission_id"]})
        text = "Mission aborted."
        assistant = Message(thread_id=thread_id, mission_id=th["mission_id"], role="praefectus", text=text)
        adoc = assistant.model_dump(); adoc["_id"] = assistant.id
        await COLL_MESSAGES.insert_one(adoc)
        await update_by_id(COLL_THREADS, thread_id, {})
        await log_event("run_controls_used", "backend/mission_control", {"action": "abort", "thread_id": thread_id, "mission_id": th["mission_id"]})
        return {"assistant": {"text": text, "created_at": assistant.created_at}}

    # default LLM reply
    client = get_llm_client(); model_id = select_praefectus_default_model()
    try:
        r = client.chat(model_id=model_id, messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": txt}], temperature=0.3, max_tokens=800)
        assistant_text = r.get("text", "")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")
    assistant = Message(thread_id=thread_id, mission_id=th.get("mission_id"), role="praefectus", text=assistant_text)
    adoc = assistant.model_dump(); adoc["_id"] = assistant.id
    await COLL_MESSAGES.insert_one(adoc)
    await update_by_id(COLL_THREADS, thread_id, {})
    await log_event("praefectus_message_appended", "backend/mission_control", {"thread_id": thread_id})
    return {"assistant": {"text": assistant_text, "created_at": assistant.created_at}}

# Duplicate run and start
class DuplicateRunInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mission_id: str
    source_thread_id: str
    new_thread: Optional[bool] = True
    start_now: Optional[bool] = True

async def duplicate_run_internal(mission_id: str, source_thread_id: str, start_now: bool = True):
    base = await get_by_id(COLL_OPERATIONS, mission_id)
    if not base: raise HTTPException(status_code=404, detail="Mission not found")
    src_thread = await COLL_THREADS.find_one({"_id": source_thread_id})
    if not src_thread: raise HTTPException(status_code=404, detail="Source thread not found")
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
        await update_by_id(COLL_OPERATIONS, created["id"], {"state": "engaging"})
        await log_event("mission_started", "backend/mission_control", {"mission_id": created["id"]})
    # system message
    text = "New run created. Any changes before starting?"
    assistant = Message(thread_id=new_thread.thread_id, mission_id=created["id"], role="praefectus", text=text, metadata={"actions": ["start_now", "edit_draft"]})
    adoc = assistant.model_dump(); adoc["_id"] = assistant.id
    await COLL_MESSAGES.insert_one(adoc)
    await update_by_id(COLL_THREADS, new_thread.thread_id, {})
    await log_event("run_controls_used", "backend/mission_control", {"action": "duplicate_start", "thread_id": new_thread.thread_id, "mission_id": created["id"]})
    return {"assistant": {"text": text, "created_at": assistant.created_at, "metadata": assistant.metadata}, "mission_id": created["id"], "thread_id": new_thread.thread_id}

@api.post("/mission_control/duplicate_run")
async def duplicate_run(payload: DuplicateRunInput):
    return await duplicate_run_internal(mission_id=payload.mission_id, source_thread_id=payload.source_thread_id, start_now=bool(payload.start_now))

# Forums endpoints (runtime error fix)
class Forum(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=new_id)
    platform: str
    name: str
    url: str
    rule_profile: str
    topic_tags: List[str] = Field(default_factory=list)
    size_velocity: Optional[str] = None
    relevance_notes: Optional[str] = None
    last_seen_at: Optional[str] = None
    link_status: Optional[str] = None
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
    link_status: Optional[str] = None
    last_checked_at: Optional[str] = None

@api.get("/forums")
async def list_forums():
    docs = await COLL_FORUMS.find().sort("updated_at", -1).to_list(500)
    out = []
    for d in docs:
        d.pop("_id", None)
        d.setdefault("topic_tags", [])
        out.append(d)
    return out

@api.post("/forums")
async def create_forum(payload: ForumCreate):
    f = Forum(**payload.model_dump())
    doc = await insert_with_id(COLL_FORUMS, f.model_dump())
    return doc

@api.post("/forums/{forum_id}/check_link")
async def forum_check_link(forum_id: str):
    f = await get_by_id(COLL_FORUMS, forum_id)
    if not f:
        raise HTTPException(status_code=404, detail="Forum not found")
    status = "blocked"
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f.get("url"), timeout=8) as resp:
                if 200 <= resp.status < 400:
                    status = "ok"
                elif resp.status == 404:
                    status = "not_found"
                else:
                    status = "blocked"
    except Exception:
        status = "blocked"
    await update_by_id(COLL_FORUMS, forum_id, {"link_status": status, "last_checked_at": now_iso()})
    return await get_by_id(COLL_FORUMS, forum_id)

# Agents endpoints
class Agent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=new_id)
    agent_name: str
    status_light: str = "green"  # green, yellow, red
    error_state: Optional[str] = None
    next_retry_at: Optional[str] = None
    activity_stream: List[Dict[str, Any]] = Field(default_factory=list)
    last_activity: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

async def seed_agents():
    """Ensure the three core agents exist"""
    agent_names = ["Praefectus", "Explorator", "Legatus"]
    existing = await COLL_AGENTS.find({"agent_name": {"$in": agent_names}}).to_list(10)
    existing_names = {a["agent_name"] for a in existing}
    
    for name in agent_names:
        if name not in existing_names:
            agent = Agent(
                agent_name=name,
                status_light="yellow" if name == "Legatus" else "green",
                last_activity=now_iso()
            )
            await insert_with_id(COLL_AGENTS, agent.model_dump())
            await log_event("agent_seeded", "backend/agents", {"agent_name": name})

@api.get("/agents")
async def list_agents():
    # Ensure core agents exist
    await seed_agents()
    
    # Get agents with proper status logic
    docs = await COLL_AGENTS.find().to_list(100)
    agents = []
    
    for d in docs:
        d.pop("_id", None)
        
        # Apply status logic based on missions
        if d["agent_name"] == "Legatus":
            # Check if any research_only missions are active
            research_missions = await COLL_OPERATIONS.find({
                "posture": "research_only", 
                "state": {"$in": ["scanning", "engaging"]}
            }).to_list(1)
            if research_missions:
                d["status_light"] = "yellow"
            else:
                d["status_light"] = "green"
        
        # Handle auto-reset for Explorator
        if d["agent_name"] == "Explorator" and d.get("next_retry_at"):
            from datetime import datetime
            try:
                retry_time = datetime.fromisoformat(d["next_retry_at"].replace("Z", "+00:00"))
                now_time = datetime.now(retry_time.tzinfo)
                if now_time >= retry_time:
                    # Auto-reset: clear error state and set to green
                    d["status_light"] = "green"
                    d["error_state"] = None
                    d["next_retry_at"] = None
                    await update_by_id(COLL_AGENTS, d["id"], {
                        "status_light": "green",
                        "error_state": None,
                        "next_retry_at": None
                    })
                    await log_event("agent_error_cleared", "backend/agents", {"agent_name": "Explorator"})
            except:
                pass
        
        agents.append(d)
    
    return agents

# Scenario endpoints for testing
@api.post("/scenarios/agent_error_retry")
async def scenario_agent_error(payload: Dict[str, Any]):
    """Test scenario: trigger Explorator error with retry"""
    minutes = payload.get("minutes", 1)
    
    # Set Explorator to error state
    from datetime import datetime, timedelta
    retry_time = datetime.now(PHOENIX_TZ) + timedelta(minutes=minutes)
    
    # Find Explorator agent first
    existing = await COLL_AGENTS.find_one({"agent_name": "Explorator"})
    
    if existing:
        # Update existing agent
        await update_by_id(COLL_AGENTS, existing["_id"], {
            "status_light": "red",
            "error_state": "crawl_timeout", 
            "next_retry_at": retry_time.isoformat()
        })
        agent_data = await get_by_id(COLL_AGENTS, existing["_id"])
    else:
        # Create agent if it doesn't exist  
        agent = Agent(
            agent_name="Explorator",
            status_light="red",
            error_state="crawl_timeout",
            next_retry_at=retry_time.isoformat()
        )
        agent_doc = await insert_with_id(COLL_AGENTS, agent.model_dump())
        agent_data = agent_doc
    
    await log_event("agent_error_detected", "backend/scenarios", {"agent_name": "Explorator", "minutes": minutes})
    
    return {"agent": agent_data}

# Prospects (Rolodex) endpoints  
class Prospect(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=new_id)
    name_or_alias: str
    handles: Dict[str, str] = Field(default_factory=dict)
    priority_state: str = "cold"  # cold, warm, hot
    signals: List[Dict[str, Any]] = Field(default_factory=list)
    source_type: str = "manual"  # manual, seeded
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class ProspectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name_or_alias: str
    handles: Dict[str, str] = Field(default_factory=dict)
    priority_state: str = "cold"
    source_type: str = "manual"

@api.get("/prospects")
async def list_prospects():
    docs = await COLL_ROLODEX.find().sort("updated_at", -1).to_list(500)
    out = []
    for d in docs:
        d.pop("_id", None)
        d.setdefault("handles", {})
        d.setdefault("signals", [])
        d.setdefault("source_type", "manual")
        out.append(d)
    return out

@api.post("/prospects")
async def create_prospect(payload: ProspectCreate):
    prospect = Prospect(**payload.model_dump())
    doc = await insert_with_id(COLL_ROLODEX, prospect.model_dump())
    await log_event("prospect_created", "backend/prospects", {"prospect_id": doc["id"]})
    return doc

@api.get("/prospects/{prospect_id}")
async def get_prospect(prospect_id: str):
    d = await get_by_id(COLL_ROLODEX, prospect_id)
    if not d:
        raise HTTPException(status_code=404, detail="Prospect not found")
    d.setdefault("handles", {})
    d.setdefault("signals", [])
    d.setdefault("source_type", "manual")
    return d

# HotLeads endpoints
class HotLead(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=new_id)
    prospect_id: str
    status: str = "pending_approval"  # pending_approval, approved, deferred, removed
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    proposed_script: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class HotLeadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prospect_id: str
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    proposed_script: Optional[str] = None

class HotLeadStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str

class HotLeadScriptUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proposed_script: str

@api.get("/hotleads")
async def list_hotleads():
    docs = await COLL_HOT_LEADS.find().sort("updated_at", -1).to_list(200)
    out = []
    for d in docs:
        d.pop("_id", None)
        d.setdefault("evidence", [])
        out.append(d)
    return out

@api.post("/hotleads")
async def create_hotlead(payload: HotLeadCreate):
    hotlead = HotLead(**payload.model_dump())
    doc = await insert_with_id(COLL_HOT_LEADS, hotlead.model_dump())
    await log_event("hotlead_created", "backend/hotleads", {"hotlead_id": doc["id"], "prospect_id": doc["prospect_id"]})
    return doc

@api.get("/hotleads/{hotlead_id}")
async def get_hotlead(hotlead_id: str):
    d = await get_by_id(COLL_HOT_LEADS, hotlead_id)
    if not d:
        raise HTTPException(status_code=404, detail="HotLead not found")
    d.setdefault("evidence", [])
    return d

@api.post("/hotleads/{hotlead_id}/status")
async def update_hotlead_status(hotlead_id: str, payload: HotLeadStatusUpdate):
    count = await update_by_id(COLL_HOT_LEADS, hotlead_id, {"status": payload.status})
    if count == 0:
        raise HTTPException(status_code=404, detail="HotLead not found")
    await log_event("hotlead_status_updated", "backend/hotleads", {"hotlead_id": hotlead_id, "status": payload.status})
    return await get_by_id(COLL_HOT_LEADS, hotlead_id)

@api.patch("/hotleads/{hotlead_id}")
async def update_hotlead_script(hotlead_id: str, payload: HotLeadScriptUpdate):
    count = await update_by_id(COLL_HOT_LEADS, hotlead_id, {"proposed_script": payload.proposed_script})
    if count == 0:
        raise HTTPException(status_code=404, detail="HotLead not found")
    await log_event("hotlead_script_edited", "backend/hotleads", {"hotlead_id": hotlead_id})
    return await get_by_id(COLL_HOT_LEADS, hotlead_id)

# Guardrails endpoints
class Guardrail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=new_id)
    type: Optional[str] = None
    scope: str = "global"
    value: Optional[str] = None
    notes: Optional[str] = None
    # Legacy fields from original schema
    default_posture: Optional[str] = None
    frequency_caps: Optional[Dict[str, Any]] = None
    sensitive_topics: Optional[List[str]] = None
    standing_permissions: Optional[List[str]] = None
    dm_etiquette: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class GuardrailCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Optional[str] = None
    scope: str = "global"
    value: Optional[str] = None
    notes: Optional[str] = None
    # Legacy fields
    default_posture: Optional[str] = None
    frequency_caps: Optional[Dict[str, Any]] = None
    sensitive_topics: Optional[List[str]] = None
    standing_permissions: Optional[List[str]] = None
    dm_etiquette: Optional[str] = None

@api.get("/guardrails")
async def list_guardrails():
    docs = await COLL_GUARDRAILS.find().sort("updated_at", -1).to_list(200)
    out = []
    for d in docs:
        d.pop("_id", None)
        d.setdefault("scope", "global")
        d.setdefault("sensitive_topics", [])
        d.setdefault("standing_permissions", [])
        out.append(d)
    return out

@api.post("/guardrails")
async def create_guardrail(payload: GuardrailCreate):
    guardrail = Guardrail(**payload.model_dump())
    doc = await insert_with_id(COLL_GUARDRAILS, guardrail.model_dump())
    await log_event("guardrail_created", "backend/guardrails", {"guardrail_id": doc["id"], "type": doc.get("type")})
    return doc

@api.get("/guardrails/{guardrail_id}")
async def get_guardrail(guardrail_id: str):
    d = await get_by_id(COLL_GUARDRAILS, guardrail_id)
    if not d:
        raise HTTPException(status_code=404, detail="Guardrail not found")
    d.setdefault("scope", "global")
    d.setdefault("sensitive_topics", [])
    d.setdefault("standing_permissions", [])
    return d

# Exports endpoints
class Export(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=new_id)
    recipe_name: str
    filter_spec: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"  # pending, generating, complete
    file_url: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)

class ExportRecipeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipe_name: str
    filter_spec: Dict[str, Any] = Field(default_factory=dict)

class ExportGenerate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipe_name: str

@api.get("/exports")
async def list_exports():
    docs = await COLL_EXPORTS.find().sort("updated_at", -1).to_list(100)
    out = []
    for d in docs:
        d.pop("_id", None)
        d.setdefault("filter_spec", {})
        out.append(d)
    return out

@api.post("/exports/recipe")
async def create_export_recipe(payload: ExportRecipeCreate):
    export = Export(**payload.model_dump())
    doc = await insert_with_id(COLL_EXPORTS, export.model_dump())
    await log_event("export_recipe_created", "backend/exports", {"export_id": doc["id"], "recipe_name": doc["recipe_name"]})
    return doc

@api.post("/exports/generate")
async def generate_export(payload: ExportGenerate):
    # Find the recipe by name
    recipe = await COLL_EXPORTS.find_one({"recipe_name": payload.recipe_name})
    if not recipe:
        raise HTTPException(status_code=404, detail="Export recipe not found")
    
    # Update status to generating
    await update_by_id(COLL_EXPORTS, recipe["_id"], {"status": "generating"})
    
    # For now, just mark as complete with a mock file URL
    # In a real implementation, this would generate the actual export file
    file_url = f"/downloads/{recipe['_id']}.csv"
    await update_by_id(COLL_EXPORTS, recipe["_id"], {
        "status": "complete",
        "file_url": file_url
    })
    
    await log_event("export_generated", "backend/exports", {"export_id": recipe["_id"], "recipe_name": payload.recipe_name})
    return await get_by_id(COLL_EXPORTS, recipe["_id"])

# Praetoria Knowledge Base endpoint
@api.get("/knowledge/praetoria")
async def get_praetoria_knowledge():
    """Comprehensive knowledge base about Praetoria for Augustus agents"""
    return {
        "company": "Praetoria",
        "mission": "Visibility and control layer for the agent economy",
        "tagline": "Unified command center for monitoring, validating, and coordinating autonomous AI agents",
        
        "evolution_stages": {
            "stage_1": {
                "name": "Agent Observability",
                "status": "Live now",
                "description": "Mission Control for live agent fleets",
                "features": [
                    "Real-time agent monitoring and status tracking",
                    "Agent Trace Log & Replay for forensics-grade debugging", 
                    "Organization Views with KPIs and alerts",
                    "Error analysis with root-cause and fix suggestions",
                    "Global agent index with performance metrics"
                ]
            },
            "stage_2": {
                "name": "Platform & Registry", 
                "timeline": "2-4 months",
                "description": "Registry of registries with verified agent identity",
                "features": [
                    "Unified Agent Index across all registries",
                    "Praetoria Agent ID (PAID) canonical identity",
                    "Claim & Verification with ownership proofs",
                    "Reputation & History tracking",
                    "Legal/Audit logging for compliance"
                ]
            },
            "stage_3": {
                "name": "Control Infrastructure",
                "timeline": "6-12 months", 
                "description": "Internet-grade routing, payments, and security",
                "features": [
                    "Behavior-aware Routing (Praetoria Relay)",
                    "Agent-to-Agent Payments with escrow/metering",
                    "Security & Threat Intelligence",
                    "Agent firewalls and policy guards",
                    "Premium reputation & compliance APIs"
                ]
            }
        },
        
        "target_personas": [
            {
                "name": "Developers/Agent Teams",
                "pain_points": ["Lack of agent visibility", "Difficult debugging", "No trace replay"],
                "value_props": ["Real-time observability", "Fast debugging", "Reproducible traces", "Verified identity path"]
            },
            {
                "name": "Startups", 
                "pain_points": ["No post-launch monitoring", "Building custom dashboards", "Investor visibility"],
                "value_props": ["Ready-made monitoring", "Clear performance views", "Professional dashboards"]
            },
            {
                "name": "Enterprises",
                "pain_points": ["Multi-vendor agent chaos", "No governance", "Compliance gaps"],
                "value_props": ["Unified visibility", "Governance controls", "Audit logs", "Risk scores"]
            },
            {
                "name": "Security & Compliance",
                "pain_points": ["Unknown agent behavior", "No policy enforcement", "Audit difficulties"],
                "value_props": ["Anomaly detection", "Policy enforcement", "Provenance tracking", "Compliance logging"]
            },
            {
                "name": "Investors & Analysts",
                "pain_points": ["No agent economy visibility", "Market intelligence gaps"],
                "value_props": ["Real-time market view", "Performance analytics", "Ecosystem insights"]
            }
        ],
        
        "competitive_advantages": [
            "Built for agents, not generic apps or ML models",
            "Captures prompt/response traces and multi-step reasoning",
            "Framework-agnostic (LangChain, CrewAI, AutoGen, LangGraph, on-chain)",
            "Privacy-by-design with tiered visibility",
            "Evolution path: tool → platform → infrastructure",
            "Agent-native routing, payments, and security"
        ],
        
        "market_problems": [
            "Agent proliferation without control towers",
            "No shared identity or registry for agents", 
            "Hard to verify ownership, provenance, performance",
            "Need for agent-native routing, payments, security",
            "Lack of interoperability and trust mechanisms"
        ],
        
        "business_model": {
            "stage_1": "SaaS subscription by org/agent with usage tiers",
            "stage_2": "Registry fees, data intelligence APIs, compliance services", 
            "stage_3": "Routing fees, reputation APIs, threat-intel subscriptions, verification tolls"
        },
        
        "north_star": "As agents become first-class internet citizens, they need accountability, discovery, trust, and safe interoperation. Praetoria lays the rails for a resilient, thriving agent economy."
    }

# Basic health endpoints
@api.get("/health")
async def health():
    """Health check endpoint"""
    return {"ok": True, "timestamp": now_iso()}

@api.get("/")
async def root():
    """Root API endpoint"""
    return {"message": "API ready", "timestamp": now_iso()}

# Providers router
from providers.routes import router as provider_router
app.include_router(provider_router)
app.include_router(api)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()