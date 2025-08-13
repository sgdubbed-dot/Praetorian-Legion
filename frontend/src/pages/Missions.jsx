import React, { useEffect, useState } from "react";
import { api, phoenixTime } from "../api";
import { useNavigate } from "react-router-dom";

const postureLabel = (p) => (p === "research_only" ? "Research Mode" : p);

export default function Missions() {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ title: "", objective: "", posture: "help_only" });
  const nav = useNavigate();

  const fetchAll = async () => {
    try {
      setItems((await api.get("/campaigns")).data);
    } catch (e) {
      console.error("PAGE ERROR:", e?.name || e?.message || e);
    }
  };
  useEffect(() => { fetchAll(); }, []);

  const create = async () => {
    try {
      await api.post("/campaigns", form);
      setForm({ title: "", objective: "", posture: "help_only" });
      await fetchAll();
    } catch (e) {
      console.error("PAGE ERROR:", e?.name || e?.message || e);
    }
  };

  const changeState = async (id, state) => {
    try {
      await api.post(`/campaigns/${id}/state`, { state });
      await fetchAll();
    } catch (e) {
      console.error("PAGE ERROR:", e?.name || e?.message || e);
    }
  };

  return (
    <div>
      <h2 className="text-lg font-semibold mb-3">Campaigns</h2>
      <div className="bg-white rounded shadow p-3 mb-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <input className="border rounded px-2 py-1" placeholder="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <input className="border rounded px-2 py-1" placeholder="Objective" value={form.objective} onChange={(e) => setForm({ ...form, objective: e.target.value })} />
          <select className="border rounded px-2 py-1" value={form.posture} onChange={(e) => setForm({ ...form, posture: e.target.value })}>
            <option value="help_only">help_only</option>
            <option value="help_plus_soft_marketing">help_plus_soft_marketing</option>
            <option value="research_only">research_only</option>
          </select>
          <button onClick={create} className="px-3 py-1 bg-neutral-800 text-white rounded">Create</button>
        </div>
      </div>

      <div className="bg-white rounded shadow">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-neutral-100 text-left">
              <th className="p-2">Title</th>
              <th className="p-2">State</th>
              <th className="p-2">Posture</th>
              <th className="p-2">Counters</th>
              <th className="p-2">Updated</th>
              <th className="p-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((m) => (
              <tr key={m.id} className="border-t hover:bg-neutral-50 cursor-pointer" onClick={() => nav(`/campaigns/${m.id}`)}>
                <td className="p-2">{m.title}</td>
                <td className="p-2">{m.state}</td>
                <td className="p-2">{postureLabel(m.posture)}</td>
                <td className="p-2">F:{m.counters?.forums_found||0} P:{m.counters?.prospects_added||0} H:{m.counters?.hot_leads||0}</td>
                <td className="p-2">{phoenixTime(m.updated_at)}</td>
                <td className="p-2">
                  <select value={m.state} onClick={(e) => e.stopPropagation()} onChange={(e) => changeState(m.id, e.target.value)} className="border rounded px-2 py-1">
                    {["draft","scanning","engaging","escalating","paused","complete"].map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}