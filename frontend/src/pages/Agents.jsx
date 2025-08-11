import React, { useEffect, useState } from "react";
import { api, phoenixTime } from "../api";

function Dot({ color = "gray" }) {
  return <span style={{ background: color }} className="inline-block w-3 h-3 rounded-full border" />;
}

export default function Agents() {
  const [agents, setAgents] = useState([]);
  const [selected, setSelected] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [toast, setToast] = useState("");

  const ensureTriad = (list) => {
    const names = ["Praefectus", "Explorator", "Legatus"];
    const index = Object.fromEntries(list.map((a) => [a.agent_name, a]));
    const filled = names.map((n) => index[n] || { id: n, agent_name: n, status_light: n === "Legatus" ? "yellow" : "green", updated_at: new Date().toISOString(), activity_stream: [] });
    return filled;
  };

  const refresh = async () => {
    try {
      const res = await api.get("/agents");
      const triad = ensureTriad(res.data);
      setAgents(triad);
      if (selected) {
        const found = triad.find((a) => a.agent_name === selected.agent_name);
        if (found) setSelected(found);
      }
    } catch (e) {
      console.error("PAGE ERROR:", e?.name || e?.message || e);
    }
  };

  const onSyncNow = async () => {
    setSyncing(true);
    try {
      await refresh();
      const t = phoenixTime(new Date().toISOString());
      setToast(`Synced at ${t}`);
      setTimeout(() => setToast(""), 2000);
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => { refresh(); const id = setInterval(refresh, 5000); return () => clearInterval(id); }, []);

  const colorFor = (s) => (s === "green" ? "green" : s === "yellow" ? "goldenrod" : s === "red" ? "crimson" : "gray");

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div className="md:col-span-1 bg-white rounded shadow">
        <div className="p-3 border-b flex items-center justify-between">
          <div className="font-semibold">Agents</div>
          <button aria-label="Sync Now" onClick={onSyncNow} className="text-sm px-2 py-1 bg-neutral-800 text-white rounded focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-neutral-500">{syncing ? "Syncing..." : "Sync Now"}</button>
        </div>
        {toast && <div className="px-2 py-1 text-sm bg-green-100 text-green-800">{toast}</div>}
        <ul>
          {agents.map((a) => {
            const tooltip = a?.error_state
              ? (a?.next_retry_at ? `retry scheduled ${phoenixTime(a.next_retry_at)}` : `error: ${a.error_state}`)
              : `last activity ${phoenixTime(a.updated_at)}`;
            return (
              <li
                key={a.id || a.agent_name}
                title={tooltip}
                className={`p-3 border-b hover:bg-neutral-50 cursor-pointer ${selected?.agent_name === a.agent_name ? "bg-neutral-50" : ""}`}
                onClick={() => setSelected(a)}
              >
                <div className="flex items-center gap-2">
                  <Dot color={colorFor(a.status_light)} />
                  <div className="font-medium">{a.agent_name}</div>
                </div>
                <div className="mt-1 text-[11px] inline-flex items-center gap-1 px-2 py-[2px] rounded-full bg-neutral-100 text-neutral-700 border">
                  {a.error_state ? (
                    a.next_retry_at ? (
                      <span>retry scheduled · {phoenixTime(a.next_retry_at)}</span>
                    ) : (
                      <span>error: {a.error_state}</span>
                    )
                  ) : (
                    <span>error cleared · {phoenixTime(a.updated_at)}</span>
                  )}
                </div>
                <div className="text-xs text-neutral-500 mt-1">Updated: {phoenixTime(a.updated_at)}</div>
                {a.error_state && <div className="text-xs text-red-600">Error: {a.error_state}</div>}
                {a.next_retry_at && <div className="text-[10px] text-neutral-500">Retry at: {phoenixTime(a.next_retry_at)}</div>}
              </li>
            );
          })}
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
              {(selected.activity_stream || []).length === 0 and <div className="text-sm text-neutral-500">No activity yet.</div>}
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