import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";

import { BetaGateNotice } from "@/components/BetaGateNotice";
import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
import { FeedSkeleton } from "@/components/FeedSkeleton";
import { TrendingRail } from "@/components/TrendingRail";
import { getArticles, getFeed, getMe, getSaves, getStats, getTrending } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode, readerLanguages, t } from "@/lib/i18n";
import { getSession } from "@/lib/session";

// The layout's description would otherwise also be emitted, deferred, as a
// second identical tag. Nulling it here leaves exactly the hoisted one.
export const metadata: Metadata = { description: null };

/**
 * The whole page as a Suspense boundary would be a route-level `loading.tsx`,
 * and that is measurably worse: a streaming route flushes its shell before
 * Next has resolved the route's metadata, so the meta description is not in
 * the initial document. Measured on this page - Lighthouse SEO 100 -> 92,
 * performance 100 -> 97, with the only change being the presence of a
 * loading.tsx. Suspending just the part that waits on the API keeps the
 * skeleton and keeps the head intact.
 */
export default async function FeedPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);

  return (
    <>
      {/* The masthead's wordmark is a link, not a heading - axe correctly
          flags a page with no h1 at all. Visually hidden: the design
          doesn't need a second, redundant "JustNews" banner under the one
          already in the header, it just needs a real heading to exist. */}
      <h1 className="visually-hidden">{t(active.code, "feed.heading")}</h1>
      {/* A suspending page streams its shell before Next has resolved route
          metadata, so the description from generateMetadata is not in the
          initial document - Lighthouse SEO drops to 92. React hoists this tag
          into <head>, and it sits above the Suspense boundary so it flushes
          with the shell. It lives on the two suspending routes rather than in
          the layout: in the layout it would also land on the article route,
          ahead of that article's own, more specific description. */}
      <meta name="description" content="Personalised, multilingual news." />
      <Suspense fallback={<FeedSkeleton />}>
        <FeedBody active={active} />
      </Suspense>
    </>
  );
}

async function FeedBody({ active }: { active: ReturnType<typeof getLocale> }) {
  const session = await getSession();

  const auth = session
    ? { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() }
    : null;
  const profile = auth ? await getMe(auth) : null;
  const hasBetaAccess = profile?.has_beta_access ?? false;
  // Anonymous readers have told us nothing, so the locale is all we have. A
  // signed-in reader waiting on an invite has already chosen their languages
  // in onboarding, and this holding page is the first thing that should
  // honour them.
  const languages = readerLanguages(profile?.preferred_languages, active.code);

  const [feed, stats, trending, savedIds] = await Promise.all([
    auth && hasBetaAccess
      ? getFeed(auth, { locale: active.code, pageSize: 24 }).then((page) => ({
          degraded: page.degraded,
          items: page.data.items,
          nextCursor: page.data.next_cursor,
        }))
      : getArticles({ languages, pageSize: 24 }).then((page) => ({
          degraded: page.degraded,
          // Uniform shape either way - an anonymous read has no impression
          // to report a click against, so there is nothing to attribute.
          items: page.data.items.map((article) => ({ article, impression_id: null })),
          nextCursor: page.data.next_cursor,
        })),
    getStats(),
    getTrending(languages),
    auth && hasBetaAccess
      ? getSaves(auth).then((page) => new Set(page.data.items.map((item) => item.article.id)))
      : Promise.resolve(new Set<number>()),
  ]);

  return (
    <>
      {session && !hasBetaAccess && <BetaGateNotice locale={active.code} />}

      {feed.degraded && (
        <p className="notice" role="status">
          {t(active.code, hasBetaAccess ? "feed.degraded.personal" : "feed.degraded.anonymous")}
        </p>
      )}

      {feed.items.length === 0 ? (
        <EmptyState
          title={t(active.code, "feed.empty.title")}
          body={t(active.code, "feed.empty.body")}
          action={{
            href: `/${active.code}/explore`,
            label: t(active.code, "feed.empty.action"),
          }}
        />
      ) : (
        <FeedList
          items={feed.items.map((item) => ({
            article: item.article,
            impressionId: item.impression_id,
            saved: savedIds.has(item.article.id),
          }))}
          locale={active.code}
          surface="feed"
          signedIn={hasBetaAccess}
          revalidatePath={`/${active.code}`}
          aboveFold
        />
      )}

      <TrendingRail articles={trending.data} locale={active.code} />

      {!stats.degraded && (
        // dt-then-dd per stat, each pair wrapped in its own div - the only
        // content model <dl> actually allows. <b> stood in for <dd> before,
        // which axe (rightly) flags: a <dl> whose direct children aren't
        // dt/dd groups.
        <dl className="stats">
          <div>
            <dt>{t(active.code, "stats.articles")}</dt>
            <dd>{stats.data.articles.toLocaleString(active.code)}</dd>
          </div>
          <div>
            <dt>{t(active.code, "stats.sources")}</dt>
            <dd>{stats.data.sources.toLocaleString(active.code)}</dd>
          </div>
          <div>
            <dt>{t(active.code, "stats.languages")}</dt>
            <dd>{stats.data.languages.toLocaleString(active.code)}</dd>
          </div>
          <div>
            <dt>{t(active.code, "stats.stories")}</dt>
            <dd>{stats.data.story_clusters.toLocaleString(active.code)}</dd>
          </div>
        </dl>
      )}

    </>
  );
}
