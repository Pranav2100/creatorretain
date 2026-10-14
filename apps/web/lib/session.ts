import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export const SESSION_COOKIE = "cr_session";

// The API's tokens last 30 minutes. The cookie is given the same
// life so the browser stops sending one the server will only
// reject - a 401 the user cannot act on is worse than being asked
// to sign in again.
export const SESSION_MAX_AGE = 30 * 60;

export async function getToken(): Promise<string | null> {
  const store = await cookies();

  return store.get(SESSION_COOKIE)?.value ?? null;
}

/**
 * The token, or a redirect to sign in.
 *
 * `next` carries where they were headed, so signing in returns
 * them to it rather than dumping them on a default page.
 */
export async function requireToken(returnTo?: string): Promise<string> {
  const token = await getToken();

  if (!token) {
    redirect(
      returnTo
        ? `/login?next=${encodeURIComponent(returnTo)}`
        : "/login",
    );
  }

  return token;
}

/**
 * The three things every signed-in page needs, or a redirect to
 * wherever the person actually belongs.
 *
 * Expired token and missing workspace look the same from a page's
 * point of view - neither can render - but the way out differs, so
 * they are separated here once rather than in every page.
 */
export async function requireWorkspace(returnTo: string) {
  const { getWorkspaceContext, NO_WORKSPACE } = await import(
    "@/lib/workspace"
  );

  const token = await requireToken(returnTo);
  const context = await getWorkspaceContext(token);

  if (context === NO_WORKSPACE) {
    redirect("/setup");
  }

  if (!context) {
    redirect(`/login?next=${encodeURIComponent(returnTo)}`);
  }

  return { token, ...context };
}
