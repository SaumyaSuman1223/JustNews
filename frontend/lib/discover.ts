import "server-only";

import { cookies } from "next/headers";

import { getDiscover, getMe, getSaves, getTopics } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { hasAnalyticsConsent } from "@/lib/consent";
import { curatedTopicLabel } from "@/lib/curatedTopics";
import type { DiscoverItem, DiscoverPage, DiscoverView } from "@/lib/discoverView";
import { readerLanguages, type LocaleCode } from "@/lib/i18n";
import { INTERESTS_COOKIE, parseInterests } from "@/lib/interests";
import { READ_HISTORY_COOKIE, parseReadHistory } from "@/lib/readHistory";
import { READING_LANGUAGES_COOKIE, parseReadingLanguages } from "@/lib/readingLanguages";
import type { RankReason } from "@/lib/rankReason";
import { getSession } from "@/lib/session";

/** A Discover page: large enough that one scroll is several screens, small
 * enough that the first byte is not waiting on a long ranking. */
const PAGE_SIZE = 24;

type ApiReason = {
  kind:
    | "followed_topic"
    | "followed_source"
    | "followed_story"
    | "similar"
    | "trending"
    | "exploration";
  topic_id?: string | null;
};

/** Who is reading, resolved once per request (getSession and getMe are
 * deduped per request - see lib/session.ts). */
export async function discoverReader(locale: LocaleCode) {
  const session = await getSession();
  const sessionId = await getBrowsingSessionId();
  const auth = session ? { accessToken: session.accessToken, sessionId } : null;
  const profile = auth ? await getMe(auth) : null;
  const store = await cookies();
  const consented = await hasAnalyticsConsent();
  // The account's languages when it has some; "Read in" otherwise; the
  // interface language when the reader has said nothing.
  const chosen = profile?.preferred_languages?.length
    ? profile.preferred_languages
    : parseReadingLanguages(store.get(READING_LANGUAGES_COOKIE)?.value);
  return {
    auth,
    sessionId,
    consented,
    hasBetaAccess: profile?.has_beta_access ?? false,
    languages: readerLanguages(chosen, locale),
    interests: parseInterests(store.get(INTERESTS_COOKIE)?.value),
    // This device's recent reads - only ever set with consent (lib/readHistory.ts).
    history: consented ? parseReadHistory(store.get(READ_HISTORY_COOKIE)?.value) : [],
  };
}

type Reader = Awaited<ReturnType<typeof discoverReader>>;

/**
 * One page of a Discover view, from the API's ranker v2 (ADR 0015): For You,
 * Top and a topic are all one call, for every reader. For You is personal -
 * from the account, or from this device's recent reads when signed out - and
 * an invited reader's For You is the feed experiment. With consent, every
 * page logs what it served and with what probability, so it is never cached
 * here; the one page every unconsented reader shares is cached a layer down.
 *
 * Cursors are the ranker's own: page 2 is the same ranking page 1 was cut
 * from, so no story repeats at the join and none is skipped.
 */
export async function loadDiscoverPage(
  reader: Reader,
  view: DiscoverView,
  locale: LocaleCode,
  cursor?: string,
): Promise<DiscoverPage> {
  const [page, topics] = await Promise.all([
    getDiscover(
      { auth: reader.auth, sessionId: reader.sessionId, consented: reader.consented },
      {
        view: view.kind === "for-you" ? "for_you" : view.kind,
        topic: view.kind === "topic" ? view.topicId : undefined,
        interests: reader.interests,
        history: reader.auth ? undefined : reader.history,
        languages: reader.languages,
        locale,
        cursor,
        pageSize: PAGE_SIZE,
      },
    ),
    // Only For You's reasons name a topic.
    view.kind === "for-you" ? getTopics(locale) : Promise.resolve(null),
  ]);
  const labels = new Map(
    (topics?.data ?? []).map((topic) => [
      topic.id,
      curatedTopicLabel(topic.id, topic.label, locale),
    ]),
  );
  return {
    items: page.data.items.map((item): DiscoverItem => ({
      article: item.article,
      impressionId: item.impression_id ?? null,
      position: item.position,
      why: whyFor(item.reason as ApiReason | null | undefined, labels),
    })),
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
