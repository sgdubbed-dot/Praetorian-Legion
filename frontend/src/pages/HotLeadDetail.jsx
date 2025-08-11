import React, { useEffect, useState } from "react";
import { api, phoenixTime } from "../api";
import { useParams, Link, useNavigate } from "react-router-dom";

export default function HotLeadDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [h, setH] = useState(null);
  const [prospect, setProspect] = useState(null);
  const [events, setEvents] = useState([]);
  const [editOpen, setEditOpen] = useState(false);
  const [scriptText, setScriptText] = useState("");
  const [myMessage, setMyMessage] = useState("");

  const refresh = async () => {
    const d = (await api.get(`/hotleads/${id}`)).data;
    setH(d);
    const p = (await api.get(`/prospects/${d.prospect_id}`)).data;
    setProspect(p);
    const ev = (await api.get(`/events`, { params: { hotlead_id: id, limit: 50 } })).data;
    setEvents(ev);
  };

  useEffect(() => { refresh(); }, [id]);

  const saveScript = async () => {
    await api.patch(`/hotleads/${id}`, { proposed_script: scriptText });
    setEditOpen(false);
    await refresh();
  };

  const proposeMyMessage = async () => {
    if (!myMessage.trim()) return;
    await api.patch(`/hotleads/${id}`, { proposed_script: myMessage.trim() });
    setMyMessage("");
    await refresh();
  };

  if (!h) return <div>Loading...</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <button onClick={() => navigate("/hotleads")} className="px-3 py-1 bg-neutral-200 rounded">Back to Hot Leads</button>
        {prospect && <div className="text-sm"><Link className="text-blue-600 underline" to={`/prospects/${prospect.id}`}>View Prospect</Link></div>}
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="text-xl font-semibold">Hot Lead {h.id.slice(0,8)}</div>
        <div className="text-sm">Status: {h.status}</div>
        <div className="text-sm">Prospect: {prospect?.name_or_alias || h.prospect_id}</div>
        <div className="text-sm">Created: {phoenixTime(h.created_at)} — Updated: {phoenixTime(h.updated_at)}</div>
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold mb-2">Evidence</div>
        <ul className="text-sm space-y-1">
          {(h.evidence||[]).map((e, i) => (
            <li key={i} className="border rounded p-2">
              <div className="text-xs text-neutral-500">{phoenixTime(e.timestamp)}</div>
              <div className="text-sm">
                {e.quote} {e.link ? (<a className="text-blue-600 underline" href={e.link} target="_blank" rel="noreferrer">link</a>) : <span className="text-neutral-500">Example only (no source)</span>}
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="flex items-center justify-between">
          <div className="font-semibold mb-2">Proposed Script</div>
          <div className="flex gap-2">
            <button onClick={() => setEditOpen(true)} className="px-2 py-1 text-xs bg-neutral-200 rounded">Edit Script</button>
            <button onClick={() => api.post(`/hotleads/${id}/status`, { status: "approved" }).then(refresh)} className="px-2 py-1 text-xs bg-green-600 text-white rounded">Approve</button>
            <button onClick={() => api.post(`/hotleads/${id}/status`, { status: "deferred" }).then(refresh)} className="px-2 py-1 text-xs bg-yellow-600 text-white rounded">Defer</button>
            <button onClick={() => api.post(`/hotleads/${id}/status`, { status: "removed" }).then(refresh)} className="px-2 py-1 text-xs bg-red-600 text-white rounded">Reject</button>
          </div>
        </div>
        <pre className="text-sm whitespace-pre-wrap">{h.proposed_script || '-'}</pre>
        <div className="mt-3">
          <div className="font-semibold mb-1">Propose My Message</div>
          <div className="flex gap-2">
            <textarea className="flex-1 border rounded px-2 py-1" rows={3} placeholder="Write your alternative script..." value={myMessage} onChange={(e) => setMyMessage(e.target.value)} />
            <button onClick={proposeMyMessage} className="px-3 py-1 bg-blue-600 text-white rounded">Save</button>
          </div>
        </div>
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold mb-2">Status History</div>
        <ul className="text-sm space-y-1">
          {events.filter(e => ["hotlead_approved","hotlead_deferred","hotlead_removed","hotlead_script_edited"].includes(e.event_name)).map((e) => (
            <li key={e.id} className="border rounded p-2">
              <div className="text-xs text-neutral-500">{phoenixTime(e.timestamp)} — {e.event_name}</div>
            </li>
          ))}
        </ul>
      </div>

      {editOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center">
          <div className="bg-white rounded shadow p-4 w-full max-w-xl">
            <div className="text-lg font-semibold mb-2">Edit Proposed Script</div>
            <textarea className="w-full border rounded px-2 py-1" rows={8} value={scriptText} onChange={(e) => setScriptText(e.target.value)} />
            <div className="mt-3 flex justify-end gap-2">
              <button onClick={() => setEditOpen(false)} className="px-3 py-1 bg-neutral-200 rounded">Cancel</button>
              <button onClick={saveScript} className="px-3 py-1 bg-blue-600 text-white rounded">Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}