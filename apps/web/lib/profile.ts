import { API_URL, ApiError } from "@/lib/api";
import type { Category, SocialPlatform } from "@/lib/discovery";
import type { DeliverableType } from "@/lib/retainers";

export type Availability = "available" | "limited" | "unavailable";

export type SocialAccount = {
  id: string;
  platform: SocialPlatform;
  handle: string;
  profile_url: string | null;
  claimed_followers: number | null;
  claimed_engagement_rate: string | null;
  verified_followers: number | null;
  verified_engagement_rate: string | null;
  verified_at: string | null;
  is_verified: boolean;
};

export type PortfolioItem = {
  id: string;
  title: string;
  description: string | null;
  platform: SocialPlatform | null;
  external_url: string | null;
  media_url: string | null;
  position: number;
};

export type Rate = {
  id: string;
  deliverable_type: DeliverableType;
  quantity: number;
  price: string;
  currency: string;
  notes: string | null;
};

export type MyProfile = {
  id: string;
  workspace_id: string;
  headline: string | null;
  bio: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  languages: string[];
  skills: string[];
  monthly_retainer_min: string | null;
  currency: string;
  availability: Availability;
  verification_status: string;
  status: "draft" | "published" | "suspended";
  is_hidden: boolean;
  is_discoverable: boolean;
  completeness: number;
  missing_fields: string[];
  categories: Category[];
  social_accounts: SocialAccount[];
  portfolio_items: PortfolioItem[];
  rates: Rate[];
};

/**
 * What each missing field actually means, in the creator's words.
 *
 * The API names them after the completeness rule - "social",
 * "pricing" - which is right for the code and useless on screen.
 */
export const MISSING_LABEL: Record<string, string> = {
  headline: "a headline",
  bio: "a bio",
  location: "your city and country",
  languages: "the languages you work in",
  categories: "at least one beat",
  social: "a social account with a follower count",
  pricing: "a monthly rate or a rate card",
};

function headers(token: string) {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

async function body(response: Response) {
  const parsed = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = parsed?.detail;

    if (typeof detail === "string") {
      throw new ApiError(response.status, detail);
    }

    if (Array.isArray(detail) && detail[0]?.msg) {
      throw new ApiError(
        response.status,
        String(detail[0].msg).replace(/^Value error, /, ""),
      );
    }

    throw new ApiError(
      response.status,
      "Could not save that. Try again.",
    );
  }

  return parsed;
}

export async function getMyProfile(
  token: string,
): Promise<MyProfile | null> {
  const response = await fetch(`${API_URL}/creator-profile/me`, {
    headers: headers(token),
    cache: "no-store",
  });

  if (response.status === 403 || response.status === 404) {
    return null;
  }

  return body(response);
}

export async function saveBasics(
  token: string,
  payload: Record<string, unknown>,
): Promise<void> {
  await body(
    await fetch(`${API_URL}/creator-profile`, {
      method: "PUT",
      headers: headers(token),
      body: JSON.stringify(payload),
    }),
  );
}

export async function saveCategories(
  token: string,
  categoryIds: string[],
): Promise<void> {
  await body(
    await fetch(`${API_URL}/creator-profile/categories`, {
      method: "PUT",
      headers: headers(token),
      body: JSON.stringify({ category_ids: categoryIds }),
    }),
  );
}

export async function setVisibility(
  token: string,
  isHidden: boolean,
): Promise<void> {
  await body(
    await fetch(`${API_URL}/creator-profile/visibility`, {
      method: "PATCH",
      headers: headers(token),
      body: JSON.stringify({ is_hidden: isHidden }),
    }),
  );
}

type Sub = "social-accounts" | "portfolio" | "rates";

export async function addItem(
  token: string,
  kind: Sub,
  payload: Record<string, unknown>,
): Promise<void> {
  await body(
    await fetch(`${API_URL}/creator-profile/${kind}`, {
      method: "POST",
      headers: headers(token),
      body: JSON.stringify(payload),
    }),
  );
}

export async function removeItem(
  token: string,
  kind: Sub,
  id: string,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/creator-profile/${kind}/${id}`,
    { method: "DELETE", headers: headers(token) },
  );

  if (response.status === 204) return;

  await body(response);
}
