import { NextResponse } from "next/server";

import { reportViews } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { hasAnalyticsConsent } from "@/lib/consent";
import { isSameOrigin } from "@/lib/sameOrigin";
import { getSession } from "@/lib/session";

const SLOTS = new Set(["lead", "wide", "card", "row", "page"]);
const MAX_VIEWS = 100;

/**
 * Served cards that were on screen (lib/track.ts batches them, often by
 * `navigator.sendBeacon` as the page is hidden). Consent-gated like clicks:
 * without it nothing is forwarded. The API itself records only views of the
 * reader's own impressions.
 */
export async function POST(request: Request): Promise<Response> {
  if (!isSameOrigin(request)) return NextResponse.json({ ok: false }, { status: 403 });
  if (!(await hasAnalyticsConsent())) return NextResponse.json({ ok: true });
  const sessionId = await getBrowsingSessionId();
  if (!sessionId) return NextResponse.json({ ok: true });

  const body: unknown = await request.json().catch(() => null);
  const raw = (body as { views?: unknown } | null)?.views;
  if (!Array.isArray(raw) || raw.length > MAX_VIEWS) {
    return NextResponse.json({ ok: false }, { status: 422 });
  }
  const views = raw.filter(
    (view): view is { impressionId: number; renderedPosition: number; slot: string } =>
      typeof view === "object" &&
      view !== null &&
      Number.isSafeInteger((view as Record<string, unknown>).impressionId) &&
      Number.isSafeInteger((view as Record<string, unknown>).renderedPosition) &&
      ((view as Record<string, unknown>).renderedPosition as number) >= 0 &&
      SLOTS.has((view as Record<string, unknown>).slot as string),
  );
  if (views.length === 0) return NextResponse.json({ ok: true });

  const session = await getSession();
  try {
    await reportViews({ accessToken: session?.accessToken ?? null, sessionId }, views);
  } catch {
    // A view report is a measurement; losing one is not the reader's problem.
  }
  return NextResponse.json({ ok: true });
}
