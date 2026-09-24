import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
import { FeedSkeleton } from "@/components/FeedSkeleton";
import { Pagination } from "@/components/Pagination";
import { SearchControls } from "@/components/SearchControls";
import { getAllSources, getMe, getSaves, getTopics, searchArticles, type Article } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { curatedTopicLabel } from "@/lib/curatedTopics";
import { viewHref } from "@/lib/discoverView";
import { getLocale, isLocaleCode, readerLanguages, t, tPlural } from "@/lib/i18n";
import { getSession } from "@/lib/session";

export async function generateMetadata({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ q?: string }>;
}): Promise<Metadata> {
  const [{ locale }, { q }] = await Promise.all([params, searchParams]);
  const code = isLocaleCode(locale) ? locale : "en";
  return {
    title: q ? t(code, "search.titleWithQuery", { query: q }) : t(code, "search.heading"),
  };
}

export default async function SearchPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{
    q?: string;
    cursor?: string;
    topic?: string;
    lang?: string;
    source?: string;
    date?: string;
  }>;
}) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const { q, cursor, topic, lang, source, date } = await searchParams;
  const query = (q ?? "").trim();
  // An unknown locale code in `lang` is dropped rather than passed through:
  // no query may return content in a language this product does not ship.
  const language = lang && isLocaleCode(lang) ? lang : "";
  const dateWindow = date === "day" || date === "week" || date === "month" ? date : "";
  const [topics, sources] = await Promise.all([getTopics(active.code), getAllSources()]);

  return (
    <>
      <div className="page-header">
        <h1>{t(active.code, "search.heading")}</h1>
        <p>{t(active.code, "search.intro")}</p>
      </div>

      <SearchControls
        locale={active.code}
        query={query}
        topic={topic ?? ""}
        language={language}
        source={source ?? ""}
        date={dateWindow}
        topics={topics.data}
        sources={sources.data}
      />

      <Suspense
        key={`${query}:${topic ?? ""}:${language}:${source ?? ""}:${dateWindow}:${cursor ?? "start"}`}
        fallback={
          query.length >= 2 ? <FeedSkeleton layout="list" secondaries={0} rows={5} /> : null
        }
      >
        <SearchBody
          locale={active.code}
          query={query}
          topic={topic ?? ""}
          language={language}
          source={source ?? ""}
          date={dateWindow}
          cursor={cursor}
        />
      </Suspense>
    </>
  );
}

