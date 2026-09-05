from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.core.db import get_session
from justnews_api.repositories import topics as repo
from justnews_api.routers.content import StoryOut
from justnews_api.services import topics as service
from justnews_core.errors import NotFoundError, ValidationError
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


class TopicOverviewOut(BaseModel):
    articles: int
    sources: int
    stories: int


class RelatedTopicOut(BaseModel):
    id: str
    slug: str
    label: str
    article_count: int


class PerspectiveSourceOut(BaseModel):
    id: int
    slug: str
    name: str
    homepage_url: str = Field(description="Always link out to the publisher.")


class PerspectiveGroupOut(BaseModel):
    role: str = Field(
        description="One of industry, government, academic, investor, consumer, public - "
        "the labels the perspectives copy shows, not an invented category name.",
    )
    article_count: int
    sources: list[PerspectiveSourceOut]


async def _require_topic(session: AsyncSession, topic_id: str) -> None:
    if await repo.get_topic(session, topic_id) is None:
        raise NotFoundError(f"No topic with id {topic_id!r}.")


@router.get("/topics/{topic_id}/overview", response_model=TopicOverviewOut)
async def topic_overview(
    topic_id: str, session: AsyncSession = Depends(get_session)
) -> TopicOverviewOut:
    await _require_topic(session, topic_id)
    overview = await repo.topic_overview(session, topic_id)
    return TopicOverviewOut(
        articles=overview.articles, sources=overview.sources, stories=overview.stories
    )


@router.get("/topics/{topic_id}/stories", response_model=list[StoryOut])
async def topic_stories(
    topic_id: str,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=50),
) -> list[StoryOut]:
    """My Desk's Timeline: this topic's own story clusters, most recently
    active first - `StoryCluster.first_seen_at`/`last_seen_at` are what the
    timeline plots, not an invented per-day rollup."""
    await _require_topic(session, topic_id)
    clusters = await repo.list_story_clusters_for_topic(session, topic_id=topic_id, limit=limit)
    return [StoryOut.from_cluster(cluster) for cluster in clusters]


@router.get("/topics/{topic_id}/related", response_model=list[RelatedTopicOut])
async def topic_related(
    topic_id: str,
    session: AsyncSession = Depends(get_session),
    language: str = Query(default="en"),
    limit: int = Query(default=6, ge=1, le=20),
) -> list[RelatedTopicOut]:
    await _require_topic(session, topic_id)
    code = normalise_language_code(language)
    if code is None:
        raise ValidationError(f"Not a language code: {language!r}")
    related = await service.related_topics(session, topic_id, limit=limit)
    return [
        RelatedTopicOut(
            id=item.topic.id,
            slug=item.topic.slug,
            label=service.label_for(item.topic, code),
            article_count=item.article_count,
        )
        for item in related
    ]


@router.get("/topics/{topic_id}/perspectives", response_model=list[PerspectiveGroupOut])
async def topic_perspectives(
    topic_id: str, session: AsyncSession = Depends(get_session)
) -> list[PerspectiveGroupOut]:
    """My Desk's Perspectives tab (ADR 0013): this topic's recent articles,
    grouped by the editorially-assigned role of who published them. A group
    only exists here if a reader can click through to the named sources
    behind it - nothing here is inferred from an article's text."""
    await _require_topic(session, topic_id)
    groups = await service.topic_perspectives(session, topic_id)
    return [
        PerspectiveGroupOut(
            role=group.role,
            article_count=group.article_count,
            sources=[
                PerspectiveSourceOut(
                    id=source.id,
                    slug=source.slug,
                    name=source.name,
                    homepage_url=source.homepage_url,
                )
                for source in group.sources
            ],
        )
        for group in groups
    ]
