import { API_URL } from "@/lib/api";
import type { WorkspaceType } from "@/lib/workspace";

export type TrackRecord = {
  live_retainers: number;
  creators_worked_with: number;
  member_since: string;
  typical_review_hours: number | null;
  reviews_counted: number;
};

export type BrandProfile = {
  id: string;
  slug: string;
  display_name: string;
  workspace_type: WorkspaceType;
  verification_status: string;
  legal_name: string | null;
  bio: string | null;
  logo_url: string | null;
  website_url: string | null;
  track_record: TrackRecord;
};

export async function getBrand(
  token: string,
  slug: string,
): Promise<BrandProfile | null> {
  const response = await fetch(`${API_URL}/brands/${slug}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!response.ok) return null;

  return response.json();
}

/**
 * A review time as a person would say it.
 *
 * Hours are the honest unit to store and a terrible one to read:
 * nobody thinks "31.4 hours", they think "about a day and a bit".
 */
export function reviewSpeed(hours: number | null): string | null {
  if (hours === null) return null;

  if (hours < 4) return "within a few hours";
  if (hours < 12) return "the same day";
  if (hours < 36) return "within a day";

  const days = Math.round(hours / 24);

  if (days <= 7) return `in about ${days} days`;

  return "after a week or so";
}

/**
 * How long they have been here, rounded the way someone would say
 * it out loud rather than to the day.
 */
export function since(iso: string): string {
  const then = new Date(iso);

  if (Number.isNaN(then.getTime())) return "a while";

  const days = Math.floor(
    (Date.now() - then.getTime()) / 86_400_000,
  );

  if (days < 1) return "today";
  if (days < 14) return `${days} days`;
  if (days < 60) return `${Math.round(days / 7)} weeks`;
  if (days < 730) return `${Math.round(days / 30)} months`;

  return `${Math.floor(days / 365)} years`;
}
