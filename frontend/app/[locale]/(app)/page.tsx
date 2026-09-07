import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { notFound } from "next/navigation";

import { BetaGateNotice } from "@/components/BetaGateNotice";
import { DailyBrief } from "@/components/DailyBrief";
import { EmptyState } from "@/components/EmptyState";
import { FeedList } from "@/components/FeedList";
import { GlanceRail } from "@/components/GlanceRail";
import { HomeSkeleton } from "@/components/HomeSkeleton";
import { HomeTabs, type HomeTab } from "@/components/HomeTabs";
import { Pagination } from "@/components/Pagination";
import { TrendingRail } from "@/components/TrendingRail";
import {
  getArticles,
  getFeed,
  getHistory,
  getMe,
  getSaves,
  getStats,
  getTrending,
  type Article,
} from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode, readerLanguages, t } from "@/lib/i18n";
import { getSession } from "@/lib/session";

// The layout's description would otherwise also be emitted, deferred, as a
// second identical tag. Nulling it here leaves exactly the hoisted one.
export const metadata: Metadata = { description: null };

/**
 * Home reads in three levels, not one feed.
 *
 *   1. What matters          - §17's Big Three: one dominant story, two beside
 *   2. What you should know  - §18: two picture stories over four text entries
 *   3. More from the world   - §19: the denser stream, under the tabs
 *
 * The second-pass audit's complaint (§15, §31) was that the levels existed but
 * every level was built from the same card, so the page still read as one
 * feed with headings in it. The fix is that each level now has a *different*
 * composition: big and spacious, then mixed picture-and-text, then dense
 * two-column rows. §32's rule holds throughout - these are rules, type and
 * whitespace, not a page of boxes.
 *
 * The ranking is untouched; this is presentation. The feed still arrives in
 * one ranked order and the tiers are slices of it, so the reader's top story
 * is still the model's top story - what changes is that the page stops
 * presenting the fifteenth as though it were the first.
 */
const TIER_ONE = 3;
const TIER_ONE_LEADS = 1;
/** §18's "approximately 5-10": six, split two picture-led and four text. */
const TIER_TWO = 6;
const TIER_TWO_FEATURES = 1;
const TIER_TWO_PICTURES = 2;
const TAB_PAGE_SIZE = 10;

function isHomeTab(value: string | undefined): value is HomeTab {
  return value === "trending" || value === "history" || value === "saved";
}

/**
 * The whole page as a Suspense boundary would be a route-level `loading.tsx`,
 * and that is measurably worse: a streaming route flushes its shell before
 * Next has resolved the route's metadata, so the meta description is not in
 * the initial document. Measured on this page - Lighthouse SEO 100 -> 92,
 * performance 100 -> 97, with the only change being the presence of a
 * loading.tsx. Suspending just the part that waits on the API keeps the
 * skeleton and keeps the head intact.
 */
export default async function FeedPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ cursor?: string; tab?: string }>;
}) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const { cursor, tab: tabParam } = await searchParams;
  const tab: HomeTab = isHomeTab(tabParam) ? tabParam : "forYou";

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
      <meta name="description" content={t(active.code, "site.description")} />
      {/* Keyed on the cursor+tab so switching between them shows the
          skeleton again rather than holding the previous view's cards while
          the new one loads. */}
      <Suspense key={`${tab}:${cursor ?? "start"}`} fallback={<HomeSkeleton />}>
        <FeedBody active={active} cursor={cursor} tab={tab} />
      </Suspense>
    </>
  );
}

