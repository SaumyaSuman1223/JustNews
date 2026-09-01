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

# Below this probability we prefer whatever the feed or source declared.
MIN_DETECTION_CONFIDENCE = 0.5
MIN_DETECTABLE_CHARS = 12


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
    if confidence < MIN_DETECTION_CONFIDENCE and fallback:
        return fallback
    return normalise_language_code(str(code)) or fallback or UNKNOWN_LANGUAGE
