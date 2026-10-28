import { NextResponse } from "next/server";

import { getPulse, type Watchable } from "@/lib/pulse";
import { getToken } from "@/lib/session";

/**
 * "Has anything changed?", asked by every open tab.
 *
 * This exists because the session is an httpOnly cookie, which
 * the browser will send but no script can read. A client
 * component therefore cannot call the API itself; it calls this,
 * which reads the cookie on the server and passes the question
 * on. The alternative - handing the token to the browser so it
 * could poll directly - would trade a cookie no script can touch
 * for one any script can.
 *
 * The answer is two numbers. Nothing here renders anything, so
 * there is no temptation to poll for content and end up showing
 * a page built half from one answer and half from another.
 */
export async function GET(request: Request) {
  const token = await getToken();

  if (!token) {
    // Not an error worth shouting about: the tab has been open
    // past the token's life. Said plainly so the poller can stop
    // rather than hammer a route that will only redirect.
    return NextResponse.json({ signedOut: true }, { status: 401 });
  }

  const query = new URL(request.url).searchParams;

  const scopes = query.getAll("scope") as Watchable[];
  const retainer = query.get("retainer") ?? undefined;
  const creator = query.get("creator") ?? undefined;

  const pulse = await getPulse(token, {
    scopes: scopes.length > 0 ? scopes : ["retainers"],
    retainer,
    creator,
  });

  return NextResponse.json(pulse, {
    headers: { "Cache-Control": "no-store" },
  });
}
