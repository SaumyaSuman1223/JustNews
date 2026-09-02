import { notFound } from "next/navigation";

import { ArticleCard } from "@/components/ArticleCard";
import { BetaGateNotice } from "@/components/BetaGateNotice";
import { getArticles, getFeed, getMe, getSaves, getStats } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode } from "@/lib/i18n";
import { getSession } from "@/lib/session";

export default async function FeedPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const session = await getSession();

  const auth = session
    ? { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() }
    : null;
  const profile = auth ? await getMe(auth) : null;
  const hasBetaAccess = profile?.has_beta_access ?? false;

  const [feed, stats, savedIds] = await Promise.all([
    auth && hasBetaAccess
      ? getFeed(auth, { locale: active.code, pageSize: 24 }).then((page) => ({
          degraded: page.degraded,
          items: page.data.items,
          nextCursor: page.data.next_cursor,
        }))
      : getArticles({ languages: active.code, pageSize: 24 }).then((page) => ({
          degraded: page.degraded,
          // Uniform shape either way - an anonymous read has no impression
          // to report a click against, so there is nothing to attribute.
          items: page.data.items.map((article) => ({ article, impression_id: null })),
          nextCursor: page.data.next_cursor,
        })),
    getStats(),
    auth && hasBetaAccess
      ? getSaves(auth).then((page) => new Set(page.data.items.map((item) => item.article.id)))
      : Promise.resolve(new Set<number>()),
  ]);

  return (
    <>
      {/* The masthead's wordmark is a link, not a heading - axe correctly
          flags a page with no h1 at all. Visually hidden: the design
          doesn't need a second, redundant "JustNews" banner under the one
          already in the header, it just needs a real heading to exist. */}
      <h1 className="visually-hidden">Feed</h1>
      {session && !hasBetaAccess && <BetaGateNotice locale={active.code} />}

      {feed.degraded && (
        <p className="notice" role="status">
          {hasBetaAccess
            ? "Your feed is unavailable right now, so this page may be out of date."
            : "Live headlines are unavailable right now, so this page may be out of date."}{" "}
          Everything else still works.
        </p>
      )}

      {!stats.degraded && (
        // dt-then-dd per stat, each pair wrapped in its own div - the only
        // content model <dl> actually allows. <b> stood in for <dd> before,
        // which axe (rightly) flags: a <dl> whose direct children aren't
        // dt/dd groups.
        <dl className="stats">
          <div>
            <dt>articles</dt>
            <dd>{stats.data.articles.toLocaleString(active.code)}</dd>
          </div>
          <div>
            <dt>sources</dt>
            <dd>{stats.data.sources.toLocaleString(active.code)}</dd>
          </div>
          <div>
            <dt>languages</dt>
            <dd>{stats.data.languages.toLocaleString(active.code)}</dd>
          </div>
          <div>
            <dt>stories</dt>
            <dd>{stats.data.story_clusters.toLocaleString(active.code)}</dd>
          </div>
        </dl>
      )}

      {feed.items.length === 0 ? (
        <p className="empty">
          Nothing here yet in {active.label}. Run <code>make ingest</code> to fetch headlines, or
          pick another language above.
        </p>
      ) : (
        <ul className="feed">
          {feed.items.map((item, index) => (
            <ArticleCard
              key={item.article.id}
              article={item.article}
              impressionId={item.impression_id}
              locale={active.code}
              surface="feed"
              position={index}
              signedIn={hasBetaAccess}
              saved={savedIds.has(item.article.id)}
              revalidatePath={`/${active.code}`}
            />
          ))}
        </ul>
      )}
    </>
  );
}
