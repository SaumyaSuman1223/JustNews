"""Language detection and per-language Postgres search configuration.

Every article carries a language and every reader chooses languages, so this
module is on the path of both ingestion and every feed query (ADR 0005).
"""

from __future__ import annotations

from functools import lru_cache

from justnews_core.text import normalise_text

# Postgres ships stemmers for a fixed set of languages. Anything outside it
# falls back to 'simple', which does no stemming but still tokenises - a worse
# search experience, never a broken one.
_TSVECTOR_CONFIG: dict[str, str] = {
    "ar": "arabic",
    "da": "danish",
    "de": "german",
    "el": "greek",
    "en": "english",
    "es": "spanish",
    "fi": "finnish",
    "fr": "french",
    "ga": "irish",
    "hi": "simple",
    "hu": "hungarian",
    "id": "indonesian",
    "it": "italian",
    "lt": "lithuanian",
    "ne": "nepali",
    "nl": "dutch",
    "no": "norwegian",
    "pt": "portuguese",
    "ro": "romanian",
    "ru": "russian",
    "sv": "swedish",
    "ta": "tamil",
    "tr": "turkish",
    "zh": "simple",
}

DEFAULT_LANGUAGE = "en"
UNKNOWN_LANGUAGE = "und"

# The languages this product ships in. Single source of truth, and it has two
# obligations that are easy to break independently:
#
#   * every language we ingest must be reachable by a reader - the feed filter
#     is exact, so a language with no locale is content nobody can ever see;
#   * every locale we offer must have a working source behind it, or a reader
#     picks it and lands on an empty page.
#
# Both are asserted in packages/core/tests/test_launch_languages.py, one of
# which reads the web locale registry directly, because these two lists live on
# opposite sides of a language boundary and will otherwise drift apart.
LAUNCH_LANGUAGES: tuple[str, ...] = (
    "en",
    "es",
    "hi",
)

# Confidence needed before a detection overrides the language a feed declared.
#
# These numbers are high on purpose, and they were measured rather than picked.
# On headline-length text langid is badly calibrated - confidence does not
# separate its right answers from its wrong ones. Sampled from articles this
# pipeline actually misfiled:
#
#     it  0.955  "Argentinian footballer Lionel Messi announces his..."   WRONG
#     ms  0.979  "Telangana CM launches Amberpet-Moosarambagh high-..."   WRONG
#     nb  0.846  "Strengere EU-regler for ChatGPT, Reddit og Roblox..."   right
#     ca  1.000  "L'idCAT Mobil permet accedir a La Meva Salut..."        right
#     en  1.000  "The central bank held interest rates steady..."         right
#
# A wrong answer at 0.98 and a right one at 0.85 means no ordinary threshold
# works. What does work is treating the feed's own declaration as strong prior
# evidence and demanding near-certainty to overturn it, which is exactly what a
# short string cannot usually provide. Longer text is better behaved and gets a
# looser bar.
#
# The cost of getting this wrong is not cosmetic: readers only ever see the
# languages they chose, so a misfiled article is invisible to everyone.
MIN_DETECTION_CONFIDENCE_SHORT = 0.99
MIN_DETECTION_CONFIDENCE_LONG = 0.85
SHORT_TEXT_CHARS = 80
MIN_DETECTABLE_CHARS = 12

# Variants folded onto the macrolanguage a feed is likely to declare.
#
# NRK declares "no" and publishes both Bokmal and Nynorsk. Detection is right
# to tell them apart, but storing nb and nn splits one audience across three
# codes and a reader who picked "no" then matches nothing.
_MACROLANGUAGE: dict[str, str] = {"nb": "no", "nn": "no"}


def tsvector_config(language: str) -> str:
    """Postgres text-search configuration name for a language code."""
    return _TSVECTOR_CONFIG.get(language.split("-")[0].lower(), "simple")


def normalise_language_code(value: str | None) -> str | None:
    """Reduce ``en-GB``/``EN_gb`` to ``en``. Returns None for junk input."""
    if not value:
        return None
    code = value.strip().lower().replace("_", "-").split("-")[0]
    return code if code.isalpha() and 2 <= len(code) <= 3 else None


@lru_cache(maxsize=1)
def _identifier() -> object | None:
    """A langid model configured to return normalised probabilities.

    ``py3langid.classify`` returns an unnormalised **log-probability** - a
    number like -134.9, not a confidence in [0, 1]. Comparing that against a
    0.5 threshold is always true, so every detection silently fell back to the
    declared language and the detector never ran. Building the identifier with
    ``norm_probs=True`` is what makes the threshold below mean anything.
    """
    try:
        from py3langid.langid import MODEL_FILE, LanguageIdentifier
    except ImportError:  # detector is optional in minimal installs
        return None
    identifier: object = LanguageIdentifier.from_pickled_model(MODEL_FILE, norm_probs=True)
    return identifier


def detect_language(text: str, *, fallback: str | None = None) -> str:
    """Detect the language of a headline.

    Short strings are genuinely hard, so a language declared by the feed or
    source (passed as ``fallback``) beats a low-confidence guess. Returns
    ``und`` only when there is nothing to go on at all.
    """
    cleaned = normalise_text(text)
    if len(cleaned) < MIN_DETECTABLE_CHARS:
        return fallback or UNKNOWN_LANGUAGE

    identifier = _identifier()
    if identifier is None:
        return fallback or UNKNOWN_LANGUAGE

    code, confidence = identifier.classify(cleaned)  # type: ignore[attr-defined]
    required = (
        MIN_DETECTION_CONFIDENCE_SHORT
        if len(cleaned) < SHORT_TEXT_CHARS
        else MIN_DETECTION_CONFIDENCE_LONG
    )
    if confidence < required and fallback:
        return fallback

    detected = normalise_language_code(str(code))
    if detected is None:
        return fallback or UNKNOWN_LANGUAGE

    # Fold a variant onto its macrolanguage when that is what the feed declared,
    # so nb and nn under a "no" feed stay reachable from "no".
    macro = _MACROLANGUAGE.get(detected)
    if macro is not None and fallback == macro:
        return macro
    return detected
