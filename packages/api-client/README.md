Typed TypeScript client generated from the live FastAPI OpenAPI schema.
Consumed by `frontend` and `apps/mobile`. Generated — never hand-edit
`src/schema.ts` or `openapi.json`.

## Regenerating

After any backend route change:

```bash
make generate-client
```

which runs `scripts/generate_openapi.py` (dumps the schema — no database
needed, route registration happens at import time) then
`pnpm --filter @justnews/api-client generate`. CI regenerates both and fails
on any diff against what's committed, the same shape as `alembic check` for
migrations — a route changed without the client that depends on it being
told.
