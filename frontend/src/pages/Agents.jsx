import React, { useEffect, useState } from "react";
import { api, phoenixTime } from "../api";

const Dot = ({ color = "gray" }) => (
  <span className={`inline-block w-3 h-3 rounded-full`} style={{ backgroundColor: color }} />
);

export default function Agents() {
  const [agents, setAgents] = useState([]);
  const [selected, setSelected] = useState(null);

  const refresh = async () => {
    try {
      const res = await api.get("/agents");
      setAgents(res.data);
      if (selected) {
        const found = res.data.find((a) => a.id === selected.id);
        if (found) setSelected(found);
      }
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error("PAGE ERROR:", e?.name || e?.message || e);
    }
  };

  useEffect(() => { refresh(); const id = setInterval(refresh, 5000); return () => clearInterval(id); }, []);

  const colorFor = (s) => (s === "green" ? "green" : s === "yellow" ? "goldenrod" : s === "red" ? "crimson" : "gray");

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div className="md:col-span-1 bg-white rounded shadow">
        <div className="p-3 border-b flex items-center justify-between">
          <div className="font-semibold">Agents</div>
          <button onClick={refresh} className="text-sm px-2 py-1 bg-neutral-800 text-white rounded">Refresh</button>
        </div>
        <ul>
          {agents.map((a) => (
            <li key={a.id} className={`p-3 border-b hover:bg-neutral-50 cursor-pointer ${selected?.id === a.id ? "bg-neutral-50" : ""}`} onClick={() => setSelected(a)}>
              <div className="flex items-center gap-2">
                <Dot color={colorFor(a.status_light)} />
                <div className="font-medium">{a.agent_name}</div>
              </div>
              <div className="text-xs text-neutral-500">Updated: {phoenixTime(a.updated_at)}</div>
              {a.error_state && <div className="text-xs text-red-600">Error: {a.error_state}</div>}
            </li>
          ))}
        </ul>
      </div>
      <div className="md:col-span-2 bg-white rounded shadow p-3">
        {!selected && <div className="text-neutral-500">Select an agent to view activity.</div>}
        {selected && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="text-lg font-semibold">{selected.agent_name} — Activity</div>
            </div>
            <div className="h-[480px] overflow-y-auto border rounded p-3 bg-neutral-50 space-y-2">
              {(selected.activity_stream || []).length === 0 && <div className="text-sm text-neutral-500">No activity yet.</div>}
              {(selected.activity_stream || []).map((m, i) => (
                <div key={i} className="border bg-white rounded p-2">
                  <div className="text-xs text-neutral-500">{phoenixTime(m.timestamp)} {m.channel ? `• ${m.channel}` : ""}</div>
                  <div className="text-sm whitespace-pre-wrap">{m.content || JSON.stringify(m)}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}