import React, { useEffect, useState } from "react";
import { api, phoenixTime } from "../api";
import { useNavigate } from "react-router-dom";

export default function Rolodex() {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ name_or_alias: "", handles: {}, priority_state: "cold" });
  const [handleKey, setHandleKey] = useState("");
  const [handleVal, setHandleVal] = useState("");
  const nav = useNavigate();

  const fetchAll = async () => setItems((await api.get(`/prospects`)).data);
  useEffect(() => { fetchAll(); }, []);

  const addHandle = () => {
    if (!handleKey.trim() || !handleVal.trim()) return;
    setForm({ ...form, handles: { ...(form.handles || {}), [handleKey.trim()]: handleVal.trim() } });
    setHandleKey(""); setHandleVal("");
  };

  const create = async () => {
    await api.post(`/prospects`, form);
    setForm({ name_or_alias: "", handles: {}, priority_state: "cold" });
    await fetchAll();
  };

  return (
    <div>
      <h2 className="text-lg font-semibold mb-3">Rolodex</h2>
      <div className="bg-white rounded shadow p-3 mb-4 grid grid-cols-1 md:grid-cols-5 gap-2">
        <input className="border rounded px-2 py-1" placeholder="Name or alias" value={form.name_or_alias} onChange={(e) => setForm({ ...form, name_or_alias: e.target.value })} />
        <input className="border rounded px-2 py-1" placeholder="Handle key (e.g., linkedin)" value={handleKey} onChange={(e) => setHandleKey(e.target.value)} />
        <input className="border rounded px-2 py-1" placeholder="Handle value" value={handleVal} onChange={(e) => setHandleVal(e.target.value)} />
        <button onClick={addHandle} className="px-3 py-1 bg-neutral-800 text-white rounded">Add Handle</button>
        <select className="border rounded px-2 py-1" value={form.priority_state} onChange={(e) => setForm({ ...form, priority_state: e.target.value })}>
          <option value="cold">cold</option>
          <option value="warm">warm</option>
          <option value="hot">hot</option>
        </select>
        <div className="col-span-full text-xs text-neutral-600">Handles: {Object.entries(form.handles||{}).map(([k,v]) => `${k}:${v}`).join(", ")}</div>
        <div className="col-span-full"><button onClick={create} className="px-3 py-1 bg-neutral-800 text-white rounded">Create</button></div>
      </div>

      <div className="bg-white rounded shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-neutral-100 text-left">
              <th className="p-2">Name/Alias</th>
              <th className="p-2">Priority</th>
              <th className="p-2">Handles</th>
              <th className="p-2">Signals</th>
              <th className="p-2">Updated</th>
            </tr>
          </thead>
          <tbody>
            {items.map((p) => (
              <tr key={p.id} className="border-t hover:bg-neutral-50 cursor-pointer" onClick={() => nav(`/prospects/${p.id}`)}>
                <td className="p-2">{p.name_or_alias}</td>
                <td className="p-2">{p.priority_state}</td>
                <td className="p-2">{Object.entries(p.handles||{}).map(([k,v]) => `${k}:${v}`).join(", ")}</td>
                <td className="p-2">{(p.signals||[]).length}</td>
                <td className="p-2">{phoenixTime(p.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}