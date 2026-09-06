import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
import { FeedSkeleton } from "@/components/FeedSkeleton";
import { Pagination } from "@/components/Pagination";
import { getMe, getSaves, searchArticles } from "@/lib/api";
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
    title: q ? t(code, "search.titleWithQuery", { query: q }) : t(code, "search.heading"),
  };
}

export default async function SearchPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ q?: string; cursor?: string }>;
}) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const { q, cursor } = await searchParams;
  const query = (q ?? "").trim();

  return (
    <>
      <div className="page-header">
        <h1>{t(active.code, "search.heading")}</h1>
        <p>{t(active.code, "search.intro")}</p>
      </div>
      <Suspense
        key={`${query}:${cursor ?? "start"}`}
        fallback={query.length >= 2 ? <FeedSkeleton layout="list" secondaries={0} rows={5} /> : null}
      >
        <SearchBody locale={active.code} query={query} cursor={cursor} />
      </Suspense>
    </>
  );
}

async function SearchBody({
  locale,
  query,
  cursor,
}: {
  locale: ReturnType<typeof getLocale>["code"];
  query: string;
  cursor?: string;
}) {
  const session = await getSession();
  const auth = session
    ? { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() }
    : null;

  // A reader searching for a name expects hits in every language they read,
  // not only the one the interface happens to be in.
  const profile = auth ? await getMe(auth) : null;
  const languages = readerLanguages(profile?.preferred_languages, locale);

  const [results, savedIds] = await Promise.all([
    query.length >= 2
      ? searchArticles({ query, languages, cursor })
      : Promise.resolve({ data: { items: [], next_cursor: null }, degraded: false }),
    auth
      ? getSaves(auth).then((page) => new Set(page.data.items.map((item) => item.article.id)))
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

      {query.length >= 2 && results.data.items.length === 0 && !results.degraded && (
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
          revalidatePath={`/${locale}/search?q=${encodeURIComponent(query)}`}
          layout="list"
        />
      )}

      {/* The query rides in baseHref, so page two is still a search for the
          same thing - this route has accepted a cursor since Stage 2 and
          nothing ever linked to it. */}
      {query.length >= 2 && (
        <Pagination
          locale={locale}
          baseHref={`/${locale}/search?q=${encodeURIComponent(query)}`}
          nextCursor={results.data.next_cursor}
          onLaterPage={Boolean(cursor)}
        />
      )}
    </>
  );
}
