"""Tests for the news encoder contract.

Both implementations must satisfy the same properties, because the pipeline
does not know which one it has.
"""

from __future__ import annotations

import math

from justnews_core.embedding import (
    HashingEmbedder,
    build_embedder,
    cosine_similarity,
    embed_article_text,
)
from justnews_core.settings import Settings


class TestHashingEmbedder:
    def test_dimensionality_matches_the_schema(self) -> None:
        embedder = HashingEmbedder(384)
        assert len(embedder.embed(["hello"])[0]) == 384

    def test_is_deterministic(self) -> None:
        # Not a nicety: dedup compares vectors written by different runs.
        assert HashingEmbedder().embed(["a headline"]) == HashingEmbedder().embed(["a headline"])

    def test_output_is_l2_normalised(self) -> None:
        # The pipeline relies on this so cosine and inner product agree.
        vector = HashingEmbedder().embed(["a reasonably long news headline"])[0]
        assert math.isclose(math.sqrt(sum(x * x for x in vector)), 1.0, abs_tol=1e-6)

    def test_empty_string_does_not_crash(self) -> None:
        assert len(HashingEmbedder().embed([""])[0]) == 384

    def test_similar_text_scores_higher_than_unrelated(self) -> None:
        embedder = HashingEmbedder()
        a, b, c = embedder.embed(
            [
                "Fed holds interest rates steady",
                "Fed holds interest rates unchanged",
                "Barcelona win the Copa del Rey",
            ]
        )
        assert cosine_similarity(a, b) > cosine_similarity(a, c)


class TestCosineSimilarity:
    def test_identical_vectors(self) -> None:
        assert math.isclose(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)

    def test_orthogonal_vectors(self) -> None:
        assert math.isclose(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0)

    def test_zero_vector_is_zero_not_nan(self) -> None:
        assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


class TestBuildEmbedder:
    def test_defaults_to_hashing(self) -> None:
        assert isinstance(build_embedder(Settings(embedder="hashing")), HashingEmbedder)


class TestEmbedArticleText:
    def test_title_dominates_a_long_snippet(self) -> None:
        # Snippets are often boilerplate; the headline says what the story is.
        embedder = HashingEmbedder()
        boilerplate = "Subscribe to our newsletter for more coverage. " * 5
        with_snippet = embed_article_text(embedder, "Volcano erupts in Iceland", boilerplate)
        title_only = embed_article_text(embedder, "Volcano erupts in Iceland", None)
        unrelated = embed_article_text(embedder, "Stock markets close higher", None)
        assert cosine_similarity(with_snippet, title_only) > cosine_similarity(
            with_snippet, unrelated
        )
