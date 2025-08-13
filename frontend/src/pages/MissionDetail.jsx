import React, { useEffect, useMemo, useState } from "react";
import { api, phoenixTime } from "../api";
import { useParams, useNavigate } from "react-router-dom";

export default function MissionDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [m, setM] = useState(null);
  const [events, setEvents] = useState([]);
  const [showRaw, setShowRaw] = useState(false);
  const [newInsight, setNewInsight] = useState("");
  const [editingIndex, setEditingIndex] = useState(null);
  const [editingText, setEditingText] = useState("");

  const refresh = async () => {
    const d = (await api.get(`/operations/${id}`)).data;
    setM(d);
    const ev = (await api.get(`/events`, { params: { mission_id: id, limit: 50 } })).data;
    setEvents(ev);
  };

  useEffect(() => { refresh(); }, [id]);

  const stateChipColor = (s) => ({
    draft: "bg-neutral-200 text-neutral-800",
    scanning: "bg-blue-100 text-blue-800",
    engaging: "bg-green-100 text-green-800",
    escalating: "bg-purple-100 text-purple-800",
    paused: "bg-yellow-100 text-yellow-800",
    complete: "bg-neutral-300 text-neutral-700",
    aborted: "bg-red-100 text-red-800",
  }[s] || "bg-neutral-200 text-neutral-800");

  const override = async (action) => {
    if (!m) return;
    if (action === "resume") {
      await api.post(`/operations/${id}/state`, { state: "resume" });
    } else if (action === "pause") {
      await api.post(`/operations/${id}/state`, { state: "paused" });
    } else if (action === "abort") {
      await api.post(`/operations/${id}/state`, { state: "abort" });
    }
    await refresh();
  };

  const duplicateMission = async () => {
    if (!m) return;
    const payload = {
      title: `${m.title} (copy)`,
      objective: m.objective,
      posture: m.posture,
      state: "draft",
      agents_assigned: m.agents_assigned || [],
      insights: (m.insights || []),
    };
    await api.post("/operations", payload);
    navigate("/operations");
  };

  const plainSentence = (e) => {
    const t = phoenixTime(e.timestamp);
    switch (e.event_name) {
      case "mission_created": return `Mission created · ${t}`;
      case "mission_updated_state": return `Mission updated · ${t}`;
      case "mission_paused": return `Mission paused · ${t}`;
      case "mission_resumed": return `Mission resumed · ${t}`;
      case "mission_completed": return `Mission completed · ${t}`;
      case "mission_aborted": return `Mission aborted · ${t}`;
      default: return `${e.event_name} · ${t}`;
    }
  };

  const insightsRich = useMemo(() => m?.insights_rich || [], [m]);
  const addInsight = async () => {
    if (!newInsight.trim()) return;
    const next = [...insightsRich, { text: newInsight.trim(), timestamp: new Date().toISOString() }];
    await api.patch(`/operations/${id}`, { insights_rich: next });
    setNewInsight("");
    await refresh();
  };
  const startEdit = (idx) => { setEditingIndex(idx); setEditingText(insightsRich[idx].text); };
  const saveEdit = async () => {
    const next = insightsRich.map((it, i) => i === editingIndex ? { ...it, text: editingText } : it);
    await api.patch(`/operations/${id}`, { insights_rich: next });
    setEditingIndex(null); setEditingText("");
    await refresh();
  };

  if (!m) return <div>Loading...</div>;
  const isAborted = m.state === "aborted";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <button onClick={() => navigate("/operations")} className="px-3 py-1 bg-neutral-200 rounded focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-neutral-500">Back to Missions</button>
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xl font-semibold">{m.title}</div>
            <div className="text-sm text-neutral-600">Objective: {m.objective}</div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-xs px-2 py-1 rounded-full ${stateChipColor(m.state)}`}>{m.state}</span>
            {!isAborted ? (
              <div className="relative inline-block text-left">
                <details>
                  <summary className="cursor-pointer text-sm px-2 py-1 border rounded">Override</summary>
                  <div className="absolute right-0 mt-2 w-40 bg-white border rounded shadow z-10">
                    <button onClick={() => override("pause")} className="w-full text-left px-3 py-2 hover:bg-neutral-50">Pause</button>
                    <button onClick={() => override("resume")} className="w-full text-left px-3 py-2 hover:bg-neutral-50">Resume</button>
                    <button onClick={() => override("abort")} className="w-full text-left px-3 py-2 text-red-700 hover:bg-neutral-50">Abort</button>
                  </div>
                </details>
              </div>
            ) : (
              <button onClick={duplicateMission} className="text-sm px-2 py-1 bg-blue-600 text-white rounded">Duplicate</button>
            )}
          </div>
        </div>
        <div className="text-xs text-neutral-500 mt-1">Created: {phoenixTime(m.created_at)} · Updated: {phoenixTime(m.updated_at)}</div>
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold mb-1">Insights</div>
        <div className="text-xs text-neutral-600 mb-2">Insights help summarize patterns and opportunities — for example, but not limited to: repeating pain points, outperforming platforms, opportunities/risks.</div>
        <ul className="text-sm space-y-1">
          {insightsRich.map((it, i) => (
            <li key={i} className="border rounded p-2 flex justify-between items-start">
              <div>
                <div className="text-xs text-neutral-500">{phoenixTime(it.timestamp)}</div>
                {editingIndex === i ? (
                  <textarea value={editingText} onChange={(e) => setEditingText(e.target.value)} className="border rounded px-2 py-1 w-full mt-1" />
                ) : (
                  <div className="whitespace-pre-wrap">{it.text}</div>
                )}
              </div>
              <div className="ml-2">
                {editingIndex === i ? (
                  <button onClick={saveEdit} className="text-xs px-2 py-1 bg-green-600 text-white rounded">Save</button>
                ) : (
                  <button onClick={() => startEdit(i)} className="text-xs px-2 py-1 bg-neutral-200 rounded">Edit</button>
                )}
              </div>
            </li>
          ))}
        </ul>
        <div className="mt-3 flex gap-2">
          <input className="flex-1 border rounded px-2 py-1" placeholder="Add an insight..." value={newInsight} onChange={(e) => setNewInsight(e.target.value)} />
          <button onClick={addInsight} className="px-3 py-1 bg-neutral-800 text-white rounded">Add</button>
        </div>
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="flex items-center justify-between">
          <div className="font-semibold">Recent Events</div>
          <label className="text-sm flex items-center gap-1"><input type="checkbox" checked={showRaw} onChange={(e) => setShowRaw(e.target.checked)} /> Show raw JSON</label>
        </div>
        {!showRaw ? (
          <ul className="text-sm mt-2 space-y-1">
            {events.map((e) => (
              <li key={e.id} className="border rounded p-2">{plainSentence(e)}</li>
            ))}
          </ul>
        ) : (
          <div className="mt-2 text-xs whitespace-pre-wrap bg-neutral-50 border rounded p-2">{JSON.stringify(events, null, 2)}</div>
        )}
      </div>
    </div>
  );
}