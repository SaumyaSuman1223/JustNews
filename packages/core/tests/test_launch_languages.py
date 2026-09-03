"""The launch-language set must agree across three places.

The seed feed list (Python), the locale registry (TypeScript) and
``LAUNCH_LANGUAGES`` are edited independently and by different reflexes. When
they drift, nothing raises: articles are ingested in a language no route
exposes, or a locale is offered that has no source behind it. Both fail
silently and look like "the site is a bit empty".
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from justnews_core.language import LAUNCH_LANGUAGES

REPO_ROOT = Path(__file__).resolve().parents[3]
WEB_I18N = REPO_ROOT / "frontend" / "lib" / "i18n.ts"


def _web_locale_codes() -> set[str]:
    source = WEB_I18N.read_text(encoding="utf-8")
    return set(re.findall(r'\{\s*code:\s*"([a-z-]+)"', source))


def _seed_languages() -> set[str]:
    from justnews_ingestion.seed import SEED_SOURCES

    return {feed.language for source in SEED_SOURCES for feed in source.feeds}


class TestLaunchLanguages:
    def test_no_duplicates(self) -> None:
        assert len(LAUNCH_LANGUAGES) == len(set(LAUNCH_LANGUAGES))

    def test_english_is_present(self) -> None:
        # The default locale and the fallback for everything else.
        assert "en" in LAUNCH_LANGUAGES


class TestWebRegistryMatches:
    def test_web_locale_file_exists(self) -> None:
        assert WEB_I18N.is_file(), f"expected the locale registry at {WEB_I18N}"

    def test_every_launch_language_has_a_locale(self) -> None:
        # Otherwise the articles are ingested and no reader can ever reach them.
        missing = set(LAUNCH_LANGUAGES) - _web_locale_codes()
        assert not missing, f"languages with no route: {sorted(missing)}"

    def test_every_locale_is_a_launch_language(self) -> None:
        # Otherwise a reader picks a language and lands on an empty page.
        extra = _web_locale_codes() - set(LAUNCH_LANGUAGES)
        assert not extra, f"locales with no content: {sorted(extra)}"


class TestSeedCoverage:
    def test_every_launch_language_has_at_least_one_feed(self) -> None:
        uncovered = set(LAUNCH_LANGUAGES) - _seed_languages()
        assert not uncovered, f"launch languages with no source: {sorted(uncovered)}"

    def test_no_feed_targets_a_language_we_do_not_ship(self) -> None:
        stray = _seed_languages() - set(LAUNCH_LANGUAGES)
        assert not stray, f"feeds for languages with no locale: {sorted(stray)}"

    @pytest.mark.parametrize("language", ["hi"])
    def test_non_latin_scripts_are_covered(self, language: str) -> None:
        # Devanagari is now the only non-Latin script shipping, and it is still
        # the one most likely to break a Latin-first layout or an English-only
        # encoder. Arabic and Chinese left the launch set; the logical-CSS
        # discipline that made Arabic work stays, so re-adding an RTL language
        # is a locale-registry edit rather than a layout retrofit (ADR 0005).
        assert language in _seed_languages()
