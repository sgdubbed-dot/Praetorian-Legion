# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Praetorian Legion is a full-stack web application built for mission management and agent coordination. The project consists of a FastAPI backend with MongoDB storage and a React frontend, designed to run in containerized environments with Kubernetes Ingress.

## Architecture

### Backend (FastAPI + MongoDB)
- **Entry point**: `backend/server.py` - Main FastAPI application with all endpoints
- **Database**: MongoDB with collections for missions, threads, messages, findings, forums, agents, exports, guardrails, hot leads, and rolodex
- **LLM Integration**: Provider abstraction in `backend/providers/` with OpenAI client implementation
- **Key Collections**: All MongoDB collections use UUID-based IDs stored as `_id` field
- **Time Zone**: All timestamps normalized to America/Phoenix timezone

### Frontend (React + Tailwind)
- **Entry point**: `frontend/src/App.js` - Main React app with routing
- **API Client**: `frontend/src/api.js` - Axios-based API client with error handling
- **Pages**: Complete UI for all major features in `frontend/src/pages/`
- **Navigation**: Single-page application with React Router
- **Styling**: Tailwind CSS for all styling

## Development Commands

### Backend Development
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run development server (binds to 0.0.0.0:8001)
cd backend && python server.py

# Environment variables required in backend/.env:
# MONGO_URL=mongodb://localhost:27017
# DB_NAME=your_database_name  
# CORS_ORIGINS=*
```

### Frontend Development
```bash
# Install dependencies
cd frontend && yarn install

# Start development server
yarn start

# Build for production  
yarn build

# Run tests
yarn test

# Environment variables required in frontend/.env:
# REACT_APP_BACKEND_URL=http://localhost:8001 (no trailing slash)
```

### Code Quality
Backend includes linting and formatting tools in requirements.txt:
- black (code formatting)
- isort (import sorting)  
- flake8 (linting)
- mypy (type checking)
- pytest (testing)

## Key API Patterns

### REST Endpoints
- All backend routes prefixed with `/api` for Kubernetes Ingress
- Standard CRUD operations with Pydantic models for validation
- UUID-based IDs across all collections
- Automatic timestamp management (created_at, updated_at)

### Mission Control System
- **Threads**: Chat-like interface for mission planning (`/api/mission_control/threads`)
- **Messages**: Support for human/praefectus conversations with LLM integration
- **Quick Commands**: Text-based triggers like "create mission now", "run mission now", "pause mission"
- **Agent Integration**: Three-agent system (Praefectus, Explorator, Legatus) with status monitoring

### Data Models
- **Missions**: Core entity with states (draft, scanning, engaging, paused, complete, aborted)
- **Findings**: Research results linked to missions/threads with markdown support
- **Forums**: External forum tracking with link validation
- **Guardrails**: Rule system with types (posture, frequency_cap, scope_block, etc.)
- **Hot Leads**: Prospect tracking with approval workflows

## Deployment Architecture

### Container Environment
- Backend runs on port 8001 internally
- Frontend serves on port 3000 internally  
- Supervisor manages both processes inside container
- Kubernetes Ingress routes `/api/*` to backend, everything else to frontend

### Management Commands
```bash
# Inside container (via supervisor)
sudo supervisorctl status
sudo supervisorctl restart all
sudo supervisorctl restart backend
sudo supervisorctl restart frontend

# Health checks
curl $REACT_APP_BACKEND_URL/api/health
curl $REACT_APP_BACKEND_URL/api/
```

### Database Management
```bash
# Backup MongoDB
mongodump --uri "$MONGO_URL" --db "$DB_NAME" --out /backup/path

# Restore MongoDB  
mongorestore --uri "$MONGO_URL" --db "$DB_NAME" /backup/path/$DB_NAME
```

## Testing and Demo Features

### Scenario Endpoints
Backend includes demo scenario generators:
- `POST /api/scenarios/strict_rule_mission` - Seeds help-only mission with forums
- `POST /api/scenarios/open_forum_plan` - Creates marketing mission with open forums  
- `POST /api/scenarios/generate_hotlead` - Creates sample hot leads
- `POST /api/scenarios/export_shortcut` - Demo CSV export workflow
- `POST /api/scenarios/agent_error_retry` - Simulates agent errors for testing

### Agent System
- Auto-reset mechanism for Explorator errors based on retry windows
- Status light system (green/yellow/red) with real-time updates
- Research-only missions keep Legatus in idle (yellow) state

## Important Conventions

### Environment Variables
- Never hardcode URLs - always use environment variables
- Backend uses MONGO_URL, DB_NAME, CORS_ORIGINS
- Frontend uses REACT_APP_BACKEND_URL (no trailing slash)

### Error Handling
- Frontend has ErrorBoundary component for page-level error catching
- API client includes request/response interceptors for debugging
- Backend logs events to Events collection for audit trails

### Phoenix Timezone
- All timestamps converted to America/Phoenix timezone
- Frontend phoenixTime() utility for consistent display
- Backend now_iso() and to_phoenix() functions for timezone handling