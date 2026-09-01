/**
 * Server-side API access.
 *
 * Two calling styles, deliberately:
 *
 * Anonymous, cacheable reads (articles, stats, topics, a story, search) use
 * plain `fetch` with an explicit `revalidate` - Next's fetch cache is how
 * these pages avoid a round trip to Cloud Run on every request (ADR 0003).
 * Their *types* still come from the generated schema, so a route that
 * changes shape fails `tsc` here too.
 *
 * Personalised, authenticated calls (the feed, saves, follows, history) go
 * through `@justnews/api-client`'s generated runtime client instead. There is
 * no caching wrinkle to route around - a signed-in reader's data is always
 * request-scoped and never cached - so the generated client's own types and
 * error handling apply directly with nothing to reconcile.
 *
 * Both rules hold regardless of which style is calling: every request has an
 * explicit timeout, and every failure degrades - empty content plus a flag,
 * so the page renders with a banner rather than a 500.
 */
import { createApiClient } from "@justnews/api-client";
import type { components } from "@justnews/api-client";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
const TIMEOUT_MS = 4000;

export type Article = components["schemas"]["ArticleOut"];
export type ArticlePage = components["schemas"]["ArticlePageOut"];
export type CorpusStats = components["schemas"]["StatsOut"];
export type Topic = components["schemas"]["TopicOut"];
export type Story = components["schemas"]["StoryOut"];
export type StoryDetail = components["schemas"]["StoryDetailOut"];
export type FeedPage = components["schemas"]["FeedPageOut"];
export type MeProfile = components["schemas"]["MeOut"];
export type SaveOut = components["schemas"]["SaveOut"];
export type SavePage = components["schemas"]["SavePageOut"];
export type FollowOut = components["schemas"]["FollowOut"];
export type HistoryPage = components["schemas"]["HistoryPageOut"];

export interface Degradable<T> {
  data: T;
  degraded: boolean;
}

// --- anonymous, cacheable reads -----------------------------------------

async function get<T>(path: string, fallback: T, revalidate: number): Promise<Degradable<T>> {
  try {
    const response = await fetch(`${API_URL}${path}`, {
      signal: AbortSignal.timeout(TIMEOUT_MS),
      next: { revalidate },
    });
    // 503 means the API is up but its database is not, and it has told us so
    // deliberately (Retry-After). Everything else non-2xx is equally unusable
    // to the reader; both render the degraded banner rather than an error page.
    if (!response.ok) return { data: fallback, degraded: true };
    return { data: (await response.json()) as T, degraded: false };
  } catch {
    // Timeout, DNS failure, connection refused - all the same to the reader.
    return { data: fallback, degraded: true };
  }
}

export function getArticles(params: {
  languages?: string;
  topic?: string;
  cursor?: string;
  pageSize?: number;
}): Promise<Degradable<ArticlePage>> {
  const query = new URLSearchParams();
  if (params.languages) query.set("languages", params.languages);
  if (params.topic) query.set("topic", params.topic);
  if (params.cursor) query.set("cursor", params.cursor);
  query.set("page_size", String(params.pageSize ?? 20));
  // 60s: a news feed may be a minute stale; it may not be a minute slow.
  return get<ArticlePage>(`/v1/articles?${query}`, { items: [], next_cursor: null }, 60);
}

export function getArticle(id: number): Promise<Degradable<Article | null>> {
  return get<Article | null>(`/v1/articles/${id}`, null, 60);
}

export function getStats(): Promise<Degradable<CorpusStats>> {
  return get<CorpusStats>(
    "/v1/stats",
    { articles: 0, sources: 0, story_clusters: 0, languages: 0 },
    300,
  );
}

export function getTopics(language: string): Promise<Degradable<Topic[]>> {
  // Topics change on a deploy cadence, not a content one.
  return get<Topic[]>(`/v1/topics?language=${encodeURIComponent(language)}`, [], 3600);
}

export function getStory(id: number): Promise<Degradable<StoryDetail | null>> {
  return get<StoryDetail | null>(`/v1/stories/${id}`, null, 60);
}

