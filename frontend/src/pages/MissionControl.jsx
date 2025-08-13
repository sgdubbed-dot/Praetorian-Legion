import React, { useEffect, useMemo, useState } from "react";
import { api, phoenixTime } from "../api";

function StatusPill({ status }) {
  const s = (status || "Unlinked").toLowerCase();
  const map = {
    running: "bg-green-100 text-green-800",
    paused: "bg-yellow-100 text-yellow-800",
    completed: "bg-neutral-200 text-neutral-700",
    aborted: "bg-red-100 text-red-800",
    unlinked: "bg-neutral-100 text-neutral-700",
  };
  const cls = map[s] || map.unlinked;
  const label = status || "Unlinked";
  return <span className={`text-[11px] px-2 py-0.5 rounded ${cls}`}>{label}</span>;
}

function RunControls({ thread, onActionDone }) {
  const [busy, setBusy] = useState(false);
  const tid = thread.thread_id;
  const mid = thread.mission_id;

  const call = async (method, url, body) => {
    setBusy(true);
    try {
      if (method === "patch") await api.patch(url, body || {});
      else if (method === "post") await api.post(url, body || {});
      else if (method === "get") await api.get(url);
      onActionDone && onActionDone();
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error("RUN CTRL ERROR", e);
    } finally { setBusy(false); }
  };

  const onRun = async () => {
    if (!tid) return;
    // If no mission linked: create mission now via chat trigger
    if (!mid) {
      await api.post("/mission_control/message", { thread_id: tid, text: "create mission now" });
      onActionDone && onActionDone();
      return;
    }
    // If mission linked and paused → resume; if completed/aborted → duplicate & start
    try {
      const thr = await api.get(`/mission_control/thread/${tid}?limit=1`);
      const status = (thr.data?.thread?.thread_status || "Unlinked").toLowerCase();
      if (status === "paused") {
        await call("post", `/missions/${thread.mission_id}/state`, { state: "resume" });
        return;
      }
      if (status === "completed" || status === "aborted") {
        const ok = window.confirm("Duplicate & Start a new run?");
        if (!ok) return;
        await call("post", "/mission_control/duplicate_run", { mission_id: thread.mission_id, source_thread_id: tid, new_thread: true, start_now: true });
        return;
      }
      // Already running → post a short note
      await api.post("/mission_control/message", { thread_id: tid, text: "run mission now" });
      onActionDone && onActionDone();
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error("RUN status check failed", e);
    }
  };

  const onPause = async () => { if (!mid) return; await call("post", `/missions/${mid}/state`, { state: "paused" }); };
  const onStop = async () => { if (!mid) return; await call("post", `/missions/${mid}/state`, { state: "complete" }); };
  const onAbort = async () => { if (!mid) return; await call("post", `/missions/${mid}/state`, { state: "aborted" }); };

  return (
    <div className="flex items-center gap-1">
      <button disabled={busy} onClick={onRun} className="text-[11px] px-2 py-0.5 rounded bg-green-600 text-white">Run</button>
      <button disabled={busy || !mid} onClick={onPause} className="text-[11px] px-2 py-0.5 rounded bg-yellow-600 text-white">Pause</button>
      <button disabled={busy || !mid} onClick={onStop} className="text-[11px] px-2 py-0.5 rounded bg-neutral-700 text-white">Stop</button>
      <button disabled={busy || !mid} onClick={onAbort} className="text-[11px] px-2 py-0.5 rounded bg-red-700 text-white">Abort</button>
    </div>
  );
}

