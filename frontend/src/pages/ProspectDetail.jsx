import React, { useEffect, useState } from "react";
import { api, phoenixTime } from "../api";
import { useParams, Link, useNavigate } from "react-router-dom";

export default function ProspectDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [p, setP] = useState(null);

  const refresh = async () => {
    const d = (await api.get(`/prospects/${id}`)).data;
    setP(d);
  };

  useEffect(() => { refresh(); }, [id]);

  const platformIcon = (link) => {
    if (!link) return null;
    const l = link.toLowerCase();
    if (l.includes("reddit")) return "[reddit]";
    if (l.includes("linkedin")) return "[linkedin]";
    if (l.includes("twitter") || l.includes("x.com")) return "[x]";
    if (l.includes("github")) return "[github]";
    return "[link]";
  };

  if (!p) return <div>Loading...</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <button onClick={() => navigate("/rolodex")} className="px-3 py-1 bg-neutral-200 rounded">Back to Rolodex</button>
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="text-xl font-semibold">{p.name_or_alias}</div>
        <div className="text-sm">Priority: {p.priority_state}</div>
        <div className="text-sm">Company/Role: {p.company || "-"} / {p.role || "-"}</div>
        <div className="text-sm">Source: {p.source_type || "manual"}</div>
        <div className="text-sm">Created: {phoenixTime(p.created_at)} — Updated: {phoenixTime(p.updated_at)}</div>
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold mb-2">Handles</div>
        <div className="text-sm">{Object.entries(p.handles||{}).map(([k,v]) => `${k}:${v}`).join(", ") || '-'}</div>
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold mb-2">Signals</div>
        <ul className="text-sm space-y-1">
          {(p.signals||[]).map((s, i) => (
            <li key={i} className="border rounded p-2">
              <div className="text-xs text-neutral-500">{phoenixTime(s.timestamp)} — {s.type}</div>
              <div className="text-sm">
                {platformIcon(s.link)} {s.quote} {s.link ? (<a className="text-blue-600 underline" href={s.link} target="_blank" rel="noreferrer">link</a>) : <span className="text-neutral-500">(no source)</span>}
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold mb-2">Engagement History</div>
        <ul className="text-sm space-y-1">
          {(p.engagement_history||[]).map((e, i) => (
            <li key={i} className="border rounded p-2">
              <div className="text-xs text-neutral-500">{phoenixTime(e.timestamp)} {e.channel ? `• ${e.channel}` : ''}</div>
              <div className="text-sm">{e.content || JSON.stringify(e)}</div>
            </li>
          ))}
        </ul>
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold mb-2">Tags</div>
        <div className="text-sm">Mission: {(p.mission_tags||[]).join(", ") || '-'}</div>
        <div className="text-sm">Platform: {(p.platform_tags||[]).join(", ") || '-'}</div>
        <div className="font-semibold mt-3">Contact (public)</div>
        <div className="text-sm">{Object.entries(p.contact_public||{}).map(([k,v]) => `${k}:${v}`).join(", ") || '-'}</div>
      </div>
    </div>
  );
}