import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
import { FeedSkeleton } from "@/components/FeedSkeleton";
import { Pagination } from "@/components/Pagination";
import { SearchControls } from "@/components/SearchControls";
import { getMe, getSaves, getTopics, searchArticles } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode, readerLanguages, t } from "@/lib/i18n";
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
    title: q
      ? t(code, "search.titleWithQuery", { query: q })
      : t(code, "search.heading"),
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
  }>;
}) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const { q, cursor, topic, lang } = await searchParams;
  const query = (q ?? "").trim();
  // An unknown locale code in `lang` is dropped rather than passed through:
  // no query may return content in a language this product does not ship.
  const language = lang && isLocaleCode(lang) ? lang : "";
  const topics = await getTopics(active.code);

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
        topics={topics.data}
      />

      <Suspense
        key={`${query}:${topic ?? ""}:${language}:${cursor ?? "start"}`}
        fallback={
          query.length >= 2 ? (
            <FeedSkeleton layout="list" secondaries={0} rows={5} />
          ) : null
        }
      >
        <SearchBody
          locale={active.code}
          query={query}
          topic={topic ?? ""}
          language={language}
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
  cursor,
}: {
  locale: ReturnType<typeof getLocale>["code"];
  query: string;
  topic: string;
  language: string;
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
  const languages =
    language || readerLanguages(profile?.preferred_languages, locale);

  const [results, savedIds] = await Promise.all([
    query.length >= 2
      ? searchArticles({ query, languages, topic: topic || undefined, cursor })
      : Promise.resolve({
          data: { items: [], next_cursor: null },
          degraded: false,
        }),
    auth
      ? getSaves(auth).then(
          (page) => new Set(page.data.items.map((item) => item.article.id)),
        )
      : Promise.resolve(new Set<number>()),
  ]);

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

      {query.length >= 2 &&
        results.data.items.length === 0 &&
        !results.degraded && (
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
        <FeedList
          items={results.data.items.map((article) => ({
            article,
            saved: savedIds.has(article.id),
          }))}
          locale={locale}
          surface="search"
          signedIn={Boolean(session)}
          revalidatePath={searchHref(locale, query, topic, language)}
          layout="list"
        />
      )}

      {/* The query rides in baseHref, so page two is still a search for the
          same thing - this route has accepted a cursor since Stage 2 and
          nothing ever linked to it. */}
      {query.length >= 2 && (
        <Pagination
          locale={locale}
          baseHref={searchHref(locale, query, topic, language)}
          nextCursor={results.data.next_cursor}
          onLaterPage={Boolean(cursor)}
        />
      )}
    </>
  );
}

/** The current search as a URL, so page two keeps the filters page one had. */
function searchHref(
  locale: ReturnType<typeof getLocale>["code"],
  query: string,
  topic: string,
  language: string,
): string {
  const params = new URLSearchParams({ q: query });
  if (topic) params.set("topic", topic);
  if (language) params.set("lang", language);
  return `/${locale}/search?${params}`;
}
