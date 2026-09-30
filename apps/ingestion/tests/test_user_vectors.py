"""`justnews-ingest user-vectors` (ADR 0016), with a stand-in tower: the
job's own work - whose history, in what order, which group, what gets
written - is what is under test, not the model's arithmetic (ml/ tests that,
and the ONNX parity check at export)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import numpy as np
import numpy.typing as npt
from justnews_testing.factories import make_article, make_source
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.models import InteractionEvent, UserProfile, UserSave, UserVector
from justnews_ingestion.user_vectors import MIN_POSITIVES, Model, compute_user_vectors

NOW = datetime.now(UTC)


class FakeTower:
    """user = the mean of the history; each group adds its own offset, so a
    served vector says which group's head produced it."""

    def __init__(self) -> None:
        self.histories: list[npt.NDArray[np.bool_]] = []

    def user(self, history: np.ndarray, mask: npt.NDArray[np.bool_]) -> np.ndarray:
        self.histories.append(mask.copy())
        counts = np.maximum(mask.sum(axis=1, keepdims=True), 1)
        return (history * mask[..., None]).sum(axis=1) / counts

    def serving(self, group: int, history: np.ndarray, mask: npt.NDArray[np.bool_]) -> np.ndarray:
        return self.user(history, mask) + float(group)


def _model(tower: FakeTower) -> Model:
    # Two centroids far apart on the first axis; relabelled 0 <-> 1.
    centroids = np.zeros((2, 384), dtype=np.float32)
    centroids[0, 0], centroids[1, 0] = -10.0, 10.0
    return Model(
        version="test-v1",
        dimensions=384,
        history=4,
        centroids=centroids,
        relabel={0: 1, 1: 0},
        tower=tower,
    )


async def _reader(session: AsyncSession, reads: int, source) -> uuid.UUID:  # type: ignore[no-untyped-def]
    user_id = uuid.uuid4()
    session.add(UserProfile(id=user_id))
    await session.flush()
    for index in range(reads):
        article = await make_article(session, source, title=f"Read {index} by {user_id}")
        session.add(
            InteractionEvent(
                user_id=user_id,
                session_id="s",
                article_id=article.id,
                event_type="click",
                surface="feed",
                locale="en",
                created_at=NOW - timedelta(hours=reads - index),
            )
        )
    await session.flush()
    return user_id


class TestUserVectors:
    async def test_writes_a_vector_for_each_reader_with_enough_reads(
        self, session: AsyncSession
    ) -> None:
        source = await make_source(session)
        enough = await _reader(session, MIN_POSITIVES + 2, source)
        too_few = await _reader(session, MIN_POSITIVES - 1, source)
        await session.commit()

        summary = await compute_user_vectors(session, _model(FakeTower()), now=NOW)
        await session.commit()

        assert summary["readers"] == 2
        assert summary["written"] == 1
        rows = (await session.execute(select(UserVector))).scalars().all()
        assert [row.user_id for row in rows] == [enough]
        assert too_few not in [row.user_id for row in rows]
        assert rows[0].model_version == "test-v1"
        assert rows[0].history_count == 4  # capped at the model's history

    async def test_history_is_the_latest_reads_left_padded(self, session: AsyncSession) -> None:
        source = await make_source(session)
        await _reader(session, MIN_POSITIVES, source)
        await session.commit()
        tower = FakeTower()
        model = Model(
            version="t",
            dimensions=384,
            history=8,
            centroids=np.zeros((1, 384), dtype=np.float32),
            relabel={},
            tower=tower,
        )
        await compute_user_vectors(session, model, now=NOW, dry_run=True)
        mask = tower.histories[0][0]
        # Five reads in an eight-slot history: padding first, reads last.
        assert mask.tolist() == [False] * 3 + [True] * 5

    async def test_group_is_the_nearest_centroid_relabelled(self, session: AsyncSession) -> None:
        source = await make_source(session)
        user_id = await _reader(session, MIN_POSITIVES, source)
        await session.commit()
        await compute_user_vectors(session, _model(FakeTower()), now=NOW)
        await session.commit()
        row = (await session.execute(select(UserVector))).scalar_one()
        # Mean vectors sit near the origin - nearer centroid 1 or 0 depends
        # on the first axis; whichever it is, the stored group is relabelled.
        vector = np.asarray(row.vector.to_list() if hasattr(row.vector, "to_list") else row.vector)
        label = 0 if vector[0] - row.group_id < 0 else 1
        assert row.group_id == {0: 1, 1: 0}[label]
        assert row.user_id == user_id

    async def test_saves_count_and_a_rerun_updates_in_place(self, session: AsyncSession) -> None:
        source = await make_source(session)
        user_id = await _reader(session, MIN_POSITIVES - 1, source)
        saved = await make_article(session, source, title="Saved one")
        session.add(UserSave(user_id=user_id, article_id=saved.id, created_at=NOW))
        await session.commit()

        first = await compute_user_vectors(session, _model(FakeTower()), now=NOW)
        await session.commit()
        second = await compute_user_vectors(session, _model(FakeTower()), now=NOW)
        await session.commit()
        assert first["written"] == second["written"] == 1
        assert len((await session.execute(select(UserVector))).all()) == 1

    async def test_dry_run_writes_nothing(self, session: AsyncSession) -> None:
        source = await make_source(session)
        await _reader(session, MIN_POSITIVES, source)
        await session.commit()
        summary = await compute_user_vectors(session, _model(FakeTower()), now=NOW, dry_run=True)
        assert summary["written"] == 0
        assert (await session.execute(select(UserVector))).first() is None
