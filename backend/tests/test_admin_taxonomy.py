"""Integration tests for the admin taxonomy browser and article topic override
editor - scoped to the 17 real top-level IPTC concepts (see
repositories/topics.py's own note: nothing below level 1 is loaded yet)."""

from __future__ import annotations

from httpx import AsyncClient
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source, make_topic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import AdminAuditLog, ArticleTopic, Topic


class TestListTopics:
    async def test_lists_active_top_level_topics_with_article_counts(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        topic = await make_topic(session, topic_id="medtop:20000001", slug="topic-a")
        session.add(ArticleTopic(article_id=article.id, topic_id=topic.id, is_primary=True))
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        response = await client.get("/v1/admin/topics", headers=admin)

        assert response.status_code == 200
        rows = {row["id"]: row for row in response.json()}
        assert rows["medtop:20000001"]["article_count"] == 1

    async def test_inactive_topics_are_excluded(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        session.add(
            Topic(
                id="medtop:20000002",
                level=1,
                path=["medtop:20000002"],
                slug="inactive-topic",
                active=False,
            )
        )
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        response = await client.get("/v1/admin/topics", headers=admin)

        assert "medtop:20000002" not in {row["id"] for row in response.json()}


class TestArticleTopicsOverride:
    async def test_writes_an_override_and_an_audit_log_entry(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        topic_a = await make_topic(session, topic_id="medtop:20000003", slug="topic-b")
        topic_b = await make_topic(session, topic_id="medtop:20000004", slug="topic-c")
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        response = await client.put(
            f"/v1/admin/articles/{article.id}/topics",
            json={
                "topic_ids": [topic_a.id, topic_b.id],
                "primary_topic_id": topic_b.id,
            },
            headers=admin,
        )
        assert response.status_code == 204

        read_back = await client.get(f"/v1/admin/articles/{article.id}/topics", headers=admin)
        assignments = {row["id"]: row["is_primary"] for row in read_back.json()}
        assert assignments == {topic_a.id: False, topic_b.id: True}

        audit_rows = (
            (
                await session.execute(
                    select(AdminAuditLog).where(AdminAuditLog.action == "article_topics_override")
                )
            )
            .scalars()
            .all()
        )
        assert len(audit_rows) == 1
        assert audit_rows[0].details["after"] == [topic_a.id, topic_b.id]
        assert audit_rows[0].details["primary"] == topic_b.id

    async def test_replaces_rather_than_adds_to_the_existing_set(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        topic_a = await make_topic(session, topic_id="medtop:20000005", slug="topic-d")
        topic_b = await make_topic(session, topic_id="medtop:20000006", slug="topic-e")
        session.add(ArticleTopic(article_id=article.id, topic_id=topic_a.id, is_primary=True))
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        await client.put(
            f"/v1/admin/articles/{article.id}/topics",
            json={"topic_ids": [topic_b.id], "primary_topic_id": topic_b.id},
            headers=admin,
        )

        rows = (
            (
                await session.execute(
                    select(ArticleTopic).where(ArticleTopic.article_id == article.id)
                )
            )
            .scalars()
            .all()
        )
        assert [row.topic_id for row in rows] == [topic_b.id]

    async def test_rejects_a_zero_topic_set(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        response = await client.put(
            f"/v1/admin/articles/{article.id}/topics",
            json={"topic_ids": [], "primary_topic_id": ""},
            headers=admin,
        )
        assert response.status_code == 422

    async def test_rejects_a_primary_topic_not_in_the_set(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        topic = await make_topic(session, topic_id="medtop:20000007", slug="topic-f")
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        response = await client.put(
            f"/v1/admin/articles/{article.id}/topics",
            json={"topic_ids": [topic.id], "primary_topic_id": "medtop:99999999"},
            headers=admin,
        )
        assert response.status_code == 422

    async def test_rejects_an_inactive_topic(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        session.add(
            Topic(
                id="medtop:20000008",
                level=1,
                path=["medtop:20000008"],
                slug="inactive-for-override",
                active=False,
            )
        )
        await session.commit()

        admin = await make_beta_headers(session, role="admin")
        response = await client.put(
            f"/v1/admin/articles/{article.id}/topics",
            json={"topic_ids": ["medtop:20000008"], "primary_topic_id": "medtop:20000008"},
            headers=admin,
        )
        assert response.status_code == 422

    async def test_a_reader_is_forbidden(self, client: AsyncClient, session: AsyncSession) -> None:
        source = await make_source(session)
        article = await make_article(session, source)
        await session.commit()

        reader = await make_beta_headers(session, role="reader")
        response = await client.get(f"/v1/admin/articles/{article.id}/topics", headers=reader)
        assert response.status_code == 403
