"""Tests for the URL and hashing primitives.

These are dedup layers one and two. A bug in ``canonicalise_url`` shows up as
the same story on the front page four times; a bug in ``simhash64`` shows up as
unrelated stories silently merged. Both are worth pinning down precisely.
"""

from __future__ import annotations

import pytest

from justnews_core.text import (
    canonicalise_url,
    decode_entities,
    hamming_distance,
    make_snippet,
    normalise_text,
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


class TestEntityDecoding:
    """Audit §21, against strings taken from the live corpus.

    ``Antonelli&#039;s`` was on production's Home page. In the production RSS
    feed the same row appears as ``Antonelli&amp;#039;s`` - the publisher
    double-encoded it, feedparser resolved one layer, and nothing resolved the
    second. That is why one ``html.unescape`` is not enough.
    """

    def test_single_encoded(self) -> None:
        assert decode_entities("students&#x27; wellbeing") == "students' wellbeing"

    def test_double_encoded_from_production(self) -> None:
        assert (
            decode_entities("Antonelli&amp;#039;s sensational race")
            == "Antonelli's sensational race"
        )

    def test_stops_when_stable(self) -> None:
        # A literal ampersand is not an entity and must survive untouched, or
        # every "Tom & Jerry" in the corpus quietly changes.
        assert decode_entities("Tom & Jerry") == "Tom & Jerry"

    def test_normalise_text_decodes_and_folds_nbsp(self) -> None:
        # "Manchester&nbsp;City" appears verbatim in the Guardian feed. NFKC
        # folds the resulting no-break space, so the word does not become one
        # token to the search vector and another to a reader.
        assert normalise_text("Manchester&nbsp;City") == "Manchester City"

    def test_snippet_decodes(self) -> None:
        assert make_snippet("Wright&amp;#039;s comments", 300) == "Wright's comments"


class TestFurniture:
    """§21's "raw live-blog content must be cleaned", against real strings."""

    def test_trailing_matchday_live_marker(self) -> None:
        # Verbatim from the audit's live-site sample.
        assert (
            make_snippet(
                "Premier League buildup to Arsenal v Chelsea, plus Everton v "
                "Manchester United and WSL — matchday live",
                300,
            )
            == "Premier League buildup to Arsenal v Chelsea, plus Everton v "
            "Manchester United and WSL"
        )

    def test_live_blog_navigation_segments(self) -> None:
        # Verbatim from the audit's §21 example.
        assert (
            make_snippet(
                "Updates from 5.30pm BST kick-off Everton held United to a draw. "
                "Live scoreboard | Clockwatch | Mail Billy 4 min",
                300,
            )
            == "Everton held United to a draw."
        )

    def test_continue_reading_trailer(self) -> None:
        # Ends nearly every description in the Guardian's football feed.
        assert (
            make_snippet("The order of discovery will worry him. Continue reading...", 300)
            == "The order of discovery will worry him."
        )

    def test_newsletter_promo_spliced_into_the_middle(self) -> None:
        # Verbatim from the Guardian's live feed: a promo run wedged between
        # the standfirst and the body, so it has to come out of the middle.
        assert (
            make_snippet(
                "The casket takes just 45 days to break down, enriching the soil in "
                "the process Get our breaking news email , free app or daily news "
                "podcast A woman has been buried in a coffin made from mushrooms",
                300,
            )
            == "The casket takes just 45 days to break down, enriching the soil in the "
            "process A woman has been buried in a coffin made from mushrooms"
        )

    def test_publisher_pipes_survive(self) -> None:
        # Pipes are only furniture when the segments are. A description that
        # uses one as punctuation must come through untouched, or the rule is
        # eating real text.
        text = "Live music | the week in review, from Berlin to Buenos Aires"
        assert make_snippet(text, 300) == text


class TestSummaryLength:
    """§20: "do not show large publisher descriptions unless genuinely useful"."""

    def test_prefers_a_whole_sentence_and_adds_no_ellipsis(self) -> None:
        # The Guardian pattern: a standfirst, then the article's own first
        # paragraph glued straight onto it with no separator.
        text = (
            "Storm may make impact as soon as Monday. Hawaii has declared a state of "
            "emergency as powerful Hurricane Lowell makes its way toward the islands, "
            "with officials warning of flooding across low-lying coastal districts."
        )
        assert make_snippet(text, 300, summary_max_chars=200) == (
            "Storm may make impact as soon as Monday."
        )

    def test_falls_back_to_a_word_boundary_when_no_sentence_fits(self) -> None:
        result = make_snippet("word " * 100, 300, summary_max_chars=200)
        assert result is not None
        assert len(result) <= 200
        assert result.endswith("…")

    def test_summary_cap_never_exceeds_the_storage_cap(self) -> None:
        # The storage cap is a copyright constraint and wins whenever the two
        # disagree, whichever way round they are set.
        result = make_snippet("word " * 100, 80, summary_max_chars=200)
        assert result is not None
        assert len(result) <= 80

    def test_devanagari_sentences_are_cut_at_the_danda(self) -> None:
        # A Latin-only sentence rule would never find a boundary here and
        # would fall through to a mid-word truncation for every Hindi summary.
        text = "यह पहला वाक्य है जो पर्याप्त लंबा है ताकि सीमा पार हो सके। " + ("शब्द " * 60)
        result = make_snippet(text, 300, summary_max_chars=200)
        assert result == "यह पहला वाक्य है जो पर्याप्त लंबा है ताकि सीमा पार हो सके।"

    def test_is_idempotent(self) -> None:
        # The repair command re-runs over rows it has already cleaned, so a
        # second pass must be a no-op or every run reports work to do.
        once = make_snippet(
            "Officials described the decision as provisional and said a fuller "
            "assessment would follow once the review board reports later this month. "
            "The committee meets again in November. Continue reading...",
            300,
            summary_max_chars=200,
        )
        assert once is not None
        assert make_snippet(once, 300, summary_max_chars=200) == once


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
