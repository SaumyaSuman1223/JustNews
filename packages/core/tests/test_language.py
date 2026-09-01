"""Tests for language handling."""

from __future__ import annotations

import pytest

from justnews_core.language import detect_language, normalise_language_code, tsvector_config


class TestNormaliseLanguageCode:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [("en", "en"), ("en-GB", "en"), ("EN_gb", "en"), ("pt-BR", "pt"), ("  fr  ", "fr")],
    )
    def test_reduces_to_base_language(self, raw: str, expected: str) -> None:
        assert normalise_language_code(raw) == expected

    @pytest.mark.parametrize("junk", [None, "", "123", "e", "toolong", "!!"])
    def test_rejects_junk(self, junk: str | None) -> None:
        assert normalise_language_code(junk) is None


class TestTsvectorConfig:
    @pytest.mark.parametrize(
        ("language", "config"),
        [("en", "english"), ("es", "spanish"), ("ar", "arabic"), ("en-GB", "english")],
    )
    def test_known_languages_get_a_stemmer(self, language: str, config: str) -> None:
        assert tsvector_config(language) == config

    @pytest.mark.parametrize("language", ["hi", "zh", "xx", "und"])
    def test_unsupported_languages_fall_back_to_simple(self, language: str) -> None:
        # 'simple' does no stemming but still tokenises: worse search, never
        # broken search.
        assert tsvector_config(language) == "simple"


class TestDetectLanguage:
    def test_short_text_uses_the_declared_fallback(self) -> None:
        # Headlines are short and detection on them is unreliable, so a
        # language declared by the feed beats a low-confidence guess.
        assert detect_language("Hi", fallback="de") == "de"

    def test_no_signal_and_no_fallback_is_undetermined(self) -> None:
        assert detect_language("", fallback=None) == "und"

    def test_detects_a_clear_english_sentence(self) -> None:
        result = detect_language(
            "The central bank held interest rates steady for the third consecutive meeting",
            fallback="de",
        )
        assert result == "en"
