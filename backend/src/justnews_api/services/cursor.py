"""Opaque keyset cursors.

A cursor encodes the sort key of the last row returned - here
``(published_at, id)`` - base64url-encoded so clients cannot construct one by
hand and start depending on its shape. It is deliberately not an offset: on a
feed that gains rows continuously, offsets repeat and skip items.
"""

from __future__ import annotations

import base64
import binascii
import json
from datetime import UTC, datetime

from justnews_core.errors import ValidationError

_CURSOR_VERSION = 1


def encode_cursor(published_at: datetime, article_id: int, *, served: int | None = None) -> str:
    """``served`` is how many items came before the next page - only the
    feed's chronological policy sets it, so an impression's ``position`` is
    its place in the whole feed rather than restarting at 0 on every page
    (ADR 0015). Readers of the cursor that do not log positions ignore it."""
    payload: dict[str, object] = {
        "v": _CURSOR_VERSION,
        "p": published_at.astimezone(UTC).isoformat(),
        "i": article_id,
    }
    if served is not None:
        payload["n"] = served
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, int]:
    padding = "=" * (-len(cursor) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor + padding))
        if payload["v"] != _CURSOR_VERSION:
            raise ValidationError("Cursor is from an incompatible version.")
        published_at = datetime.fromisoformat(payload["p"])
        article_id = int(payload["i"])
    except ValidationError:
        raise
    except (KeyError, ValueError, TypeError, binascii.Error, UnicodeDecodeError) as exc:
        raise ValidationError("Cursor is not valid.") from exc

    if published_at.tzinfo is None:
        raise ValidationError("Cursor timestamp must be timezone-aware.")
    return published_at, article_id


def decode_cursor_served(cursor: str) -> int:
    """How many items came before this cursor's page; 0 for a cursor
    written before positions ran across pages."""
    padding = "=" * (-len(cursor) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor + padding))
        served = int(payload.get("n", 0))
    except (ValueError, TypeError, AttributeError, binascii.Error, UnicodeDecodeError) as exc:
        raise ValidationError("Cursor is not valid.") from exc
    if served < 0:
        raise ValidationError("Cursor is not valid.")
    return served


_RANK_CURSOR_VERSION = 2


def encode_rank_cursor(window_upper_bound: datetime, offset: int) -> str:
    """For the Stage 5 ranked feed: not a row's sort key, but a position
    inside one already-scored, frozen candidate window - see
    ``repositories.content.list_articles_window``."""
    payload = {
        "v": _RANK_CURSOR_VERSION,
        "w": window_upper_bound.astimezone(UTC).isoformat(),
        "o": offset,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_rank_cursor(cursor: str) -> tuple[datetime, int]:
    padding = "=" * (-len(cursor) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor + padding))
        if payload["v"] != _RANK_CURSOR_VERSION:
            raise ValidationError("Cursor is from an incompatible version.")
        window_upper_bound = datetime.fromisoformat(payload["w"])
        offset = int(payload["o"])
    except ValidationError:
        raise
    except (KeyError, ValueError, TypeError, binascii.Error, UnicodeDecodeError) as exc:
        raise ValidationError("Cursor is not valid.") from exc

    if window_upper_bound.tzinfo is None:
        raise ValidationError("Cursor timestamp must be timezone-aware.")
    if offset < 0:
        raise ValidationError("Cursor is not valid.")
    return window_upper_bound, offset
