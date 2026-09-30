"""A trained FINDING tower, as ONNX files the user-vector job can run
(ADR 0016). Only these files and the vectors the job writes cross from ml/
into the app (CLAUDE.md: apps/ never imports ml/).

    uv run --project .. python -m jnfinding.export adressa-1week --version finding-v1-adressa

Writes `ml/export/<version>/`:
- `global.onnx`: (history, mask) -> the global model's user vector, which
  assigns a reader their group (nearest centroid, as KMeans predicts);
- `group_<k>.onnx`: (history, mask) -> that group's serving vector, Wᵀu,
  ranked against raw article vectors by a dot product;
- `meta.json`: version, sizes, the centroids and the group relabelling.

Every file is checked against PyTorch on random histories before meta.json
is written - a model whose export disagrees with itself never ships.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import numpy as np
import onnxruntime
import torch
from torch import nn

from jnfinding.model import UserTower

ML = Path(__file__).resolve().parents[2]
TOLERANCE = 1e-4


class _Head(nn.Module):
    def __init__(self, tower: UserTower, output: Literal["user", "serving"]) -> None:
        super().__init__()
        self.tower, self.output = tower, output

    def forward(self, history: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        if self.output == "user":
            return self.tower.user(history, mask)
        return self.tower.serving_vector(history, mask)


def export_tower(
    tower: UserTower, path: Path, output: Literal["user", "serving"], *, history: int = 50
) -> float:
    """Writes one ONNX file and returns its largest difference from PyTorch."""
    head = _Head(tower, output).eval()
    dim = tower.news_adapter.in_features
    example = (torch.randn(2, history, dim), torch.ones(2, history, dtype=torch.bool))
    torch.onnx.export(
        head,
        example,
        str(path),
        input_names=["history", "mask"],
        output_names=["vector"],
        dynamic_axes={"history": {0: "batch"}, "mask": {0: "batch"}, "vector": {0: "batch"}},
        opset_version=17,
        dynamo=False,
    )
    return parity(head, path, history=history, dim=dim)


@torch.no_grad()
def parity(head: nn.Module, path: Path, *, history: int, dim: int) -> float:
    rng = np.random.default_rng(0)
    session = onnxruntime.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    worst = 0.0
    cases = [(batch, filled) for batch in (1, 3) for filled in (history, 5, 1, 0)]
    for batch, filled in cases:  # one reader and several; full, short, one item, none
        vectors = rng.normal(size=(batch, history, dim)).astype(np.float32)
        mask = np.zeros((batch, history), dtype=bool)
        if filled:
            mask[:, -filled:] = True
        vectors[~mask] = 0.0
        expected = head(torch.from_numpy(vectors), torch.from_numpy(mask)).numpy()
        (actual,) = session.run(None, {"history": vectors, "mask": mask})
        worst = max(worst, float(np.abs(expected - actual).max()))
    return worst


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset")
    parser.add_argument("--version", required=True)
    args = parser.parse_args()

    state = torch.load(
        ML / "data" / "checkpoints" / f"tower-finding-{args.dataset}.pt", weights_only=False
    )
    out = ML / "export" / args.version
    out.mkdir(parents=True, exist_ok=True)
    history = state["config"].history

    global_tower = UserTower()
    global_tower.load_state_dict(state["global"])
    differences = {
        "global": export_tower(global_tower, out / "global.onnx", "user", history=history)
    }
    for index, weights in enumerate(state["groups"]):
        tower = UserTower()
        tower.load_state_dict(weights)
        differences[f"group_{index}"] = export_tower(
            tower, out / f"group_{index}.onnx", "serving", history=history
        )
    failed = {name: diff for name, diff in differences.items() if diff > TOLERANCE}
    if failed:
        raise SystemExit(f"ONNX disagrees with PyTorch beyond {TOLERANCE}: {failed}")

    meta = {
        "version": args.version,
        "trained_on": args.dataset,
        "created_at": datetime.now(UTC).isoformat(),
        "dimensions": int(global_tower.news_adapter.in_features),
        "history": history,
        "groups": len(state["groups"]),
        "centroids": np.asarray(state["centroids"]).tolist(),
        # KMeans label -> group index; empty means labels are group indexes.
        "relabel": {str(k): int(v) for k, v in state["relabel"].items()},
        "parity": differences,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    sys.stdout.write(
        str(json.dumps({k: v for k, v in meta.items() if k != "centroids"}, indent=2)) + "\n"
    )


if __name__ == "__main__":
    main()
