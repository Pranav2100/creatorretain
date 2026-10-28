"use server";

import { revalidatePath } from "next/cache";

import { storeToken } from "@/app/actions/session";
import { changePassword, updateAccount } from "@/lib/account";
import { ApiError } from "@/lib/api";
import { noError, type FormState } from "@/lib/forms";
import { requireToken } from "@/lib/session";

function failed(caught: unknown): FormState {
  if (caught instanceof ApiError) {
    return { error: caught.message };
  }

  return { error: "Could not reach the server. Is the API running?" };
}

export async function saveDetails(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const token = await requireToken();

  const first = String(formData.get("first_name") ?? "").trim();
  const last = String(formData.get("last_name") ?? "").trim();
  const email = String(formData.get("email") ?? "").trim();
  const phone = String(formData.get("phone") ?? "").trim();
  const title = String(formData.get("job_title") ?? "").trim();
  const password = String(formData.get("current_password") ?? "");

  if (!first || !last) {
    return { error: "Your name cannot be empty." };
  }

  if (!email) {
    return { error: "Enter the email you sign in with." };
  }

  try {
    await updateAccount(token, {
      first_name: first,
      last_name: last,
      email,
      phone,
      job_title: title,
      current_password: password || undefined,
    });
  } catch (caught) {
    return failed(caught);
  }

  // The header carries this person's name on some pages, and the
  // team list carries it on others, so the whole tree is stale.
  revalidatePath("/", "layout");

  return { ...noError, done: "Saved." };
}

export async function setPassword(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const token = await requireToken();

  const current = String(formData.get("current_password") ?? "");
  const next = String(formData.get("new_password") ?? "");
  const confirm = String(formData.get("confirm_password") ?? "");

  if (!current || !next) {
    return { error: "Fill in both passwords." };
  }

  let replacement: string;

  try {
    replacement = await changePassword(token, {
      current_password: current,
      new_password: next,
      confirm_password: confirm,
    });
  } catch (caught) {
    return failed(caught);
  }

  // The cookie is holding a token that stopped working the moment
  // the password changed. Swapping it is what keeps this browser
  // signed in while every other one is signed out.
  await storeToken(replacement);

  return {
    ...noError,
    done: "Password changed. Any other browser has been signed out.",
  };
}
