import type { Metadata } from "next";
import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { Discover, type DiscoverTopic } from "@/components/discover/Discover";
import { DiscoverSkeleton, RailSkeleton } from "@/components/discover/DiscoverSkeleton";
import { DiscoverRail } from "@/components/rail/DiscoverRail";
import {
  getAcrossLanguages,
  getIssueFrontPage,
  getMarketTiles,
  getTodaysIssue,
  getTopics,
  getTrending,
  getTrendingCompanies,
  type Issue,
} from "@/lib/api";
import { curatedTopicLabel, curatedTopics } from "@/lib/curatedTopics";
import { discoverReader, loadDiscoverPage, savedArticleIds } from "@/lib/discover";
import { parseView, viewTitle, type DiscoverView } from "@/lib/discoverView";
import { getLocale, isLocaleCode, t, type LocaleCode } from "@/lib/i18n";
import { INTERESTS_DISMISSED_COOKIE } from "@/lib/interests";
import {
  RAIL_COOKIE,
  TEMP_UNIT_COOKIE,
  WEATHER_COOKIE,
  parseRailPrefs,
  parseWeatherPlace,
  type RailPrefs,
  type WeatherPlace,
} from "@/lib/railPrefs";

/** Today's edition and its front page, for the rail's teaser. Read without
 * the reader's session: the teaser is not the reader opening Aquila, so it
 * logs nothing - and both reads are shared and cached. */
async function todaysAquila(
  locale: LocaleCode,
): Promise<{ issue: Issue | null; front: Awaited<ReturnType<typeof getIssueFrontPage>> }> {
  const issue = await getTodaysIssue(locale);
  return { issue, front: issue ? await getIssueFrontPage(issue.id, locale) : null };
}

/** Everything the rail shows that comes from the API. All of it is shared
 * between readers and cached (ADR 0014). */
async function loadRail(locale: LocaleCode, languages: string) {
  const [across, aquila, mostRead, markets, companies] = await Promise.all([
    getAcrossLanguages(languages),
    todaysAquila(locale),
    getTrending(languages, 5),
    getMarketTiles(),
    getTrendingCompanies(),
  ]);
  return {
    acrossLanguages: across.data,
    issue: aquila.issue,
    issueFront: aquila.front,
    mostRead: mostRead.data,
    markets: markets.data,
    companies: companies.data,
  };
}

/** A topic's label: the curated one where there is one, the API's otherwise. */
async function topicLabelFor(view: DiscoverView, locale: LocaleCode): Promise<string | undefined> {
  if (view.kind !== "topic") return undefined;
  const topic = (await getTopics(locale)).data.find((item) => item.id === view.topicId);
  return curatedTopicLabel(view.topicId, topic?.label ?? "", locale) || undefined;
}

export async function generateMetadata({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ view?: string; topic?: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const code = isLocaleCode(locale) ? locale : "en";
  const view = parseView(await searchParams);
  // `absolute`: the helper already carries the site name, and For You is
  // the plain name rather than "JustNews · JustNews".
  return {
    title: { absolute: viewTitle(code, view, await topicLabelFor(view, code)) },
    // Written in the body below, so it flushes with the shell.
    description: null,
  };
}

/** The Topics menu offers the top level of the taxonomy (and AI, the one
 * curated subtopic) - a browsable handful, not the whole IPTC tree. */
const MENU_TOPIC = /^medtop:(\d{2}000000|20000045)$/;

/**
 * Discover: the front door. For You, Top and any topic, in the Perplexity
 * rhythm - a lead, rows of three, wide features - beside the reader's rail.
 *
 * The page answers at once and streams (ADR 0014, "Rendering"): the shell
 * and a skeleton first, the feed when its page is ranked, the rail after
 * it. It used to await all nine reads before sending a byte, so the first
 * byte waited on the slowest of them. Only the first page of the feed is
 * rendered here; `Discover` takes over from there (view switches and
 * infinite scroll through /api/discover).
 */
export default async function DiscoverRoute({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ view?: string; topic?: string }>;
}) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const view = parseView(await searchParams);

  return (
    <div className="discover-page">
      {/* A description that flushes with the shell, above anything that
          waits on data - see the note that used to live on Home. */}
      <meta name="description" content={t(active.code, "site.description")} />
      <div className="discover-page__main">
        <Suspense fallback={<DiscoverSkeleton locale={active.code} view={view} />}>
          <DiscoverFeed locale={active.code} view={view} />
        </Suspense>
      </div>
    </div>
  );
}

