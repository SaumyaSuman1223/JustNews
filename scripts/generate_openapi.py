"""Regenerates packages/api-client/openapi.json from the live FastAPI schema.

Building the schema needs no database - route registration and Pydantic model
introspection happen at import time, before the app's lifespan ever runs.

Run this after any route change, then `pnpm --filter @justnews/api-client
generate` to refresh the generated TypeScript types. CI regenerates both and
fails on any diff against what's committed - the same shape as `alembic
check` for migrations, and for the same reason: a route changed without the
client that depends on it being told.
"""

from __future__ import annotations

import json
import pathlib
import sys

from justnews_api.main import create_app

OUTPUT = pathlib.Path(__file__).resolve().parent.parent / "packages" / "api-client" / "openapi.json"


def main() -> None:
    schema = create_app().openapi()
    # Sorted keys: a stable diff. FastAPI's own key order depends on route
    # registration order, which does not matter and should not show up as
    # unrelated churn in an unrelated change's diff.
    OUTPUT.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    sys.stdout.write(f"wrote {OUTPUT}\n")


if __name__ == "__main__":
    main()