export function searchArticles(params: {
  query: string;
  languages?: string;
  cursor?: string;
}): Promise<Degradable<ArticlePage>> {
  const query = new URLSearchParams({ q: params.query });
  if (params.languages) query.set("languages", params.languages);
  if (params.cursor) query.set("cursor", params.cursor);
  // Search results are per-query already; a short cache just absorbs repeats
  // (back button, double submit) rather than serving stale results.
  return get<ArticlePage>(`/v1/search?${query}`, { items: [], next_cursor: null }, 30);
}

// --- personalised, authenticated calls ----------------------------------

interface AuthContext {
  accessToken: string;
  sessionId: string;
}

function authedClient({ accessToken, sessionId }: AuthContext) {
  return createApiClient(API_URL, { accessToken, sessionId });
}

const EMPTY_FEED: FeedPage = { items: [], next_cursor: null };

export async function getFeed(
  auth: AuthContext,
  params: { languages?: string; locale: string; cursor?: string; pageSize?: number },
): Promise<Degradable<FeedPage>> {
  const { data, error } = await authedClient(auth).GET("/v1/feed", {
    params: {
      query: {
        languages: params.languages,
        locale: params.locale,
        cursor: params.cursor,
        page_size: params.pageSize ?? 20,
      },
    },
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  if (error || !data) return { data: EMPTY_FEED, degraded: true };
  return { data, degraded: false };
}

export async function getMe(auth: AuthContext): Promise<MeProfile | null> {
  const { data } = await authedClient(auth).GET("/v1/me", {
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  return data ?? null;
}

export async function updateMe(
  auth: AuthContext,
  preferredLanguages: string[],
): Promise<MeProfile | null> {
  const { data } = await authedClient(auth).PATCH("/v1/me", {
    body: { preferred_languages: preferredLanguages },
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  return data ?? null;
}

export async function getSaves(
  auth: AuthContext,
  cursor?: string,
): Promise<Degradable<SavePage>> {
  const { data, error } = await authedClient(auth).GET("/v1/saves", {
    params: { query: { cursor } },
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  if (error || !data) return { data: { items: [], next_cursor: null }, degraded: true };
  return { data, degraded: false };
}

export async function saveArticle(auth: AuthContext, articleId: number): Promise<boolean> {
  const { error } = await authedClient(auth).POST("/v1/saves", {
    body: { article_id: articleId },
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  return !error;
}

export async function unsaveArticle(auth: AuthContext, articleId: number): Promise<boolean> {
  const { error } = await authedClient(auth).DELETE("/v1/saves/{article_id}", {
    params: { path: { article_id: articleId } },
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  return !error;
}

export async function getFollows(auth: AuthContext): Promise<FollowOut[]> {
  const { data } = await authedClient(auth).GET("/v1/follows", {
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  return data ?? [];
}

export async function followTopic(auth: AuthContext, topicId: string): Promise<boolean> {
  const { error } = await authedClient(auth).POST("/v1/follows", {
    body: { topic_id: topicId },
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  return !error;
}

export async function unfollowTopic(auth: AuthContext, topicId: string): Promise<boolean> {
  const { error } = await authedClient(auth).DELETE("/v1/follows/{topic_id}", {
    params: { path: { topic_id: topicId } },
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  return !error;
}

export async function getHistory(
  auth: AuthContext,
  cursor?: string,
): Promise<Degradable<HistoryPage>> {
  const { data, error } = await authedClient(auth).GET("/v1/history", {
    params: { query: { cursor } },
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  if (error || !data) return { data: { items: [], next_cursor: null }, degraded: true };
  return { data, degraded: false };
}

export async function reportClick(
  auth: AuthContext,
  params: { articleId: number; surface: string; position?: number; impressionId?: number },
): Promise<void> {
  await authedClient(auth).POST("/v1/history", {
    body: {
      article_id: params.articleId,
      surface: params.surface,
      position: params.position,
      impression_id: params.impressionId,
    },
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
}

export async function reportNotInterested(
  auth: AuthContext,
  params: { articleId: number; surface: string },
): Promise<boolean> {
  const { error } = await authedClient(auth).POST("/v1/not-interested", {
    body: { article_id: params.articleId, surface: params.surface },
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  return !error;
}
