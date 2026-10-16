"use server";

import { revalidatePath } from "next/cache";

import { ApiError } from "@/lib/api";
import type { FormState } from "@/lib/forms";
import { requireToken } from "@/lib/session";
import {
  cancelInvitation,
  changeRole,
  inviteMember,
  removeLogo,
  removeMember,
  resendInvitation,
  saveWorkspace,
  uploadLogo,
} from "@/lib/team";

const noError: FormState = { error: null };

async function attempt(
  work: (token: string) => Promise<unknown>,
): Promise<FormState> {
  const token = await requireToken("/settings");

  try {
    await work(token);
    revalidatePath("/settings");
    return noError;
  } catch (caught) {
    if (caught instanceof ApiError) {
      return { error: caught.message };
    }

    return {
      error: "Could not reach the server. Is the API running?",
    };
  }
}

/**
 * Null, not undefined, for the fields someone cleared.
 *
 * The API applies exactly what it is sent, so an emptied box has
 * to arrive as an explicit null or the old value stays put and the
 * form appears to have silently ignored the person.
 */
function cleared(value: FormDataEntryValue | null): string | null {
  return String(value ?? "").trim() || null;
}

export async function updateWorkspace(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const name = String(formData.get("display_name") ?? "").trim();

  if (name.length < 2) {
    return { error: "Give the workspace a name." };
  }

  return attempt((token) =>
    saveWorkspace(token, {
      display_name: name,
      legal_name: cleared(formData.get("legal_name")),
      bio: cleared(formData.get("bio")),
      website_url: cleared(formData.get("website_url")),
    }),
  );
}

export async function setLogo(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const file = formData.get("file");

  if (!(file instanceof File) || file.size === 0) {
    return { error: "Choose an image first." };
  }

  return attempt((token) => uploadLogo(token, file));
}

export async function clearLogo(): Promise<FormState> {
  return attempt((token) => removeLogo(token));
}

export async function invite(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const email = String(formData.get("email") ?? "").trim();

  if (!email) {
    return { error: "Enter an email address." };
  }

  const role =
    String(formData.get("role") ?? "member") === "admin"
      ? "admin"
      : "member";

  return attempt((token) => inviteMember(token, email, role));
}

export async function setRole(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const role =
    String(formData.get("role") ?? "") === "admin"
      ? "admin"
      : "member";

  return attempt((token) =>
    changeRole(token, String(formData.get("member_id") ?? ""), role),
  );
}

export async function dropMember(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  return attempt((token) =>
    removeMember(token, String(formData.get("member_id") ?? "")),
  );
}

export async function withdrawInvitation(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  return attempt((token) =>
    cancelInvitation(
      token,
      String(formData.get("invitation_id") ?? ""),
    ),
  );
}

export async function sendAgain(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  return attempt((token) =>
    resendInvitation(
      token,
      String(formData.get("invitation_id") ?? ""),
    ),
  );
}
