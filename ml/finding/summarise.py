"""The original code's results, out of its logs and into JSON.

    python ml/finding/summarise.py

`reproduce.sh train` tees the original code's output to
`results/<model>-<dataset>.log`, which is git-ignored because it is mostly
progress bars. This pulls out what RESULTS.md reports - the validation curve,
the best validation metrics and the test metrics - into
`results/original-<model>-<dataset>.json`, which is kept.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"
KEYS = ("AUC", "MRR", "nDCG@5", "nDCG@10")
NUMBER = r"([\d.]+)"
TABLE = (
    r"\| AUC \| MRR \| nDCG@5 \| nDCG@10 \|\n\| --- \| --- \| --- \| --- \|\n"
    + r"\| "
    + r" \| ".join([NUMBER] * 4)
    + r" \|"
)


def _metrics(values: tuple[str, ...]) -> dict[str, float]:
    return dict(zip(KEYS, map(float, values), strict=True))


def summarise(model: str, dataset: str) -> dict[str, object] | None:
    text = (RESULTS / f"{model}-{dataset}.log").read_text(errors="replace").replace("\r", "\n")
    curve = [
        {m.group(2): int(m.group(3)), "elapsed": m.group(1), **_metrics(m.groups()[3:])}
        for m in re.finditer(r"Time ([\d:]+), (epoch|round) (\d+), metrics:\n" + TABLE, text)
    ]
    best = re.search(r"Best metrics on validation set:\n" + TABLE, text)
    test = re.search(r"Metrics on test set:\n" + TABLE, text)
    if test is None:
        return None
    return {
        "model": f"{model} (original FINDING code at be9bb78 + porting.patch)",
        "dataset": dataset,
        "runs": 1,
        "validation": curve,
        "early_stopped": "Early stop." in text,
        "best_val": _metrics(best.groups()) if best else None,
        "test": _metrics(test.groups()),
    }


def main() -> None:
    for model in ("NRMS", "FindingNRMS"):
        summary = summarise(model, "adressa-1week")
        if summary is None:
            sys.stderr.write(f"{model}: no test result in its log yet\n")
            continue
        path = RESULTS / f"original-{model}-adressa-1week.json"
        path.write_text(json.dumps(summary, indent=2) + "\n")
        sys.stdout.write(f"{path.name}: test {json.dumps(summary['test'])}\n")


if __name__ == "__main__":
    main()
