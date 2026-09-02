"""Text and URL primitives shared by ingestion and the API.

The two that matter are :func:`canonicalise_url` and :func:`simhash64` - they
are dedup layers one and two, and a bug in either shows up as either duplicate
front-page stories or silently merged unrelated ones.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Tracking parameters carry no meaning for identity. Anything matching these is
# dropped before a URL is compared or stored.
_TRACKING_PARAM_PREFIXES = ("utm_", "utm-", "pk_", "mc_", "at_", "ns_", "cmpid", "CMP")
_TRACKING_PARAMS = frozenset(
    {
        "fbclid",
        "gclid",
        "dclid",
        "msclkid",
        "igshid",
        "twclid",
        "yclid",
        "ref",
        "referrer",
        "source",
        "src",
        "spm",
        "cmp",
        "campaign_id",
        "ito",
        "icid",
        "ncid",
        "sh",
        "guccounter",
        "guce_referrer",
        "guce_referrer_sig",
        "amp",
        "output",
        "smid",
        "partner",
    }
)
# `\w` matches letters and digits but *not* combining marks (Unicode category
# Mn), and Devanagari writes most of its vowels as combining marks - so a bare
# `\w+` splits भारत into ["भ", "रत"] at the matra. That is not only a
# classification problem: simhash64 shingles these tokens, so dedup layer two
# was comparing fragments rather than words for every Devanagari headline.
# Adding the combining ranges for the scripts we ship fixes both at once.
_COMBINING_MARKS = (
    "\u0300-\u036f"  # generic diacritics, for any decomposed Latin text
    "\u0900-\u0903\u093a-\u094f\u0951-\u0957\u0962-\u0963"  # Devanagari
)
_WORD_RE = re.compile(rf"[\w{_COMBINING_MARKS}]+", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")
_SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")


def _is_tracking_param(key: str) -> bool:
    lowered = key.lower()
    return lowered in _TRACKING_PARAMS or lowered.startswith(_TRACKING_PARAM_PREFIXES)


def canonicalise_url(url: str) -> str:
    """Reduce a URL to a stable identity string. Dedup layer one.

    Lowercases scheme and host, drops ``www.``, forces https, removes tracking
    parameters and fragments, sorts what survives, and strips a trailing slash.
    Two URLs that differ only in campaign tracking must produce the same output
    or the same story is ingested once per referrer.
    """
    url = url.strip()
    if not url:
        raise ValueError("empty url")

    parts = urlsplit(url)
    if not parts.netloc:
        raise ValueError(f"url has no host: {url!r}")

    scheme = "https" if parts.scheme in ("", "http", "https") else parts.scheme.lower()

    host = parts.netloc.lower()
    if "@" in host:  # strip any credentials; they are never part of identity
        host = host.rsplit("@", 1)[1]
    host = host.removeprefix("www.")
    host = host.removesuffix(":80").removesuffix(":443")

    query = sorted(
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=False)
        if not _is_tracking_param(k)
    )

    path = parts.path
    if len(path) > 1:
        path = path.rstrip("/")

    return urlunsplit((scheme, host, path, urlencode(query), ""))


def url_fingerprint(canonical_url: str) -> str:
    """Short stable hash of a canonical URL, for logging and cache keys."""
    return hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:32]


def normalise_text(value: str) -> str:
    """NFKC-normalise, collapse whitespace, strip. Applied before hashing."""
    return _WHITESPACE_RE.sub(" ", unicodedata.normalize("NFKC", value)).strip()


def tokenise(value: str) -> list[str]:
    """Unicode-aware word tokens, lowercased. Works for any script."""
    return _WORD_RE.findall(normalise_text(value).lower())


def shingles(tokens: list[str], size: int = 2) -> list[str]:
    """Overlapping n-grams. Word order matters for near-duplicate detection:
    two headlines with the same bag of words but different order are usually
    different stories."""
    if len(tokens) < size:
        return tokens[:]
    return [" ".join(tokens[i : i + size]) for i in range(len(tokens) - size + 1)]


def simhash64(value: str, *, shingle_size: int = 2) -> int:
    """64-bit SimHash over word shingles. Dedup layer two.

    Returned as a signed integer because Postgres ``bigint`` is signed and we
    index this column; the sign carries no meaning, only the bit pattern does.
    """
    tokens = tokenise(value)
    if not tokens:
        return 0

    weights = [0] * 64
    for shingle in shingles(tokens, shingle_size):
        digest = hashlib.blake2b(shingle.encode("utf-8"), digest_size=8).digest()
        h = int.from_bytes(digest, "big")
        for bit in range(64):
            weights[bit] += 1 if (h >> bit) & 1 else -1

    unsigned = 0
    for bit in range(64):
        if weights[bit] > 0:
            unsigned |= 1 << bit
    return unsigned - (1 << 64) if unsigned >= (1 << 63) else unsigned


def hamming_distance(a: int, b: int) -> int:
    """Bit distance between two 64-bit simhashes, sign-safe."""
    mask = (1 << 64) - 1
    return ((a & mask) ^ (b & mask)).bit_count()


def make_snippet(value: str | None, max_chars: int) -> str | None:
    """Trim a summary to the storage cap, cutting at a word boundary.

    The cap is a copyright constraint, not a display preference: we store a
    snippet, never the article.
    """
    if not value:
        return None
    text = normalise_text(re.sub(r"<[^>]+>", " ", value))
    if not text:
        return None
    if len(text) <= max_chars:
        return text
    cut = text[: max_chars - 1]
    if " " in cut:
        cut = cut[: cut.rindex(" ")]
    return cut.rstrip(" ,;:.-") + "…"


def slugify(value: str, *, max_length: int = 120) -> str:
    """ASCII slug. Falls back to a hash for scripts that transliterate to
    nothing, so a Chinese or Arabic name never produces an empty slug."""
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii").lower()
    slug = _SLUG_STRIP_RE.sub("-", ascii_only).strip("-")[:max_length].strip("-")
    if slug:
        return slug
    return "x-" + hashlib.blake2b(value.encode("utf-8"), digest_size=6).hexdigest()
