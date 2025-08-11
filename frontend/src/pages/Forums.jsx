import React, { useEffect, useState } from "react";
import { api, phoenixTime } from "../api";

export default function Forums() {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ platform: "", name: "", url: "", rule_profile: "strict_help_only", topic_tags: [] });
  const [tagInput, setTagInput] = useState("");

  const fetchAll = async () => setItems((await api.get("/forums")).data);
  useEffect(() => { fetchAll(); }, []);

  const create = async () => {
    const payload = { ...form, topic_tags: form.topic_tags.filter(Boolean) };
    await api.post(`/forums`, payload);
    setForm({ platform: "", name: "", url: "", rule_profile: "strict_help_only", topic_tags: [] });
    setTagInput("");
    await fetchAll();
  };

  const addTag = () => {
    if (!tagInput.trim()) return;
    setForm({ ...form, topic_tags: [...form.topic_tags, tagInput.trim()] });
    setTagInput("");
  };

  const retryLink = async (id) => {
    await api.post(`/forums/${id}/check_link`);
    await fetchAll();
  };

  const statusChip = (s) => {
    const map = { ok: "bg-green-100 text-green-800", not_found: "bg-red-100 text-red-800", blocked: "bg-yellow-100 text-yellow-800" };
    return <span className={`text-xs px-2 py-1 rounded-full ${map[s] || "bg-neutral-100 text-neutral-700"}`}>{s || "unknown"}</span>;
  };

  return (
    <div>
      <h2 className="text-lg font-semibold mb-3">Forums</h2>
      <div className="bg-white rounded shadow p-3 mb-4 grid grid-cols-1 md:grid-cols-5 gap-2">
        <input aria-label="Platform" className="border rounded px-2 py-1" placeholder="Platform" value={form.platform} onChange={(e) => setForm({ ...form, platform: e.target.value })} />
        <input aria-label="Name" className="border rounded px-2 py-1" placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <input aria-label="URL" className="border rounded px-2 py-1" placeholder="URL" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
        <select aria-label="Rule Profile" className="border rounded px-2 py-1" value={form.rule_profile} onChange={(e) => setForm({ ...form, rule_profile: e.target.value })}>
          <option value="strict_help_only">strict_help_only</option>
          <option value="open_soft_marketing">open_soft_marketing</option>
        </select>
        <div className="flex gap-1">
          <input aria-label="Topic tag" className="border rounded px-2 py-1 flex-1" placeholder="topic tag" value={tagInput} onChange={(e) => setTagInput(e.target.value)} />
          <button aria-label="Add tag" className="px-2 py-1 bg-neutral-800 text-white rounded" onClick={addTag}>Add</button>
        </div>
        <div className="col-span-full text-xs text-neutral-600">Tags: {form.topic_tags.join(", ")}</div>
        <div className="col-span-full">
          <button onClick={create} className="px-3 py-1 bg-neutral-800 text-white rounded">Create</button>
        </div>
      </div>

      <div className="bg-white rounded shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-neutral-100 text-left">
              <th className="p-2">Platform</th>
              <th className="p-2">Name</th>
              <th className="p-2">Rule</th>
              <th className="p-2">Tags</th>
              <th className="p-2">Link</th>
              <th className="p-2">Checked</th>
              <th className="p-2">Updated</th>
            </tr>
          </thead>
          <tbody>
            {items.map((f) => (
              <tr key={f.id} className="border-t">
                <td className="p-2">{f.platform}</td>
                <td className="p-2">
                  {f.link_status === "ok" ? (
                    <a href={f.url} target="_blank" rel="noreferrer" className="text-blue-600 underline">{f.name}</a>
                  ) : (
                    <span className="text-neutral-600" title={f.url}>{f.name}</span>
                  )}
                </td>
                <td className="p-2">{f.rule_profile}</td>
                <td className="p-2">{(f.topic_tags||[]).join(", ")}</td>
                <td className="p-2 flex items-center gap-2">{statusChip(f.link_status)} <button onClick={() => retryLink(f.id)} className="px-2 py-1 text-xs bg-neutral-200 rounded">Retry</button></td>
                <td className="p-2">{phoenixTime(f.last_checked_at)}</td>
                <td className="p-2">{phoenixTime(f.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}