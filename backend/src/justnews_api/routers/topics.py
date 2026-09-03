from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.db import get_session
from justnews_api.repositories import topics as repo
from justnews_api.services import topics as service
from justnews_core.errors import ValidationError
from justnews_core.language import normalise_language_code

router = APIRouter(prefix="/v1", tags=["topics"])


class TopicOut(BaseModel):
    id: str
    slug: str
    label: str


@router.get("/topics", response_model=list[TopicOut])
async def list_topics(
    session: AsyncSession = Depends(get_session),
    language: str = Query(default="en"),
) -> list[TopicOut]:
    code = normalise_language_code(language)
    if code is None:
        raise ValidationError(f"Not a language code: {language!r}")

    topics = await repo.list_top_level_topics(session)
    return [
        TopicOut(id=topic.id, slug=topic.slug, label=service.label_for(topic, code))
        for topic in topics
    ]