async function SearchBody({
  locale,
  query,
  topic,
  language,
  source,
  date,
  cursor,
}: {
  locale: ReturnType<typeof getLocale>["code"];
  query: string;
  topic: string;
  language: string;
  source: string;
  date: string;
  cursor?: string;
}) {
  const session = await getSession();
  const auth = session
    ? {
        accessToken: session.accessToken,
        sessionId: await getBrowsingSessionId(),
      }
    : null;

  // A reader searching for a name expects hits in every language they read,
  // not only the one the interface happens to be in.
  const profile = auth ? await getMe(auth) : null;
  // An explicit language filter narrows the reader's own set rather than
  // widening it - picking one is asking for a subset of what they read, and
  // must never reach for a language they did not choose.
  const languages = language || readerLanguages(profile?.preferred_languages, locale);

  const [results, savedIds] = await Promise.all([
    query.length >= 2
      ? searchArticles({
          query,
          languages,
          topic: topic || undefined,
          source: source || undefined,
          date: date || undefined,
          interfaceLanguage: locale,
          cursor,
        })
      : Promise.resolve({
          data: {
            items: [],
            next_cursor: null,
            total: null,
            matched_topics: null,
            matched_sources: null,
          },
          degraded: false,
        }),
    auth
      ? getSaves(auth).then((page) => new Set(page.data.items.map((item) => item.article.id)))
      : Promise.resolve(new Set<number>()),
  ]);

  // §21's result grouping: a query naming a topic or a source says so, not
  // just the articles that happen to mention the word. Both are `null` past
  // the first page (the service reuses the first page's answer rather than
  // recomputing an unchanging predicate).
  const matchedTopics = results.data.matched_topics ?? [];
  const matchedSources = results.data.matched_sources ?? [];
  const hasGroups = matchedTopics.length > 0 || matchedSources.length > 0;

  return (
    <>
      {results.degraded && (
        // Two sentences, the second entirely a link. The recovery route used
        // to be a single word inside the sentence, which only lands in the
        // right place in languages built like English.
        <p className="notice" role="status">
          {t(locale, "search.degraded")}{" "}
          <a href={`/${locale}/desk`}>{t(locale, "search.browseInstead")}</a>
        </p>
      )}

      {query.length > 0 && query.length < 2 && (
        <p className="empty">{t(locale, "search.tooShort")}</p>
      )}

      {(matchedTopics.length > 0 || matchedSources.length > 0) && (
        <section className="search-groups">
          {matchedTopics.length > 0 && (
            <div className="search-group">
              <h2 className="search-group__heading">{t(locale, "search.group.topics")}</h2>
              <ul className="search-group__list">
                {matchedTopics.map((match) => (
                  <li key={match.id}>
                    <a
                      className="topic-chip"
                      href={viewHref(locale, { kind: "topic", topicId: match.id })}
                    >
                      {curatedTopicLabel(match.id, match.label, locale)}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {matchedSources.length > 0 && (
            <div className="search-group">
              <h2 className="search-group__heading">{t(locale, "search.group.sources")}</h2>
              <ul className="search-group__list">
                {matchedSources.map((match) => (
                  <li key={match.id}>
                    <a
                      className="topic-chip"
                      href={`/${locale}/source/${encodeURIComponent(match.slug)}`}
                    >
                      {match.name}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {query.length >= 2 && results.data.items.length === 0 && !hasGroups && !results.degraded && (
        <EmptyState
          title={t(locale, "search.empty.title", { query })}
          body={t(locale, "search.empty.body")}
          action={{
            href: `/${locale}/desk`,
            label: t(locale, "common.browseTopics"),
          }}
        />
      )}

      {results.data.items.length > 0 && (
        <section className="search-results">
          {/* §28: a results heading, and how many there are. The total comes
              from the API on the first page only - a keyset feed cannot count
              its own result set, and recounting the same predicate on page
              four returns the same number. So a later page keeps the heading
              and drops the count rather than showing a number for the page. */}
          <h2 className="home-tier">
            {hasGroups ? t(locale, "search.group.stories") : t(locale, "search.results")}
          </h2>
          {typeof results.data.total === "number" && (
            <p className="search-count">
              {tPlural(locale, "search.resultCount", results.data.total)}
            </p>
          )}
        </section>
      )}

      {results.data.items.length > 0 && (
        <FeedList
          items={groupByStory(results.data.items).map(({ article, others }) => ({
            article,
            saved: savedIds.has(article.id),
            moreReports:
              others > 0 && article.story_cluster_id !== null
                ? {
                    label: tPlural(locale, "search.moreReports", others),
                    href: `/${locale}/story/${article.story_cluster_id}`,
                  }
                : undefined,
          }))}
          highlight={query}
          locale={locale}
          surface="search"
          signedIn={Boolean(session)}
          revalidatePath={searchHref(locale, query, topic, language, source, date)}
          layout="list"
        />
      )}

      {/* The query rides in baseHref, so page two is still a search for the
          same thing - this route has accepted a cursor since Stage 2 and
          nothing ever linked to it. */}
      {query.length >= 2 && (
        <Pagination
          locale={locale}
          baseHref={searchHref(locale, query, topic, language, source, date)}
          nextCursor={results.data.next_cursor}
          onLaterPage={Boolean(cursor)}
        />
      )}
    </>
  );
}

/**
 * One row per story (fifth pass §2.4): "trump" returned the UN speech five
 * times, once per outlet, as five separate rows. Results that share a story
 * cluster collapse into the first - the most recent, since search is
 * recency-ordered - with a link to the story's full coverage for the rest.
 * Within this page only: the cursor pages over articles, so a story whose
 * reports straddle a page boundary can appear on both, and the count above
 * still counts articles, which is what it says it counts.
 */
function groupByStory(articles: Article[]): { article: Article; others: number }[] {
  const groups: { article: Article; others: number }[] = [];
  const byCluster = new Map<number, { article: Article; others: number }>();
  for (const article of articles) {
    const cluster = article.story_cluster_id;
    const existing = cluster === null ? undefined : byCluster.get(cluster);
    if (existing) {
      existing.others += 1;
      continue;
    }
    const group = { article, others: 0 };
    groups.push(group);
    if (cluster !== null) byCluster.set(cluster, group);
  }
  return groups;
}

/** The current search as a URL, so page two keeps the filters page one had. */
function searchHref(
  locale: ReturnType<typeof getLocale>["code"],
  query: string,
  topic: string,
  language: string,
  source: string,
  date: string,
): string {
  const params = new URLSearchParams({ q: query });
  if (topic) params.set("topic", topic);
  if (language) params.set("lang", language);
  if (source) params.set("source", source);
  if (date) params.set("date", date);
  return `/${locale}/search?${params}`;
}
