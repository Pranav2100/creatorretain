"use server";

import { revalidatePath } from "next/cache";

import { ApiError } from "@/lib/api";
import type { FormState } from "@/lib/forms";
import {
  createRole,
  deleteRole,
  grantRole,
  reorderRoles,
  revokeRole,
  updateRole,
} from "@/lib/roles";
import { requireToken } from "@/lib/session";

const noError: FormState = { error: null };

async function attempt(
  work: (token: string) => Promise<unknown>,
  done?: string,
): Promise<FormState> {
  const token = await requireToken("/settings");

  try {
    await work(token);
    // Roles change what the header and every page will allow, so
    // this invalidates the layout rather than only this page.
    revalidatePath("/", "layout");

    // `done` is how the form knows it worked. A new role appears
    // in the list above, which is some confirmation, but the
    // form itself has to close and clear - and it cannot tell
    // success from "nothing happened yet" without being told.
    return done ? { error: null, done } : noError;
  } catch (caught) {
    if (caught instanceof ApiError) {
      return { error: caught.message };
    }

    return { error: "Could not reach the server. Is the API running?" };
  }
}

/**
 * The checkboxes arrive as repeated fields of the same name, so
 * getAll rather than get - and an empty set is left for the
 * server to refuse, which it does with a message worth showing.
 */
function chosen(formData: FormData): string[] {
  return formData
    .getAll("permissions")
    .map((value) => String(value))
    .filter(Boolean);
}

export async function addRole(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const name = String(formData.get("name") ?? "").trim();
  const permissions = chosen(formData);

  if (!name) {
    return { error: "Give the role a name." };
  }

  if (permissions.length === 0) {
    return { error: "Tick at least one thing the role can do." };
  }

  return attempt(
    (token) => createRole(token, name, permissions),
    `Created ${name}.`,
  );
}

export async function editRole(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const roleId = String(formData.get("role_id") ?? "");
  const name = String(formData.get("name") ?? "").trim();
  const permissions = chosen(formData);

  if (!roleId) {
    return { error: "Could not tell which role that was." };
  }

  if (!name) {
    return { error: "Give the role a name." };
  }

  if (permissions.length === 0) {
    return { error: "A role has to be able to do something." };
  }

  return attempt(
    (token) => updateRole(token, roleId, { name, permissions }),
    `Saved ${name}.`,
  );
}

export async function dropRole(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const roleId = String(formData.get("role_id") ?? "");

  return attempt((token) => deleteRole(token, roleId));
}

export async function moveRole(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  // The whole order, recomputed on the client and sent as one
  // list. Sending "move this one up" instead would need the
  // server to hold an opinion about what the list looked like
  // when the button was drawn.
  const ids = formData
    .getAll("role_ids")
    .map((value) => String(value))
    .filter(Boolean);

  if (ids.length === 0) {
    return { error: "Nothing to reorder." };
  }

  return attempt((token) => reorderRoles(token, ids));
}

export async function giveRole(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const userId = String(formData.get("user_id") ?? "");
  const roleId = String(formData.get("role_id") ?? "");

  if (!roleId) {
    return { error: "Pick a role first." };
  }

  return attempt((token) => grantRole(token, userId, roleId));
}

export async function takeRole(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const userId = String(formData.get("user_id") ?? "");
  const roleId = String(formData.get("role_id") ?? "");

  return attempt((token) => revokeRole(token, userId, roleId));
}
