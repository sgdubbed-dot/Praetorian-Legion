# Praetorian Legion — Phase 1 Operator Guide

This short guide helps operators run, monitor, and demo the Phase‑1 stack (FastAPI + React + MongoDB) with Kubernetes Ingress and Supervisor.

## 1) Environment variables

Backend (.env in /app/backend)
- MONGO_URL: mongodb connection string
  - Example: mongodb://localhost:27017
- DB_NAME: logical database name
  - Example: test_database
- CORS_ORIGINS: comma-separated origins or *
  - Example: *

Frontend (.env in /app/frontend)
- REACT_APP_BACKEND_URL: external URL used by frontend to call backend
  - Example: https://progress-pulse-21.preview.emergentagent.com

Notes
- Never hardcode URLs in code. Frontend must use REACT_APP_BACKEND_URL; backend must use MONGO_URL and DB_NAME.
- All backend routes are under /api (Ingress rule).

## 2) Start/Stop/Restart, Health, Logs

Supervisor (inside container):
- Restart both: sudo supervisorctl restart all
- Restart backend only: sudo supervisorctl restart backend
- Restart frontend only: sudo supervisorctl restart frontend
- Status: sudo supervisorctl status

Health checks:
- Backend: GET {REACT_APP_BACKEND_URL}/api/health (returns { ok: true })
- Root:   GET {REACT_APP_BACKEND_URL}/api/

Logs (tail):
- Backend error: tail -n 100 /var/log/supervisor/backend.err.log
- Backend out:   tail -n 100 /var/log/supervisor/backend.out.log
- Frontend logs typically via browser devtools (network/console)

## 3) Scenario helper endpoints (for demos)
Base URL: {REACT_APP_BACKEND_URL}/api

- POST /scenarios/strict_rule_mission
  Seeds a help_only mission, several strict forums, a couple of prospects.
  curl -s -X POST "$BASE/scenarios/strict_rule_mission"

- POST /scenarios/open_forum_plan
  Creates a help_plus_soft_marketing mission and two open forums.
  curl -s -X POST "$BASE/scenarios/open_forum_plan"

- POST /scenarios/generate_hotlead
  Creates a Hot Lead tied to an existing or seeded prospect.
  curl -s -X POST "$BASE/scenarios/generate_hotlead"

- POST /scenarios/export_shortcut
  Creates a recipe and generates a CSV export in one call.
  curl -s -X POST "$BASE/scenarios/export_shortcut"

- POST /scenarios/agent_error_retry
  Simulates an Explorator error and schedules a retry window.
  Body: { "minutes": 1 } (default 5)
  curl -s -H "Content-Type: application/json" -d '{"minutes":1}' "$BASE/scenarios/agent_error_retry"

Expected UI changes:
- Agents page shows three agents with status lights.
- After agent_error_retry: Explorator turns red with a visible "Retry at" time; resets to yellow/green after the window.
- Research-only missions keep Legatus yellow (idle).

## 4) CSV Exports
- Create recipe: POST /api/exports/recipe with a filter_spec
- Generate CSV: POST /api/exports/generate with { recipe_name }
- Download: GET /api/exports/{export_id}/download
- Files are served directly from backend via the download route; link appears in the Exports UI.

## 5) Backing up Mongo
- Use mongodump from within an environment that can reach MONGO_URL.
  Example:
  mongodump --uri "$MONGO_URL" --db "$DB_NAME" --out /backup/path

To restore:
  mongorestore --uri "$MONGO_URL" --db "$DB_NAME" /backup/path/$DB_NAME

## 6) Guardrails
- List/add via UI (Guardrails tab) or API (/api/guardrails).
- You can add posture, frequency caps, DM etiquette, scope blocks, and escalation rules.
- Inline DM etiquette guidance: "No cold DMs; DM only after public opt-in; disclose affiliation; one nudge per 7 days; escalate sensitive topics for human approval."
- Quick templates (in Add Rule modal):
  - Frequency cap → {"type":"frequency_cap","value":"1 reply / 24h / user"}
  - Posture → {"type":"posture","value":"help_only"}
  - Scope block → {"type":"scope_block","value":"no posting in r/<subreddit>"}
- Detail view: Click Open to view/edit a rule and see history from /api/events?source=guardrails
- Mission Control shows a warning when a draft posture conflicts with guardrails.

## 7) Research Mode
- Any active mission with posture = research_only forces Legatus idle (yellow).
- When no research_only mission is active, Legatus becomes green if outreach is underway (e.g., approved hot leads); otherwise yellow.

## 8) Agents and Auto‑Reset
- GET /api/agents always returns Praefectus, Explorator, Legatus.
- Explorator: if status = red and now >= next_retry_at, the next GET /api/agents resets the error and clears next_retry_at.
- All timestamps are normalized to America/Phoenix; UI also renders Phoenix zone.