async function FeedBody({
  active,
  cursor,
  tab,
}: {
  active: ReturnType<typeof getLocale>;
  cursor?: string;
  tab: HomeTab;
}) {
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
      ? getFeed(auth, { locale: active.code, cursor, pageSize: 24 }).then((page) => ({
          degraded: page.degraded,
          items: page.data.items,
          nextCursor: page.data.next_cursor,
        }))
      : getArticles({ languages, cursor, pageSize: 24 }).then((page) => ({
          degraded: page.degraded,
          // Uniform shape either way - an anonymous read has no impression
          // to report a click against, so there is nothing to attribute.
          items: page.data.items.map((article) => ({ article, impression_id: null })),
          nextCursor: page.data.next_cursor,
        })),
    getStats(),
    getTrending(languages, 20),
    auth && hasBetaAccess
      ? getSaves(auth).then((page) => new Set(page.data.items.map((item) => item.article.id)))
      : Promise.resolve(new Set<number>()),
  ]);

  // The two editorial tiers always lead with the same top stories, whichever
  // tab is selected below them - the tabs switch the dense stream, not the
  // page's own judgement about what matters.
  const tierOne = feed.items.slice(0, TIER_ONE);
  const tierTwo = feed.items.slice(TIER_ONE, TIER_ONE + TIER_TWO);
  const briefArticles = tierOne.slice(1, 4).map((item) => item.article);

  return (
    <>
      {session && !hasBetaAccess && <BetaGateNotice locale={active.code} />}

      {feed.degraded && (
        <p className="notice" role="status">
          {t(active.code, hasBetaAccess ? "feed.degraded.personal" : "feed.degraded.anonymous")}
        </p>
      )}

      {/* The page's real h1 is the hidden one above (present even while the
          Suspense fallback is showing); this is a visible h2 rather than a
          second h1, so the outline stays a single-heading page with one
          subheading, not two competing top-level headings. */}
      {/* §16's quiet editorial header. The standing line is the identity the
          icon rail gave up in Chunk 3 - a 56px rail can carry a monogram and
          nothing else, and §16 asks for the name and the promise here, above
          the greeting, rather than in the navigation. */}
      <div className="home-greeting">
        <p className="home-greeting__standing">
          <span className="home-greeting__mark">JustNews</span>
          <span className="home-greeting__tagline">{t(active.code, "site.tagline")}</span>
        </p>
        <p className="eyebrow">{t(active.code, greetingKey())}</p>
        <h2>{t(active.code, "home.greeting.subtitle")}</h2>
      </div>

      {feed.items.length === 0 ? (
        <EmptyState
          title={t(active.code, "feed.empty.title")}
          body={t(active.code, "feed.empty.body")}
          action={{
            href: `/${active.code}/aquila`,
            label: t(active.code, "feed.empty.action"),
          }}
        />
      ) : (
        <div className="home">
          <div className="home__hero">
            <TierHeading label={t(active.code, "home.tier.matters")} />
            <FeedList
              items={tierOne.map((item) => ({
                article: item.article,
                impressionId: item.impression_id,
                saved: savedIds.has(item.article.id),
              }))}
              locale={active.code}
              surface="feed"
              signedIn={hasBetaAccess}
              revalidatePath={`/${active.code}`}
              leads={TIER_ONE_LEADS}
              secondaries={TIER_ONE - TIER_ONE_LEADS}
              aboveFold
            />
          </div>

          {tierTwo.length > 0 && (
            <div className="home__know">
              <TierHeading label={t(active.code, "home.tier.shouldKnow")} />
              <FeedList
                items={tierTwo.map((item) => ({
                  article: item.article,
                  impressionId: item.impression_id,
                  saved: savedIds.has(item.article.id),
                }))}
                locale={active.code}
                surface="feed"
                signedIn={hasBetaAccess}
                revalidatePath={`/${active.code}`}
                leads={0}
                // §16/§18: "use varied compositions, avoid repeated
                // identical cards". One story opens the band at full-width
                // `feature` weight, two more carry a picture at `secondary`
                // size, and the rest are headline and source only - three
                // distinct treatments instead of six equal rectangles.
                features={TIER_TWO_FEATURES}
                secondaries={TIER_TWO_PICTURES}
                rest="compact"
                allowClusterPromotion
              />
            </div>
          )}

          <div className="home__rail">
            {!stats.degraded && <GlanceRail stats={stats.data} locale={active.code} />}
            <TrendingRail
              articles={trending.data.slice(0, 5)}
              locale={active.code}
              variant="rail"
            />
            <DailyBrief articles={briefArticles} locale={active.code} />
          </div>

          <div className="home__feed">
            <TierHeading label={t(active.code, "home.tier.world")} />
            <HomeTabs
              locale={active.code}
              active={tab}
              signedIn={hasBetaAccess}
              basePath={`/${active.code}`}
            />
            <TabPanel
              tab={tab}
              active={active}
              auth={auth}
              hasBetaAccess={hasBetaAccess}
              feedRest={feed.items.slice(TIER_ONE + TIER_TWO)}
              trending={trending.data}
              savedIds={savedIds}
              cursor={cursor}
              nextCursor={feed.nextCursor ?? null}
            />
          </div>
        </div>
      )}
    </>
  );
}

