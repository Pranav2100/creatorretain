"use server";

import { redirect } from "next/navigation";

import { ApiError, login, register } from "@/lib/api";
import type { FormState } from "@/lib/forms";
import { createWorkspace } from "@/lib/signup";
import { requireToken } from "@/lib/session";
import {
  getWorkspaceContext,
  landingFor,
  NO_WORKSPACE,
  type WorkspaceType,
} from "@/lib/workspace";

import { storeToken } from "./session";

const TYPES: WorkspaceType[] = ["creator", "brand", "agency"];

/**
 * Creates the account and signs them straight in.
 *
 * Deliberately stops short of the workspace. Making both at once
 * means a taken username leaves behind an account that exists but
 * cannot be finished, and the person has to work out whether to
 * register again. Two steps makes the half-done state a normal
 * place to be rather than a dead end.
 */
export async function signUp(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const firstName = String(formData.get("first_name") ?? "").trim();
  const lastName = String(formData.get("last_name") ?? "").trim();
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  const confirm = String(formData.get("confirm_password") ?? "");

  if (!firstName || !lastName) {
    return { error: "Enter your first and last name." };
  }

  if (!email) {
    return { error: "Enter your email." };
  }

  if (password !== confirm) {
    return { error: "Those passwords do not match." };
  }

  try {
    await register({
      first_name: firstName,
      last_name: lastName,
      email,
      password,
      confirm_password: confirm,
    });
  } catch (caught) {
    if (caught instanceof ApiError) {
      return { error: caught.message };
    }

    return {
      error: "Could not reach the server. Is the API running?",
    };
  }

  try {
    await storeToken(await login(email, password));
  } catch {
    // The account is real; only the automatic sign-in failed.
    return {
      error:
        "Your account was created, but signing you in failed. " +
        "Try signing in.",
    };
  }

  const chosen = String(formData.get("workspace_type") ?? "");

  redirect(
    TYPES.includes(chosen as WorkspaceType)
      ? `/setup?as=${chosen}`
      : "/setup",
  );
}

export async function setUpWorkspace(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const token = await requireToken();

  const displayName = String(formData.get("display_name") ?? "").trim();
  const username = String(formData.get("username") ?? "")
    .trim()
    .toLowerCase();
  const type = String(formData.get("workspace_type") ?? "");
  const legalName = String(formData.get("legal_name") ?? "").trim();

  if (!displayName) {
    return { error: "Give your workspace a name." };
  }

  if (!TYPES.includes(type as WorkspaceType)) {
    return { error: "Choose what kind of workspace this is." };
  }

  try {
    await createWorkspace(token, {
      display_name: displayName,
      username,
      workspace_type: type as WorkspaceType,
      legal_name: legalName || null,
    });
  } catch (caught) {
    if (caught instanceof ApiError) {
      return { error: caught.message };
    }

    return {
      error: "Could not reach the server. Is the API running?",
    };
  }

  const context = await getWorkspaceContext(token);

  if (context === NO_WORKSPACE || !context) {
    redirect("/setup");
  }

  // A creator's first stop is their profile: an empty one is
  // invisible, and nothing else in the product works until it is
  // filled in.
  if (context.workspace.workspace_type === "creator") {
    redirect("/profile");
  }

  redirect(landingFor(context.plan));
}
