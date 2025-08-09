import React, { useEffect, useState } from "react";
import { api, phoenixTime } from "../api";
import { useParams, Link } from "react-router-dom";

export default function MissionDetail() {
  const { id } = useParams();
  const [mission, setMission] = useState(null);
  const [events, setEvents] = useState([]);

  const refresh = async () => {
    const m = (await api.get(`/missions/${id}`)).data;
    setMission(m);
    const ev = (await api.get(`/events`, { params: { mission_id: id, limit: 50 } })).data;
    setEvents(ev);
  };

  useEffect(() => { refresh(); }, [id]);

  if (!mission) return <div>Loading...</div>;

  return (
    <div className="space-y-4">
      <div className="bg-white rounded shadow p-4">
        <div className="text-xl font-semibold">{mission.title}</div>
        <div className="text-sm text-neutral-600">Objective: {mission.objective}</div>
        <div className="text-sm">Posture: {mission.posture}</div>
        <div className="text-sm">State: {mission.state}</div>
        <div className="text-sm">Created: {phoenixTime(mission.created_at)} — Updated: {phoenixTime(mission.updated_at)}</div>
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold mb-2">Counters</div>
        <div className="text-sm">Forums: {mission.counters?.forums_found||0} — Prospects: {mission.counters?.prospects_added||0} — Hot Leads: {mission.counters?.hot_leads||0}</div>
        <div className="font-semibold mt-3">Insights</div>
        <ul className="list-disc pl-5 text-sm">
          {(mission.insights||[]).map((i, idx) => <li key={idx}>{i}</li>)}
        </ul>
      </div>

      <div className="bg-white rounded shadow p-4">
        <div className="font-semibold mb-2">Recent Events</div>
        <ul className="text-sm space-y-1">
          {events.map((e) => (
            <li key={e.id} className="border rounded p-2">
              <div className="text-xs text-neutral-500">{phoenixTime(e.timestamp)} — {e.event_name}</div>
              <div className="text-xs break-all">{JSON.stringify(e.payload)}</div>
            </li>
          ))}
        </ul>
      </div>

      <div className="text-sm text-neutral-500">Linked Forums / Prospects / Hot Leads will appear as data grows (Phase 1 auto‑add is handled by Praefectus/Explorator flow).</div>
    </div>
  );
}