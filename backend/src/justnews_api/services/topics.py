from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from justnews_api.repositories import topics as repo
from justnews_api.services.perspectives import PerspectiveGroup, group_by_role
from justnews_core.models import Topic


@dataclass(frozen=True, slots=True)
class RelatedTopic:
    topic: Topic
    article_count: int


async def related_topics(
    session: AsyncSession, topic_id: str, *, limit: int = 6
) -> list[RelatedTopic]:
    pairs = await repo.related_topic_ids(session, topic_id, limit=limit)
    related: list[RelatedTopic] = []
    for related_id, count in pairs:
        topic = await repo.get_topic(session, related_id)
        if topic is not None:
            related.append(RelatedTopic(topic=topic, article_count=count))
    return related


async def topic_perspectives(session: AsyncSession, topic_id: str) -> list[PerspectiveGroup]:
    rows = await repo.article_source_roles_for_topic(session, topic_id)
    return group_by_role(rows)


def label_for(topic: Topic, language: str) -> str:
    """The display label in the reader's language, falling back to English and
    then the slug - a topic missing a translation must still render as
    something, never a blank cell or a raw concept id."""
    by_language = {label.language: label.label for label in topic.labels}
    return (
        by_language.get(language) or by_language.get("en") or topic.slug.replace("-", " ").title()
    )
