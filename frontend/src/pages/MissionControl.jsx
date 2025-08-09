import React, { useEffect, useMemo, useState } from "react";
import { api, phoenixTime } from "../api";

const postureLabel = (p) => (p === "research_only" ? "Research Mode" : p);

export default function MissionControl() {
  const [praefectus, setPraefectus] = useState(null);
  const [chatInput, setChatInput] = useState("");
  const [hotLeads, setHotLeads] = useState([]);
  const [creating, setCreating] = useState(false);
  const [missionForm, setMissionForm] = useState({ title: "", objective: "", posture: "help_only" });
  const [mcReply, setMcReply] = useState(null);
  const [guardrails, setGuardrails] = useState([]);

  const refresh = async () => {
    try {
      const agents = (await api.get("/agents")).data;
      const pf = agents.find((a) => a.agent_name === "Praefectus") || null;
      setPraefectus(pf);
      const hls = (await api.get("/hotleads")).data.filter((h) => h.status === "pending_approval");
      setHotLeads(hls);
      const gs = (await api.get("/guardrails")).data;
      setGuardrails(gs);
    } catch (e) {
      console.error("PAGE ERROR:", e?.name || e?.message || e);
    }
  };

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, []);

  const postureConflict = useMemo(() => {
    // Warn if missionForm.posture conflicts with any posture guardrail (e.g., research_only rules exist but posture is marketing)
    const hasResearchOnly = guardrails.some((g) => g.default_posture === "research_only" || (g.type === "posture" && g.value === "research_only"));
    if (hasResearchOnly && missionForm.posture === "help_plus_soft_marketing") return "Guardrail conflict: Research-only in effect. No public engagement allowed.";
    return null;
  }, [guardrails, missionForm.posture]);

  const messages = useMemo(() => praefectus?.activity_stream ?? [], [praefectus]);

  const appendPraefectusActivity = async (entry) => {
    try {
      const existing = praefectus || { agent_name: "Praefectus", status_light: "green", activity_stream: [] };
      const updated = {
        ...existing,
        last_activity: new Date().toISOString(),
        activity_stream: [...(existing.activity_stream || []), entry],
      };
      await api.post("/agents/status", updated);
      await refresh();
    } catch (e) {
      console.error("PAGE ERROR:", e?.name || e?.message || e);
    }
  };

  const sendMessage = async () => {
    if (!chatInput.trim()) return;
    const human = { who: "human", content: chatInput.trim(), timestamp: new Date().toISOString() };
    setChatInput("");
    await appendPraefectusActivity(human);
    try {
      const res = await api.post("/mission_control/message", { text: human.content });
      setMcReply(res.data);
      await appendPraefectusActivity({ who: "Praefectus", content: `Understanding: ${res.data.understanding}` , timestamp: new Date().toISOString() });
      await appendPraefectusActivity({ who: "Praefectus", content: `Recommended Draft: ${res.data.recommended_mission_draft?.title}` , timestamp: new Date().toISOString() });
    } catch (e) {
      console.error("PAGE ERROR:", e?.name || e?.message || e);
    }
  };

  const approveDraft = async () => {
    if (!mcReply) return;
    try {
      await api.post("/mission_control/message", { text: "approve", approve: true, draft: mcReply.recommended_mission_draft });
      await refresh();
    } catch (e) {
      console.error("PAGE ERROR:", e?.name || e?.message || e);
    }
  };

  const createMission = async () => {
    setCreating(true);
    try {
      const res = await api.post("/missions", missionForm);
      await appendPraefectusActivity({ who: "Praefectus", content: `Mission created: ${res.data.title}`, timestamp: new Date().toISOString() });
      setMissionForm({ title: "", objective: "", posture: "help_only" });
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="lg:col-span-2 bg-white rounded shadow p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">Mission Control — Praefectus</h2>
          <button onClick={refresh} className="text-sm px-2 py-1 bg-neutral-800 text-white rounded">Refresh</button>
        </div>
        <div className="h-[420px] overflow-y-auto space-y-2 border rounded p-3 bg-neutral-50">
          {messages.length === 0 && (
            <div className="text-sm text-neutral-500">No activity yet. Say hello to Praefectus.</div>
          )}
          {messages.map((m, idx) => (
            <div key={idx} className={`flex ${m.who === "human" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] p-2 rounded ${m.who === "human" ? "bg-blue-600 text-white" : "bg-white border"}`}>
                <div className="text-xs text-neutral-400">{phoenixTime(m.timestamp)} — {m.who}</div>
                <div className="whitespace-pre-wrap text-sm">{m.content}</div>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-3 flex gap-2">
          <input className="flex-1 border rounded px-3 py-2" placeholder="Type a message to Praefectus..." value={chatInput} onChange={(e) => setChatInput(e.target.value)} />
          <button onClick={sendMessage} className="px-4 py-2 bg-blue-600 text-white rounded">Send</button>
        </div>

        {mcReply && (
          <div className="mt-4 border rounded p-3 bg-white">
            <div className="font-semibold mb-2">Praefectus Reply</div>
            <div className="text-sm mb-1"><span className="font-medium">Understanding:</span> {mcReply.understanding}</div>
            <div className="text-sm mb-1"><span className="font-medium">Critique & Options:</span>
              <ul className="list-disc pl-5">
                {mcReply.critique_options.map((c, i) => <li key={i}>{c}</li>)}
              </ul>
            </div>
            <div className="text-sm mb-1"><span className="font-medium">Recommended Draft:</span> <code>{mcReply.recommended_mission_draft?.title}</code> — posture {postureLabel(mcReply.recommended_mission_draft?.posture)}</div>
            <div className="text-sm mb-3"><span className="font-medium">Open Questions:</span>
              <ul className="list-disc pl-5">
                {mcReply.open_questions.map((q, i) => <li key={i}>{q}</li>)}
              </ul>
            </div>
            <div className="flex gap-2">
              <button onClick={approveDraft} className="px-3 py-1 bg-green-600 text-white rounded text-sm">Approve Draft</button>
            </div>
          </div>
        )}
      </div>

      <div className="bg-white rounded shadow p-4 space-y-4">
        <h3 className="font-semibold">Approvals</h3>
        <div className="space-y-3">
          {hotLeads.length === 0 && <div className="text-sm text-neutral-500">No Hot Leads awaiting approval.</div>}
          {hotLeads.map((hl) => (
            <div key={hl.id} className="border rounded p-2">
              <div className="text-sm font-medium">Hot Lead {hl.id.slice(0, 8)}</div>
              <div className="text-xs text-neutral-500">Prospect: {hl.prospect_id.slice(0, 8)}</div>
              <div className="text-xs">Evidence: {hl.evidence?.[0]?.quote || "-"}</div>
              <div className="mt-2 flex gap-2">
                <button onClick={() => api.post(`/hotleads/${hl.id}/status`, { status: "approved" }).then(refresh)} className="px-2 py-1 bg-green-600 text-white text-xs rounded">Approve</button>
                <button onClick={() => api.post(`/hotleads/${hl.id}/status`, { status: "deferred" }).then(refresh)} className="px-2 py-1 bg-yellow-600 text-white text-xs rounded">Defer</button>
                <button onClick={() => api.post(`/hotleads/${hl.id}/status`, { status: "removed" }).then(refresh)} className="px-2 py-1 bg-red-600 text-white text-xs rounded">Reject</button>
              </div>
            </div>
          ))}
        </div>

        <div>
          <h3 className="font-semibold mb-2">Draft Mission</h3>
          {postureConflict && (<div className="mb-2 p-2 bg-yellow-100 text-yellow-800 rounded text-sm">{postureConflict}</div>)}
          <div className="space-y-2">
            <input className="w-full border rounded px-2 py-1" placeholder="Title" value={missionForm.title} onChange={(e) => setMissionForm({ ...missionForm, title: e.target.value })} />
            <textarea className="w-full border rounded px-2 py-1" placeholder="Objective" value={missionForm.objective} onChange={(e) => setMissionForm({ ...missionForm, objective: e.target.value })} />
            <select className="w-full border rounded px-2 py-1" value={missionForm.posture} onChange={(e) => setMissionForm({ ...missionForm, posture: e.target.value })}>
              <option value="help_only">help_only</option>
              <option value="help_plus_soft_marketing">help_plus_soft_marketing</option>
              <option value="research_only">research_only</option>
            </select>
            <div className="text-xs text-neutral-600">Selected: {postureLabel(missionForm.posture)}</div>
            <button disabled={creating} onClick={createMission} className="px-3 py-1 bg-neutral-800 text-white rounded text-sm">{creating ? "Creating..." : "Create Mission"}</button>
          </div>
        </div>
      </div>
    </div>
  );
}