export default function MissionControl() {
  // Threads + selection
  const [threads, setThreads] = useState([]);
  const [selectedThreadId, setSelectedThreadId] = useState(null);
  const [selectedThread, setSelectedThread] = useState(null);
  const [messages, setMessages] = useState([]);

  // Provider badge
  const [modelId, setModelId] = useState("");

  // Composer + sync
  const [chatInput, setChatInput] = useState("");
  const [sending, setSending] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [toast, setToast] = useState("");

  // Load provider health (model id)
  const loadProvider = async () => {
    try {
      const res = await api.get("/providers/health");
      setModelId(res.data?.praefectus_model_id || "");
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error("PROVIDER ERROR:", e?.message || e);
    }
  };

  // Load threads
  const loadThreads = async () => {
    try {
      const res = await api.get("/mission_control/threads");
      const list = res.data || [];
      setThreads(list);
      // Auto-select first (backend auto-creates General if none existed)
      if (!selectedThreadId && list.length > 0) {
        setSelectedThreadId(list[0].thread_id);
        setSelectedThread(list[0]);
      }
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error("THREADS ERROR:", e?.message || e);
    }
  };

  // Load messages for a thread (ascending order expected from API)
  const loadMessages = async (threadId) => {
    if (!threadId) return;
    try {
      const res = await api.get(`/mission_control/thread/${threadId}?limit=100`);
      const data = res.data || {};
      setSelectedThread(data.thread || null);
      setMessages(Array.isArray(data.messages) ? data.messages : []);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error("MESSAGES ERROR:", e?.message || e);
    }
  };

  // Initial load
  useEffect(() => {
    (async () => {
      await Promise.all([loadProvider(), loadThreads()]);
    })();
  }, []);

  // When selection changes, load its messages
  useEffect(() => {
    if (selectedThreadId) {
      loadMessages(selectedThreadId);
    }
  }, [selectedThreadId]);

  // Sync Now
  const onSyncNow = async () => {
    setSyncing(true);
    try {
      await Promise.all([loadProvider(), loadThreads()]);
      if (selectedThreadId) await loadMessages(selectedThreadId);
      const t = phoenixTime(new Date().toISOString());
      setToast(`Synced at ${t}`);
      setTimeout(() => setToast(""), 2000);
    } finally {
      setSyncing(false);
    }
  };

  // Create new thread
  const onNewThread = async () => {
    try {
      const title = window.prompt("Thread title", "New Thread");
      const body = { title: title && title.trim() ? title.trim() : "New Thread" };
      const res = await api.post("/mission_control/threads", body);
      const newId = res.data?.thread_id;
      await loadThreads();
      if (newId) setSelectedThreadId(newId);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error("CREATE THREAD ERROR:", e?.message || e);
    }
  };

  // Send message
  const sendMessage = async () => {
    const content = (chatInput || "").trim();
    if (!content) return;
    setSending(true);
    try {
      if (selectedThreadId) {
        await api.post("/mission_control/message", { thread_id: selectedThreadId, text: content });
        setChatInput("");
        await loadMessages(selectedThreadId);
      } else {
        // Fallback: let backend default to General if no thread_id yet
        await api.post("/mission_control/message", { text: content });
        setChatInput("");
        // Reload threads to get auto-created General and select it
        await loadThreads();
        // Try to load messages for the (likely) first thread
        if (threads && threads[0]?.thread_id) {
          setSelectedThreadId(threads[0].thread_id);
          await loadMessages(threads[0].thread_id);
        }
      }
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error("SEND ERROR:", e?.message || e);
    } finally {
      setSending(false);
    }
  };

  const sendOnKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Derived
  const threadChips = useMemo(() => threads || [], [threads]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Main Chat Column */}
      <div className="lg:col-span-2 bg-white rounded shadow p-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold">Mission Control</h2>
            {modelId && (
              <span className="text-xs px-2 py-1 rounded bg-neutral-100 border text-neutral-700">
                Model: {modelId}
              </span>
            )}
          </div>
          <button
            aria-label="Sync Now"
            onClick={onSyncNow}
            className="text-sm px-2 py-1 bg-neutral-800 text-white rounded focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-neutral-500"
          >
            {syncing ? "Syncing..." : "Sync Now"}
          </button>
        </div>

        {/* Thread switcher */}
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm text-neutral-600">Recent threads</div>
          <button
            onClick={onNewThread}
            className="text-xs px-2 py-1 bg-blue-600 text-white rounded focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600"
          >
            + New Thread
          </button>
        </div>
        <div className="flex gap-2 overflow-x-auto pb-2 mb-2 border-b">
          {threadChips.map((t) => (
            <button
              key={t.thread_id}
              onClick={() => setSelectedThreadId(t.thread_id)}
              className={`text-xs px-3 py-1 border rounded whitespace-nowrap ${
                selectedThreadId === t.thread_id ? "bg-blue-600 text-white border-blue-600" : "bg-white hover:bg-neutral-100"
              }`}
              title={t.synopsis || t.title}
            >
              {t.title || "Untitled"}
            </button>
          ))}
        </div>

        {toast && (
          <div className="mb-2 text-sm px-2 py-1 bg-green-100 text-green-800 rounded inline-block">{toast}</div>
        )}

        {/* Messages */}
        <div className="h-[420px] overflow-y-auto space-y-2 border rounded p-3 bg-neutral-50">
          {!messages || messages.length === 0 ? (
            <div className="text-sm text-neutral-500">No messages yet. Say hello to Praefectus.</div>
          ) : (
            messages.map((m) => (
              <div key={m.id} className={`flex ${m.role === "human" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[80%] p-2 rounded ${m.role === "human" ? "bg-blue-600 text-white" : "bg-white border"}`}>
                  <div className="text-xs text-neutral-400">{phoenixTime(m.created_at)} — {m.role}</div>
                  <div className="whitespace-pre-wrap text-sm">{m.text}</div>
                  {m.role === "praefectus" && (
                    <div className="mt-1 text-[11px] italic text-neutral-500">Praefectus replied.</div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Composer */}
        <div className="mt-3 flex gap-2">
          <textarea
            aria-label="Message to Praefectus"
            className="flex-1 border rounded px-3 py-2"
            rows={2}
            placeholder="Type a message… (Enter to send, Shift+Enter for newline)"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyDown={sendOnKey}
          />
          <button
            aria-label="Send"
            onClick={sendMessage}
            disabled={sending || !selectedThreadId}
            className="px-4 py-2 bg-blue-600 text-white rounded focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600 disabled:opacity-60"
          >
            {sending ? "Sending…" : "Send"}
          </button>
        </div>
      </div>

      {/* Secondary Column: Recent Threads + Run Controls */}
      <div className="bg-white rounded shadow p-0 flex flex-col">
        <div className="px-4 py-3 border-b flex items-center justify-between">
          <h3 className="text-sm font-semibold">Recent Threads</h3>
          <button onClick={() => loadThreads()} className="text-xs px-2 py-1 bg-neutral-800 text-white rounded">Refresh</button>
        </div>
        <div className="overflow-y-auto" style={{maxHeight: 520}}>
          {(threads || []).map((t) => (
            <div key={t.thread_id} className={`p-3 border-b hover:bg-neutral-50 ${selectedThreadId===t.thread_id?"bg-blue-50":""}`}>
              <div className="flex items-center justify-between">
                <button onClick={() => setSelectedThreadId(t.thread_id)} className="text-left">
                  <div className="text-sm font-medium truncate" title={t.title}>{t.title || "Untitled"}</div>
                  <div className="text-[11px] text-neutral-500">{phoenixTime(t.updated_at)} • <StatusPill status={t.thread_status || (t.mission_id?"Running":"Unlinked")} /></div>
                </button>
                <div className="flex items-center gap-1">
                  <RunControls thread={t} onActionDone={() => {loadThreads(); if(selectedThreadId===t.thread_id){loadMessages(t.thread_id);} }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}