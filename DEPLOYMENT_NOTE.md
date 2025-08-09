# Praetorian Legion — Quick Deployment Note (Phase 1)

Stack: FastAPI (backend) + React (frontend) + MongoDB
Ingress: All backend routes under /api
Supervisor-managed services inside container(s)

## Required environment variables

Backend (/app/backend/.env)
- MONGO_URL: mongodb://HOST:PORT
- DB_NAME: logical database name
- CORS_ORIGINS: comma-separated origins or *

Frontend (/app/frontend/.env)
- REACT_APP_BACKEND_URL: https://PUBLIC_HOST (no trailing slash)

## Ports & routing
- Backend binds internally to 0.0.0.0:8001 (do not change)
- Frontend serves on 3000 internally
- Kubernetes Ingress maps /api/* → backend (8001) and all other paths → frontend (3000)

## One working command set (inside container)
- Check status: sudo supervisorctl status
- Restart all:  sudo supervisorctl restart all
- Restart backend: sudo supervisorctl restart backend
- Restart frontend: sudo supervisorctl restart frontend

## Health checks
- Backend: GET $REACT_APP_BACKEND_URL/api/health
- Root:   GET $REACT_APP_BACKEND_URL/api/

## Notes
- Never hardcode URLs; use env vars only.
- All backend endpoints MUST be prefixed with /api to pass Ingress.
- Mongo backups: use mongodump/mongorestore against MONGO_URL/DB_NAME.