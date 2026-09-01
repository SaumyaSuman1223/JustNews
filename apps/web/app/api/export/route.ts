import { NextResponse } from "next/server";

import { exportMe } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getSession } from "@/lib/session";

/**
 * A download, not a Server Action - a Server Action cannot hand the browser
 * a file with its own filename and content-disposition, and this is exactly
 * the data-portability request GDPR/CCPA/DPDP all require answering.
 */
export async function GET(): Promise<Response> {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Sign in first." }, { status: 401 });

  const auth = { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() };
  const data = await exportMe(auth);
  if (!data) return NextResponse.json({ error: "Export failed." }, { status: 502 });

  return new NextResponse(JSON.stringify(data, null, 2), {
    headers: {
      "content-type": "application/json",
      "content-disposition": "attachment; filename=justnews-data.json",
    },
  });
}
