from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import follows as follows_repo
from justnews_api.repositories import interactions as interactions_repo
from justnews_api.repositories import saves as saves_repo
from justnews_api.repositories import users as repo
from justnews_core.errors import ValidationError
from justnews_core.language import normalise_language_code
from justnews_core.models import UserProfile

MAX_LANGUAGES = 20
# A beta-scale bound, not a page size - this is a one-shot "everything you
# have" export, not something a reader pages through.
EXPORT_ROW_LIMIT = 10_000


def validate_languages(codes: list[str]) -> list[str]:
    if not codes or len(codes) > MAX_LANGUAGES:
        raise ValidationError(f"preferred_languages must have 1 to {MAX_LANGUAGES} entries.")
    normalised: list[str] = []
    for raw in codes:
        code = normalise_language_code(raw)
        if code is None:
            raise ValidationError(f"Not a language code: {raw!r}")
        if code not in normalised:
            normalised.append(code)
    return normalised


async def get_or_create_profile(session: AsyncSession, user_id: UUID) -> UserProfile:
    """Every route that requires auth touches this first, lazily creating the
    profile row on a reader's very first authenticated request rather than
    depending on a trigger over Supabase's ``auth.users``."""
    return await repo.upsert_profile(session, user_id)


async def update_profile(
    session: AsyncSession, user_id: UUID, *, preferred_languages: list[str]
) -> UserProfile:
    validated = validate_languages(preferred_languages)
    return await repo.upsert_profile(session, user_id, preferred_languages=validated)


@dataclass(frozen=True, slots=True)
class UserDataExport:
    profile: dict[str, Any]
    saves: list[dict[str, Any]]
    follows: list[dict[str, Any]]
    history: list[dict[str, Any]]


async def export_user_data(session: AsyncSession, user_id: UUID) -> UserDataExport:
    """Everything this system holds about one reader, keyed by their own id -
    a global audience means GDPR/UK GDPR/CCPA/DPDP data-portability all apply,
    and this is what answers all four the same way."""
    profile = await repo.get_profile(session, user_id)
    saves = await saves_repo.list_saves(
        session, user_id, limit=EXPORT_ROW_LIMIT, before_created_at=None, before_id=None
    )
    follows = await follows_repo.list_follows(session, user_id)
    history = await interactions_repo.list_history(
        session, user_id, limit=EXPORT_ROW_LIMIT, before_viewed_at=None, before_id=None
    )
    return UserDataExport(
        profile={
            "id": str(profile.id) if profile else str(user_id),
            "preferred_languages": list(profile.preferred_languages) if profile else [],
            "role": profile.role if profile else None,
            "created_at": _iso(profile.created_at) if profile else None,
        },
        saves=[{"article_id": row.article_id, "saved_at": _iso(row.created_at)} for row in saves],
        follows=[
            {"topic_id": row.topic_id, "followed_at": _iso(row.created_at)} for row in follows
        ],
        history=[
            {"article_id": row.article_id, "viewed_at": _iso(row.viewed_at)} for row in history
        ],
    )


def _iso(value: datetime) -> str:
    return value.isoformat()


async def delete_account(session: AsyncSession, user_id: UUID) -> None:
    """Deletes this system's own record of the reader: the profile row, which
    cascades to saves and follows and anonymises (``user_id`` set NULL) every
    impression and interaction event already logged - retained, but no longer
    attributable to anyone.

    The Supabase auth account itself is untouched - that needs the service
    role key, which this API does not hold. A reader who deletes their data
    here still needs to delete their Supabase account separately; documented
    as a known gap, not silently pretended away.
    """
    await repo.delete_profile(session, user_id)
