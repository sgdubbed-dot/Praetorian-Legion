import React, { useEffect, useState } from "react";
import { api, phoenixTime } from "../api";

export default function Guardrails() {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ default_posture: "help_only", frequency_caps: { dm_per_week: 1 }, sensitive_topics: ["politics","religion"], standing_permissions: [], dm_etiquette: "" });

  const refresh = async () => setItems((await api.get(`/guardrails`)).data);
  useEffect(() => { refresh(); }, []);

  const create = async () => {
    await api.post(`/guardrails`, form);
    await refresh();
  };

  return (
    <div>
      <h2 className="text-lg font-semibold mb-3">Guardrails</h2>
      <div className="bg-white rounded shadow p-3 mb-4 grid grid-cols-1 md:grid-cols-3 gap-2">
        <select className="border rounded px-2 py-1" value={form.default_posture} onChange={(e) => setForm({ ...form, default_posture: e.target.value })}>
          <option value="help_only">help_only</option>
          <option value="help_plus_soft_marketing">help_plus_soft_marketing</option>
        </select>
        <input className="border rounded px-2 py-1" placeholder="DM etiquette" value={form.dm_etiquette} onChange={(e) => setForm({ ...form, dm_etiquette: e.target.value })} />
        <button onClick={create} className="px-3 py-1 bg-neutral-800 text-white rounded">Create</button>
      </div>

      <div className="bg-white rounded shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-neutral-100 text-left">
              <th className="p-2">Posture</th>
              <th className="p-2">Sensitive Topics</th>
              <th className="p-2">Updated</th>
            </tr>
          </thead>
          <tbody>
            {items.map((g) => (
              <tr key={g.id} className="border-t">
                <td className="p-2">{g.default_posture}</td>
                <td className="p-2">{(g.sensitive_topics||[]).join(", ")}</td>
                <td className="p-2">{phoenixTime(g.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}