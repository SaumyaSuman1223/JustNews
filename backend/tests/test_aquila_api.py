"""Integration tests for serving The Aquila Tribune.

Serving is a keyed read of frozen rows, so the interesting cases are the
edges: no issue yet, the flag off, a taken-down article inside a published
paper, and whether impressions land under the right surface and policy.
"""

from __future__ import annotations

from datetime import UTC, datetime

from httpx import AsyncClient
from justnews_testing.factories import make_article, make_source, make_topic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import Article, ArticleTopic, FeatureFlag, Impression, IssueSlot
from justnews_ingestion.aquila import compose_issue

POLITICS = "medtop:11000000"
CONSENT = {"x-analytics-consent": "granted", "x-session-id": "sess-aquila"}


async def _published_issue(session: AsyncSession, *, locale: str = "en") -> int:
    """A real composed issue, so the tests read what the composer writes."""
    topic = await make_topic(session, topic_id=POLITICS, slug="politics")
    sources = [await make_source(session, slug=f"aq-{i}") for i in range(4)]
    for i in range(24):
        article = await make_article(
            session, sources[i % 4], title=f"Story {i}", language=locale, minutes_ago=i * 2
        )
        if i % 2 == 0:
            session.add(ArticleTopic(article_id=article.id, topic_id=topic.id, is_primary=True))
    await session.commit()

    result = await compose_issue(session, locale=locale, edition_slot="morning")
    await session.commit()
    assert result.issue_id is not None
    return result.issue_id


