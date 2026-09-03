"""Entry point for ``justnews-api``."""

from __future__ import annotations

import uvicorn

from justnews_core.settings import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "justnews_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_env == "local",
        log_config=None,
    )


if __name__ == "__main__":
    main()
