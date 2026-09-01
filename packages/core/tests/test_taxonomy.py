"""Tests for the IPTC taxonomy layer."""

from __future__ import annotations

import pytest

from justnews_core.taxonomy import (
    DEFAULT_CATEGORY_MAP,
    TOP_LEVEL_IDS,
    TOP_LEVEL_TOPICS,
    map_category,
)


class TestTopLevelTopics:
    def test_there_are_seventeen(self) -> None:
        assert len(TOP_LEVEL_TOPICS) == 17

    def test_ids_are_unique_and_well_formed(self) -> None:
        assert len(TOP_LEVEL_IDS) == 17
        for topic in TOP_LEVEL_TOPICS:
            assert topic.id.startswith("medtop:")

    def test_slugs_are_unique(self) -> None:
        assert len({topic.slug for topic in TOP_LEVEL_TOPICS}) == 17

    def test_every_topic_has_an_english_label(self) -> None:
        # Labels are a presentation lookup; English is the guaranteed fallback.
        assert all("en" in topic.labels for topic in TOP_LEVEL_TOPICS)

    def test_labels_cover_a_right_to_left_script(self) -> None:
        # Arabic is in the launch set and is the RTL canary throughout.
        assert all("ar" in topic.labels for topic in TOP_LEVEL_TOPICS)


class TestCategoryMapping:
    def test_every_mapping_target_is_a_real_concept(self) -> None:
        # A typo here silently routes articles to a topic that does not exist.
        assert set(DEFAULT_CATEGORY_MAP.values()) <= TOP_LEVEL_IDS

    @pytest.mark.parametrize(
        ("raw", "expected_slug"),
        [
            ("Technology", "science-technology"),
            ("tech", "science-technology"),
            ("Sport", "sport"),
            ("World/Politics", "politics"),
            ("Business News", "economy-business-finance"),
            ("Climate Change", "environment"),
        ],
    )
    def test_maps_publisher_categories(self, raw: str, expected_slug: str) -> None:
        topic_id = map_category(raw)
        assert topic_id is not None
        match = next(t for t in TOP_LEVEL_TOPICS if t.id == topic_id)
        assert match.slug == expected_slug

    @pytest.mark.parametrize("unknown", ["", "   ", "Editor's picks", "zzzz"])
    def test_returns_none_when_nothing_matches(self, unknown: str) -> None:
        # None means "fall through to the feed hint or the classifier",
        # which is better than a confident wrong answer.
        assert map_category(unknown) is None
