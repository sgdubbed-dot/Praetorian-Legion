import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, phoenixTime } from "../api";

export default function Findings() {
  const [findings, setFindings] = useState([]);
  const [missions, setMissions] = useState([]);
  const [loading, setLoading] = useState(false);

  const missionById = useMemo(() => {
    const m = {};
    for (const it of missions) m[it.id] = it;
    return m;
  }, [missions]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [fRes, mRes] = await Promise.all([
        api.get("/findings"),
        api.get("/missions"),
      ]);
      setFindings(fRes.data || []);
      setMissions(mRes.data || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAll(); }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Findings</h2>
        <button onClick={loadAll} className="text-sm px-2 py-1 bg-neutral-800 text-white rounded">Refresh</button>
      </div>

      <div className="bg-white rounded shadow">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-neutral-600 border-b">
              <th className="p-2">Title</th>
              <th className="p-2">Mission</th>
              <th className="p-2">Updated</th>
              <th className="p-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(!findings || findings.length === 0) && (
              <tr><td className="p-3 text-neutral-500" colSpan={4}>{loading ? "Loading…" : "No findings yet."}</td></tr>
            )}
            {findings.map((f) => (
              <tr key={f.id} className="border-b hover:bg-neutral-50">
                <td className="p-2">
                  <Link to={`/findings/${f.id}`} className="text-blue-600 hover:underline">{f.title || "Untitled"}</Link>
                </td>
                <td className="p-2">{missionById[f.mission_id]?.title || f.mission_id}</td>
                <td className="p-2">{phoenixTime(f.updated_at)}</td>
                <td className="p-2">
                  <Link to={`/findings/${f.id}`} className="text-xs px-2 py-1 bg-neutral-200 rounded">Open</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}