from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import users as repo
from justnews_core.errors import ValidationError
from justnews_core.language import normalise_language_code
from justnews_core.models import UserProfile

MAX_LANGUAGES = 20


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
