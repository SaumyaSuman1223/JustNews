import { NextResponse } from "next/server";

import { updateMe } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { READING_LANGUAGES_COOKIE, parseReadingLanguages } from "@/lib/readingLanguages";
import { isSameOrigin } from "@/lib/sameOrigin";
import { getSession } from "@/lib/session";

const YEAR = 60 * 60 * 24 * 365;

/**
 * Discover's "Read in": the languages a reader's feed comes in. A cookie for
 * everyone, so it works signed out; for a signed-in reader, also their
 * account's languages, which the personal feed and Settings read.
 */
export async function POST(request: Request): Promise<Response> {
  if (!isSameOrigin(request)) return NextResponse.json({ ok: false }, { status: 403 });
  const body: unknown = await request.json().catch(() => null);
  const raw =
    body && typeof body === "object" ? (body as Record<string, unknown>).languages : undefined;
  const languages = Array.isArray(raw)
    ? parseReadingLanguages(raw.filter((item) => typeof item === "string").join(","))
    : [];
  if (languages.length === 0) return NextResponse.json({ ok: false }, { status: 400 });

  const session = await getSession();
  if (session) {
    // The cookie below is set either way; a failed account write leaves the
    // feed right for this browser, and Settings shows the account's own.
    await updateMe(
      { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() },
      languages,
    ).catch(() => null);
  }

  const response = NextResponse.json({ ok: true, languages });
  response.cookies.set(READING_LANGUAGES_COOKIE, languages.join(","), {
    maxAge: YEAR,
    sameSite: "lax",
    path: "/",
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
  });
  return response;
}
