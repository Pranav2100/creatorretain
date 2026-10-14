import { API_URL, ApiError } from "@/lib/api";
import type { WorkspaceType } from "@/lib/workspace";

export type UsernameCheck = {
  available: boolean;
  message: string;
  suggestions: string[];
};

async function body(response: Response) {
  const parsed = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(
      response.status,
      typeof parsed?.detail === "string"
        ? parsed.detail
        : readable(parsed) ?? "Something went wrong. Try again.",
    );
  }

  return parsed;
}

/**
 * FastAPI's 422 is a list of field errors rather than a sentence.
 * Showing the first one beats showing "Something went wrong" when
 * the real problem is that the password is too short.
 */
function readable(parsed: unknown): string | null {
  if (
    parsed &&
    typeof parsed === "object" &&
    "detail" in parsed &&
    Array.isArray((parsed as { detail: unknown[] }).detail)
  ) {
    const first = (parsed as { detail: { msg?: string }[] }).detail[0];

    if (first?.msg) {
      return first.msg.replace(/^Value error, /, "");
    }
  }

  return null;
}

export async function checkUsername(
  username: string,
): Promise<UsernameCheck> {
  const response = await fetch(
    `${API_URL}/workspaces/check-username/${encodeURIComponent(username)}`,
    { cache: "no-store" },
  );

  return body(response);
}

export async function createWorkspace(
  token: string,
  input: {
    display_name: string;
    username: string;
    workspace_type: WorkspaceType;
    legal_name?: string | null;
  },
): Promise<void> {
  const response = await fetch(`${API_URL}/workspaces`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });

  await body(response);
}
