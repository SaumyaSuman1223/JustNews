import { NextResponse } from "next/server";

import { saveArticle, unsaveArticle } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { isSameOrigin } from "@/lib/sameOrigin";
import { getSession } from "@/lib/session";

/**
 * Save and unsave from a Discover card. A fetch the card makes, not a Server
 * Action: an action re-renders the route it was called from, and Discover's
 * cards are client state - the heart only needs a yes or a no.
 */
async function handle(request: Request, save: boolean): Promise<Response> {
  if (!isSameOrigin(request)) return NextResponse.json({ ok: false }, { status: 403 });
  const session = await getSession();
  if (!session) return NextResponse.json({ ok: false }, { status: 401 });
  const body: unknown = await request.json().catch(() => null);
  const articleId =
    body && typeof body === "object" ? (body as Record<string, unknown>).articleId : null;
  if (typeof articleId !== "number" || !Number.isInteger(articleId) || articleId < 1) {
    return NextResponse.json({ ok: false }, { status: 422 });
  }
  const auth = { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() };
  const ok = save ? await saveArticle(auth, articleId) : await unsaveArticle(auth, articleId);
  return NextResponse.json({ ok }, { status: ok ? 200 : 502 });
}

export function POST(request: Request): Promise<Response> {
  return handle(request, true);
}

export function DELETE(request: Request): Promise<Response> {
  return handle(request, false);
}
