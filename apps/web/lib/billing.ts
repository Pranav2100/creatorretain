import "server-only";

import { API_URL, ApiError } from "@/lib/api";

export type PlanOffer = {
  plan: string;
  /** Monthly, in whole rupees. Null when it is not for sale. */
  price: number | null;
  purchasable: boolean;
  current: boolean;
};

export type Subscription = {
  plan: string;
  status: "pending" | "active" | "past_due" | "cancelling" | "ended";
  amount: number | null;
  currency: string;
  current_period_end: string | null;
  cancelled: boolean;
};

export type Billing = {
  plans: PlanOffer[];
  subscription: Subscription | null;
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
      "Could not do that. Try again.",
    );
  }

  return parsed;
}

/**
 * Only the owner may read this, so a refusal is an ordinary
 * answer rather than a fault - the page leaves the section out.
 */
export async function getBilling(
  token: string,
): Promise<Billing | null> {
  const response = await fetch(`${API_URL}/billing`, {
    headers: headers(token),
    cache: "no-store",
  });

  if (response.status === 403) return null;

  return await body(response);
}

export async function startSubscription(
  token: string,
  plan: string,
): Promise<{ subscription_id: string; pay_url: string | null }> {
  return await body(
    await fetch(`${API_URL}/billing/subscription`, {
      method: "POST",
      headers: headers(token),
      body: JSON.stringify({ plan }),
    }),
  );
}

export async function cancelSubscription(
  token: string,
): Promise<Subscription> {
  return await body(
    await fetch(`${API_URL}/billing/subscription`, {
      method: "DELETE",
      headers: headers(token),
    }),
  );
}
