"""Unit tests for the grouping rule ADR 0013 actually depends on - no
database needed, since this is pure logic over already-fetched rows."""

from __future__ import annotations

from justnews_api.services.perspectives import group_by_role


class TestGroupByRole:
    def test_groups_articles_by_role(self) -> None:
        rows = [
            ("industry", 1, "trade-daily", "Trade Daily", "https://trade.example"),
            ("industry", 1, "trade-daily", "Trade Daily", "https://trade.example"),
            ("government", 2, "gov-wire", "Gov Wire", "https://gov.example"),
        ]
        groups = group_by_role(rows)
        assert [g.role for g in groups] == ["industry", "government"]
        assert groups[0].article_count == 2
        assert groups[1].article_count == 1

    def test_wire_is_never_a_perspective(self) -> None:
        rows = [("wire", 1, "ap", "AP", "https://ap.example")]
        assert group_by_role(rows) == []

    def test_an_unroled_source_is_silent_not_invented(self) -> None:
        rows = [(None, 1, "unroled", "Unroled Outlet", "https://unroled.example")]
        assert group_by_role(rows) == []

    def test_role_order_is_display_order_not_arrival_order(self) -> None:
        rows = [
            ("public", 1, "a", "A", "https://a.example"),
            ("industry", 2, "b", "B", "https://b.example"),
        ]
        groups = group_by_role(rows)
        assert [g.role for g in groups] == ["industry", "public"]

    def test_a_source_appears_once_per_group_regardless_of_article_count(self) -> None:
        rows = [
            ("industry", 1, "trade-daily", "Trade Daily", "https://trade.example"),
            ("industry", 1, "trade-daily", "Trade Daily", "https://trade.example"),
            ("industry", 1, "trade-daily", "Trade Daily", "https://trade.example"),
        ]
        groups = group_by_role(rows)
        assert len(groups) == 1
        assert groups[0].article_count == 3
        assert len(groups[0].sources) == 1

    def test_sources_within_a_group_are_sorted_by_name(self) -> None:
        rows = [
            ("industry", 1, "zeta", "Zeta Press", "https://zeta.example"),
            ("industry", 2, "alpha", "Alpha Press", "https://alpha.example"),
        ]
        groups = group_by_role(rows)
        assert [s.name for s in groups[0].sources] == ["Alpha Press", "Zeta Press"]
