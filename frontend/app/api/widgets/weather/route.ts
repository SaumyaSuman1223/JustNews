import { NextResponse } from "next/server";

import { forecast } from "@/lib/openMeteo";

/** The Weather widget's forecast for a point. Public and the same for every
 * reader at that point, so it is cacheable by the browser and the CDN too. */
export async function GET(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const lat = Number(url.searchParams.get("lat"));
  const lon = Number(url.searchParams.get("lon"));
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) {
    return NextResponse.json({ error: "lat and lon are required" }, { status: 422 });
  }
  try {
    return NextResponse.json(await forecast(lat, lon), {
      headers: {
        "Cache-Control": "public, max-age=600, s-maxage=1800, stale-while-revalidate=3600",
      },
    });
  } catch {
    return NextResponse.json({ error: "forecast unavailable" }, { status: 502 });
  }
}
