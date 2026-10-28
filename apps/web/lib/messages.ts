import "server-only";

import { API_URL, ApiError } from "@/lib/api";

export type Correspondent = {
  workspace_id: string;
  slug: string;
  display_name: string;
  logo_url: string | null;
  /** Brands have a public page at their slug; creators do not. */
  workspace_type: "brand" | "agency" | "creator";
};

export type ChatMessage = {
  id: string;
  body: string;
  at: string;
  /** The workspace it came from, as it read that day. */
  sender_name: string | null;
  /** The person who typed it. */
  sender_person: string | null;
  /** Whether this side sent it, which decides which way it sits. */
  mine: boolean;
};

export type ConversationSummary = {
  id: string;
  other: Correspondent;
  last_message_at: string | null;
  message_count: number;
  unread: number;
  preview: string | null;
};

export type Inbox = {
  conversations: ConversationSummary[];
  total: number;
  unread_total: number;
  requests_waiting: number;
};

export type Thread = {
  id: string;
  other: Correspondent;
  messages: ChatMessage[];
  /** False once either side has blocked, or turned the other away. */
  open: boolean;
  /** Waiting on this reader to let it in. Never true for the sender. */
  is_request: boolean;
  started_by_me: boolean;
  /** How far the far end has read. */
  seen_at: string | null;
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

    if (Array.isArray(detail)) {
      throw new ApiError(
        response.status,
        String(detail[0]?.msg ?? "Check what you typed.").replace(
          /^Value error,\s*/,
          "",
        ),
      );
    }

    throw new ApiError(
      response.status,
      typeof detail === "string"
        ? detail
        : "Something went wrong. Try again.",
    );
  }

  return parsed;
}

export async function getInbox(
  token: string,
  requests = false,
): Promise<Inbox> {
  const response = await fetch(
    `${API_URL}/conversations?requests=${requests}`,
    { headers: headers(token), cache: "no-store" },
  );

  if (!response.ok) {
    return {
      conversations: [],
      total: 0,
      unread_total: 0,
      requests_waiting: 0,
    };
  }

  return response.json();
}

/**
 * What the header badge needs, without fetching a list.
 *
 * Never throws and never reports a count it is not sure of: a
 * badge that appears because something failed is worse than no
 * badge at all.
 */
export async function getUnread(
  token: string,
): Promise<{ unread: number; requests: number }> {
  try {
    const response = await fetch(
      `${API_URL}/conversations/unread/count`,
      { headers: headers(token), cache: "no-store" },
    );

    if (!response.ok) {
      return { unread: 0, requests: 0 };
    }

    return await response.json();
  } catch {
    return { unread: 0, requests: 0 };
  }
}

export async function getThread(
  token: string,
  id: string,
): Promise<Thread | null> {
  const response = await fetch(`${API_URL}/conversations/${id}`, {
    headers: headers(token),
    cache: "no-store",
  });

  if (response.status === 404) {
    return null;
  }

  return body(response);
}

export async function sendMessage(
  token: string,
  input: {
    body: string;
    conversation_id?: string;
    to_workspace_id?: string;
  },
): Promise<Thread> {
  const response = await fetch(`${API_URL}/conversations/messages`, {
    method: "POST",
    headers: headers(token),
    body: JSON.stringify(input),
  });

  return body(response);
}

export async function markRead(
  token: string,
  id: string,
): Promise<void> {
  await fetch(`${API_URL}/conversations/${id}/read`, {
    method: "POST",
    headers: headers(token),
  });
}

export async function acceptRequest(
  token: string,
  id: string,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/conversations/${id}/accept`,
    { method: "POST", headers: headers(token) },
  );

  await body(response);
}

export async function declineRequest(
  token: string,
  id: string,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/conversations/${id}/decline`,
    { method: "POST", headers: headers(token) },
  );

  if (response.status === 204) return;

  await body(response);
}

export async function blockWorkspace(
  token: string,
  workspaceId: string,
  reason?: string,
): Promise<void> {
  const response = await fetch(`${API_URL}/conversations/blocks`, {
    method: "POST",
    headers: headers(token),
    body: JSON.stringify({ workspace_id: workspaceId, reason }),
  });

  if (response.status === 204) return;

  await body(response);
}
