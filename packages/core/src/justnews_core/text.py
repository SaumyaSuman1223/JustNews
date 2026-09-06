"""Text and URL primitives shared by ingestion and the API.

The two that matter are :func:`canonicalise_url` and :func:`simhash64` - they
are dedup layers one and two, and a bug in either shows up as either duplicate
front-page stories or silently merged unrelated ones.
"""

from __future__ import annotations

import hashlib
import html
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


def decode_entities(value: str, *, passes: int = 2) -> str:
    """Resolve HTML character references, including double-encoded ones.

    Audit §21. Production was serving ``Antonelli&#039;s`` to readers: the
    publisher's feed contained ``&amp;#039;``, feedparser resolved that one
    layer to ``&#039;``, and nothing resolved the second. A single
    ``html.unescape`` is therefore not enough, and observed real feeds need
    exactly two rounds - so this loops, but stops the moment a pass changes
    nothing rather than unescaping until a stray ampersand runs out.
    """
    for _ in range(passes):
        decoded = html.unescape(value)
        if decoded == value:
            return value
        value = decoded
    return value


def normalise_text(value: str) -> str:
    """Decode entities, NFKC-normalise, collapse whitespace, strip.

    Entity decoding belongs here rather than at the display layer: an entity
    in stored text is an encoding artifact, and every consumer downstream -
    tokenising, simhashing, search vectors, the reader's screen - is working
    with the wrong characters until it is resolved. NFKC then folds the
    no-break spaces that ``&nbsp;`` decodes to into ordinary ones, which is
    why the order matters.
    """
    unescaped = decode_entities(value)
    return _WHITESPACE_RE.sub(" ", unicodedata.normalize("NFKC", unescaped)).strip()


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


_TAG_RE = re.compile(r"<[^>]+>")

# Live-blog and navigation furniture, matched as whole pipe-separated segments
# so a word like "live" inside a real sentence is never touched. Every entry
# here is a string observed in a real feed: the first six come from the
# second-pass audit's §21 verbatim ("Live scoreboard | Clockwatch | Mail Billy
# 4 min"), the rest from the Guardian football feed, which ends nearly every
# description with "Continue reading...".
_FURNITURE = (
    r"live\s+scoreboard|clockwatch|live\s+blog|follow\s+live|as\s+it\s+happened"
    r"|minute[-\s]by[-\s]minute(?:\s+report)?|match\s+report|player\s+ratings"
    r"|mail\s+\w+(?:\s+\d+\s*min)?"
    r"|continue\s+reading[.…\s]*"
)
_FURNITURE_SEGMENT_RE = re.compile(rf"(?i)^(?:{_FURNITURE})$")
# The same vocabulary at the end of the text. Dropping furniture *segments*
# is not enough on its own: in the audit's own example the first segment is
# "Updates from 5.30pm BST kick-off ... to a draw. Live scoreboard", so the
# nav run starts mid-segment and only its tail is separated by pipes.
_TRAILING_FURNITURE_RE = re.compile(rf"(?i)[\s|,;\u2013\u2014-]*(?:{_FURNITURE})\s*$")
# "Updates from 5.30pm BST kick-off..." - the opener of a live blog, which
# says when the *page* started rather than anything about the story. Bounded
# rather than open-ended, and anchored on "kick off", so it can only ever eat
# a short opening clause. Dots are allowed inside because the real strings
# carry a time in them ("5.30pm").
_UPDATES_OPENER_RE = re.compile(
    r"(?i)^updates?\s+from\b.{0,40}?\bkick[-\s]?off\b[\s.,:;\u2013\u2014-]*"
)
# "... and WSL - matchday live" (§21, verbatim). A trailing marker, not prose.
_TRAILING_LIVE_RE = re.compile(r"(?i)\s*[|\u2013\u2014-]\s*(?:\w+\s+)?live\s*$")
_CONTINUE_READING_RE = re.compile(r"(?i)\s*continue\s+reading\s*[.…]*\s*$")
# A promotional run the Guardian splices between the standfirst and the body:
# "... enriching the soil in the process Get our breaking news email , free app
# or daily news podcast A woman has been buried ...". Bounded and anchored at
# both ends, because it has to be removed from the middle of real prose.
_PROMO_RUN_RE = re.compile(r"(?i)\s*\bget our breaking news email\b[^.]{0,80}?\bpodcast\b\s*")
# Sentence boundaries, including the danda that ends a Devanagari sentence and
# the Arabic full stop - a Latin-only rule would refuse to cut a Hindi summary
# at any sentence and fall through to the word-boundary path every time.
_SENTENCE_END_RE = re.compile(r"(?<=[.!?\u0964\u06d4\u3002])\s")


