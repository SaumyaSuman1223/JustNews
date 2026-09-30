"""Every active reader's vector from the FINDING user tower (ADR 0016).

`justnews-ingest user-vectors --model-dir DIR` runs the exported ONNX model
(ml/finding/jnfinding/export.py) offline, over each reader's recent opens,
shares and saves, and writes one vector per reader to `user_vectors`. The
`finding_v1` ranking policy then ranks by a dot product with that vector -
a forward pass on a schedule, never in a request (ADR 0004). This module
reads the model's files and nothing else from ml/ (CLAUDE.md).

Per reader:
1. their last `history` positive reads, oldest first, as the tower was
   trained (article vectors, left-padded);
2. the global model's user vector picks their group - the nearest centroid,
   as KMeans predicts, then the training run's relabelling;
3. that group's model gives the serving vector.

Readers with fewer than MIN_POSITIVES reads are skipped: a vector from two
clicks is noise, and ranker v2's own profile covers them. The job declares
itself (`app.job`) so the policies of migration 0021 let it read across
readers - it never reads anything else.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import numpy.typing as npt
from sqlalchemy import func, select, union
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from justnews_core.db import set_job
from justnews_core.logging import get_logger
from justnews_core.models import Article, InteractionEvent, UserSave, UserVector

log = get_logger(__name__)

JOB = "user-vectors"
MIN_POSITIVES = 5
WINDOW = timedelta(days=30)
BATCH = 256

Vectors = npt.NDArray[np.float32]


class Tower(Protocol):
    """The exported model: the global head assigns groups, each group's
    head gives the vector served."""

    def user(self, history: Vectors, mask: npt.NDArray[np.bool_]) -> Vectors: ...

    def serving(self, group: int, history: Vectors, mask: npt.NDArray[np.bool_]) -> Vectors: ...


@dataclass(frozen=True, slots=True)
class Model:
    version: str
    dimensions: int
    history: int
    centroids: Vectors
    relabel: dict[int, int]
    tower: Tower

    def groups_of(self, users: Vectors) -> npt.NDArray[np.int64]:
        """Nearest centroid by Euclidean distance (KMeans.predict), relabelled
        as the training run left its groups."""
        distances = ((users[:, None, :] - self.centroids[None, :, :]) ** 2).sum(axis=2)
        labels = distances.argmin(axis=1)
        return np.array([self.relabel.get(int(label), int(label)) for label in labels])


class OnnxTower:
    """The exported ONNX files, run with onnxruntime (the `finding` extra)."""

    def __init__(self, directory: Path, groups: int) -> None:
        import onnxruntime

        options = {"providers": ["CPUExecutionProvider"]}
        self._global = onnxruntime.InferenceSession(str(directory / "global.onnx"), **options)
        self._groups = [
            onnxruntime.InferenceSession(str(directory / f"group_{index}.onnx"), **options)
            for index in range(groups)
        ]

    def user(self, history: Vectors, mask: npt.NDArray[np.bool_]) -> Vectors:
        (out,) = self._global.run(None, {"history": history, "mask": mask})
        return np.asarray(out, dtype=np.float32)

    def serving(self, group: int, history: Vectors, mask: npt.NDArray[np.bool_]) -> Vectors:
        (out,) = self._groups[group].run(None, {"history": history, "mask": mask})
        return np.asarray(out, dtype=np.float32)


def load_model(directory: Path) -> Model:
    meta: dict[str, Any] = json.loads((directory / "meta.json").read_text())
    return Model(
        version=str(meta["version"]),
        dimensions=int(meta["dimensions"]),
        history=int(meta["history"]),
        centroids=np.asarray(meta["centroids"], dtype=np.float32),
        relabel={int(k): int(v) for k, v in meta.get("relabel", {}).items()},
        tower=OnnxTower(directory, int(meta["groups"])),
    )


def _as_array(value: Any) -> Vectors | None:
    if value is None:
        return None
    raw = value.to_numpy() if hasattr(value, "to_numpy") else value
    return np.asarray(raw, dtype=np.float32)


async def _readers(session: AsyncSession, since: datetime) -> list[Any]:
    events = select(InteractionEvent.user_id.label("user_id")).where(
        InteractionEvent.user_id.is_not(None),
        InteractionEvent.event_type.in_(("click", "share")),
        InteractionEvent.created_at > since,
    )
    saves = select(UserSave.user_id.label("user_id")).where(UserSave.created_at > since)
    both = union(events, saves).subquery()
    result = await session.execute(select(both.c.user_id).order_by(both.c.user_id))
    return list(result.scalars().all())


async def _history(
    session: AsyncSession, user_id: Any, *, since: datetime, limit: int
) -> list[int]:
    """The reader's positive reads in the window, oldest first, the last
    `limit` of them, each article once (its latest read)."""
    events = select(
        InteractionEvent.article_id.label("article_id"),
        InteractionEvent.created_at.label("at"),
    ).where(
        InteractionEvent.user_id == user_id,
        InteractionEvent.event_type.in_(("click", "share")),
        InteractionEvent.created_at > since,
    )
    saves = select(UserSave.article_id.label("article_id"), UserSave.created_at.label("at")).where(
        UserSave.user_id == user_id, UserSave.created_at > since
    )
    reads = union(events, saves).subquery()
    latest = (
        select(reads.c.article_id, func.max(reads.c.at).label("at"))
        .group_by(reads.c.article_id)
        .order_by(func.max(reads.c.at).desc())
        .limit(limit)
    )
    rows = (await session.execute(latest)).all()
    return [row[0] for row in reversed(rows)]


async def compute_user_vectors(
    session: AsyncSession,
    model: Model,
    *,
    now: datetime | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    since = now - WINDOW
    await set_job(session, JOB)
    readers = await _readers(session, since)

    histories: list[tuple[Any, list[int]]] = []
    for user_id in readers:
        histories.append(
            (
                user_id,
                await _history(
                    session, user_id, since=since, limit=max(model.history, MIN_POSITIVES)
                ),
            )
        )
    needed = sorted({article for _user, ids in histories for article in ids})
    vectors: dict[int, Vectors] = {}
    if needed:
        result = await session.execute(
            select(Article.id, Article.embedding).where(Article.id.in_(needed))
        )
        for article_id, embedding in result.all():
            array = _as_array(embedding)
            if array is not None and array.shape[0] == model.dimensions:
                vectors[article_id] = array

    usable = [(user_id, [vectors[a] for a in ids if a in vectors]) for user_id, ids in histories]
    usable = [(user_id, items) for user_id, items in usable if len(items) >= MIN_POSITIVES]

    written = 0
    groups_seen: dict[int, int] = {}
    for start in range(0, len(usable), BATCH):
        chunk = usable[start : start + BATCH]
        history = np.zeros((len(chunk), model.history, model.dimensions), dtype=np.float32)
        mask = np.zeros((len(chunk), model.history), dtype=bool)
        for row, (_user, items) in enumerate(chunk):
            items = items[-model.history :]
            history[row, -len(items) :] = np.stack(items)
            mask[row, -len(items) :] = True
        groups = model.groups_of(model.tower.user(history, mask))
        served = np.zeros((len(chunk), model.dimensions), dtype=np.float32)
        for group in np.unique(groups).tolist():
            rows = np.flatnonzero(groups == group)
            served[rows] = model.tower.serving(group, history[rows], mask[rows])
            groups_seen[group] = groups_seen.get(group, 0) + len(rows)
        if dry_run:
            continue
        for row, (user_id, items) in enumerate(chunk):
            values = {
                "user_id": user_id,
                "model_version": model.version,
                "group_id": int(groups[row]),
                "vector": served[row].tolist(),
                "history_count": min(len(items), model.history),
                "computed_at": now,
            }
            await session.execute(
                insert(UserVector)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=[UserVector.user_id],
                    set_={k: v for k, v in values.items() if k != "user_id"},
                )
            )
            written += 1

    summary = {
        "model_version": model.version,
        "readers": len(readers),
        "with_enough_history": len(usable),
        "written": written,
        "groups": {str(k): v for k, v in sorted(groups_seen.items())},
        "dry_run": dry_run,
    }
    log.info("user_vectors_computed", **summary)
    return summary
