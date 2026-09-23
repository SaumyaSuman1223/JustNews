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
import type { RankReason } from "@/lib/rankReason";
import { getSession } from "@/lib/session";

/** A Discover page: large enough that one scroll is several screens, small
 * enough that the first byte is not waiting on a long ranking. */
const PAGE_SIZE = 24;
/** How many of the importance order lead the first page of a stream. */
const TOP_LEAD = 12;

type ApiReason = { kind: "followed_topic" | "trending" | "exploration"; topic_id?: string | null };

/** Who is reading, resolved once per request (getSession and getMe are
 * deduped per request - see lib/session.ts). */
export async function discoverReader(locale: LocaleCode) {
  const session = await getSession();
  const auth = session
    ? { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() }
    : null;
  const profile = auth ? await getMe(auth) : null;
  return {
    auth,
    hasBetaAccess: profile?.has_beta_access ?? false,
    languages: readerLanguages(profile?.preferred_languages, locale),
    interests: parseInterests((await cookies()).get(INTERESTS_COOKIE)?.value),
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

async function stream(
  languages: string,
  topics: string[] | undefined,
  cursor: string | undefined,
): Promise<DiscoverPage> {
  const [page, top] = await Promise.all([
    getArticles({ languages, topics, cursor, pageSize: PAGE_SIZE }),
    cursor ? Promise.resolve(null) : getTopArticles(languages, TOP_LEAD, topics),
  ]);
  const lead = top && !top.degraded ? top.data : [];
  const placed = new Set(lead.map((article) => article.id));
  const articles: Article[] = [
    ...lead,
    ...page.data.items.filter((article) => !placed.has(article.id)),
  ];
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
