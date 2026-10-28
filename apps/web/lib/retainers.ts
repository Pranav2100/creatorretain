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

/**
 * The person at the hiring end, as opposed to the company. Null
 * on a retainer offered before this existed, or one whose sender
 * has since left - the agreement outlives the employee.
 */
export type Contact = {
  name: string;
  job_title: string | null;
  email: string;
  phone: string | null;
};

/**
 * Someone inside the hiring workspace who runs this account.
 * Distinct from Contact: that is who the creator deals with,
 * this is who the agency has put on it. Often the same person,
 * not necessarily.
 */
export type Assignee = {
  user_id: string;
  name: string;
  job_title: string | null;
  email: string;
  assigned_at: string;
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
  under_notice: boolean;
  awaiting_you: boolean;
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
  contact: Contact | null;
  your_side: "brand" | "creator";
  specs: Spec[];
  periods: Period[];
  accepted_at: string | null;
  responded_at: string | null;
  paused_at: string | null;
  ended_at: string | null;
  ended_reason: string | null;
  pending: PendingChange | null;
  under_notice: boolean;
  notice_given_at: string | null;
  notice_given_by_side: "brand" | "creator" | null;
  created_at: string;
};

export type ChangeAction = "pause" | "resume";

export type PendingChange = {
  action: ChangeAction;
  by_side: "brand" | "creator";
  /** Whether the reader asked. Only the other side gets buttons. */
  yours: boolean;
  reason: string | null;
  asked_at: string;
};

export type EventKind =
  | "offered"
  | "accepted"
  | "declined"
  | "offer_withdrawn"
  | "pause_requested"
  | "resume_requested"
  | "request_rejected"
  | "request_withdrawn"
  | "paused"
  | "resumed"
  | "notice_given"
  | "ended"
  | "work_submitted"
  | "work_approved"
  | "changes_requested"
  | "work_rejected";

export type RetainerEvent = {
  id: string;
  kind: EventKind;
  at: string;
  /** The workspace, as it read on the day. */
  actor_name: string | null;
  /** The person, looked up live. Null once they have left. */
  actor_person: string | null;
  actor_side: "brand" | "creator" | null;
  /** Whether the reader's own side did this. */
  yours: boolean;
  note: string | null;
  subject: string | null;
  about_work: boolean;
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

export async function getAssignees(
  token: string,
  id: string,
): Promise<Assignee[]> {
  const response = await fetch(
    `${API_URL}/retainers/${id}/assignees`,
    { headers: headers(token), cache: "no-store" },
  );

  if (!response.ok) {
    return [];
  }

  return (await response.json()).assignees as Assignee[];
}

export async function assignPerson(
  token: string,
  id: string,
  userId: string,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/retainers/${id}/assignees`,
    {
      method: "POST",
      headers: headers(token),
      body: JSON.stringify({ user_id: userId }),
    },
  );

  await body(response);
}

export async function unassignPerson(
  token: string,
  id: string,
  userId: string,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/retainers/${id}/assignees/${userId}`,
    { method: "DELETE", headers: headers(token) },
  );

  await body(response);
}

export async function getHistory(
  token: string,
  id: string,
): Promise<RetainerEvent[]> {
  const response = await fetch(`${API_URL}/retainers/${id}/history`, {
    headers: headers(token),
    cache: "no-store",
  });

  if (response.status === 404) {
    return [];
  }

  const parsed = await body(response);
  return parsed.events as RetainerEvent[];
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
  action: "accept" | "decline" | "cancel" | "end",
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

/**
 * Pausing and resuming are requests rather than commands: they do
 * nothing until the other side agrees. Kept apart from
 * actOnRetainer because the shape really is different - there is
 * an answer outstanding, and someone has to give it.
 */
export async function askForChange(
  token: string,
  id: string,
  action: ChangeAction,
  reason?: string | null,
): Promise<RetainerDetail> {
  return body(
    await fetch(`${API_URL}/retainers/${id}/requests`, {
      method: "POST",
      headers: headers(token),
      body: JSON.stringify({ action, reason: reason || null }),
    }),
  );
}

export async function answerChange(
  token: string,
  id: string,
  answer: "approve" | "reject",
  reason?: string | null,
): Promise<RetainerDetail> {
  return body(
    await fetch(`${API_URL}/retainers/${id}/requests/${answer}`, {
      method: "POST",
      headers: headers(token),
      body:
        answer === "reject" && reason
          ? JSON.stringify({ reason })
          : undefined,
    }),
  );
}

export async function withdrawChange(
  token: string,
  id: string,
): Promise<RetainerDetail> {
  return body(
    await fetch(`${API_URL}/retainers/${id}/requests`, {
      method: "DELETE",
      headers: headers(token),
    }),
  );
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
