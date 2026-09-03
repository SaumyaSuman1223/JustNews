import type { Metadata } from "next";

import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
import { getMe, getSaves, searchArticles } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode, readerLanguages, t } from "@/lib/i18n";
import { getSession } from "@/lib/session";
import { notFound } from "next/navigation";

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
  const session = await getSession();
  const auth = session
    ? { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() }
    : null;

  // A reader searching for a name expects hits in every language they read,
  // not only the one the interface happens to be in.
  const profile = auth ? await getMe(auth) : null;
  const languages = readerLanguages(profile?.preferred_languages, active.code);

  const [results, savedIds] = await Promise.all([
    query.length >= 2
      ? searchArticles({ query, languages, cursor })
      : Promise.resolve({ data: { items: [], next_cursor: null }, degraded: false }),
    auth
      ? getSaves(auth).then(
          (page) => new Set(page.data.items.map((item) => item.article.id)),
        )
      : Promise.resolve(new Set<number>()),
  ]);

  return (
    <>
      <div className="page-header">
        <h1>{t(active.code, "search.heading")}</h1>
        <p>{t(active.code, "search.intro")}</p>
      </div>

      {results.degraded && (
        // Two sentences, the second entirely a link. The recovery route used
        // to be a single word inside the sentence, which only lands in the
        // right place in languages built like English.
        <p className="notice" role="status">
          {t(active.code, "search.degraded")}{" "}
          <a href={`/${active.code}/topics`}>{t(active.code, "search.browseInstead")}</a>
        </p>
      )}

      {query.length > 0 && query.length < 2 && (
        <p className="empty">{t(active.code, "search.tooShort")}</p>
      )}

      {query.length >= 2 && results.data.items.length === 0 && !results.degraded && (
        <EmptyState
          title={t(active.code, "search.empty.title", { query })}
          body={t(active.code, "search.empty.body")}
          action={{
            href: `/${active.code}/topics`,
            label: t(active.code, "common.browseTopics"),
          }}
        />
      )}

      {results.data.items.length > 0 && (
        <FeedList
          items={results.data.items.map((article) => ({
            article,
            saved: savedIds.has(article.id),
          }))}
          locale={active.code}
          surface="search"
          signedIn={Boolean(session)}
          revalidatePath={`/${active.code}/search?q=${encodeURIComponent(query)}`}
          layout="list"
        />
      )}
    </>
  );
}
