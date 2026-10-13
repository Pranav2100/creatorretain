import { API_URL, ApiError } from "@/lib/api";

export type RetainerStatus =
  | "pending"
  | "active"
  | "paused"
  | "declined"
  | "cancelled"
  | "ended";

export type DeliverableType =
  | "reel"
  | "post"
  | "story"
  | "video"
  | "ugc"
  | "editing"
  | "strategy";

export type DeliverableStatus =
  | "pending"
  | "submitted"
  | "revision_requested"
  | "approved"
  | "rejected";

export type ReviewDecision =
  | "approve"
  | "request_revision"
  | "reject";

export type Party = {
  workspace_id: string;
  slug: string;
  display_name: string;
};

export type Spec = {
  id: string;
  deliverable_type: DeliverableType;
  quantity: number;
  notes: string | null;
};

export type Deliverable = {
  id: string;
  deliverable_type: DeliverableType;
  position: number;
  status: DeliverableStatus;
  title: string | null;
  submitted_url: string | null;
  submitted_note: string | null;
  submitted_at: string | null;
  submission_count: number;
  reviewed_at: string | null;
  review_note: string | null;
};

export type Period = {
  id: string;
  sequence: number;
  period_start: string;
  period_end: string;
  amount: string;
  currency: string;
  state: "upcoming" | "current" | "past";
  is_complete: boolean;
  outstanding_count: number;
  deliverables: Deliverable[];
};

export type RetainerSummary = {
  id: string;
  title: string;
  status: RetainerStatus;
  monthly_amount: string;
  currency: string;
  start_date: string;
  end_date: string | null;
  brand: Party;
  creator: Party;
  your_side: "brand" | "creator";
  monthly_deliverable_count: number;
  periods_so_far: number;
  created_at: string;
};

export type RetainerDetail = {
  id: string;
  title: string;
  status: RetainerStatus;
  monthly_amount: string;
  currency: string;
  start_date: string;
  end_date: string | null;
  anchor_day: number;
  notice_period_days: number;
  terms: string | null;
  message: string | null;
  brand: Party;
  creator: Party;
  your_side: "brand" | "creator";
  specs: Spec[];
  periods: Period[];
  accepted_at: string | null;
  responded_at: string | null;
  paused_at: string | null;
  ended_at: string | null;
  ended_reason: string | null;
  created_at: string;
};

export const DELIVERABLE_LABEL: Record<DeliverableType, string> = {
  reel: "Reel",
  post: "Post",
  story: "Story",
  video: "Video",
  ugc: "UGC",
  editing: "Editing",
  strategy: "Strategy",
};

export const STATUS_LABEL: Record<RetainerStatus, string> = {
  pending: "Waiting on the creator",
  active: "Running",
  paused: "Paused",
  declined: "Declined",
  cancelled: "Withdrawn",
  ended: "Ended",
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
    const detail =
      typeof parsed?.detail === "string"
        ? parsed.detail
        : "Something went wrong. Try again.";

    throw new ApiError(response.status, detail);
  }

  return parsed;
}

export async function listRetainers(
  token: string,
): Promise<{ retainers: RetainerSummary[]; total: number }> {
  const response = await fetch(`${API_URL}/retainers`, {
    headers: headers(token),
    cache: "no-store",
  });

  return body(response);
}

export async function getRetainer(
  token: string,
  id: string,
): Promise<RetainerDetail | null> {
  const response = await fetch(`${API_URL}/retainers/${id}`, {
    headers: headers(token),
    cache: "no-store",
  });

  if (response.status === 404) {
    return null;
  }

  return body(response);
}

export async function createRetainer(
  token: string,
  payload: Record<string, unknown>,
): Promise<RetainerDetail> {
  const response = await fetch(`${API_URL}/retainers`, {
    method: "POST",
    headers: headers(token),
    body: JSON.stringify(payload),
  });

  return body(response);
}

export async function actOnRetainer(
  token: string,
  id: string,
  action: "accept" | "decline" | "cancel" | "pause" | "resume" | "end",
  payload?: Record<string, unknown>,
): Promise<RetainerDetail> {
  const response = await fetch(
    `${API_URL}/retainers/${id}/${action}`,
    {
      method: "POST",
      headers: headers(token),
      body: payload ? JSON.stringify(payload) : undefined,
    },
  );

  return body(response);
}

export async function submitDeliverable(
  token: string,
  deliverableId: string,
  payload: { url: string; note?: string | null },
): Promise<Deliverable> {
  const response = await fetch(
    `${API_URL}/retainers/deliverables/${deliverableId}/submit`,
    {
      method: "POST",
      headers: headers(token),
      body: JSON.stringify(payload),
    },
  );

  return body(response);
}

export async function reviewDeliverable(
  token: string,
  deliverableId: string,
  payload: { decision: ReviewDecision; note?: string | null },
): Promise<Deliverable> {
  const response = await fetch(
    `${API_URL}/retainers/deliverables/${deliverableId}/review`,
    {
      method: "POST",
      headers: headers(token),
      body: JSON.stringify(payload),
    },
  );

  return body(response);
}
