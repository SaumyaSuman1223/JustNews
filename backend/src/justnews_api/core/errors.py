"""The single place domain errors become HTTP status codes.

Services raise typed errors and know nothing about HTTP. Routers raise nothing
and translate nothing. This module is the only translation layer, which is why
adding a status code anywhere else is a bug.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, OperationalError

from justnews_core.errors import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DomainError,
    NotFoundError,
    QuotaExceededError,
    UpstreamError,
    ValidationError,
)
from justnews_core.logging import get_logger

log = get_logger(__name__)

_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    AuthorizationError: status.HTTP_403_FORBIDDEN,
    QuotaExceededError: status.HTTP_429_TOO_MANY_REQUESTS,
    UpstreamError: status.HTTP_502_BAD_GATEWAY,
}


def error_envelope(
    code: str, message: str, *, details: dict[str, Any] | None = None, request_id: str | None = None
) -> dict[str, Any]:
    """The one response shape every failure uses. Clients parse this and
    nothing else."""
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    if request_id:
        body["error"]["request_id"] = request_id
    return body


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(request: Request, exc: DomainError) -> JSONResponse:
        code = next(
            (s for cls, s in _STATUS_BY_ERROR.items() if isinstance(exc, cls)),
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        if code >= 500:
            log.error("domain_error", code=exc.code, message=exc.message, details=exc.details)
        return JSONResponse(
            status_code=code,
            content=error_envelope(
                exc.code,
                exc.message,
                details=exc.details,
                request_id=getattr(request.state, "request_id", None),
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def _request_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_envelope(
                "validation_error",
                "Request failed validation.",
                details={"errors": exc.errors()},
                request_id=getattr(request.state, "request_id", None),
            ),
        )

    # A database outage is a 503, not a 500.
    #
    # The distinction is load-bearing for the web tier: 5xx all look alike to a
    # human, but 503 with Retry-After tells a cache it may keep serving what it
    # already has, which is exactly the degraded mode we want. A 500 says "this
    # request was wrong" and invites a retry storm.
    #
    # Both branches are needed. SQLAlchemy wraps most failures in DBAPIError,
    # but a connection refused during pool checkout propagates as a raw
    # ConnectionRefusedError through the greenlet bridge without ever being
    # wrapped - which is how this returned 500 the first time it was tested
    # against a stopped database.
    @app.exception_handler(OperationalError)
    @app.exception_handler(DBAPIError)
    @app.exception_handler(ConnectionError)
    async def _database_unavailable(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        cause = getattr(exc, "orig", exc)
        log.error("database_unavailable", error=type(cause).__name__, request_id=request_id)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            headers={"Retry-After": "15"},
            content=error_envelope(
                "database_unavailable",
                "The database is temporarily unreachable. Cached content may still be served.",
                request_id=request_id,
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Never leak an internal message to a client. Log it, return an ID.
        request_id = getattr(request.state, "request_id", None)
        log.exception("unhandled_exception", path=request.url.path, request_id=request_id)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_envelope(
                "internal_error",
                "Something went wrong on our side.",
                request_id=request_id,
            ),
        )
