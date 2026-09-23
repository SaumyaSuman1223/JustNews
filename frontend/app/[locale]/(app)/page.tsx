import type { Metadata } from "next";
import { cookies } from "next/headers";
import { notFound } from "next/navigation";

import { Discover, type DiscoverTopic } from "@/components/discover/Discover";
import { DiscoverRail } from "@/components/rail/DiscoverRail";
import { getMarketTiles, getTopics, getTrendingCompanies } from "@/lib/api";
import { curatedTopicLabel } from "@/lib/curatedTopics";
import { discoverReader, loadDiscoverPage, savedArticleIds } from "@/lib/discover";
import { parseView } from "@/lib/discoverView";
import { getLocale, isLocaleCode, t } from "@/lib/i18n";
import { INTERESTS_DISMISSED_COOKIE } from "@/lib/interests";
import {
  RAIL_COOKIE,
  TEMP_UNIT_COOKIE,
  WEATHER_COOKIE,
  parseRailPrefs,
  parseWeatherPlace,
} from "@/lib/railPrefs";

export const metadata: Metadata = { description: null };

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
  const topics: DiscoverTopic[] = topicList.data
    .filter((topic) => MENU_TOPIC.test(topic.id))
    .map((topic) => ({ id: topic.id, label: curatedTopicLabel(topic.id, topic.label, active.code) }))
    .sort((a, b) => a.label.localeCompare(b.label, active.code));

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
        askInterests={
          reader.interests.length === 0 && !cookieStore.get(INTERESTS_DISMISSED_COOKIE)
        }
        interestTopics={topics}
      />
    </div>
  );
}
