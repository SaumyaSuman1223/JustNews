import "server-only";

import { cookies } from "next/headers";

import {
  getArticles,
  getFeed,
  getMe,
  getSaves,
  getTopArticles,
  getTopics,
  type Article,
} from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { curatedTopicLabel } from "@/lib/curatedTopics";
import type { DiscoverItem, DiscoverPage, DiscoverView } from "@/lib/discoverView";
import { readerLanguages, type LocaleCode } from "@/lib/i18n";
import { INTERESTS_COOKIE, parseInterests } from "@/lib/interests";
import { READING_LANGUAGES_COOKIE, parseReadingLanguages } from "@/lib/readingLanguages";
import { spreadRuns } from "@/lib/spreadRuns";
import type { RankReason } from "@/lib/rankReason";
import { getSession } from "@/lib/session";

/** A Discover page: large enough that one scroll is several screens, small
 * enough that the first byte is not waiting on a long ranking. */
const PAGE_SIZE = 24;
/** How many of the importance order lead the first page of a stream. Top's
 * whole first page is importance-ordered; a topic or interests stream leads
 * with a dozen and continues newest-first. */
const TOP_LEAD = 24;
const TOPIC_LEAD = 12;
/** The most any one source may take of a page of Top. A publisher filing
 * regional briefs by the dozen took 18 of the first 30 cards; Top is what
 * matters now, not who posts most. */
const TOP_PER_SOURCE = 5;

type ApiReason = { kind: "followed_topic" | "trending" | "exploration"; topic_id?: string | null };

/** Who is reading, resolved once per request (getSession and getMe are
 * deduped per request - see lib/session.ts). */
export async function discoverReader(locale: LocaleCode) {
  const session = await getSession();
  const auth = session
    ? { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() }
    : null;
  const profile = auth ? await getMe(auth) : null;
  const store = await cookies();
  // The account's languages when it has some; "Read in" otherwise; the
  // interface language when the reader has said nothing.
  const chosen = profile?.preferred_languages?.length
    ? profile.preferred_languages
    : parseReadingLanguages(store.get(READING_LANGUAGES_COOKIE)?.value);
  return {
    auth,
    hasBetaAccess: profile?.has_beta_access ?? false,
    languages: readerLanguages(chosen, locale),
    interests: parseInterests(store.get(INTERESTS_COOKIE)?.value),
  };
}

type Reader = Awaited<ReturnType<typeof discoverReader>>;

/**
 * One page of a Discover view.
 *
 * For You with the personal ranker goes to `/v1/feed`, which logs what it
 * served with its propensities - so this is never cached, and every page a
 * reader scrolls to is a real serving decision. Everything else is a
 * "stream": the importance order (recency x breadth x trust, one per story)
 * leading the first page, then the chronological list by cursor, filtered to
 * the view's topics. Later pages may repeat a story the lead already placed;
 * the client drops ids it has shown.
 */
export async function loadDiscoverPage(
  reader: Reader,
  view: DiscoverView,
  locale: LocaleCode,
  cursor?: string,
): Promise<DiscoverPage> {
  if (view.kind === "for-you" && reader.auth && reader.hasBetaAccess) {
    const [page, topics] = await Promise.all([
      getFeed(reader.auth, { locale, cursor, pageSize: PAGE_SIZE }),
      getTopics(locale),
    ]);
    const labels = new Map(
      topics.data.map((topic) => [topic.id, curatedTopicLabel(topic.id, topic.label, locale)]),
    );
    return {
      items: page.data.items.map((item) => ({
        article: item.article,
        impressionId: item.impression_id ?? null,
        why: whyFor(item.reason as ApiReason | null | undefined, labels),
      })),
      nextCursor: page.data.next_cursor ?? null,
      degraded: page.degraded,
    };
  }

  const topics =
    view.kind === "topic"
      ? [view.topicId]
      : view.kind === "for-you" && reader.interests.length > 0
        ? reader.interests
        : undefined;
  return stream(reader.languages, topics, cursor);
}

/**
 * A page's articles with no source running more than twice in a row - the
 * next article from another source is brought forward instead - and, when
 * `cap` is set, no source more than `cap` times on the page. Order is
 * otherwise kept: this spreads a run, it does not re-rank.
 */
export function spreadSources(articles: Article[], cap?: number): Article[] {
  const counts = new Map<string, number>();
  const kept = articles.filter((article) => {
    const seen = counts.get(article.source_slug) ?? 0;
    if (cap !== undefined && seen >= cap) return false;
    counts.set(article.source_slug, seen + 1);
    return true;
  });
  return spreadRuns(kept, (article) => article.source_slug);
}

async function stream(
  languages: string,
  topics: string[] | undefined,
  cursor: string | undefined,
): Promise<DiscoverPage> {
  // No topics is Top, or For You before a reader has chosen any.
  const top = topics === undefined;
  const [page, ranked] = await Promise.all([
    getArticles({ languages, topics, cursor, pageSize: PAGE_SIZE }),
    cursor ? Promise.resolve(null) : getTopArticles(languages, top ? TOP_LEAD : TOPIC_LEAD, topics),
  ]);
  const lead = ranked && !ranked.degraded ? ranked.data : [];
  const placed = new Set(lead.map((article) => article.id));
  // Spread and capped over the whole page - the ranked lead as well as the
  // newest-first rest - so neither half can stack one source.
  const articles: Article[] = spreadSources(
    [...lead, ...page.data.items.filter((article) => !placed.has(article.id))],
    top ? TOP_PER_SOURCE : undefined,
  );
  return {
    items: articles.map((article): DiscoverItem => ({ article, impressionId: null, why: null })),
    nextCursor: page.data.next_cursor ?? null,
    degraded: page.degraded,
  };
}

/** The ranker's own reason, with the topic named the way the reader knows
 * it; a reason for a topic this page cannot name is dropped rather than
 * shown as a raw concept id. */
function whyFor(
  reason: ApiReason | null | undefined,
  labels: Map<string, string>,
): RankReason | null {
  if (!reason) return null;
  if (reason.kind === "followed_topic") {
    const topic = reason.topic_id ? labels.get(reason.topic_id) : undefined;
    return topic ? { kind: "followed_topic", topic } : null;
  }
  return { kind: reason.kind };
}

/** The reader's saved article ids, so hearts render filled. Signed-in
 * readers with access only; everyone else has nothing saved. */
export async function savedArticleIds(reader: Reader): Promise<number[]> {
  if (!reader.auth || !reader.hasBetaAccess) return [];
  const page = await getSaves(reader.auth);
  return page.data.items.map((item) => item.article.id);
}
