"""Typed domain errors.

Services raise these. Only routers translate them to HTTP status codes -
that mapping lives in the API layer and nowhere else.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for every error this system raises deliberately."""

    code = "domain_error"

    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    code = "not_found"


class ConflictError(DomainError):
    code = "conflict"


class ValidationError(DomainError):
    code = "validation_error"


class AuthenticationError(DomainError):
    code = "unauthenticated"


class AuthorizationError(DomainError):
    code = "forbidden"


class UpstreamError(DomainError):
    """An external dependency failed. Always carries the upstream's name."""

    code = "upstream_error"

    def __init__(self, upstream: str, message: str) -> None:
        super().__init__(message, details={"upstream": upstream})
        self.upstream = upstream


class QuotaExceededError(DomainError):
    code = "quota_exceeded"
