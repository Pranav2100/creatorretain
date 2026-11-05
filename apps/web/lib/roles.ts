import "server-only";

import { API_URL, ApiError } from "@/lib/api";

export type PermissionInfo = {
  value: string;
  label: string;
  description: string;
  /** Whether the person asking holds it, and so may grant it. */
  held: boolean;
};

export type CustomRole = {
  id: string;
  name: string;
  position: number;
  permissions: string[];
  member_count: number;
  /** Decided by the server, because the rule is the server's. */
  editable: boolean;
};

export type RoleCatalogue = {
  roles: CustomRole[];
  permissions: PermissionInfo[];
};

function headers(token: string): HeadersInit {
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

    // Pydantic rejects a bad field with an array rather than a
    // sentence - a blank name or an empty permission set arrives
    // this way - so the first message is unwrapped into
    // something worth showing somebody.
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

async function nothing(response: Response): Promise<void> {
  if (response.status === 204) return;

  await body(response);
}

/**
 * The roles, and the vocabulary to build them from.
 *
 * Both in one call because the page always needs both, and the
 * vocabulary is the server's to define - a second copy in the web
 * app would be a second thing to forget when a permission is
 * added.
 *
 * A Member cannot read this, and that is an ordinary answer
 * rather than a fault, so it comes back null and the page simply
 * leaves the section out.
 */
export async function listRoles(
  token: string,
): Promise<RoleCatalogue | null> {
  const response = await fetch(`${API_URL}/workspace-roles`, {
    headers: headers(token),
    cache: "no-store",
  });

  if (response.status === 403) return null;

  return await body(response);
}

/**
 * Who holds which role, keyed by user id.
 *
 * One call for the whole Team list rather than one per person.
 */
export async function listAssignments(
  token: string,
): Promise<Record<string, string[]>> {
  const response = await fetch(
    `${API_URL}/workspace-roles/assignments`,
    { headers: headers(token), cache: "no-store" },
  );

  if (response.status === 403) return {};

  return (await body(response)).assignments ?? {};
}

export async function createRole(
  token: string,
  name: string,
  permissions: string[],
): Promise<CustomRole> {
  return await body(
    await fetch(`${API_URL}/workspace-roles`, {
      method: "POST",
      headers: headers(token),
      body: JSON.stringify({ name, permissions }),
    }),
  );
}

export async function updateRole(
  token: string,
  roleId: string,
  changes: { name?: string; permissions?: string[] },
): Promise<CustomRole> {
  return await body(
    await fetch(`${API_URL}/workspace-roles/${roleId}`, {
      method: "PATCH",
      headers: headers(token),
      body: JSON.stringify(changes),
    }),
  );
}

export async function reorderRoles(
  token: string,
  roleIds: string[],
): Promise<void> {
  await body(
    await fetch(`${API_URL}/workspace-roles/order`, {
      method: "PUT",
      headers: headers(token),
      body: JSON.stringify({ role_ids: roleIds }),
    }),
  );
}

export async function deleteRole(
  token: string,
  roleId: string,
): Promise<void> {
  await nothing(
    await fetch(`${API_URL}/workspace-roles/${roleId}`, {
      method: "DELETE",
      headers: headers(token),
    }),
  );
}

export async function grantRole(
  token: string,
  userId: string,
  roleId: string,
): Promise<void> {
  await nothing(
    await fetch(`${API_URL}/workspace-roles/members/${userId}`, {
      method: "POST",
      headers: headers(token),
      body: JSON.stringify({ role_id: roleId }),
    }),
  );
}

export async function revokeRole(
  token: string,
  userId: string,
  roleId: string,
): Promise<void> {
  await nothing(
    await fetch(
      `${API_URL}/workspace-roles/members/${userId}/${roleId}`,
      { method: "DELETE", headers: headers(token) },
    ),
  );
}
