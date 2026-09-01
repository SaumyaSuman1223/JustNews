"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from justnews_api.core.errors import install_error_handlers
from justnews_api.core.middleware import RequestContextMiddleware
from justnews_api.routers import content, health
from justnews_core.db import dispose_engine, init_engine
from justnews_core.logging import configure_logging, get_logger
from justnews_core.settings import Settings, get_settings

log = get_logger(__name__)


def _lifespan(settings: Settings):  # type: ignore[no-untyped-def]
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        init_engine(settings)
        log.info("api_started", environment=settings.app_env)
        try:
            yield
        finally:
            await dispose_engine()
            log.info("api_stopped")

    return lifespan


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="JustNews API",
        version="0.1.0",
        summary="Personalised, multilingual news.",
        lifespan=_lifespan(settings),
        docs_url="/docs" if settings.app_env != "production" else None,
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"] if settings.app_env == "local" else [],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["authorization", "content-type", "x-request-id"],
    )

    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(content.router)
    return app


app = create_app()
