"""The news encoder.

Frozen, multilingual, 384-dimensional (ADR 0005). Frozen matters operationally
as much as architecturally: because these vectors never change when the ranker
is retrained, there is no corpus-wide re-embedding job on every model upgrade.

Two implementations:

``hashing``
    Deterministic character-n-gram hashing. No model download, no torch, runs
    in CI in milliseconds. It is a real embedding - near-identical strings land
    near each other - but it is lexical, so it does **not** match the same story
    across languages. Development and tests only.
``sentence-transformers``
    The real multilingual encoder. Shared vector space across 50+ languages,
    which is what makes cross-lingual story clustering work.

Selected by ``EMBEDDER``. Both emit L2-normalised vectors, so cosine similarity
is a dot product and pgvector's inner-product operator is exact.
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol, runtime_checkable

from justnews_core.settings import Settings
from justnews_core.text import normalise_text, tokenise


@runtime_checkable
class Embedder(Protocol):
    dimensions: int
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def _l2_normalise(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(component * component for component in vector))
    if norm == 0.0:
        return vector
    return [component / norm for component in vector]


class HashingEmbedder:
    """Deterministic hashing encoder for development and CI.

    Uses word tokens plus character 4-grams so it degrades gracefully on
    scripts without whitespace word boundaries (Chinese, Japanese).
    """

    name = "hashing-v1"

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def _features(self, text: str) -> list[str]:
        cleaned = normalise_text(text).lower()
        features = tokenise(cleaned)
        features += [cleaned[i : i + 4] for i in range(max(0, len(cleaned) - 3))]
        return features

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dimensions
            for feature in self._features(text):
                digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
                h = int.from_bytes(digest, "big")
                index = h % self.dimensions
                vector[index] += 1.0 if (h >> 63) & 1 else -1.0
            vectors.append(_l2_normalise(vector))
        return vectors


class SentenceTransformerEmbedder:
    """The production encoder. Loaded once; never fine-tuned."""

    def __init__(self, model_name: str, dimensions: int) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.name = model_name
        self.dimensions = dimensions

        actual = int(self._model.get_sentence_embedding_dimension())
        if actual != dimensions:
            raise ValueError(
                f"{model_name} emits {actual}-dim vectors but the schema expects "
                f"{dimensions}. Changing this means re-embedding the whole corpus "
                f"and rebuilding the pgvector index - do it deliberately."
            )

    def embed(self, texts: list[str]) -> list[list[float]]:
        raw = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [[float(component) for component in row] for row in raw]


def build_embedder(settings: Settings) -> Embedder:
    if settings.embedder == "sentence-transformers":
        return SentenceTransformerEmbedder(
            settings.sentence_transformer_model, settings.embedding_dim
        )
    return HashingEmbedder(settings.embedding_dim)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine of two vectors. Correct for un-normalised input too."""
    if len(a) != len(b):
        raise ValueError(f"dimension mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def embed_article_text(embedder: Embedder, title: str, snippet: str | None) -> list[float]:
    """The exact string an article is embedded from.

    Title is weighted by repetition: a snippet is often boilerplate, and the
    headline carries most of the signal about what the story is.
    """
    parts = [title, title]
    if snippet:
        parts.append(snippet)
    return embedder.embed([" \n".join(parts)])[0]
