"""Cursor encoding. Pure unit tests - no database needed."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from justnews_api.services.cursor import decode_cursor, encode_cursor
from justnews_core.errors import ValidationError


def test_round_trips() -> None:
    when = datetime(2026, 8, 31, 12, 30, 45, tzinfo=UTC)
    assert decode_cursor(encode_cursor(when, 4242)) == (when, 4242)


def test_is_opaque() -> None:
    # Clients must not be able to read or construct one, or they will start
    # depending on its shape and we can never change it.
    cursor = encode_cursor(datetime(2026, 1, 1, tzinfo=UTC), 1)
    assert "2026" not in cursor
    assert "published" not in cursor


def test_is_url_safe() -> None:
    cursor = encode_cursor(datetime(2026, 1, 1, tzinfo=UTC), 999999)
    assert all(character.isalnum() or character in "-_" for character in cursor)


def test_normalises_to_utc() -> None:
    from datetime import timedelta, timezone

    ist = timezone(timedelta(hours=5, minutes=30))
    when = datetime(2026, 8, 31, 18, 0, tzinfo=ist)
    decoded, _ = decode_cursor(encode_cursor(when, 1))
    assert decoded == when
    assert decoded.tzinfo is UTC


@pytest.mark.parametrize("bad", ["", "notbase64!!", "YWJj", "eyJ2Ijo5OSwicCI6IngiLCJpIjoxfQ"])
def test_rejects_malformed_cursors(bad: str) -> None:
    with pytest.raises(ValidationError):
        decode_cursor(bad)
