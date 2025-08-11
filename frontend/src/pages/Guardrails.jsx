import React, { useEffect, useState } from "react";
import { api, phoenixTime } from "../api";

export default function Guardrails() {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ default_posture: "help_only", frequency_caps: { dm_per_week: 1 }, sensitive_topics: ["politics","religion"], standing_permissions: [], dm_etiquette: "" });
  const [modalOpen, setModalOpen] = useState(false);
  const [rule, setRule] = useState({ type: "", scope: "global", value: "", notes: "" });
  const insertTemplate = (tpl) => setRule({ ...rule, ...tpl });
  const [warn, setWarn] = useState(null);

  const refresh = async () => setItems((await api.get(`/guardrails`)).data);
  useEffect(() => { refresh(); }, []);

  const create = async () => {
    await api.post(`/guardrails`, form);
    await refresh();
  };

  const addRule = async () => {
    const payload = { ...rule };
    await api.post(`/guardrails`, payload);
    setModalOpen(false);
    setRule({ type: "", scope: "global", value: "", notes: "" });
    await refresh();
  };

  useEffect(() => {
    // simple warning: if any guardrail explicitly restricts marketing and mission form selects help_plus_soft_marketing
    const hasResearchOnly = items.some((g) => (g.type === "posture" && (g.value === "research_only")));
    if (hasResearchOnly) setWarn("Warning: Research-only guardrail present. Ensure no public engagement.");
    else setWarn(null);
  }, [items]);

  return (
    <div>
      <h2 className="text-lg font-semibold mb-3">Guardrails</h2>
      <div className="bg-white rounded shadow p-3 mb-4 grid grid-cols-1 md:grid-cols-3 gap-2">
        <select className="border rounded px-2 py-1" value={form.default_posture} onChange={(e) => setForm({ ...form, default_posture: e.target.value })}>
          <option value="help_only">help_only</option>
          <option value="help_plus_soft_marketing">help_plus_soft_marketing</option>
          <option value="research_only">research_only</option>
        </select>
        <div>
          <input className="border rounded px-2 py-1 w-full" placeholder="DM etiquette" value={form.dm_etiquette} onChange={(e) => setForm({ ...form, dm_etiquette: e.target.value })} />
          <div className="text-[11px] text-neutral-600 mt-1">No cold DMs; DM only after public opt-in; disclose affiliation; one nudge per 7 days; escalate sensitive topics for human approval.</div>
        </div>
        <div className="flex gap-2">
          <button onClick={create} className="px-3 py-1 bg-neutral-800 text-white rounded">Create</button>
          <button onClick={() => setModalOpen(true)} className="px-3 py-1 bg-blue-600 text-white rounded">Add Rule</button>
        </div>
      </div>

      {warn && <div className="mb-3 p-2 bg-yellow-100 text-yellow-800 rounded text-sm">{warn}</div>}

      <div className="bg-white rounded shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-neutral-100 text-left">
              <th className="p-2">Type</th>
              <th className="p-2">Scope</th>
              <th className="p-2">Value</th>
              <th className="p-2">Notes</th>
              <th className="p-2">Updated</th>
            </tr>
          </thead>
          <tbody>
            {items.map((g) => (
              <tr key={g.id} className="border-t">
                <td className="p-2">{g.type || g.default_posture ? 'posture' : '-'}</td>
                <td className="p-2">{g.scope || 'global'}</td>
                <td className="p-2">{g.value || g.default_posture || '-'}</td>
                <td className="p-2">{g.notes || '-'}</td>
                <td className="p-2">{phoenixTime(g.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {modalOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center">
          <div className="bg-white rounded shadow p-4 w-full max-w-md">
            <div className="text-lg font-semibold mb-2">Add Rule</div>
            <div className="space-y-2">
              <input className="w-full border rounded px-2 py-1" placeholder="Type (e.g., posture, frequency_caps, dm_etiquette, sensitive_topics)" value={rule.type} onChange={(e) => setRule({ ...rule, type: e.target.value })} />
              <input className="w-full border rounded px-2 py-1" placeholder="Scope (global or forum URL/name)" value={rule.scope} onChange={(e) => setRule({ ...rule, scope: e.target.value })} />
              <input className="w-full border rounded px-2 py-1" placeholder="Value" value={rule.value} onChange={(e) => setRule({ ...rule, value: e.target.value })} />
              <textarea className="w-full border rounded px-2 py-1" placeholder="Notes" value={rule.notes} onChange={(e) => setRule({ ...rule, notes: e.target.value })} />
            </div>
            <div className="mt-3 flex gap-2 justify-end">
              <button onClick={() => setModalOpen(false)} className="px-3 py-1 bg-neutral-200 rounded">Cancel</button>
              <button onClick={addRule} className="px-3 py-1 bg-blue-600 text-white rounded">Save Rule</button>
            </div>
      <div className="mt-4 bg-white rounded shadow p-3">
        <div className="font-semibold mb-2">Quick Templates</div>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => insertTemplate({ type: "frequency_cap", value: "1 reply / 24h / user" })} className="px-2 py-1 text-xs bg-neutral-200 rounded">Frequency cap</button>
          <button onClick={() => insertTemplate({ type: "posture", value: "help_only" })} className="px-2 py-1 text-xs bg-neutral-200 rounded">Posture: help_only</button>
          <button onClick={() => insertTemplate({ type: "scope_block", value: "no posting in r/<subreddit>" })} className="px-2 py-1 text-xs bg-neutral-200 rounded">Scope block</button>
        </div>
        <div className="text-xs text-neutral-600 mt-1">Templates prefill the rule form; you can edit values before saving.</div>
      </div>

          </div>
        </div>
      )}
    </div>
  );
}