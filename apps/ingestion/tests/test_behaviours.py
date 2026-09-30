"""`justnews-ingest export-behaviours` (ADR 0016): what the offline replay
reads, and that no account or session id leaves in it."""

from __future__ import annotations

import csv
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from justnews_testing.factories import make_article, make_source
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import Impression, ImpressionView, InteractionEvent, UserProfile
from justnews_ingestion.behaviours import export_behaviours

NOW = datetime.now(UTC)


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open() as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


async def test_exports_seen_and_opened_cards_under_numbered_readers(
    session: AsyncSession, tmp_path: Path
) -> None:
    source = await make_source(session)
    first = await make_article(session, source, title="Opened")
    second = await make_article(session, source, title="Scrolled past")
    third = await make_article(session, source, title="Never on screen")
    user_id = uuid.uuid4()
    session.add(UserProfile(id=user_id))
    await session.flush()
    served = NOW - timedelta(hours=1)
    impressions = []
    for position, article in enumerate((first, second, third)):
        row = Impression(
            user_id=user_id,
            session_id="sess-secret",
            article_id=article.id,
            position=position,
            surface="feed",
            locale="en",
            propensity=0.5,
            ranking_policy="heuristic_v2",
            served_at=served,
        )
        session.add(row)
        impressions.append(row)
    await session.flush()
    session.add(ImpressionView(impression_id=impressions[0].id, rendered_position=0, slot="lead"))
    session.add(ImpressionView(impression_id=impressions[1].id, rendered_position=1, slot="card"))
    session.add(
        InteractionEvent(
            user_id=user_id,
            session_id="sess-secret",
            article_id=first.id,
            impression_id=impressions[0].id,
            event_type="click",
            surface="feed",
            locale="en",
            created_at=served + timedelta(minutes=1),
        )
    )
    await session.commit()

    summary = await export_behaviours(session, tmp_path, now=NOW)
    assert summary == {"impressions": 3, "pages": 1, "reads": 1, "readers": 1, "articles": 3}

    rows = _rows(tmp_path / "impressions.tsv")
    assert [(r["viewed"], r["clicked"], r["slot"]) for r in rows] == [
        ("1", "1", "lead"),
        ("1", "0", "card"),
        ("0", "0", ""),
    ]
    assert {r["reader"] for r in rows} == {"0"}
    reads = _rows(tmp_path / "reads.tsv")
    assert [(r["reader"], r["article"], r["kind"]) for r in reads] == [
        ("0", str(first.id), "click")
    ]

    everything = (tmp_path / "impressions.tsv").read_text() + (tmp_path / "reads.tsv").read_text()
    assert str(user_id) not in everything and "sess-secret" not in everything

    vectors = np.load(tmp_path / "vectors.npy")
    assert vectors.shape == (3, 384) and np.abs(vectors).sum() > 0
