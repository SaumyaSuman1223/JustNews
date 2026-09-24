import type { Metadata } from "next";
import { cookies } from "next/headers";
import { notFound } from "next/navigation";

import { Discover, type DiscoverTopic } from "@/components/discover/Discover";
import { DiscoverRail } from "@/components/rail/DiscoverRail";
import { getMarketTiles, getTopics, getTrendingCompanies } from "@/lib/api";
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
} from "@/lib/railPrefs";

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
 * Only the first page is rendered here, so the page is complete before any
 * JavaScript runs; `Discover` takes over from there (view switches and
 * infinite scroll through /api/discover). Every data read is in parallel.
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
  const reader = await discoverReader(active.code);

  const [page, topicList, saved, markets, companies, cookieStore] = await Promise.all([
    loadDiscoverPage(reader, view, active.code),
    getTopics(active.code),
    savedArticleIds(reader),
    // Both served from the API's Redis cache (ADR 0014) - fast enough to
    // render with the page rather than pop in after it.
    getMarketTiles(),
    getTrendingCompanies(),
    cookies(),
  ]);
  // The API's list when it has one; the curated ids otherwise, so the menu
  // and "Make it yours" never render empty just because the API is down.
  const source =
    topicList.data.length > 0
      ? topicList.data.map((topic) => ({
          id: topic.id,
          label: curatedTopicLabel(topic.id, topic.label, active.code),
        }))
      : curatedTopics(active.code);
  const menuTopics: DiscoverTopic[] = source
    .filter((topic) => MENU_TOPIC.test(topic.id))
    .sort((a, b) => a.label.localeCompare(b.label, active.code));
  // A deeper topic reached from a link ("Filed under", search) is shown in
  // the menu while it is the view, so the menu names where the reader is.
  const deeper =
    view.kind === "topic" && !menuTopics.some((topic) => topic.id === view.topicId)
      ? source.find((topic) => topic.id === view.topicId)
      : undefined;
  const topics = deeper ? [...menuTopics, deeper] : menuTopics;

  return (
    <div className="discover-page">
      {/* A description that flushes with the shell, above anything that
          waits on data - see the note that used to live on Home. */}
      <meta name="description" content={t(active.code, "site.description")} />
      <div className="discover-page__main">
        {page.degraded && (
          <p className="notice" role="status">
            {t(
              active.code,
              reader.hasBetaAccess ? "feed.degraded.personal" : "feed.degraded.anonymous",
            )}
          </p>
        )}
        <Discover
          locale={active.code}
          initialView={view}
          initialPage={page}
          topics={topics}
          signedIn={Boolean(reader.auth)}
          canPersonalise={Boolean(reader.auth) && reader.hasBetaAccess}
          hasInterests={reader.interests.length > 0}
          initialSaved={saved}
        />
      </div>
      <DiscoverRail
        data={{
          locale: active.code,
          markets: markets.data,
          companies: companies.data,
          weatherPlace: parseWeatherPlace(cookieStore.get(WEATHER_COOKIE)?.value),
          tempUnit: cookieStore.get(TEMP_UNIT_COOKIE)?.value === "f" ? "f" : "c",
        }}
        initialPrefs={parseRailPrefs(cookieStore.get(RAIL_COOKIE)?.value)}
        // Asked until the reader answers - by choosing, or by closing it.
        askInterests={reader.interests.length === 0 && !cookieStore.get(INTERESTS_DISMISSED_COOKIE)}
        interestTopics={menuTopics}
      />
    </div>
  );
}
