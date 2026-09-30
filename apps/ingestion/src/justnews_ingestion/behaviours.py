"""Consented logs, exported for the offline replay (ADR 0016): the
"simulated clients replayed from production logs" FINDING trains and is
judged on (CLAUDE.md's honesty constraint).

`justnews-ingest export-behaviours --out DIR` writes:
- `impressions.tsv`: one row per served card - page, reader, article, served
  position, where it was drawn and in what shape, the probability the policy
  had of placing it, the policy, the surface, and whether it was seen and
  opened;
- `reads.tsv`: every positive read (open, share, save) - reader, article,
  kind, when - from which a reader's history before any page is rebuilt;
- `vectors.npy` and `article_ids.npy`: the stored vector of every article in
  either file.

Readers are numbered in the export, never written by account id or session
id; the mapping is not kept. Only rows that exist were consented to - no
impression or event is logged without analytics consent - and nothing here
is an article's text.
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import and_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.db import set_job
from justnews_core.models import Article, Impression, ImpressionView, InteractionEvent, UserSave

JOB = "export-behaviours"
DEFAULT_WINDOW = timedelta(days=90)


IMPRESSION_COLUMNS = [
    "page",
    "reader",
    "article",
    "position",
    "rendered_position",
    "slot",
    "propensity",
    "policy",
    "surface",
    "viewed",
    "clicked",
    "served_at",
]


def _write(
    out: Path,
    impressions: list[list[object]],
    reads: list[list[object]],
    vectors: np.ndarray,
    ids: list[int],
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with (out / "impressions.tsv").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(IMPRESSION_COLUMNS)
        writer.writerows(impressions)
    with (out / "reads.tsv").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["reader", "article", "kind", "at"])
        writer.writerows(reads)
    np.save(out / "vectors.npy", vectors)
    np.save(out / "article_ids.npy", np.asarray(ids, dtype=np.int64))


def _who(user_id: Any, session_id: str) -> str:
    return f"u:{user_id}" if user_id is not None else f"s:{session_id}"


async def export_behaviours(
    session: AsyncSession,
    out: Path,
    *,
    now: datetime | None = None,
    window: timedelta = DEFAULT_WINDOW,
) -> dict[str, int]:
    now = now or datetime.now(UTC)
    since = now - window
    await set_job(session, JOB)

    clicked = exists().where(
        and_(
            InteractionEvent.impression_id == Impression.id,
            InteractionEvent.event_type == "click",
        )
    )
    impressions = (
        await session.execute(
            select(
                Impression.user_id,
                Impression.session_id,
                Impression.served_at,
                Impression.surface,
                Impression.ranking_policy,
                Impression.article_id,
                Impression.position,
                Impression.propensity,
                ImpressionView.rendered_position,
                ImpressionView.slot,
                clicked.label("clicked"),
            )
            .outerjoin(ImpressionView, ImpressionView.impression_id == Impression.id)
            .where(Impression.served_at > since)
            .order_by(Impression.served_at, Impression.position)
        )
    ).all()
    events = (
        await session.execute(
            select(
                InteractionEvent.user_id,
                InteractionEvent.session_id,
                InteractionEvent.article_id,
                InteractionEvent.event_type,
                InteractionEvent.created_at,
            ).where(
                InteractionEvent.event_type.in_(("click", "share")),
                InteractionEvent.created_at > since,
            )
        )
    ).all()
    saves = (
        await session.execute(
            select(UserSave.user_id, UserSave.article_id, UserSave.created_at).where(
                UserSave.created_at > since
            )
        )
    ).all()

    readers: dict[str, int] = {}
    pages: dict[tuple[str, str, str], int] = {}

    def reader(key: str) -> int:
        return readers.setdefault(key, len(readers))

    impression_rows: list[list[object]] = []
    articles: set[int] = set()
    for row in impressions:
        who = _who(row.user_id, row.session_id)
        page = pages.setdefault((who, row.served_at.isoformat(), row.surface), len(pages))
        articles.add(row.article_id)
        impression_rows.append(
            [
                page,
                reader(who),
                row.article_id,
                row.position,
                "" if row.rendered_position is None else row.rendered_position,
                row.slot or "",
                f"{row.propensity:.6g}",
                row.ranking_policy,
                row.surface,
                int(row.rendered_position is not None),
                int(bool(row.clicked)),
                row.served_at.isoformat(),
            ]
        )
    reads = [
        (_who(e.user_id, e.session_id), e.article_id, e.event_type, e.created_at) for e in events
    ] + [(_who(s.user_id, ""), s.article_id, "save", s.created_at) for s in saves]
    reads.sort(key=lambda item: item[3])
    read_rows: list[list[object]] = []
    for who, article_id, kind, at in reads:
        articles.add(article_id)
        read_rows.append([reader(who), article_id, kind, at.isoformat()])

    ids = sorted(articles)
    matrix = np.zeros((len(ids), 384), dtype=np.float32)
    if ids:
        found = await session.execute(
            select(Article.id, Article.embedding).where(Article.id.in_(ids))
        )
        index = {article_id: i for i, article_id in enumerate(ids)}
        for article_id, embedding in found.all():
            if embedding is not None:
                raw = embedding.to_numpy() if hasattr(embedding, "to_numpy") else embedding
                matrix[index[article_id]] = np.asarray(raw, dtype=np.float32)
    _write(out, impression_rows, read_rows, matrix, ids)
    return {
        "impressions": len(impressions),
        "pages": len(pages),
        "reads": len(reads),
        "readers": len(readers),
        "articles": len(ids),
    }
