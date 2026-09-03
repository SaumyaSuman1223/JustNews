"""Liveness and readiness.

The distinction matters and is the whole point of this module:

``/health``
    Is the process alive? Never touches the database. A dependency outage must
    not make the orchestrator kill a healthy container.
``/health/ready``
    Can it serve traffic? Runs ``SELECT 1`` under a short timeout. With
    Postgres stopped this returns 503 in about a second - it does not hang,
    which is the failure mode that makes an outage look like a deadlock.
"""

from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text

from justnews_core.db import get_session_factory
from justnews_core.logging import get_logger
from justnews_core.settings import get_settings

router = APIRouter(tags=["health"])
log = get_logger(__name__)

READINESS_TIMEOUT_SECONDS = 2.0


class Health(BaseModel):
    status: Literal["ok"]
    environment: str


class Readiness(BaseModel):
    status: Literal["ready", "degraded"]
    database: Literal["ok", "unreachable", "timeout"]
    detail: str | None = None


@router.get("/health", response_model=Health)
async def health() -> Health:
    settings = get_settings()
    return Health(status="ok", environment=settings.app_env)


@router.get("/health/ready", response_model=Readiness)
async def readiness(response: Response) -> Readiness:
    try:
        async with asyncio.timeout(READINESS_TIMEOUT_SECONDS):
            factory = get_session_factory()
            async with factory() as session:
                await session.execute(text("SELECT 1"))
    except TimeoutError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        log.warning("readiness_timeout", timeout_s=READINESS_TIMEOUT_SECONDS)
        return Readiness(
            status="degraded",
            database="timeout",
            detail=f"Database did not respond within {READINESS_TIMEOUT_SECONDS}s.",
        )
    except Exception as exc:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        log.warning("readiness_failed", error=type(exc).__name__)
        return Readiness(
            status="degraded",
            database="unreachable",
            detail=f"{type(exc).__name__}: database is not reachable.",
        )
    return Readiness(status="ready", database="ok")
