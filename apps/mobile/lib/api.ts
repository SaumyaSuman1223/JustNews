/**
 * API access for the mobile app.
 *
 * Mirrors frontend/lib/api.ts's call shapes exactly, minus everything that
 * is Next-specific: no `fetch`'s `next: { revalidate }` option (RN has no
 * such cache), and no distinction between "Server Component" and "Client
 * Component" calls - every call here runs on the device, so there is exactly
 * one calling style.
 *
 * Every failure degrades - empty content plus a flag - never a thrown error
 * a screen has to catch, the same rule frontend/lib/api.ts documents. That
 * rule needs enforcing here, not just stating: `openapi-fetch`'s `{data,
 * error}` result only ever covers HTTP-level (4xx/5xx) failures - reading
 * its source confirms a network-level failure (offline, DNS, a timeout
 * firing) is *rethrown*, not returned. Caught live in this slice's own
 * verification: a CORS-blocked call to /v1/explore crashed the whole screen
 * with an uncaught "Failed to fetch" instead of showing a degraded banner.
 * `withDegrade` below is what actually keeps the promise for every
 * authenticated call, not just the anonymous `get<T>` helper.
 */
import { createApiClient } from "@justnews/api-client";
import type { components } from "@justnews/api-client";

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
// Render's free tier cold-starts after 15 minutes idle - measured around
// 22s. Same timeout and same reasoning as frontend/lib/api.ts.
const TIMEOUT_MS = 30000;

export type Article = components["schemas"]["ArticleOut"];
export type ArticlePage = components["schemas"]["ArticlePageOut"];
export type FeedPage = components["schemas"]["FeedPageOut"];
export type MeProfile = components["schemas"]["MeOut"];

export interface Degradable<T> {
  data: T;
  degraded: boolean;
}

export interface AuthContext {
  accessToken: string;
  sessionId: string;
}

const EMPTY_ARTICLE_PAGE: ArticlePage = { items: [], next_cursor: null };
const EMPTY_FEED: FeedPage = { items: [], next_cursor: null };

/** Runs an openapi-fetch call, turning a rethrown network-level failure into
 * the same degraded shape an HTTP-level failure already gets. */
async function withDegrade<T>(fallback: T, run: () => Promise<T>): Promise<Degradable<T>> {
  try {
    return { data: await run(), degraded: false };
  } catch {
    return { data: fallback, degraded: true };
  }
}

async function get<T>(path: string, fallback: T): Promise<Degradable<T>> {
  return withDegrade(fallback, async () => {
    const response = await fetch(`${API_URL}${path}`, { signal: AbortSignal.timeout(TIMEOUT_MS) });
    if (!response.ok) throw new Error(`${path} -> ${response.status}`);
    return (await response.json()) as T;
  });
}

function authedClient(auth: AuthContext) {
  return createApiClient(API_URL, { accessToken: auth.accessToken, sessionId: auth.sessionId });
}

// --- anonymous, unauthenticated reads -------------------------------------

export function getArticles(params: {
  languages?: string;
  cursor?: string;
  pageSize?: number;
}): Promise<Degradable<ArticlePage>> {
  const query = new URLSearchParams();
  if (params.languages) query.set("languages", params.languages);
  if (params.cursor) query.set("cursor", params.cursor);
  query.set("page_size", String(params.pageSize ?? 20));
  return get<ArticlePage>(`/v1/articles?${query}`, EMPTY_ARTICLE_PAGE);
}

export function getArticle(id: number): Promise<Degradable<Article | null>> {
  return get<Article | null>(`/v1/articles/${id}`, null);
}

// --- personalised / explore reads ------------------------------------------

export function getFeed(
  auth: AuthContext,
  params: { languages?: string; locale: string; cursor?: string; pageSize?: number },
): Promise<Degradable<FeedPage>> {
  return withDegrade(EMPTY_FEED, async () => {
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
    if (error || !data) throw new Error("getFeed failed");
    return data;
  });
}

export function getExplore(
  auth: AuthContext | null,
  params: { languages?: string; locale: string; cursor?: string; pageSize?: number },
): Promise<Degradable<FeedPage>> {
  return withDegrade(EMPTY_FEED, async () => {
    const client = createApiClient(API_URL, {
      accessToken: auth?.accessToken,
      sessionId: auth?.sessionId,
    });
    const { data, error } = await client.GET("/v1/explore", {
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
    if (error || !data) throw new Error("getExplore failed");
    return data;
  });
}

// --- account ----------------------------------------------------------------

export async function getMe(auth: AuthContext): Promise<MeProfile | null> {
  const { data } = await withDegrade(null, async () => {
    const { data, error } = await authedClient(auth).GET("/v1/me", {
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    if (error || !data) throw new Error("getMe failed");
    return data;
  });
  return data;
}

export interface RedeemResult {
  ok: boolean;
  message?: string;
}

export async function redeemInvite(auth: AuthContext, code: string): Promise<RedeemResult> {
  try {
    const { error } = await authedClient(auth).POST("/v1/invites/redeem", {
      body: { code },
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    if (!error) return { ok: true };
    // Same defensive read as frontend/lib/api.ts: the standard error
    // envelope isn't part of FastAPI's declared OpenAPI response shape (it
    // comes from exception handlers), so it isn't schema-visible here.
    const body = error as { error?: { message?: string } };
    return { ok: false, message: body.error?.message ?? "That code did not work." };
  } catch {
    return { ok: false, message: "We could not reach the server. Check your connection and try again." };
  }
}

// --- interactions -------------------------------------------------------

export async function reportClick(
  auth: AuthContext,
  params: { articleId: number; surface: "feed" | "explore"; position?: number; impressionId?: number | null },
): Promise<void> {
  try {
    await authedClient(auth).POST("/v1/history", {
      body: {
        article_id: params.articleId,
        surface: params.surface,
        position: params.position,
        impression_id: params.impressionId ?? undefined,
      },
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch {
    // Fire-and-forget by design (see ArticleCard's handlePress) - a failed
    // click log must never surface as an error over a navigation the reader
    // already got.
  }
}
