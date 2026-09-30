"""Part B: FINDING's user tower over JustNews's frozen encoder.

    cd ml/finding
    uv run --project .. python -m jnfinding.train embed adressa-1week
    uv run --project .. python -m jnfinding.train centralised adressa-1week
    uv run --project .. python -m jnfinding.train finding adressa-1week

`embed` writes the headline vectors (the production encoder, frozen);
`centralised` trains the tower the ordinary way - the paper's baseline;
`finding` trains it with FINDING's procedure. Both judge by validation AUC
(early stopping, patience 3, as the paper's code does), report the test
split with the best validation state, and write the result to
`finding/results/` and the model to `ml/data/checkpoints/`.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from jnfinding import data, trainer

ML = Path(__file__).resolve().parents[2]
DATA = ML / "data" / "finding"
RESULTS = ML / "finding" / "results"
CHECKPOINTS = ML / "data" / "checkpoints"


def _paths(dataset: str) -> dict[str, Path]:
    root = DATA / dataset
    return {
        "root": root,
        "vectors": root / "news_vectors.npy",
        "train": root / "train.tsv",
        "val": root / "val.tsv",
        "test": root / "test.tsv",
        "news2int": root / "news2int.tsv",
    }


def embed(dataset: str) -> None:
    paths = _paths(dataset)
    count = len(pd.read_table(paths["news2int"])) + 1
    if dataset.startswith("adressa"):
        titles = data.adressa_titles(DATA / "raw" / f"{dataset}-clean", paths["news2int"])
    else:
        raise SystemExit(f"no headline source for {dataset}")
    matrix = data.embed_titles(titles, count)
    np.save(paths["vectors"], matrix)
    sys.stdout.write(
        str(f"{len(titles)} of {count - 1} headlines embedded -> {paths['vectors']}") + "\n"
    )


def _load(dataset: str, device: torch.device):  # type: ignore[no-untyped-def]
    paths = _paths(dataset)
    news = torch.as_tensor(np.load(paths["vectors"]), device=device)
    train = data.load_behaviours(paths["train"])
    val = data.load_behaviours(paths["val"])
    test = data.load_behaviours(paths["test"])
    samples = data.training_samples(train, len(news), k=4)
    return news, train, val, test, samples


def _write(name: str, payload: dict[str, object]) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{name}.json").write_text(json.dumps(payload, indent=2, default=str) + "\n")
    sys.stdout.write(json.dumps(payload, indent=2, default=str) + "\n")


def _suffix(seed: int) -> str:
    """Seed 0 keeps the unsuffixed names the first runs were written under."""
    return "" if seed == 0 else f"-seed{seed}"


def centralised(dataset: str, device: torch.device, seed: int = 0) -> None:
    news, train, val, test, samples = _load(dataset, device)
    started = time.time()
    model, best_val, log = trainer.train_centralised(news, train, samples, val, device, seed=seed)
    everyone = np.zeros(len(test), dtype=np.int64)
    test_report = trainer.score_impressions({0: model}, everyone, news, test, device)
    CHECKPOINTS.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), CHECKPOINTS / f"tower-centralised-{dataset}{_suffix(seed)}.pt")
    _write(
        f"tower-centralised-{dataset}{_suffix(seed)}",
        {
            "model": "UserTower (frozen MiniLM news vectors), centralised",
            "dataset": dataset,
            "seed": seed,
            "train_samples": len(samples),
            "val": best_val.as_dict(),
            "test": test_report.as_dict(),
            "minutes": round((time.time() - started) / 60, 1),
            "log": log,
        },
    )


def finding(dataset: str, device: torch.device, rounds: int | None, seed: int = 0) -> None:
    news, train, val, test, samples = _load(dataset, device)
    config = (
        trainer.Config(seed=seed) if rounds is None else trainer.Config(rounds=rounds, seed=seed)
    )
    model = trainer.Finding(config, news, train, samples, device)
    started = time.time()
    best: tuple[float, dict[str, object], dict[str, float]] | None = None
    waited = 0
    log: list[str] = []
    for round_ in range(config.rounds):
        loss = model.round(round_)
        if round_ and round_ % config.validate_every == 0:
            report = model.evaluate(val)
            line = f"round {round_} loss {loss:.4f} val {report.as_dict()}"
            log.append(line)
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
            if best is None or report.auc > best[0]:
                best, waited = (report.auc, model.state(), report.as_dict()), 0
            else:
                waited += 1
                if waited >= config.patience:
                    log.append(f"early stop at round {round_}")
                    break
    assert best is not None
    state = best[1]
    model.global_model.load_state_dict(state["global"])  # type: ignore[arg-type]
    for group, weights in zip(model.groups, state["groups"], strict=True):  # type: ignore[arg-type]
        group.model.load_state_dict(weights)
    model.kmeans.cluster_centers_ = state["centroids"]  # type: ignore[assignment]
    model.relabel = state["relabel"]  # type: ignore[assignment]
    personal = model.evaluate(test)
    shared = model.evaluate(test, personal=False)
    CHECKPOINTS.mkdir(parents=True, exist_ok=True)
    torch.save(state, CHECKPOINTS / f"tower-finding-{dataset}{_suffix(seed)}.pt")
    _write(
        f"tower-finding-{dataset}{_suffix(seed)}",
        {
            "model": "UserTower (frozen MiniLM news vectors), FINDING",
            "dataset": dataset,
            "config": dataclasses.asdict(config),
            "train_samples": len(samples),
            "val": best[2],
            "test_group_models": personal.as_dict(),
            "test_global_model": shared.as_dict(),
            "minutes": round((time.time() - started) / 60, 1),
            "log": log,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["embed", "centralised", "finding"])
    parser.add_argument("dataset")
    parser.add_argument("--rounds", type=int, default=None)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    if args.command == "embed":
        embed(args.dataset)
    elif args.command == "centralised":
        centralised(args.dataset, device, args.seed)
    else:
        finding(args.dataset, device, args.rounds, args.seed)


if __name__ == "__main__":
    main()
