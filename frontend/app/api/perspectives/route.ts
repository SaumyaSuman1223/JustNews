import { NextResponse } from "next/server";

import { getTopicPerspectives } from "@/lib/api";

const TOPIC_ID = /^medtop:\d{8}$/;

/**
 * A topic's Perspectives for Discover's topic view, which switches topic in
 * the browser. Anonymous and shared: the API caches it (ADR 0013, 0014), and
 * so may the CDN for a couple of minutes.
 */
export async function GET(request: Request): Promise<Response> {
  const topic = new URL(request.url).searchParams.get("topic") ?? "";
  if (!TOPIC_ID.test(topic)) return NextResponse.json([], { status: 400 });
  const groups = await getTopicPerspectives(topic);
  return NextResponse.json(groups.data, {
    headers: { "cache-control": "public, s-maxage=120, stale-while-revalidate=600" },
  });
}
