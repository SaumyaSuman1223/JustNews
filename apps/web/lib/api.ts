/**
 * Server-side API client.
 *
 * Provisional and hand-written; Stage 2 replaces it with the typed client
 * generated from the OpenAPI schema into `packages/api-client`, with a CI
 * check that catches contract drift.
 *
 * Two rules hold regardless of who writes it. Every call has an explicit
 * timeout - the API is a continent away from most readers (ADR 0003), and a
 * request with no deadline turns a slow origin into a hung page. And every
 * call degrades: a failure returns empty content plus a flag, so the page
 * renders with a banner rather than a 500.
 */

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
const TIMEOUT_MS = 4000;

export interface Article {
  id: number;
  title: string;
  snippet: string | null;
  image_url: string | null;
  url: string;
  language: string;
  published_at: string;
  source_name: string;
  source_slug: string;
  story_cluster_id: number | null;
}

export interface ArticlePage {
  items: Article[];
  next_cursor: string | null;
}

export interface CorpusStats {
  articles: number;
  sources: number;
  story_clusters: number;
  languages: number;
}

export interface Degradable<T> {
  data: T;
  degraded: boolean;
}

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
  cursor?: string;
  pageSize?: number;
}): Promise<Degradable<ArticlePage>> {
  const query = new URLSearchParams();
  if (params.languages) query.set("languages", params.languages);
  if (params.cursor) query.set("cursor", params.cursor);
  query.set("page_size", String(params.pageSize ?? 20));
  // 60s: a news feed may be a minute stale; it may not be a minute slow.
  return get<ArticlePage>(`/v1/articles?${query}`, { items: [], next_cursor: null }, 60);
}

export function getStats(): Promise<Degradable<CorpusStats>> {
  return get<CorpusStats>(
    "/v1/stats",
    { articles: 0, sources: 0, story_clusters: 0, languages: 0 },
    300,
  );
}
