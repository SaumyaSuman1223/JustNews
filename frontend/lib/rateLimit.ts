/**
 * Per-reader rate limiting for the web tier, over Upstash's REST API.
 *
 * The API limits anonymous callers by address, but every page this server
 * renders reaches the API from the server's own address, so the API lets
 * the web tier through on its shared key (API_PROXY_SECRET) and the limit
 * per reader is kept here instead, where the reader's address is known.
 *
 * Off unless Upstash is configured, as on the API. A slow or failing Upstash
 * fails open after one attempt - no retry: a request waiting on a second try
 * to find out whether it may run is worse than letting it run.
 */
const UPSTASH_URL = process.env.UPSTASH_REDIS_REST_URL;
const UPSTASH_TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN;
const LIMIT_PER_MINUTE = Number(process.env.WEB_RATE_LIMIT_PER_MINUTE ?? 300);
const TIMEOUT_MS = 600;

/** The reader's address as Vercel reports it: the first hop of
 * x-forwarded-for, which Vercel sets and overwrites rather than appends to. */
export function clientAddress(headers: Headers): string | null {
  const forwarded = headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  return forwarded || headers.get("x-real-ip") || null;
}

/** Whether this request is over the reader's per-minute budget. */
export async function isRateLimited(headers: Headers): Promise<boolean> {
  if (!UPSTASH_URL || !UPSTASH_TOKEN) return false;
  const address = clientAddress(headers);
  if (!address) return false;
  const key = `ratelimit:web:${address}:${Math.floor(Date.now() / 60_000)}`;
  try {
    const response = await fetch(`${UPSTASH_URL}/pipeline`, {
      method: "POST",
      headers: { authorization: `Bearer ${UPSTASH_TOKEN}`, "content-type": "application/json" },
      body: JSON.stringify([
        ["INCR", key],
        ["EXPIRE", key, "60"],
      ]),
      signal: AbortSignal.timeout(TIMEOUT_MS),
      cache: "no-store",
    });
    if (!response.ok) return false;
    const [first] = (await response.json()) as { result?: number }[];
    return typeof first?.result === "number" && first.result > LIMIT_PER_MINUTE;
  } catch {
    return false;
  }
}
