import { NextResponse } from "next/server";

import { reportNotInterested, undoNotInterested } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { isSameOrigin } from "@/lib/sameOrigin";
import { getSession } from "@/lib/session";

const SURFACES = new Set(["feed", "topic"]);

/** "Not interested" and its undo, from a Discover card's menu - a fetch for
 * the same reason as /api/saves. */
async function handle(request: Request, undo: boolean): Promise<Response> {
  if (!isSameOrigin(request)) return NextResponse.json({ ok: false }, { status: 403 });
  const session = await getSession();
  if (!session) return NextResponse.json({ ok: false }, { status: 401 });
  const body: unknown = await request.json().catch(() => null);
  const fields = body && typeof body === "object" ? (body as Record<string, unknown>) : {};
  const { articleId, surface } = fields;
  if (
    typeof articleId !== "number" ||
    !Number.isInteger(articleId) ||
    typeof surface !== "string" ||
    !SURFACES.has(surface)
  ) {
    return NextResponse.json({ ok: false }, { status: 422 });
  }
  const auth = { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() };
  const ok = undo
    ? await undoNotInterested(auth, { articleId, surface })
    : await reportNotInterested(auth, { articleId, surface });
  return NextResponse.json({ ok }, { status: ok ? 200 : 502 });
}

export function POST(request: Request): Promise<Response> {
  return handle(request, false);
}

export function DELETE(request: Request): Promise<Response> {
  return handle(request, true);
}
