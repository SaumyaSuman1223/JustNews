"""Tests for the URL and hashing primitives.

These are dedup layers one and two. A bug in ``canonicalise_url`` shows up as
the same story on the front page four times; a bug in ``simhash64`` shows up as
unrelated stories silently merged. Both are worth pinning down precisely.
"""

from __future__ import annotations

import pytest

from justnews_core.text import (
    canonicalise_url,
    hamming_distance,
    make_snippet,
    simhash64,
    slugify,
    tokenise,
)


class TestCanonicaliseUrl:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("http://www.bbc.co.uk/news/x", "https://bbc.co.uk/news/x"),
            ("https://BBC.co.uk/News/X", "https://bbc.co.uk/News/X"),
            ("https://bbc.co.uk/news/x/", "https://bbc.co.uk/news/x"),
            ("https://bbc.co.uk/news/x#comments", "https://bbc.co.uk/news/x"),
            ("https://bbc.co.uk:443/news/x", "https://bbc.co.uk/news/x"),
            ("  https://bbc.co.uk/news/x  ", "https://bbc.co.uk/news/x"),
        ],
    )
    def test_normalises_shape(self, raw: str, expected: str) -> None:
        assert canonicalise_url(raw) == expected

    def test_strips_tracking_but_keeps_meaningful_params(self) -> None:
        url = "https://site.com/a?utm_source=x&utm_medium=y&fbclid=z&id=42&page=2"
        assert canonicalise_url(url) == "https://site.com/a?id=42&page=2"

    def test_query_order_does_not_change_identity(self) -> None:
        assert canonicalise_url("https://s.com/a?b=2&a=1") == canonicalise_url(
            "https://s.com/a?a=1&b=2"
        )

    def test_same_article_from_two_referrers_is_one_url(self) -> None:
        # The case this function exists for.
        twitter = "https://www.theguardian.com/world/2026/x?utm_source=twitter&utm_medium=social"
        newsletter = "http://theguardian.com/world/2026/x/?utm_campaign=morning-mail&fbclid=abc"
        assert canonicalise_url(twitter) == canonicalise_url(newsletter)

    def test_ambiguous_single_letter_params_are_kept(self) -> None:
        # "s" is a share tag on some sites and the search query on others.
        # Stripping it would merge two genuinely different search-result pages,
        # so we keep it and let the embedding layer catch what remains.
        assert canonicalise_url("https://s.com/a?s=09") == "https://s.com/a?s=09"

    def test_path_case_is_preserved(self) -> None:
        # Hosts are case-insensitive; paths are not. Lowercasing a path would
        # 404 on any publisher with capitals in slugs.
        assert canonicalise_url("https://s.com/Section/Item") == "https://s.com/Section/Item"

    @pytest.mark.parametrize("bad", ["", "   ", "not a url", "/relative/path"])
    def test_rejects_unusable_input(self, bad: str) -> None:
        with pytest.raises(ValueError):
            canonicalise_url(bad)


class TestSimhash:
    def test_identical_text_is_identical_hash(self) -> None:
        assert simhash64("Fed holds rates steady") == simhash64("Fed holds rates steady")

    def test_fits_in_signed_bigint(self) -> None:
        # Stored in a Postgres bigint, which is signed. Overflow here would be
        # a write error in production and nowhere else.
        for text in ["a", "hello world", "x" * 500, "الطقس اليوم", "今日のニュース"]:
            assert -(2**63) <= simhash64(text) < 2**63

    def test_verbatim_syndication_is_within_the_dedup_threshold(self) -> None:
        # What layer two is actually for: the same wire copy republished with a
        # trailing attribution. Distance must stay under the configured
        # threshold of 3.
        a = simhash64("Fed holds interest rates steady amid inflation concerns")
        b = simhash64("Fed holds interest rates steady amid inflation concerns.")
        assert hamming_distance(a, b) <= 3

    def test_a_reworded_headline_falls_through_to_the_embedding_layer(self) -> None:
        # One substituted word already exceeds the simhash threshold. That is
        # correct: SimHash catches syndication, embeddings catch rewrites.
        # This test pins the boundary between layers two and three.
        a = simhash64("Fed holds interest rates steady amid inflation concerns")
        b = simhash64("Fed holds interest rates steady amid inflation worries")
        distance = hamming_distance(a, b)
        assert distance > 3
        assert distance < 25  # still recognisably related, unlike an unrelated story

    def test_unrelated_headlines_are_far(self) -> None:
        a = simhash64("Fed holds interest rates steady amid inflation concerns")
        b = simhash64("Manchester United sign teenage striker from Ajax")
        assert hamming_distance(a, b) > 20

    def test_word_order_matters(self) -> None:
        # Shingles, not a bag of words: "dog bites man" is not "man bites dog".
        a = simhash64("man bites dog in park")
        b = simhash64("dog bites man in park")
        assert a != b

    def test_empty_text_is_zero(self) -> None:
        assert simhash64("") == 0

    def test_hamming_distance_is_sign_safe(self) -> None:
        assert hamming_distance(-1, 0) == 64
        assert hamming_distance(-1, -1) == 0


