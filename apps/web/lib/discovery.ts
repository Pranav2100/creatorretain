import { API_URL, ApiError } from "@/lib/api";

export type SocialPlatform =
  | "instagram"
  | "youtube"
  | "tiktok"
  | "twitter"
  | "linkedin"
  | "facebook";

export type Availability = "available" | "limited" | "unavailable";

export type VerificationStatus =
  | "unverified"
  | "pending"
  | "verified"
  | "rejected";

export type Category = { slug: string; name: string };

export type Platform = {
  platform: SocialPlatform;
  handle: string;
  followers: number | null;
  engagement_rate: string | null;
  is_verified: boolean;
};

export type CreatorCard = {
  id: string;
  workspace_id: string;
  slug: string;
  display_name: string;
  headline: string | null;
  city: string | null;
  country: string | null;
  availability: Availability;
  verification_status: VerificationStatus;
  is_boosted: boolean;
  completeness: number;
  monthly_retainer_min: string | null;
  currency: string;
  top_followers: number | null;
  categories: Category[];
  platforms: Platform[];
};

export type PortfolioItem = {
  title: string;
  description: string | null;
  platform: SocialPlatform | null;
  external_url: string | null;
  media_url: string | null;
};

export type Rate = {
  deliverable_type: string;
  quantity: number;
  price: string;
  currency: string;
  notes: string | null;
};

export type CreatorDetail = CreatorCard & {
  bio: string | null;
  languages: string[];
  skills: string[];
  verified_at: string | null;
  portfolio_items: PortfolioItem[];
  rates: Rate[];
  can_contact: boolean;
};

export type DiscoveryResponse = {
  results: CreatorCard[];
  total_matching: number;
  returned: number;
  offset: number;
  result_cap: number | null;
  capped: boolean;
  can_contact: boolean;
};

/**
 * A search that did not run because the plan does not allow it.
 *
 * Kept as a result rather than thrown, because a 402 is not a
 * failure to show the user - it is the thing the page should be
 * showing them.
 */
export type PlanBlocked = { blocked: string };

export function isBlocked(
  value: DiscoveryResponse | PlanBlocked,
): value is PlanBlocked {
  return "blocked" in value;
}

async function authed(
  path: string,
  token: string,
): Promise<Response> {
  return fetch(`${API_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
}

async function body(response: Response) {
  const parsed = await response.json().catch(() => null);

  if (!response.ok) {
    const detail =
      typeof parsed?.detail === "string"
        ? parsed.detail
        : "Something went wrong. Try again.";

    throw new ApiError(response.status, detail);
  }

  return parsed;
}

export async function searchCreators(
  token: string,
  query: URLSearchParams,
): Promise<DiscoveryResponse | PlanBlocked> {
  const response = await authed(
    `/discovery/creators?${query.toString()}`,
    token,
  );

  if (response.status === 402) {
    const parsed = await response.json().catch(() => null);

    return {
      blocked:
        typeof parsed?.detail === "string"
          ? parsed.detail
          : "Your plan does not include this.",
    };
  }

  return body(response);
}

export async function getCreator(
  token: string,
  id: string,
): Promise<CreatorDetail | null> {
  const response = await authed(`/discovery/creators/${id}`, token);

  if (response.status === 404) {
    return null;
  }

  return body(response);
}

export async function listCategories(): Promise<Category[]> {
  const response = await fetch(`${API_URL}/content-categories`, {
    // Categories are a fixed list seeded by a migration, so this is
    // the one thing on the page worth caching.
    next: { revalidate: 3600 },
  });

  if (!response.ok) {
    return [];
  }

  const parsed = await response.json().catch(() => null);

  return parsed?.categories ?? [];
}
