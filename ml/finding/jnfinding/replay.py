"""The offline replay (ADR 0016): would the FINDING tower have ranked
JustNews's own logged pages better than the ranker that served them?

    uv run --project .. python -m jnfinding.replay ../data/justnews ../export/<version>

Reads a `justnews-ingest export-behaviours` directory. For every logged page
with at least one card that was seen and opened and one that was seen and
not, it scores the seen cards three ways and judges each with the same
metrics (jnfinding/metrics.py):

- **served**: the order the logging policy actually served (ranker v2, or
  whichever policy the page names);
- **profile**: v2's similarity term alone - the cosine to the mean of the
  reader's earlier reads;
- **finding**: the FINDING tower's serving vector for that reader, from
  their reads before the page was served, as the user-vector job would
  have computed it.

Only seen cards count - a card below the fold was never a choice. The
reader's history is rebuilt from reads strictly before the page, so
nothing a model scores could have leaked from its own outcome.

This compares orderings of the pages that were served; it does not
estimate what readers would have clicked on pages that were never shown,
which needs the logged propensities and a slate estimator (metrics.snips)
once a candidate policy's own placement probabilities are computed.
"""

from __future__ import annotations

import argparse
import json
import sys
from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
import numpy.typing as npt
import pandas as pd

from jnfinding import metrics

Vectors = npt.NDArray[np.float32]


class Tower(Protocol):
    def user(self, history: Vectors, mask: npt.NDArray[np.bool_]) -> Vectors: ...

    def serving(self, group: int, history: Vectors, mask: npt.NDArray[np.bool_]) -> Vectors: ...


class OnnxTower:
    def __init__(self, directory: Path) -> None:
        import onnxruntime

        meta = json.loads((directory / "meta.json").read_text())
        self.history = int(meta["history"])
        self.centroids = np.asarray(meta["centroids"], dtype=np.float32)
        self.relabel = {int(k): int(v) for k, v in meta.get("relabel", {}).items()}
        providers = ["CPUExecutionProvider"]
        self._global = onnxruntime.InferenceSession(
            str(directory / "global.onnx"), providers=providers
        )
        self._groups = [
            onnxruntime.InferenceSession(str(directory / f"group_{k}.onnx"), providers=providers)
            for k in range(int(meta["groups"]))
        ]

    def user(self, history: Vectors, mask: npt.NDArray[np.bool_]) -> Vectors:
        return np.asarray(self._global.run(None, {"history": history, "mask": mask})[0])

    def serving(self, group: int, history: Vectors, mask: npt.NDArray[np.bool_]) -> Vectors:
        return np.asarray(self._groups[group].run(None, {"history": history, "mask": mask})[0])

    def group_of(self, user: Vectors) -> int:
        label = int(((self.centroids - user[None, :]) ** 2).sum(axis=1).argmin())
        return self.relabel.get(label, label)


@dataclass(frozen=True, slots=True)
class Export:
    impressions: pd.DataFrame
    reads: pd.DataFrame
    vectors: dict[int, Vectors]


def load_export(directory: Path) -> Export:
    impressions = pd.read_table(directory / "impressions.tsv", keep_default_na=False)
    reads = pd.read_table(directory / "reads.tsv")
    ids = np.load(directory / "article_ids.npy")
    matrix = np.load(directory / "vectors.npy")
    return Export(
        impressions=impressions,
        reads=reads,
        vectors={int(i): matrix[row] for row, i in enumerate(ids)},
    )


def _histories(reads: pd.DataFrame) -> dict[int, tuple[list[str], list[int]]]:
    by_reader: dict[int, tuple[list[str], list[int]]] = defaultdict(lambda: ([], []))
    for row in reads.sort_values("at").itertuples(index=False):
        times, articles = by_reader[int(row.reader)]
        times.append(str(row.at))
        articles.append(int(row.article))
    return by_reader


def replay(export: Export, tower: OnnxTower, *, min_history: int = 1) -> dict[str, object]:
    histories = _histories(export.reads)
    seen = export.impressions[export.impressions["viewed"] == 1]
    impressions: dict[str, list[tuple[list[int], list[float]]]] = defaultdict(list)
    skipped = defaultdict(int)
    for _page, rows in seen.groupby("page"):
        labels = rows["clicked"].astype(int).tolist()
        if not 0 < sum(labels) < len(labels):
            skipped["no contrast"] += 1
            continue
        reader = int(rows["reader"].iloc[0])
        served_at = str(rows["served_at"].iloc[0])
        times, articles = histories.get(reader, ([], []))
        before = articles[: bisect_left(times, served_at)]
        items = [export.vectors[a] for a in before if a in export.vectors][-tower.history :]
        if len(items) < min_history:
            skipped["too little history"] += 1
            continue
        candidates = np.stack(
            [export.vectors.get(int(a), np.zeros(384, np.float32)) for a in rows["article"]]
        )

        history = np.zeros((1, tower.history, 384), dtype=np.float32)
        mask = np.zeros((1, tower.history), dtype=bool)
        history[0, -len(items) :] = np.stack(items)
        mask[0, -len(items) :] = True
        group = tower.group_of(tower.user(history, mask)[0])
        finding = candidates @ tower.serving(group, history, mask)[0]

        mean = np.stack(items).mean(axis=0)
        norms = np.linalg.norm(candidates, axis=1) * max(float(np.linalg.norm(mean)), 1e-9)
        profile = (candidates @ mean) / np.maximum(norms, 1e-9)

        impressions["served"].append((labels, (-rows["position"].to_numpy(float)).tolist()))
        impressions["profile"].append((labels, profile.tolist()))
        impressions["finding"].append((labels, finding.tolist()))

    return {
        "pages": int(seen["page"].nunique()),
        "skipped": dict(skipped),
        "results": {name: metrics.evaluate(rows).as_dict() for name, rows in impressions.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("export", type=Path)
    parser.add_argument("model", type=Path)
    args = parser.parse_args()
    report = replay(load_export(args.export), OnnxTower(args.model))
    sys.stdout.write(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
