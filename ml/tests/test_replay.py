"""The offline replay (jnfinding/replay.py) on a hand-built export."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from jnfinding.replay import load_export, replay


class MeanTower:
    """Serves the mean of the history: whatever the reader read, ranked by."""

    history = 4

    def user(self, history, mask):  # type: ignore[no-untyped-def]
        return (history * mask[..., None]).sum(axis=1) / np.maximum(
            mask.sum(axis=1, keepdims=True), 1
        )

    def serving(self, group, history, mask):  # type: ignore[no-untyped-def]
        return self.user(history, mask)

    def group_of(self, user):  # type: ignore[no-untyped-def]
        return 0


def _write(directory: Path, impressions: list[list[object]], reads: list[list[object]]) -> None:
    columns = [
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
    with (directory / "impressions.tsv").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(columns)
        writer.writerows(impressions)
    with (directory / "reads.tsv").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["reader", "article", "kind", "at"])
        writer.writerows(reads)
    vectors = np.zeros((4, 384), dtype=np.float32)
    vectors[0, 0] = vectors[1, 0] = 1.0  # 1 and 2: the reader's kind of story
    vectors[1, 1] = 0.1
    vectors[2, 2] = 1.0  # 3: something else
    vectors[3, 0] = 1.0
    np.save(directory / "vectors.npy", vectors)
    np.save(directory / "article_ids.npy", np.array([1, 2, 3, 4]))


def test_scores_seen_cards_three_ways(tmp_path: Path) -> None:
    t0, t1, t2 = "2026-09-30T10:00:00", "2026-09-30T11:00:00", "2026-09-30T12:00:00"
    _write(
        tmp_path,
        impressions=[
            # Page 0: v2 put the story unlike the reader's first; they opened the other.
            [0, 0, 3, 0, 0, "lead", 0.6, "heuristic_v2", "feed", 1, 0, t1],
            [0, 0, 2, 1, 1, "card", 0.4, "heuristic_v2", "feed", 1, 1, t1],
            [0, 0, 4, 2, "", "", 0.2, "heuristic_v2", "feed", 0, 0, t1],  # never seen
            # Page 1: nothing opened - says nothing.
            [1, 0, 3, 0, 0, "lead", 0.5, "heuristic_v2", "feed", 1, 0, t2],
        ],
        reads=[[0, 1, "click", t0], [0, 2, "click", t1 + "1"]],  # the second read is after page 0
    )
    report = replay(load_export(tmp_path), MeanTower())  # type: ignore[arg-type]
    results = report["results"]
    assert report["skipped"] == {"no contrast": 1}
    assert results["served"]["AUC"] == 0.0
    assert results["profile"]["AUC"] == 1.0
    assert results["finding"]["AUC"] == 1.0
    assert results["finding"]["impressions"] == 1.0


def test_a_reader_with_no_earlier_reads_is_skipped(tmp_path: Path) -> None:
    _write(
        tmp_path,
        impressions=[
            [0, 0, 3, 0, 0, "lead", 0.6, "heuristic_v2", "feed", 1, 0, "2026-09-30T11:00:00"],
            [0, 0, 2, 1, 1, "card", 0.4, "heuristic_v2", "feed", 1, 1, "2026-09-30T11:00:00"],
        ],
        reads=[[0, 1, "click", "2026-09-30T12:00:00"]],
    )
    report = replay(load_export(tmp_path), MeanTower())  # type: ignore[arg-type]
    assert report["skipped"] == {"too little history": 1}
    assert report["results"] == {}
