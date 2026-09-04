Dockerfiles for the local stack (`docker-compose.yml`) and as an escape
route if a hosted platform's free tier ever stops fitting.

| Dockerfile | Builds | Deployed via |
|---|---|---|
| `docker/api.Dockerfile` | `backend` (FastAPI) | `render.yaml` (Render Blueprint) |
| `docker/web.Dockerfile` | `frontend` (Next.js) | Not used in production — Vercel builds `frontend` directly (ADR 0003). Exists so `docker-compose.yml` matches prod-shaped behavior locally, and as a fallback if Vercel's terms stop fitting |
| `docker/ingestion.Dockerfile` | `apps/ingestion` | Not deployed as a service — production ingestion runs the same CLI directly on a scheduled GitHub Actions runner (`.github/workflows/ingest.yml`), since free tiers have nowhere to put an always-on worker |

Actual deploy wiring lives in `render.yaml` (API) and Vercel's own project
settings (web) — this directory only builds the images.
