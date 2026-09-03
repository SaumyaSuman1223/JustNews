import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";

import { BlindspotRail } from "@/components/BlindspotRail";
import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
import { FeedSkeleton } from "@/components/FeedSkeleton";
import { Pagination } from "@/components/Pagination";
import Link from "next/link";

import { getBlindspots, getEditions, getExplore, getMe, getSaves } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode, readerLanguages, t } from "@/lib/i18n";
import { getSession } from "@/lib/session";

// A function rather than a static object so the tab title is in the reader's
// language too - it is the one string that shows up outside the page.
export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return {
    title: t(isLocaleCode(locale) ? locale : "en", "explore.heading"),
    description: null,
  };
}

// Every request logs the impressions it served, so this page cannot be
// statically rendered or shared from a cache - two readers must not be
// attributed the same impression rows.
export const dynamic = "force-dynamic";

export default async function ExplorePage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ cursor?: string }>;
}) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const { cursor } = await searchParams;

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
        <h1>{t(active.code, "explore.heading")}</h1>
        <p>{t(active.code, "explore.intro")}</p>
      </div>
      {/* Suspended here rather than in a route-level loading.tsx: a streaming
          route flushes before Next resolves its metadata, which costs the
          page its meta description. See the note on the feed page. */}
      <Suspense key={cursor ?? "start"} fallback={<FeedSkeleton />}>
        <ExploreBody active={active} cursor={cursor} />
      </Suspense>
    </>
  );
}

async function ExploreBody({
  active,
  cursor,
}: {
  active: ReturnType<typeof getLocale>;
  cursor?: string;
}) {
  // Deliberately no beta gate and no sign-in requirement: explore is the
  // surface a reader sees *before* they have either.
  const session = await getSession();
  const auth = session
    ? { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() }
    : null;

  // The reader's chosen languages decide what this page may return, so the
  // profile has to land before the queries that filter on it. One extra
  // round trip, and only for signed-in readers - the anonymous path, which is
  // the majority of pageviews here, still starts its fetches immediately.
  const profile = auth ? await getMe(auth) : null;
  const languages = readerLanguages(profile?.preferred_languages, active.code);

  const [page, blindspots, editions, savedIds] = await Promise.all([
    getExplore(auth, { locale: active.code, languages, cursor, pageSize: 24 }),
    // Blindspots are stories covered in *no* language the reader reads, so
    // this argument has to be the full set or the rail invents gaps that are
    // not there.
    getBlindspots(languages),
    getEditions(languages),
    auth
      ? getSaves(auth).then((saves) => new Set(saves.data.items.map((item) => item.article.id)))
      : Promise.resolve(new Set<number>()),
  ]);

  return (
    <>
      {page.degraded && (
        <p className="notice" role="status">
          {t(active.code, "explore.degraded")}
        </p>
      )}

      {/* The edition chips and the blindspot rail orient a reader arriving at
          Explore. Page two is someone already reading; repeating them there
          would push the headlines they asked for further down. */}
      {!cursor && editions.data.length > 0 && (
        <nav aria-label={t(active.code, "explore.editions")}>
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

      {!cursor && <BlindspotRail blindspots={blindspots.data} locale={active.code} />}

      {page.data.items.length === 0 ? (
        <EmptyState
          title={t(active.code, "explore.empty.title")}
          body={t(active.code, "explore.empty.body")}
          action={{
            href: `/${active.code}/topics`,
            label: t(active.code, "explore.empty.action"),
          }}
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

      <Pagination
        locale={active.code}
        baseHref={`/${active.code}/explore`}
        nextCursor={page.data.next_cursor}
        onLaterPage={Boolean(cursor)}
      />
    </>
  );
}
