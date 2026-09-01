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


class TestDetectionAgainstRealMisfiles:
    """Cases taken from articles this pipeline actually misfiled.

    Each one is a real headline that reached the database under the wrong
    language, making it invisible to every reader - the language filter is
    exact, so a misfile is not a cosmetic error.
    """

    def test_short_english_headline_is_not_read_as_italian(self) -> None:
        assert (
            detect_language(
                "Argentinian footballer Lionel Messi announces his retirement",
                fallback="en",
            )
            == "en"
        )

    def test_short_english_headline_is_not_read_as_malay(self) -> None:
        assert (
            detect_language(
                "Telangana CM launches Amberpet-Moosarambagh high-level bridge",
                fallback="en",
            )
            == "en"
        )

    def test_short_arabic_headline_is_not_read_as_pashto(self) -> None:
        assert detect_language("شاهد البث المباشر لتلفزيون بي بي سي", fallback="ar") == "ar"

    def test_a_genuinely_different_language_still_wins(self) -> None:
        # El Pais declares "es" and publishes some Catalan. Deferring to the
        # feed unconditionally would be just as wrong as trusting a weak guess.
        detected = detect_language(
            "L'idCAT Mòbil permet accedir a La Meva Salut sense necessitat de contrasenya",
            fallback="es",
        )
        assert detected == "ca"


class TestMacrolanguageFolding:
    def test_bokmal_under_a_norwegian_feed_stays_norwegian(self) -> None:
        # NRK declares "no" and publishes both written standards. Splitting the
        # corpus across no, nb and nn leaves a reader who picked "no" with
        # nothing to read.
        assert (
            detect_language(
                "Strengere EU-regler for ChatGPT, Reddit og Roblox etter nye vedtak i Brussel",
                fallback="no",
            )
            == "no"
        )

    def test_nynorsk_under_a_norwegian_feed_stays_norwegian(self) -> None:
        assert (
            detect_language(
                "Truls Gulowsen trekker seg som leiar i Naturvernforbundet etter mange år",
                fallback="no",
            )
            == "no"
        )

    def test_folding_only_applies_when_the_feed_agrees(self) -> None:
        # An English-declared feed that genuinely publishes Bokmal should keep
        # the detected code rather than inventing "no".
        assert detect_language("Kort tekst", fallback="en") == "en"
