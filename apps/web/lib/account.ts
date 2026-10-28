import { API_URL, ApiError } from "@/lib/api";

/**
 * The person signed in, as opposed to the workspace they are
 * acting for. Everywhere else in this app "you" means a
 * workspace; here it means a human being.
 */
export type Account = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  job_title: string | null;
  email_verified: boolean;
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

    // Pydantic refusals arrive as a list of problems. The first
    // one is the one to fix, and its message is already written
    // for a person - "Include at least one number." - so it is
    // passed through rather than replaced with something vaguer.
    if (Array.isArray(detail)) {
      throw new ApiError(
        response.status,
        detail[0]?.msg?.replace(/^Value error,\s*/, "") ??
          "Check what you typed.",
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

export async function getAccount(
  token: string,
): Promise<Account | null> {
  const response = await fetch(`${API_URL}/auth/me`, {
    headers: headers(token),
    cache: "no-store",
  });

  if (!response.ok) {
    return null;
  }

  return response.json();
}

export async function updateAccount(
  token: string,
  changes: Record<string, unknown>,
): Promise<Account> {
  const response = await fetch(`${API_URL}/auth/me`, {
    method: "PATCH",
    headers: headers(token),
    body: JSON.stringify(changes),
  });

  return body(response);
}

/**
 * Returns a replacement token.
 *
 * Changing a password ends every session this person has, which
 * includes the browser doing the changing - so the API hands back
 * a new one and the cookie is swapped for it.
 */
export async function changePassword(
  token: string,
  input: {
    current_password: string;
    new_password: string;
    confirm_password: string;
  },
): Promise<string> {
  const response = await fetch(`${API_URL}/auth/change-password`, {
    method: "POST",
    headers: headers(token),
    body: JSON.stringify(input),
  });

  const parsed = await body(response);

  return parsed.access_token as string;
}