/** The feed: who is reading, their first page, and what the tabs need. */
async function DiscoverFeed({ locale, view }: { locale: LocaleCode; view: DiscoverView }) {
  const reader = await discoverReader(locale);
  // Started beside the feed's reads and awaited by nothing here: the rail
  // streams in through its own boundary, so a slow widget never holds the
  // feed back. (Starting it only after the feed was measured and dropped:
  // the feed was no faster and the rail arrived seconds later.)
  const rail = loadRail(locale, reader.languages);
  const [page, topicList, saved, cookieStore] = await Promise.all([
    loadDiscoverPage(reader, view, locale),
    getTopics(locale),
    savedArticleIds(reader),
    cookies(),
  ]);

  // The API's list when it has one; the curated ids otherwise, so the menu
  // and "Make it yours" never render empty just because the API is down.
  const source =
    topicList.data.length > 0
      ? topicList.data.map((topic) => ({
          id: topic.id,
          label: curatedTopicLabel(topic.id, topic.label, locale),
        }))
      : curatedTopics(locale);
  const menuTopics: DiscoverTopic[] = source
    .filter((topic) => MENU_TOPIC.test(topic.id))
    .sort((a, b) => a.label.localeCompare(b.label, locale));
  // A deeper topic reached from a link ("Filed under", search) is shown in
  // the menu while it is the view, so the menu names where the reader is.
  const deeper =
    view.kind === "topic" && !menuTopics.some((topic) => topic.id === view.topicId)
      ? source.find((topic) => topic.id === view.topicId)
      : undefined;
  const topics = deeper ? [...menuTopics, deeper] : menuTopics;

  return (
    <>
      {page.degraded && (
        <p className="notice" role="status">
          {t(locale, reader.hasBetaAccess ? "feed.degraded.personal" : "feed.degraded.anonymous")}
        </p>
      )}
      <Discover
        locale={locale}
        initialView={view}
        initialPage={page}
        topics={topics}
        signedIn={Boolean(reader.auth)}
        canPersonalise={Boolean(reader.auth) && reader.hasBetaAccess}
        hasInterests={reader.interests.length > 0}
        learnsFromReading={reader.consented}
        initialSaved={saved}
        readLanguages={reader.languages}
        rail={
          <Suspense fallback={<RailSkeleton />}>
            <Rail
              locale={locale}
              rail={rail}
              weatherPlace={parseWeatherPlace(cookieStore.get(WEATHER_COOKIE)?.value)}
              tempUnit={cookieStore.get(TEMP_UNIT_COOKIE)?.value === "f" ? "f" : "c"}
              initialPrefs={parseRailPrefs(cookieStore.get(RAIL_COOKIE)?.value)}
              // Asked until the reader answers - by choosing, or by closing it.
              askInterests={
                reader.interests.length === 0 && !cookieStore.get(INTERESTS_DISMISSED_COOKIE)
              }
              interestTopics={menuTopics}
            />
          </Suspense>
        }
      />
    </>
  );
}

/** The rail, once its reads are in. */
async function Rail({
  locale,
  rail,
  weatherPlace,
  tempUnit,
  initialPrefs,
  askInterests,
  interestTopics,
}: {
  locale: LocaleCode;
  rail: ReturnType<typeof loadRail>;
  weatherPlace: WeatherPlace | null;
  tempUnit: "c" | "f";
  initialPrefs: RailPrefs;
  askInterests: boolean;
  interestTopics: DiscoverTopic[];
}) {
  return (
    <DiscoverRail
      data={{ locale, ...(await rail), weatherPlace, tempUnit }}
      initialPrefs={initialPrefs}
      askInterests={askInterests}
      interestTopics={interestTopics}
    />
  );
}
