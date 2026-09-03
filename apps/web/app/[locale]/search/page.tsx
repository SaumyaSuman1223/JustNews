import type { Metadata } from "next";

import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
import { getSaves, searchArticles } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode } from "@/lib/i18n";
import { getSession } from "@/lib/session";
import { notFound } from "next/navigation";

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}): Promise<Metadata> {
  const { q } = await searchParams;
  return { title: q ? `Search: ${q}` : "Search" };
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

  const [results, savedIds] = await Promise.all([
    query.length >= 2
      ? searchArticles({ query, languages: active.code, cursor })
      : Promise.resolve({ data: { items: [], next_cursor: null }, degraded: false }),
    session
      ? getSaves({ accessToken: session.accessToken, sessionId: await getBrowsingSessionId() }).then(
          (page) => new Set(page.data.items.map((item) => item.article.id)),
        )
      : Promise.resolve(new Set<number>()),
  ]);

  return (
    <>
      <div className="page-header">
        <h1>Search</h1>
        <p>Full text search over headlines and summaries in {active.label}.</p>
      </div>

      {results.degraded && (
        <p className="notice" role="status">
          Search is unavailable right now. Try browsing by{" "}
          <a href={`/${active.code}/topics`}>topic</a> instead.
        </p>
      )}

      {query.length > 0 && query.length < 2 && (
        <p className="empty">Type at least two characters to search.</p>
      )}

      {query.length >= 2 && results.data.items.length === 0 && !results.degraded && (
        <EmptyState
          title={`No headlines match \u201c${query}\u201d in ${active.label}`}
          body="Try a shorter phrase, or a different language - the same story is often filed under quite different words."
          action={{ href: `/${active.code}/topics`, label: "Browse topics" }}
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
