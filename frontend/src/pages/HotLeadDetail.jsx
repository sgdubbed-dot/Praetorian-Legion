import React, { useEffect, useState } from "react";
import { api, phoenixTime } from "../api";
import { useParams, Link } from "react-router-dom";

export default function HotLeadDetail() {
  const { id } = useParams();
  const [h, setH] = useState(null);
  const [prospect, setProspect] = useState(null);

  const refresh = async () => {
    const d = (await api.get(`/hotleads/${id}`)).data;
    setH(d);
    const p = (await api.get(`/prospects/${d.prospect_id}`)).data;
    setProspect(p);
  };

  useEffect(() => { refresh(); }, [id]);

  if (!h) return <div>Loading...</div>;

  return (
    <div className="space-y-4">
      <div className="bg-white rounded shadow p-4">
        <div className="text-xl font-semibold">Hot Lead {h.id.slice(0,8)}</div>
        <div className="text-sm">Status: {h.status}</div>
        <div className="text-sm">Prospect: {prospect?.name_or_alias || h.prospect_id}</div>
        <div className="text-sm">Created: {phoenixTime(h.created_at)} — Updated: {phoenixTime(h.updated_at)}</div>
        {prospect && <div className="text-sm"><Link className="text-blue-600 underline" to={`/prospects/${prospect.id}`}>View Prospect</Link></div>}
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold mb-2">Evidence</div>
        <ul className="text-sm space-y-1">
          {(h.evidence||[]).map((e, i) => (
            <li key={i} className="border rounded p-2">
              <div className="text-xs text-neutral-500">{phoenixTime(e.timestamp)}</div>
              <div className="text-sm">{e.quote} {e.link && (<a className="text-blue-600 underline" href={e.link} target="_blank" rel="noreferrer">link</a>)}</div>
            </li>
          ))}
        </ul>
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold mb-2">Proposed Script</div>
        <pre className="text-sm whitespace-pre-wrap">{h.proposed_script || '-'}</pre>
        <div className="font-semibold mt-3">Suggested Actions</div>
        <ul className="list-disc pl-5 text-sm">
          {(h.suggested_actions||[]).map((a, i) => <li key={i}>{a}</li>)}
        </ul>
      </div>
    </div>
  );
}