import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";

import { BlindspotRail } from "@/components/BlindspotRail";
import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
import { FeedSkeleton } from "@/components/FeedSkeleton";
import Link from "next/link";

import { getBlindspots, getEditions, getExplore, getSaves } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode } from "@/lib/i18n";
import { getSession } from "@/lib/session";

export const metadata: Metadata = { title: "Explore", description: null };

// Every request logs the impressions it served, so this page cannot be
// statically rendered or shared from a cache - two readers must not be
// attributed the same impression rows.
export const dynamic = "force-dynamic";

export default async function ExplorePage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);

  return (
    <>
      {/* A suspending page streams its shell before Next has resolved route
          metadata, so the description from generateMetadata is not in the
          initial document - Lighthouse SEO drops to 92. React hoists this tag
          into <head>, and it sits above the Suspense boundary so it flushes
          with the shell. It lives on the two suspending routes rather than in
          the layout: in the layout it would also land on the article route,
          ahead of that article's own, more specific description. */}
      <meta name="description" content="Personalised, multilingual news." />
      <div className="page-header">
        <h1>Explore</h1>
        <p>
          The latest across every source we follow, ranked by recency and spread across topics -
          the same for everyone, whether or not you are signed in.
        </p>
      </div>
      {/* Suspended here rather than in a route-level loading.tsx: a streaming
          route flushes before Next resolves its metadata, which costs the
          page its meta description. See the note on the feed page. */}
      <Suspense fallback={<FeedSkeleton />}>
        <ExploreBody active={active} />
      </Suspense>
    </>
  );
}

async function ExploreBody({ active }: { active: ReturnType<typeof getLocale> }) {
  // Deliberately no beta gate and no sign-in requirement: explore is the
  // surface a reader sees *before* they have either.
  const session = await getSession();
  const auth = session
    ? { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() }
    : null;

  const [page, blindspots, editions, savedIds] = await Promise.all([
    getExplore(auth, { locale: active.code, languages: active.code, pageSize: 24 }),
    getBlindspots(active.code),
    getEditions(active.code),
    auth
      ? getSaves(auth).then((saves) => new Set(saves.data.items.map((item) => item.article.id)))
      : Promise.resolve(new Set<number>()),
  ]);

  return (
    <>
      {page.degraded && (
        <p className="notice" role="status">
          Live headlines are unavailable right now, so this page may be out of date.
        </p>
      )}

      {editions.data.length > 0 && (
        <nav aria-label="Editions">
          <ul className="chip-list">
            {editions.data.map((edition) => (
              <li key={edition.code}>
                <Link className="chip" href={`/${active.code}/edition/${edition.code}`}>
                  {edition.name}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      )}

      <BlindspotRail blindspots={blindspots.data} locale={active.code} />

      {page.data.items.length === 0 ? (
        <EmptyState
          title={`Nothing to explore in ${active.label} yet`}
          body="No sources we follow have published in this language recently. Switching language in the header will show you what is running elsewhere."
          action={{ href: `/${active.code}/topics`, label: "Browse topics" }}
        />
      ) : (
        <FeedList
          items={page.data.items.map((item) => ({
            article: item.article,
            impressionId: item.impression_id,
            saved: savedIds.has(item.article.id),
          }))}
          locale={active.code}
          surface="explore"
          signedIn={Boolean(auth)}
          revalidatePath={`/${active.code}/explore`}
        />
      )}
    </>
  );
}
