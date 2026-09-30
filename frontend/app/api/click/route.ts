import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { reportClick } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { hasAnalyticsConsent } from "@/lib/consent";
import {
  READ_HISTORY_COOKIE,
  parseReadHistory,
  serialiseReadHistory,
  withRead,
} from "@/lib/readHistory";
import { isSameOrigin } from "@/lib/sameOrigin";
import { getSession } from "@/lib/session";

/**
 * Logs a click on a card, for any reader (ADR 0015).
 *
 * A `<form action={serverAction}>` cannot fire *alongside* a plain `<a
 * target="_blank">` navigating to the publisher, so this is a small fetch a
 * client component makes on click instead (lib/track.ts).
 *
 * The consent gate for click logging is here: this route is the choke point
 * every click report passes through, and without analytics consent it
 * records nothing and remembers nothing. With it, a signed-out reader's
 * click also moves the article to the front of this device's read history -
 * the cookie Discover personalises them from (lib/readHistory.ts).
 */
export async function POST(request: Request): Promise<Response> {
  if (!isSameOrigin(request)) return NextResponse.json({ ok: false }, { status: 403 });
  if (!(await hasAnalyticsConsent())) return NextResponse.json({ ok: true });
  const sessionId = await getBrowsingSessionId();
  if (!sessionId) return NextResponse.json({ ok: true });

  const body: unknown = await request.json().catch(() => null);
  if (
    !body ||
    typeof body !== "object" ||
    typeof (body as Record<string, unknown>).articleId !== "number" ||
    typeof (body as Record<string, unknown>).surface !== "string"
  ) {
    return NextResponse.json({ ok: false }, { status: 422 });
  }
  const { articleId, surface, position, impressionId, topicId, locale } = body as {
    articleId: number;
    surface: string;
    position?: number;
    impressionId?: number;
    topicId?: string;
    locale?: string;
  };

  const session = await getSession();
  try {
    await reportClick(
      { accessToken: session?.accessToken ?? null, sessionId },
      { articleId, surface, position, impressionId, topicId, locale },
    );
  } catch {
    // The reader already navigated; a lost click is not theirs to hear about.
  }

  const response = NextResponse.json({ ok: true });
  if (!session) {
    const store = await cookies();
    const history = withRead(parseReadHistory(store.get(READ_HISTORY_COOKIE)?.value), articleId);
    response.cookies.set(READ_HISTORY_COOKIE, serialiseReadHistory(history), {
      maxAge: 60 * 60 * 24 * 30,
      sameSite: "lax",
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      path: "/",
    });
  }
  return response;
}
