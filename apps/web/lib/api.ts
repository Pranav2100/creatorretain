export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type InvitationStatus =
  | "pending"
  | "accepted"
  | "declined"
  | "expired"
  | "cancelled";

export type InvitationPreview = {
  workspace_name: string | null;
  invited_by_name: string | null;
  email: string;
  role: "owner" | "admin" | "member";
  status: InvitationStatus;
  is_expired: boolean;
  requires_signup: boolean;
  expires_at: string;
};

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parse(response: Response) {
  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const detail =
      typeof body?.detail === "string"
        ? body.detail
        : "Something went wrong. Try again.";

    throw new ApiError(response.status, detail);
  }

  return body;
}

export async function getInvitation(
  token: string,
): Promise<InvitationPreview | null> {
  const response = await fetch(
    `${API_URL}/workspace-invitations/token/${encodeURIComponent(token)}`,
    { cache: "no-store" },
  );

  if (response.status === 404) {
    return null;
  }

  return parse(response);
}

export async function login(
  email: string,
  password: string,
): Promise<string> {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  const body = await parse(response);
  return body.access_token as string;
}

export async function register(input: {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  confirm_password: string;
}): Promise<void> {
  const response = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  await parse(response);
}

export async function acceptByToken(
  token: string,
  accessToken: string,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/workspace-invitations/accept-by-token`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ token }),
    },
  );

  await parse(response);
}
