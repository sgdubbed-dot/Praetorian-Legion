import React, { useEffect, useState } from "react";
import { api, phoenixTime } from "../api";
import { useParams, useNavigate } from "react-router-dom";

export default function GuardrailDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [g, setG] = useState(null);
  const [events, setEvents] = useState([]);

  const refresh = async () => {
    const d = (await api.get(`/guardrails/${id}`)).data;
    setG(d);
    const ev = (await api.get(`/events`, { params: { source: "guardrails", limit: 50 } })).data;
    setEvents(ev);
  };
  useEffect(() => { refresh(); }, [id]);

  const save = async () => {
    const payload = { ...g };
    delete payload.id; // not needed for update
    await api.put(`/guardrails/${id}`, payload);
    await refresh();
  };

  if (!g) return <div>Loading...</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <button onClick={() => navigate("/guardrails")} className="px-3 py-1 bg-neutral-200 rounded">Back</button>
        <div className="text-sm text-neutral-600">Updated: {phoenixTime(g.updated_at)}</div>
      </div>

      <div className="bg-white rounded shadow p-4 space-y-2">
        <div className="text-lg font-semibold">Guardrail</div>
        <input className="w-full border rounded px-2 py-1" placeholder="Type" value={g.type || ""} onChange={(e) => setG({ ...g, type: e.target.value })} />
        <input className="w-full border rounded px-2 py-1" placeholder="Scope" value={g.scope || "global"} onChange={(e) => setG({ ...g, scope: e.target.value })} />
        <input className="w-full border rounded px-2 py-1" placeholder="Value" value={g.value || g.default_posture || ""} onChange={(e) => setG({ ...g, value: e.target.value })} />
        <textarea className="w-full border rounded px-2 py-1" placeholder="Notes" value={g.notes || ""} onChange={(e) => setG({ ...g, notes: e.target.value })} />
        <button onClick={save} className="px-3 py-1 bg-blue-600 text-white rounded">Save</button>
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold">History</div>
        <ul className="text-sm mt-2 space-y-1">
          {events.map((e) => (
            <li key={e.id} className="border rounded p-2">
              <div className="text-xs text-neutral-500">{phoenixTime(e.timestamp)} — {e.event_name}</div>
              <div className="text-xs text-neutral-600">{JSON.stringify(e.payload)}</div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
