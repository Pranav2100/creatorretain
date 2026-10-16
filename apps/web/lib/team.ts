import "server-only";

import { API_URL, ApiError } from "@/lib/api";
import type { WorkspaceRole } from "@/lib/workspace";

export type MemberStatus = "active" | "invited" | "removed" | "left";

export type Member = {
  id: string;
  user_id: string;
  first_name: string;
  last_name: string;
  email: string;
  role: WorkspaceRole;
  status: MemberStatus;
  created_at: string;
};

export type InvitationStatus =
  | "pending"
  | "accepted"
  | "declined"
  | "expired"
  | "cancelled";

export type SentInvitation = {
  id: string;
  email: string;
  role: WorkspaceRole;
  status: InvitationStatus;
  resend_requested_at: string | null;
  created_at: string;
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
 * Listing members needs a permission a Member does not have, so a
 * refusal here is an ordinary answer rather than a fault. The page
 * shows what it can and says why the rest is missing.
 */
export async function listMembers(
  token: string,
): Promise<Member[] | null> {
  const response = await fetch(`${API_URL}/workspace-members`, {
    headers: headers(token),
    cache: "no-store",
  });

  if (response.status === 403) return null;

  return (await body(response)).members;
}

export async function listSentInvitations(
  token: string,
): Promise<SentInvitation[] | null> {
  const response = await fetch(
    `${API_URL}/workspace-invitations/sent`,
    { headers: headers(token), cache: "no-store" },
  );

  if (response.status === 403) return null;

  return (await body(response)).invitations;
}

export async function inviteMember(
  token: string,
  email: string,
  role: "admin" | "member",
): Promise<void> {
  await body(
    await fetch(`${API_URL}/workspace-invitations/invite`, {
      method: "POST",
      headers: headers(token),
      body: JSON.stringify({ email, role }),
    }),
  );
}

export async function cancelInvitation(
  token: string,
  invitationId: string,
): Promise<void> {
  await body(
    await fetch(
      `${API_URL}/workspace-invitations/${invitationId}/cancel`,
      { method: "POST", headers: headers(token) },
    ),
  );
}

export async function resendInvitation(
  token: string,
  invitationId: string,
): Promise<void> {
  await body(
    await fetch(
      `${API_URL}/workspace-invitations/${invitationId}/resend`,
      { method: "POST", headers: headers(token) },
    ),
  );
}

export async function changeRole(
  token: string,
  memberId: string,
  role: "admin" | "member",
): Promise<void> {
  await body(
    await fetch(
      `${API_URL}/workspace-members/${memberId}/role`,
      {
        method: "PATCH",
        headers: headers(token),
        body: JSON.stringify({ role }),
      },
    ),
  );
}

export async function removeMember(
  token: string,
  memberId: string,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/workspace-members/${memberId}`,
    { method: "DELETE", headers: headers(token) },
  );

  if (response.status === 204) return;

  await body(response);
}

export async function saveWorkspace(
  token: string,
  payload: Record<string, unknown>,
): Promise<void> {
  await body(
    await fetch(`${API_URL}/workspaces`, {
      method: "PUT",
      headers: headers(token),
      body: JSON.stringify(payload),
    }),
  );
}

export async function uploadLogo(
  token: string,
  file: File,
): Promise<void> {
  const form = new FormData();
  form.append("file", file);

  await body(
    await fetch(`${API_URL}/workspaces/logo`, {
      method: "POST",
      // No Content-Type: fetch sets it with the multipart
      // boundary, and naming it by hand breaks the body.
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    }),
  );
}

export async function removeLogo(token: string): Promise<void> {
  await body(
    await fetch(`${API_URL}/workspaces/logo`, {
      method: "DELETE",
      headers: headers(token),
    }),
  );
}
