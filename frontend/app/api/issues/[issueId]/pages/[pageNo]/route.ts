import { NextResponse } from "next/server";

import { getIssuePage } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { defaultLocale, isLocaleCode } from "@/lib/i18n";
import { getSession } from "@/lib/session";

/**
 * One page of an issue, for the reader's page turns.
 *
 * A route handler rather than a Server Action: this is a plain read, and it
 * carries the reader's own auth and browsing session so the impressions the
 * API logs are attributed to them rather than to the build. Turning a page is
 * exactly as much of a "view" as loading the route was, and the impression
 * has to say so.
 */
export async function GET(
  request: Request,
  context: { params: Promise<{ issueId: string; pageNo: string }> },
): Promise<Response> {
  const { issueId, pageNo } = await context.params;
  const id = Number(issueId);
  const page = Number(pageNo);
  if (!Number.isInteger(id) || !Number.isInteger(page) || id < 1 || page < 1) {
    return NextResponse.json({ error: "bad_request" }, { status: 400 });
  }

  const localeParam = new URL(request.url).searchParams.get("locale") ?? defaultLocale;
  const locale = isLocaleCode(localeParam) ? localeParam : defaultLocale;

  const session = await getSession();
  const auth = session
    ? { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() }
    : null;
  const content = await getIssuePage(auth, { issueId: id, pageNo: page, locale });
  if (content === null) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }
  return NextResponse.json(content);
}
