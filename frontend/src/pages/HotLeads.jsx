import React, { useEffect, useState } from "react";
import { api, phoenixTime } from "../api";
import { useNavigate } from "react-router-dom";

export default function HotLeads() {
  const [items, setItems] = useState([]);
  const [pending, setPending] = useState([]);
  const nav = useNavigate();

  const refresh = async () => {
    const list = (await api.get(`/hotleads`)).data;
    // join with prospects to show name
    const prospects = (await api.get(`/prospects`)).data;
    const byId = Object.fromEntries(prospects.map((p) => [p.id, p]));
    const joined = list.map((h) => ({ ...h, prospect: byId[h.prospect_id] }));
    setItems(joined);
    setPending(joined.filter((h) => h.status === "pending_approval"));
  };
  useEffect(() => { refresh(); }, []);

  const setStatus = async (id, status) => {
    await api.post(`/hotleads/${id}/status`, { status });
    await refresh();
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">Hot Leads</h2>
      </div>
      <div className="bg-white rounded shadow p-3">
        <div className="font-medium mb-2">Awaiting Approval</div>
        {pending.length === 0 && <div className="text-sm text-neutral-500">None</div>}
        <div className="grid gap-2">
          {pending.map((h) => (
            <div key={h.id} className="border rounded p-2">
              <div className="text-sm">{h.evidence?.[0]?.quote}</div>
              <div className="text-xs text-neutral-500">{phoenixTime(h.created_at)} — Prospect: {h.prospect?.name_or_alias || h.prospect_id.slice(0,8)}</div>
              <div className="mt-2 flex gap-2">
                <button className="px-2 py-1 bg-green-600 text-white text-xs rounded" onClick={() => setStatus(h.id, "approved")}>Approve</button>
                <button className="px-2 py-1 bg-yellow-600 text-white text-xs rounded" onClick={() => setStatus(h.id, "deferred")}>Defer</button>
                <button className="px-2 py-1 bg-red-600 text-white text-xs rounded" onClick={() => setStatus(h.id, "removed")}>Reject</button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-neutral-100 text-left">
              <th className="p-2">ID</th>
              <th className="p-2">Prospect</th>
              <th className="p-2">Status</th>
              <th className="p-2">Updated</th>
            </tr>
          </thead>
          <tbody>
            {items.map((h) => (
              <tr key={h.id} className="border-t hover:bg-neutral-50 cursor-pointer" onClick={() => nav(`/hotleads/${h.id}`)}>
                <td className="p-2">{h.id.slice(0,8)}</td>
                <td className="p-2">{h.prospect?.name_or_alias || h.prospect_id.slice(0,8)}</td>
                <td className="p-2">{h.status}</td>
                <td className="p-2">{phoenixTime(h.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}