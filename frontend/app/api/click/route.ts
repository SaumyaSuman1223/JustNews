import { NextResponse } from "next/server";

import { reportClick } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { hasAnalyticsConsent } from "@/lib/consent";
import { getSession } from "@/lib/session";

/**
 * Logs a click on an outbound article link.
 *
 * A `<form action={serverAction}>` cannot fire *alongside* a plain `<a
 * target="_blank">` navigating to the publisher, so this is a small fetch a
 * client component makes on click instead - the one place in this app that
 * calls an internal API route rather than a Server Action, and only because
 * the interaction genuinely originates in the browser.
 */
export async function POST(request: Request): Promise<Response> {
  const session = await getSession();
  // Impressions are only logged against the authenticated /v1/feed - an
  // anonymous explorer's click has nothing to correlate against yet.
  if (!session) return NextResponse.json({ ok: true });

  // The consent gate for click logging: not a client-side self-censor, this
  // route is the actual choke point every click report passes through,
  // matching how a card's own fire-and-forget fetch has no way to know or
  // enforce the reader's choice on its own.
  if (!(await hasAnalyticsConsent())) return NextResponse.json({ ok: true });

  const body: unknown = await request.json().catch(() => null);
  if (
    !body ||
    typeof body !== "object" ||
    typeof (body as Record<string, unknown>).articleId !== "number" ||
    typeof (body as Record<string, unknown>).surface !== "string"
  ) {
    return NextResponse.json({ ok: false }, { status: 422 });
  }
  const { articleId, surface, position, impressionId } = body as {
    articleId: number;
    surface: string;
    position?: number;
    impressionId?: number;
  };

  await reportClick(
    { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() },
    { articleId, surface, position, impressionId },
  );
  return NextResponse.json({ ok: true });
}
