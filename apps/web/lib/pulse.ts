import { API_URL } from "@/lib/api";

/**
 * What a page watches so it can keep itself current.
 *
 * Named for what the reader is looking at, not for the tables
 * underneath: a page knows it is showing "the team", and should
 * not have to know which three tables that is.
 */
export type Watchable =
  | "retainers"
  | "workspace"
  | "profile"
  | "creator"
  | "discovery"
  | "messages";

/**
 * Two numbers: the newest change in everything being watched,
 * and how many rows there are. The count is what catches a
 * deletion, which moves no timestamp anywhere.
 */
export type Pulse = {
  latest: string | null;
  count: number;
};

export type Watching = {
  scopes: Watchable[];
  /** Narrows "retainers" to one of them. */
  retainer?: string;
  /** Which creator, for the "creator" scope. */
  creator?: string;
};

/** The query string both the server and the browser ask with. */
export function pulseQuery(watching: Watching): string {
  const params = new URLSearchParams();

  for (const scope of watching.scopes) {
    params.append("scope", scope);
  }

  if (watching.retainer) {
    params.set("retainer", watching.retainer);
  }

  if (watching.creator) {
    params.set("creator", watching.creator);
  }

  return params.toString();
}

/**
 * A pulse that matches nothing, including itself in spirit.
 *
 * Stands for "could not tell". A page that starts here will
 * refresh once as soon as a real reading arrives, which is the
 * right way round: being told late that you were current costs
 * nothing, and deciding you are current on the strength of an
 * error costs the whole point of this.
 */
export const UNKNOWN: Pulse = { latest: null, count: -1 };

/**
 * Never throws.
 *
 * A pulse is not content - it is the question of whether the
 * content is stale - so failing to read one must not take a page
 * down with it. Every caller treats UNKNOWN as "ask again
 * shortly", which is exactly what an outage deserves.
 */
export async function getPulse(
  token: string,
  watching: Watching,
): Promise<Pulse> {
  try {
    const response = await fetch(
      `${API_URL}/pulse?${pulseQuery(watching)}`,
      {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      },
    );

    if (!response.ok) {
      return UNKNOWN;
    }

    const parsed = await response.json();

    return typeof parsed?.count === "number" ? parsed : UNKNOWN;
  } catch {
    return UNKNOWN;
  }
}
