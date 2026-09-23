import { NextResponse } from "next/server";

import { isLocaleCode } from "@/lib/i18n";
import { searchPlaces } from "@/lib/openMeteo";

/** City search for the Weather widget. */
export async function GET(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const name = (url.searchParams.get("q") ?? "").trim();
  const locale = url.searchParams.get("locale") ?? "en";
  if (name.length < 2 || name.length > 80) return NextResponse.json([]);
  try {
    const places = await searchPlaces(name, isLocaleCode(locale) ? locale : "en");
    return NextResponse.json(places, {
      headers: { "Cache-Control": "public, max-age=3600, s-maxage=86400" },
    });
  } catch {
    return NextResponse.json({ error: "search unavailable" }, { status: 502 });
  }
}
