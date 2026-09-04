Shared Python: `Settings` (env config, `src/justnews_core/settings.py`),
SQLAlchemy models, the IPTC taxonomy, and other logic used by both `backend`
and `apps/ingestion`. Imported by both; imports neither.

Rules:
- Business logic here must not import FastAPI — it has no idea it's ever
  served over HTTP.
- Never imports `ml/` — only ONNX files and vectors cross that line.
- `backend/migrations` owns schema migrations; this package owns the ORM
  models Alembic diffs against, not the migration files themselves.

## Commands

```bash
uv run pytest packages/core -q
uv run mypy packages/core/src
```
