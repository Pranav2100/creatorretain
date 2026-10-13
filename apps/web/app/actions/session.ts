"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ApiError, login } from "@/lib/api";
import type { FormState } from "@/lib/forms";
import { SESSION_COOKIE, SESSION_MAX_AGE } from "@/lib/session";
import { getWorkspaceContext, landingFor } from "@/lib/workspace";

/**
 * Exchanges a password for a session cookie.
 *
 * The token is set httpOnly, so no script on the page can read it -
 * including anything injected into the page. The browser attaches it
 * to requests this app makes; the token itself never reaches
 * client-side JavaScript.
 */
export async function signIn(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  const next = String(formData.get("next") ?? "").trim();

  if (!email || !password) {
    return { error: "Enter your email and password." };
  }

  let token: string;

  try {
    token = await login(email, password);
  } catch (caught) {
    if (caught instanceof ApiError) {
      return { error: caught.message };
    }

    return {
      error: "Could not reach the server. Is the API running?",
    };
  }

  await storeToken(token);

  // Only internal paths, so a crafted ?next= cannot bounce someone
  // to another site straight after they type their password.
  if (next.startsWith("/")) {
    redirect(next);
  }

  const context = await getWorkspaceContext(token);

  redirect(context ? landingFor(context.plan) : "/retainers");
}

export async function signOut(): Promise<void> {
  const store = await cookies();
  store.delete(SESSION_COOKIE);

  redirect("/login");
}

export async function storeToken(token: string): Promise<void> {
  const store = await cookies();

  store.set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: SESSION_MAX_AGE,
  });
}
