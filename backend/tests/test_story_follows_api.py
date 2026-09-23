"""Integration tests for followed stories (fifth pass F2)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from justnews_testing.beta import make_beta_headers
from justnews_testing.factories import make_article, make_source
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import Article, StoryCluster


async def _story(session: AsyncSession, *articles: Article) -> StoryCluster:
    cluster = StoryCluster(
        title=articles[0].title,
        first_seen_at=articles[0].published_at,
        last_seen_at=articles[-1].published_at,
        article_count=len(articles),
        source_count=len(articles),
        language_count=1,
        country_count=1,
    )
    session.add(cluster)
    await session.flush()
    for article in articles:
        article.story_cluster_id = cluster.id
    await session.flush()
    return cluster


class TestStoryFollows:
    async def test_follow_then_list(self, client: AsyncClient, session: AsyncSession) -> None:
        source = await make_source(session)
        story = await _story(session, await make_article(session, source, title="Summit opens"))
        await session.commit()
        headers = await make_beta_headers(session)

        response = await client.post(
            "/v1/follows/stories", json={"story_id": story.id}, headers=headers
        )
        assert response.status_code == 204
        listed = (await client.get("/v1/follows/stories", headers=headers)).json()
        assert [row["story_id"] for row in listed] == [story.id]
        assert listed[0]["new_reports"] == 0

    async def test_following_twice_is_one_follow(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        story = await _story(session, await make_article(session, source, title="Summit opens"))
        await session.commit()
        headers = await make_beta_headers(session)

        for _ in range(2):
            await client.post("/v1/follows/stories", json={"story_id": story.id}, headers=headers)
        assert len((await client.get("/v1/follows/stories", headers=headers)).json()) == 1

    async def test_reports_arriving_after_the_last_look_count_as_new(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        first = await make_article(session, source, title="Summit opens")
        story = await _story(session, first)
        await session.commit()
        headers = await make_beta_headers(session)
        await client.post("/v1/follows/stories", json={"story_id": story.id}, headers=headers)

        later = await make_article(session, source, title="Summit agrees a fund")
        later.story_cluster_id = story.id
        later.fetched_at = datetime.now(UTC) + timedelta(minutes=5)
        await session.commit()

        listed = (await client.get("/v1/follows/stories", headers=headers)).json()
        assert listed[0]["new_reports"] == 1

        seen = await client.post(f"/v1/follows/stories/{story.id}/seen", headers=headers)
        assert seen.status_code == 204

    async def test_state_endpoint_says_whether_this_reader_follows(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        story = await _story(session, await make_article(session, source, title="Summit opens"))
        await session.commit()
        headers = await make_beta_headers(session)

        state = (await client.get(f"/v1/follows/stories/{story.id}", headers=headers)).json()
        assert state == {"following": False}
        await client.post("/v1/follows/stories", json={"story_id": story.id}, headers=headers)
        state = (await client.get(f"/v1/follows/stories/{story.id}", headers=headers)).json()
        assert state == {"following": True}

    async def test_unfollow(self, client: AsyncClient, session: AsyncSession) -> None:
        source = await make_source(session)
        story = await _story(session, await make_article(session, source, title="Summit opens"))
        await session.commit()
        headers = await make_beta_headers(session)
        await client.post("/v1/follows/stories", json={"story_id": story.id}, headers=headers)

        assert (
            await client.delete(f"/v1/follows/stories/{story.id}", headers=headers)
        ).status_code == 204
        assert (await client.get("/v1/follows/stories", headers=headers)).json() == []
        assert (
            await client.delete(f"/v1/follows/stories/{story.id}", headers=headers)
        ).status_code == 404

    async def test_unknown_story_is_404(self, client: AsyncClient, session: AsyncSession) -> None:
        headers = await make_beta_headers(session)
        response = await client.post(
            "/v1/follows/stories", json={"story_id": 999999}, headers=headers
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"

    async def test_marking_an_unfollowed_story_seen_is_404(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        story = await _story(session, await make_article(session, source, title="Summit opens"))
        await session.commit()
        headers = await make_beta_headers(session)
        response = await client.post(f"/v1/follows/stories/{story.id}/seen", headers=headers)
        assert response.status_code == 404

    async def test_requires_sign_in(self, client: AsyncClient) -> None:
        assert (await client.get("/v1/follows/stories")).status_code == 401

    async def test_followed_stories_are_in_the_data_export(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        story = await _story(session, await make_article(session, source, title="Summit opens"))
        await session.commit()
        headers = await make_beta_headers(session)
        await client.post("/v1/follows/stories", json={"story_id": story.id}, headers=headers)
        await client.post("/v1/follows/sources", json={"source_id": source.id}, headers=headers)

        body = (await client.get("/v1/me/export", headers=headers)).json()
        assert [row["story_id"] for row in body["story_follows"]] == [story.id]
        assert [row["source_id"] for row in body["source_follows"]] == [source.id]
