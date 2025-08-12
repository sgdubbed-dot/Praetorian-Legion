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
COLL_MISSIONS = db["Missions"]
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
    if source:
        q["source"] = source
    if mission_id:
        q["payload.mission_id"] = mission_id
    if thread_id:
        q["payload.thread_id"] = thread_id
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
    doc = await insert_with_id(COLL_MISSIONS, mission.model_dump())
    await log_event("mission_created", "backend/api", {"mission_id": doc["id"]})
    return doc

@api.get("/missions")
async def list_missions():
    docs = await COLL_MISSIONS.find().sort("updated_at", -1).to_list(1000)
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
    d = await get_by_id(COLL_MISSIONS, mission_id)
    if not d:
        raise HTTPException(status_code=404, detail="Mission not found")
    # migrate-on-read
    changed = False
    if "counters" not in d: d["counters"] = {"forums_found":0, "prospects_added":0, "hot_leads":0}; changed = True
    if "insights" not in d: d["insights"] = []; changed = True
    if "insights_rich" not in d: d["insights_rich"] = []; changed = True
    if "previous_active_state" not in d: d["previous_active_state"] = None; changed = True
    if changed:
        await update_by_id(COLL_MISSIONS, mission_id, {k: d[k] for k in ["counters","insights","insights_rich","previous_active_state"]})
    return d

@api.post("/missions/{mission_id}/state")
async def change_mission_state(mission_id: str, payload: Dict[str, Any]):
    doc = await get_by_id(COLL_MISSIONS, mission_id)
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
    await update_by_id(COLL_MISSIONS, mission_id, {"state": state})
    return await get_by_id(COLL_MISSIONS, mission_id)

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

# Snapshot Findings (used elsewhere)
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

# Include provider routes
from providers.routes import router as provider_router
app.include_router(provider_router)
app.include_router(api)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()