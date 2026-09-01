import { ArticleCard } from "@/components/ArticleCard";
import { getArticles, getFeed, getSaves, getStats } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode } from "@/lib/i18n";
import { getSession } from "@/lib/session";
import { notFound } from "next/navigation";

export default async function FeedPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const session = await getSession();

  const [feed, stats, savedIds] = await Promise.all([
    session
      ? getFeed(
          { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() },
          { locale: active.code, pageSize: 24 },
        )
      : getArticles({ languages: active.code, pageSize: 24 }),
    getStats(),
    session
      ? getSaves({ accessToken: session.accessToken, sessionId: await getBrowsingSessionId() }).then(
          (page) => new Set(page.data.items.map((item) => item.article.id)),
        )
      : Promise.resolve(new Set<number>()),
  ]);

  return (
    <>
      {feed.degraded && (
        <p className="notice" role="status">
          {session
            ? "Your feed is unavailable right now, so this page may be out of date."
            : "Live headlines are unavailable right now, so this page may be out of date."}{" "}
          Everything else still works.
        </p>
      )}

      {!stats.degraded && (
        <dl className="stats">
          <div>
            <b>{stats.data.articles.toLocaleString(active.code)}</b>
            <dt>articles</dt>
          </div>
          <div>
            <b>{stats.data.sources.toLocaleString(active.code)}</b>
            <dt>sources</dt>
          </div>
          <div>
            <b>{stats.data.languages.toLocaleString(active.code)}</b>
            <dt>languages</dt>
          </div>
          <div>
            <b>{stats.data.story_clusters.toLocaleString(active.code)}</b>
            <dt>stories</dt>
          </div>
        </dl>
      )}

      {feed.data.items.length === 0 ? (
        <p className="empty">
          Nothing here yet in {active.label}. Run <code>make ingest</code> to fetch headlines, or
          pick another language above.
        </p>
      ) : (
        <ul className="feed">
          {feed.data.items.map((article, index) => (
            <ArticleCard
              key={article.id}
              article={article}
              locale={active.code}
              surface="feed"
              position={index}
              signedIn={Boolean(session)}
              saved={savedIds.has(article.id)}
              revalidatePath={`/${active.code}`}
            />
          ))}
        </ul>
      )}
    </>
  );
}