def strip_furniture(text: str) -> str:
    """Remove live-blog and navigation furniture from a publisher summary.

    Audit §21: "this looks like raw publisher/live-blog content leaking into
    the UI". It is - the ingester stores whatever the feed put in
    ``<description>``, and for a live blog that is the page's own chrome
    rather than a summary of anything.
    """
    text = _UPDATES_OPENER_RE.sub("", text)
    text = _PROMO_RUN_RE.sub(" ", text)
    if "|" in text:
        parts = [part.strip() for part in text.split("|")]
        kept = [part for part in parts if part and not _FURNITURE_SEGMENT_RE.match(part)]
        # Only rejoin when something was actually dropped. A description whose
        # pipes are the publisher's own punctuation must survive unchanged.
        if len(kept) != len(parts):
            text = " ".join(kept)
    text = _CONTINUE_READING_RE.sub("", text)
    # Repeated because a live blog stacks them: "... Live scoreboard Clockwatch".
    while True:
        trimmed = _TRAILING_FURNITURE_RE.sub("", text)
        if trimmed == text:
            break
        text = trimmed
    text = _TRAILING_LIVE_RE.sub("", text)
    return text.strip(" |,;:\u2013\u2014-")


def _shorten(text: str, max_chars: int, *, min_sentence_chars: int = 30) -> str:
    """Cut to the first whole sentence that stands on its own, else to a word.

    The *first* boundary past the floor, not the last one that fits: a
    publisher's ``<description>`` is very often a standfirst with the article's
    own opening paragraph glued to the end of it, and keeping every sentence
    that fits keeps half the glued paragraph. §21 asks for aggressive
    truncation, and the first sentence is usually the standfirst - the one
    part actually written as a summary.
    """
    if len(text) <= max_chars:
        return text
    window = text[:max_chars]
    # A complete sentence needs no ellipsis - that is the whole reason to
    # prefer this cut. The floor stops a three-word opener ("Live. ") from
    # becoming the entire summary.
    for end in (match.start() for match in _SENTENCE_END_RE.finditer(window)):
        if end >= min_sentence_chars:
            return window[:end].rstrip()
    cut = text[: max_chars - 1]
    if " " in cut:
        cut = cut[: cut.rindex(" ")]
    return cut.rstrip(" ,;:.-") + "…"


def make_snippet(
    value: str | None, max_chars: int, *, summary_max_chars: int | None = None
) -> str | None:
    """Clean a publisher summary and trim it to a snippet.

    ``max_chars`` is a copyright constraint, not a display preference: we store
    a snippet, never the article. ``summary_max_chars`` is the editorial one
    (§20) - "do not show large publisher descriptions unless they are genuinely
    useful" - and is the shorter of the two when both are given.

    The cleaning is not optional and has no flag: entities and live-blog
    furniture are wrong in storage, not merely ugly on screen.
    """
    if not value:
        return None
    # Tags are stripped on both sides of the entity decoding: a feed that
    # escapes its own markup (`&lt;p&gt;`) only reveals it once decoded.
    text = _TAG_RE.sub(" ", normalise_text(_TAG_RE.sub(" ", value)))
    text = _WHITESPACE_RE.sub(" ", strip_furniture(text)).strip()
    if not text:
        return None
    limit = min(max_chars, summary_max_chars) if summary_max_chars else max_chars
    return _shorten(text, limit)


def slugify(value: str, *, max_length: int = 120) -> str:
    """ASCII slug. Falls back to a hash for scripts that transliterate to
    nothing, so a Chinese or Arabic name never produces an empty slug."""
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii").lower()
    slug = _SLUG_STRIP_RE.sub("-", ascii_only).strip("-")[:max_length].strip("-")
    if slug:
        return slug
    return "x-" + hashlib.blake2b(value.encode("utf-8"), digest_size=6).hexdigest()
