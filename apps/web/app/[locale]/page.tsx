import Image from "next/image";

import { getArticles, getStats } from "@/lib/api";
import { formatRelativeTime, getLocale, isLocaleCode } from "@/lib/i18n";
import { notFound } from "next/navigation";

// Rendered on the server and cached at the edge. Anonymous, cacheable routes
// like this one never reach Cloud Run, which is what absorbs the transatlantic
// latency for readers outside North America (ADR 0003).
export const revalidate = 60;

export default async function FeedPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);

  const [feed, stats] = await Promise.all([
    getArticles({ languages: active.code, pageSize: 24 }),
    getStats(),
  ]);

  return (
    <>
      {feed.degraded && (
        <p className="notice" role="status">
          Live headlines are unavailable right now, so this page may be out of date. Everything
          else still works.
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
          {feed.data.items.map((article) => (
            <li key={article.id} className="card">
              {article.image_url && (
                <Image
                  className="card__media"
                  src={article.image_url}
                  alt=""
                  width={640}
                  height={360}
                  unoptimized
                />
              )}
              <div className="card__body">
                <h2 className="card__title">
                  {/* Always link out to the publisher. We store metadata only. */}
                  <a href={article.url} target="_blank" rel="noopener noreferrer nofollow">
                    {article.title}
                  </a>
                </h2>
                {article.snippet && <p className="card__snippet">{article.snippet}</p>}
                <p className="card__meta">
                  <span>{article.source_name}</span>
                  <time dateTime={article.published_at}>
                    {formatRelativeTime(article.published_at, active.code)}
                  </time>
                  {article.language !== active.code && (
                    <span className="badge">{article.language}</span>
                  )}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