class TestSnippet:
    def test_under_cap_is_unchanged(self) -> None:
        assert make_snippet("Short summary.", 300) == "Short summary."

    def test_strips_html_and_collapses_whitespace(self) -> None:
        assert make_snippet("<p>Hello   <b>world</b></p>\n", 300) == "Hello world"

    def test_respects_the_cap(self) -> None:
        # The cap is a copyright constraint, not a display preference.
        result = make_snippet("word " * 200, 100)
        assert result is not None
        assert len(result) <= 100

    def test_cuts_at_a_word_boundary(self) -> None:
        result = make_snippet("alpha beta gamma delta epsilon", 20)
        assert result is not None
        assert "gamm" not in result or result.startswith("alpha beta gamma")

    @pytest.mark.parametrize("empty", [None, "", "   ", "<p></p>"])
    def test_empty_input_is_none(self, empty: str | None) -> None:
        assert make_snippet(empty, 300) is None


class TestSlugify:
    def test_ascii(self) -> None:
        assert slugify("The Guardian") == "the-guardian"

    def test_accents_are_folded(self) -> None:
        assert slugify("El País") == "el-pais"

    @pytest.mark.parametrize("value", ["新华社", "الجزيرة", "日本経済新聞"])
    def test_non_latin_scripts_never_produce_empty_slugs(self, value: str) -> None:
        slug = slugify(value)
        assert slug
        assert slug == slugify(value)  # and it is stable


class TestTokenise:
    def test_is_unicode_aware(self) -> None:
        assert tokenise("Café münchen") == ["café", "münchen"]

    def test_drops_punctuation(self) -> None:
        assert tokenise("Hello, world! -- again.") == ["hello", "world", "again"]

    def test_devanagari_words_survive_their_vowel_marks(self) -> None:
        # Regression: `\w+` excludes Unicode combining marks, so this used to
        # come back as ["भ", "रत", "म", ...] - every Devanagari word split at
        # its matra. Hindi is a launch language; this has to hold.
        assert tokenise("भारत में क्रिकेट मैच") == ["भारत", "में", "क्रिकेट", "मैच"]

    def test_devanagari_tokens_are_whole_words_not_fragments(self) -> None:
        assert all(len(t) > 1 for t in tokenise("अर्थव्यवस्था और राजनीति"))


class TestSimhashAcrossScripts:
    """Dedup layer two runs over `tokenise` output, so a tokeniser that
    shatters a script silently weakens deduplication for it."""

    def test_near_duplicate_hindi_headlines_are_close(self) -> None:
        a = simhash64("मोदी ने संसद में नया कानून पेश किया")
        b = simhash64("मोदी ने संसद में नया कानून पेश किया है")
        assert hamming_distance(a, b) < 16

    def test_unrelated_hindi_headlines_are_far(self) -> None:
        a = simhash64("मोदी ने संसद में नया कानून पेश किया")
        b = simhash64("क्रिकेट मैच में भारत की जीत")
        assert hamming_distance(a, b) > 16
