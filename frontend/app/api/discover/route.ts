import { NextResponse } from "next/server";

import { discoverReader, loadDiscoverPage } from "@/lib/discover";
import { parseView } from "@/lib/discoverView";
import { isLocaleCode } from "@/lib/i18n";

/**
 * One page of a Discover view, for the client: switching tabs and scrolling
 * for more fetch here instead of re-rendering the whole route, so the shell
 * and the rail stay put and a tab already visited is instant.
 *
 * Never cached: For You's personal pages log the impressions they serve, and
 * the other views are already cached one layer down (Next's fetch cache and
 * the API's Redis, ADR 0014).
 */
export async function GET(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const locale = url.searchParams.get("locale") ?? "en";
  if (!isLocaleCode(locale)) {
    return NextResponse.json({ error: "unknown locale" }, { status: 422 });
  }
  const view = parseView({
    view: url.searchParams.get("view"),
    topic: url.searchParams.get("topic"),
  });
  const reader = await discoverReader(locale);
  const page = await loadDiscoverPage(reader, view, locale, url.searchParams.get("cursor") ?? undefined);
  return NextResponse.json(page, { headers: { "Cache-Control": "private, no-store" } });
}
