import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, phoenixTime } from "../api";

export default function FindingDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [f, setF] = useState(null);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [highlights, setHighlights] = useState("");
  const [metrics, setMetrics] = useState("");
  const [saving, setSaving] = useState(false);

  const load = async () => {
    const res = await api.get(`/findings/${id}`);
    setF(res.data);
    setTitle(res.data.title || "");
    setBody(res.data.body_markdown || "");
    setHighlights(JSON.stringify(res.data.highlights || [], null, 2));
    setMetrics(JSON.stringify(res.data.metrics || {}, null, 2));
  };

  useEffect(() => { load(); }, [id]);

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        title,
        body_markdown: body,
      };
      try {
        const parsedH = JSON.parse(highlights);
        if (Array.isArray(parsedH)) payload.highlights = parsedH;
      } catch (e) {}
      try {
        const parsedM = JSON.parse(metrics);
        if (parsedM && typeof parsedM === "object") payload.metrics = parsedM;
      } catch (e) {}
      await api.patch(`/findings/${id}`, payload);
      await load();
    } finally {
      setSaving(false);
    }
  };

  const exportFile = async (format) => {
    const url = `${process.env.REACT_APP_BACKEND_URL}/api/findings/${id}/export?format=${format}`;
    try {
      const resp = await fetch(url, { method: "POST" });
      const blob = await resp.blob();
      const a = document.createElement("a");
      const downloadUrl = window.URL.createObjectURL(blob);
      a.href = downloadUrl;
      a.download = `finding_${id}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error("EXPORT ERROR", e);
    }
  };

  if (!f) return <div>Loading…</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <button onClick={() => navigate(-1)} className="px-3 py-1 bg-neutral-200 rounded">Back</button>
        <div className="text-xs text-neutral-600">Updated: {phoenixTime(f.updated_at)}</div>
      </div>

      <div className="bg-white rounded shadow p-4 space-y-3">
        <div>
          <label className="text-xs text-neutral-600">Title</label>
          <input className="w-full border rounded px-2 py-1" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div>
          <label className="text-xs text-neutral-600">Body (Markdown)</label>
          <textarea rows={12} className="w-full border rounded px-2 py-1 font-mono" value={body} onChange={(e) => setBody(e.target.value)} />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-neutral-600">Highlights (JSON array)</label>
            <textarea rows={6} className="w-full border rounded px-2 py-1 font-mono" value={highlights} onChange={(e) => setHighlights(e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-neutral-600">Metrics (JSON object)</label>
            <textarea rows={6} className="w-full border rounded px-2 py-1 font-mono" value={metrics} onChange={(e) => setMetrics(e.target.value)} />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={save} disabled={saving} className="px-3 py-1 bg-blue-600 text-white rounded">{saving ? "Saving…" : "Save"}</button>
          <button onClick={() => exportFile("md")} className="px-3 py-1 bg-neutral-200 rounded">Export Markdown</button>
          <button onClick={() => exportFile("csv")} className="px-3 py-1 bg-neutral-200 rounded">Export CSV</button>
        </div>
      </div>
    </div>
  );
}