class TestLatestIssue:
    async def test_returns_the_masthead_and_contents(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        issue_id = await _published_issue(session)

        response = await client.get("/v1/issues/latest", params={"locale": "en"})
        assert response.status_code == 200
        body = response.json()

        assert body["id"] == issue_id
        assert body["edition_slot"] == "morning"
        assert body["volume"] >= 1 and body["number"] >= 1
        assert body["page_count"] == len(body["sections"])
        assert body["sections"][0]["page_no"] == 1
        assert body["sections"][0]["title"] is None, (
            "the front page has a masthead, not a section head"
        )
        # No article content: a page is its own request.
        assert "slots" not in body

    async def test_no_issue_yet_is_null_not_an_error(self, client: AsyncClient) -> None:
        """A publication that has not published is a real state, not a fault."""
        response = await client.get("/v1/issues/latest", params={"locale": "en"})
        assert response.status_code == 200
        assert response.json() is None

    async def test_section_pages_are_named_in_the_requested_locale(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        await _published_issue(session)

        english = (await client.get("/v1/issues/latest", params={"locale": "en"})).json()
        sections = [s for s in english["sections"] if s["topic_id"] == POLITICS]
        assert sections, "the politics page should exist"
        assert sections[0]["title"], "a section page carries its IPTC label, not a stored string"

    async def test_rejects_a_bad_locale(self, client: AsyncClient) -> None:
        # "not-a-language" would pass: normalise_language_code takes the
        # primary subtag, so it resolves to "not". A value with no language
        # subtag at all is what actually has to be rejected.
        response = await client.get("/v1/issues/latest", params={"locale": "!!"})
        assert response.status_code == 422


class TestIssuePage:
    async def test_serves_a_page_with_its_articles(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        issue_id = await _published_issue(session)

        response = await client.get(f"/v1/issues/{issue_id}/pages/1", params={"locale": "en"})
        assert response.status_code == 200
        body = response.json()

        assert body["page_no"] == 1
        assert body["slots"], "the front page should not be empty"
        roles = [slot["role"] for slot in body["slots"]]
        assert roles.count("lead") == 1
        positions = [slot["position"] for slot in body["slots"]]
        assert positions == sorted(positions), "slots arrive in reading order"
        assert body["slots"][0]["article"]["title"]

    async def test_missing_page_is_404(self, client: AsyncClient, session: AsyncSession) -> None:
        issue_id = await _published_issue(session)
        response = await client.get(f"/v1/issues/{issue_id}/pages/99", params={"locale": "en"})
        assert response.status_code == 404

    async def test_missing_issue_is_404(self, client: AsyncClient) -> None:
        assert (await client.get("/v1/issues/999999/pages/1")).status_code == 404

    async def test_impressions_are_logged_under_the_aquila_surface(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        issue_id = await _published_issue(session)

        response = await client.get(
            f"/v1/issues/{issue_id}/pages/1", params={"locale": "en"}, headers=CONSENT
        )
        assert response.status_code == 200
        assert all(slot["impression_id"] is not None for slot in response.json()["slots"])

        rows = (await session.scalars(select(Impression))).all()
        assert rows, "a composed page is still a selection, and must be replayable"
        assert {row.surface for row in rows} == {"aquila"}
        assert {row.ranking_policy for row in rows} == {"aquila_issue_v1"}
        # Genuinely 1.0 here, unlike the sampled exploration deck: given the
        # issue, this article was shown in this position with certainty.
        assert {row.propensity for row in rows} == {1.0}

    async def test_without_consent_nothing_is_logged(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        issue_id = await _published_issue(session)

        response = await client.get(f"/v1/issues/{issue_id}/pages/1", params={"locale": "en"})
        assert response.status_code == 200
        assert all(slot["impression_id"] is None for slot in response.json()["slots"])
        assert (await session.scalars(select(Impression))).all() == []

    async def test_a_taken_down_article_leaves_the_page(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        """A takedown hides an article everywhere, including in a paper that
        was already printed. The slot stays - the issue is immutable - but
        the page renders without it."""
        issue_id = await _published_issue(session)
        lead_article_id = await session.scalar(
            select(IssueSlot.article_id).order_by(IssueSlot.position).limit(1)
        )
        article = await session.get(Article, lead_article_id)
        assert article is not None
        article.removed_at = datetime.now(UTC)
        article.removed_reason = "test takedown"
        await session.commit()

        body = (await client.get(f"/v1/issues/{issue_id}/pages/1", params={"locale": "en"})).json()
        served = [slot["article"]["id"] for slot in body["slots"]]
        assert lead_article_id not in served

        still_slotted = await session.scalar(
            select(IssueSlot.id).where(IssueSlot.article_id == lead_article_id)
        )
        assert still_slotted is not None, "the issue itself is immutable"


class TestPageReferences:
    """Third-pass audit §8/§46's "PAGE X": a front-page story whose own topic
    has a section page elsewhere in the same issue.

    Deliberately not "this article continues on page X" - the product stores
    no body text, so nothing continues anywhere, and CLAUDE.md forbids a
    fabricated "2-3 paragraphs of context" as much as it forbids storing the
    full article. What this points at instead is real: the front-page story's
    topic has its own page, and that page is genuinely fuller coverage of the
    same subject, the way a broadsheet's front-page teaser sends a reader to
    the section inside.
    """

    async def test_a_front_page_story_whose_topic_has_a_section_gets_a_page_ref(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        issue_id = await _published_issue(session)

        sections = (await client.get(f"/v1/issues/{issue_id}", params={"locale": "en"})).json()[
            "sections"
        ]
        politics_page = next((s["page_no"] for s in sections if s["topic_id"] == POLITICS), None)
        assert politics_page is not None, "the fixture tags enough articles for its own page"

        front = (await client.get(f"/v1/issues/{issue_id}/pages/1", params={"locale": "en"})).json()
        politics_article_ids = set(
            (
                await session.scalars(
                    select(ArticleTopic.article_id).where(
                        ArticleTopic.topic_id == POLITICS, ArticleTopic.is_primary.is_(True)
                    )
                )
            ).all()
        )
        politics_slots_on_front = [
            slot for slot in front["slots"] if slot["article"]["id"] in politics_article_ids
        ]
        assert politics_slots_on_front, "at least one Politics story should have led the front page"
        for slot in politics_slots_on_front:
            assert slot["page_ref"] == politics_page

    async def test_a_topic_with_no_section_page_gets_no_reference(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # A single-source, single-topic corpus: the topic prints nowhere, so
        # nothing on the front page should claim a page it does not have.
        source = await make_source(session, slug="no-section")
        for i in range(20):
            await make_article(session, source, title=f"Untagged {i}", minutes_ago=i)
        await session.commit()

        result = await compose_issue(session, locale="en", edition_slot="morning")
        await session.commit()
        assert result.issue_id is not None

        front = (
            await client.get(f"/v1/issues/{result.issue_id}/pages/1", params={"locale": "en"})
        ).json()
        assert front["slots"], "the front page should not be empty"
        assert all(slot["page_ref"] is None for slot in front["slots"])

    async def test_section_page_slots_never_carry_a_page_ref(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        # A cross-reference points *from* the front page *to* a section - a
        # section page referencing another page would be the paper pointing
        # at itself, which is not what this feature is for.
        issue_id = await _published_issue(session)
        sections = (await client.get(f"/v1/issues/{issue_id}", params={"locale": "en"})).json()[
            "sections"
        ]
        section_pages = [s["page_no"] for s in sections if s["page_no"] != 1]
        assert section_pages, "the fixture composes at least one section page"

        for page_no in section_pages:
            body = (
                await client.get(f"/v1/issues/{issue_id}/pages/{page_no}", params={"locale": "en"})
            ).json()
            assert all(slot["page_ref"] is None for slot in body["slots"])


class TestEditions:
    async def test_lists_the_days_editions(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        await _published_issue(session)
        second = await compose_issue(session, locale="en", edition_slot="midday")
        await session.commit()
        assert second.issue_id is not None

        response = await client.get("/v1/issues", params={"locale": "en"})
        assert response.status_code == 200
        slots = [row["edition_slot"] for row in response.json()]
        assert slots == ["morning", "midday"], "earliest first, so the selector reads as a day"

    async def test_empty_when_nothing_has_published(self, client: AsyncClient) -> None:
        assert (await client.get("/v1/issues", params={"locale": "en"})).json() == []


class TestKillSwitch:
    async def test_flag_off_hides_aquila_entirely(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        issue_id = await _published_issue(session)
        session.add(FeatureFlag(key="aquila", enabled=False, description="off for this test"))
        await session.commit()

        assert (await client.get("/v1/issues/latest", params={"locale": "en"})).json() is None
        assert (await client.get("/v1/issues", params={"locale": "en"})).json() == []
        assert (await client.get(f"/v1/issues/{issue_id}/pages/1")).status_code == 404
