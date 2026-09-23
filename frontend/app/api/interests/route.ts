import { NextResponse } from "next/server";

import { followTopic, getMe } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { INTERESTS_COOKIE, INTERESTS_DISMISSED_COOKIE, MAX_INTERESTS } from "@/lib/interests";
import { isSameOrigin } from "@/lib/sameOrigin";
import { getSession } from "@/lib/session";

const TOPIC_ID = /^medtop:\d{8}$/;
const YEAR = 60 * 60 * 24 * 365;

/**
 * "Make it yours": save the topics a reader picked, or remember that they
 * closed the card. Saved as a cookie that For You reads for everyone; for a
 * signed-in reader with access, also as topic follows, which the personal
 * ranker reads - so the choice counts either way, and carries into the
 * account.
 */
export async function POST(request: Request): Promise<Response> {
  if (!isSameOrigin(request)) return NextResponse.json({ ok: false }, { status: 403 });
  const body: unknown = await request.json().catch(() => null);
  const fields = body && typeof body === "object" ? (body as Record<string, unknown>) : {};

  const cookieOptions = { maxAge: YEAR, sameSite: "lax" as const, path: "/", httpOnly: true };
  if (fields.dismiss === true) {
    const response = NextResponse.json({ ok: true });
    response.cookies.set(INTERESTS_DISMISSED_COOKIE, "1", cookieOptions);
    return response;
  }

  const topics = Array.isArray(fields.topics) ? fields.topics : null;
  if (
    !topics ||
    topics.length === 0 ||
    topics.length > MAX_INTERESTS ||
    !topics.every((id): id is string => typeof id === "string" && TOPIC_ID.test(id))
  ) {
    return NextResponse.json({ ok: false }, { status: 422 });
  }

  const session = await getSession();
  if (session) {
    const auth = { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() };
    const profile = await getMe(auth);
    if (profile?.has_beta_access) {
      // Best effort per topic: the cookie below already makes For You follow
      // these, so one follow failing is not a reason to fail the save.
      await Promise.all(topics.map((id) => followTopic(auth, id)));
    }
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(INTERESTS_COOKIE, [...new Set(topics)].join(","), cookieOptions);
  response.cookies.set(INTERESTS_DISMISSED_COOKIE, "1", cookieOptions);
  return response;
}
