import createClient from "openapi-fetch";
import type { paths } from "./schema";

export type { components, paths } from "./schema";

export interface ApiClientOptions {
  /** A Supabase access token. Omit for the public, unauthenticated routes. */
  accessToken?: string;
  /** Groups impressions and interaction events into one browsing session. */
  sessionId?: string;
}

/**
 * A typed fetch client for the JustNews API, generated from its own OpenAPI
 * schema (see ../openapi.json and scripts/generate_openapi.py at the repo
 * root). Route paths, query params, request bodies and response shapes are
 * all checked at compile time - a route that changes without this package
 * being regenerated fails `tsc`, not a user's browser.
 */
export function createApiClient(baseUrl: string, options: ApiClientOptions = {}) {
  const headers: Record<string, string> = {};
  if (options.accessToken) {
    headers.authorization = `Bearer ${options.accessToken}`;
  }
  if (options.sessionId) {
    headers["x-session-id"] = options.sessionId;
  }
  return createClient<paths>({ baseUrl, headers });
}

export type ApiClient = ReturnType<typeof createApiClient>;