async function TabPanel({
  tab,
  active,
  auth,
  hasBetaAccess,
  feedRest,
  trending,
  savedIds,
  cursor,
  nextCursor,
}: {
  tab: HomeTab;
  active: ReturnType<typeof getLocale>;
  auth: { accessToken: string; sessionId: string | null } | null;
  hasBetaAccess: boolean;
  feedRest: { article: Article; impression_id: number | null }[];
  trending: Article[];
  savedIds: Set<number>;
  cursor?: string;
  nextCursor: string | null;
}) {
  if (tab === "trending") {
    return (
      <FeedList
        items={trending.map((article) => ({ article }))}
        locale={active.code}
        surface="explore"
        signedIn={hasBetaAccess}
        revalidatePath={`/${active.code}`}
        layout="list"
        allowClusterPromotion
      />
    );
  }

  if (tab === "history" && auth && hasBetaAccess) {
    const page = await getHistory(auth, undefined, TAB_PAGE_SIZE);
    return page.data.items.length === 0 ? (
      <p className="notice">{t(active.code, "history.empty.title")}</p>
    ) : (
      <>
        <FeedList
          items={page.data.items.map((item) => ({
            key: `${item.article.id}-${item.viewed_at}`,
            article: item.article,
            saved: savedIds.has(item.article.id),
          }))}
          locale={active.code}
          surface="feed"
          signedIn={hasBetaAccess}
          revalidatePath={`/${active.code}`}
          layout="list"
        />
        <p className="form-note">
          <Link href={`/${active.code}/history`}>{t(active.code, "history.heading")} →</Link>
        </p>
      </>
    );
  }

  if (tab === "saved" && auth && hasBetaAccess) {
    const page = await getSaves(auth);
    const items = page.data.items.slice(0, TAB_PAGE_SIZE);
    return items.length === 0 ? (
      <p className="notice">{t(active.code, "saved.empty.title")}</p>
    ) : (
      <>
        <FeedList
          items={items.map((item) => ({ article: item.article, saved: true }))}
          locale={active.code}
          surface="feed"
          signedIn={hasBetaAccess}
          revalidatePath={`/${active.code}`}
          layout="list"
        />
        <p className="form-note">
          <Link href={`/${active.code}/saved`}>{t(active.code, "saved.heading")} →</Link>
        </p>
      </>
    );
  }

  // "forYou" - the rest of the ranked feed, continuing where the hero left off.
  return (
    <>
      <FeedList
        items={feedRest.map((item) => ({
          article: item.article,
          impressionId: item.impression_id,
          saved: savedIds.has(item.article.id),
        }))}
        locale={active.code}
        surface="feed"
        signedIn={hasBetaAccess}
        revalidatePath={`/${active.code}`}
        layout="list"
        allowClusterPromotion
      />
      <Pagination
        locale={active.code}
        baseHref={`/${active.code}`}
        nextCursor={nextCursor}
        onLaterPage={Boolean(cursor)}
      />
    </>
  );
}

/**
 * A tier's standing label.
 *
 * An h2 rather than a styled paragraph: these are the page's three real
 * divisions, and a screen reader's heading list should be able to say so.
 * The page's h1 is the visually hidden one at the top, so this is the right
 * level and the outline stays flat rather than nesting.
 */
function TierHeading({ label }: { label: string }) {
  return <h2 className="home-tier">{label}</h2>;
}

/** UTC-based: there is no reader timezone signal on the server without
 * client JS, so this is a friendly heuristic, not a precise local greeting. */
function greetingKey(): "home.greeting.morning" | "home.greeting.afternoon" | "home.greeting.evening" {
  const hour = new Date().getUTCHours();
  if (hour < 12) return "home.greeting.morning";
  if (hour < 18) return "home.greeting.afternoon";
  return "home.greeting.evening";
}
