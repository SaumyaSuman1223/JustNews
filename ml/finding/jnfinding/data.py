"""Behaviours and news vectors.

Part B reads the same preprocessed splits Part A's original code wrote
(`reproduce.sh prepare`): `train.tsv`, `val.tsv` and `test.tsv`, one row per
reader and day, with the history left-padded with 0 and the day's clicked
and not-clicked candidates. Same readers, same days, same negatives - so the
two parts differ in their model, not their data.

News vectors come from the production encoder (paraphrase-multilingual-
MiniLM-L12-v2, 384 dimensions; ADR 0005) over each article's headline, the
way JustNews embeds its own (`embed_article_text`: title twice, then the
snippet). Row 0 is the padding article and stays zero.
"""

from __future__ import annotations

import ast
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pandas as pd

ENCODER = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@dataclass(frozen=True, slots=True)
class Behaviours:
    """One row per reader-day: `history` (R, H) news ids, left-padded with 0."""

    user: npt.NDArray[np.int64]
    history: npt.NDArray[np.int64]
    positives: list[list[int]]
    negatives: list[list[int]]

    def __len__(self) -> int:
        return len(self.user)


def load_behaviours(path: Path) -> Behaviours:
    table = pd.read_table(path)
    parse = ast.literal_eval
    return Behaviours(
        user=table["user"].to_numpy(dtype=np.int64),
        history=np.array([parse(x) for x in table["history"]], dtype=np.int64),
        positives=[parse(x) for x in table["positive_candidates"]],
        negatives=[parse(x) for x in table["negative_candidates"]],
    )


@dataclass(frozen=True, slots=True)
class Samples:
    """One training sample per click: the reader's row, the clicked article,
    and `k` of that day's not-clicked ones - FINDING's training set."""

    row: npt.NDArray[np.int64]
    candidates: npt.NDArray[np.int64]  # (S, 1 + k); column 0 is the click

    def __len__(self) -> int:
        return len(self.row)


def training_samples(
    behaviours: Behaviours, news_count: int, *, k: int = 4, seed: int = 0
) -> Samples:
    """As FINDING's TrainingBehaviorsDataset: each click becomes a sample,
    with k negatives drawn from the row's own, topped up at random when a
    row has fewer than k."""
    rng = random.Random(seed)
    rows: list[int] = []
    candidates: list[list[int]] = []
    for index, (positives, negatives) in enumerate(
        zip(behaviours.positives, behaviours.negatives, strict=True)
    ):
        for positive in positives:
            if len(negatives) > k:
                drawn = rng.sample(negatives, k)
            else:
                drawn = negatives + rng.sample(range(news_count), k - len(negatives))
            rows.append(index)
            candidates.append([positive, *drawn])
    return Samples(row=np.array(rows, dtype=np.int64), candidates=np.array(candidates))


def adressa_titles(clean_dir: Path, news2int_path: Path) -> dict[int, str]:
    """Headline per news int id, from the cleaned day files Part A wrote."""
    news2int = dict(pd.read_table(news2int_path).to_numpy().tolist())
    titles: dict[int, str] = {}
    for day in sorted(clean_dir.iterdir()):
        table = pd.read_table(day, usecols=["id", "title"]).drop_duplicates("id")
        for news_id, title in zip(table["id"], table["title"], strict=True):
            index = news2int.get(news_id)
            if index is not None and index not in titles:
                titles[int(index)] = str(title)
    return titles


def embed_titles(
    titles: dict[int, str], count: int, *, batch_size: int = 256
) -> npt.NDArray[np.float32]:
    """(count, 384) unit vectors; rows with no headline, and row 0, zero."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(ENCODER)
    ids = sorted(titles)
    texts = [f"{titles[i]} \n{titles[i]}" for i in ids]  # embed_article_text, no snippet
    vectors = model.encode(
        texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=True
    )
    matrix = np.zeros((count, vectors.shape[1]), dtype=np.float32)
    matrix[np.array(ids)] = vectors
    return matrix
