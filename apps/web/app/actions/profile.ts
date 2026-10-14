"use server";

import { revalidatePath } from "next/cache";

import { ApiError } from "@/lib/api";
import type { FormState } from "@/lib/forms";
import { isLanguageCode } from "@/lib/places";
import {
  addItem,
  removeItem,
  saveBasics,
  saveCategories,
  setVisibility,
} from "@/lib/profile";
import { requireToken } from "@/lib/session";

const noError: FormState = { error: null };

async function attempt(
  work: (token: string) => Promise<unknown>,
): Promise<FormState> {
  const token = await requireToken("/profile");

  try {
    await work(token);
    revalidatePath("/profile");
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

function list(value: FormDataEntryValue | null): string[] {
  return String(value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

/**
 * An ISO code is stored lowercase, the way the rest of the API
 * expects it. Anything else came from the "Other" box, so it keeps
 * the capitalisation the creator typed - lowercasing "Tulu" into
 * "tulu" would be us mangling their own answer.
 */
function language(value: string): string {
  return isLanguageCode(value) ? value.toLowerCase() : value;
}

function optional(value: FormDataEntryValue | null): string | null {
  const text = String(value ?? "").trim();
  return text || null;
}

export async function updateBasics(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  return attempt((token) =>
    saveBasics(token, {
      headline: optional(formData.get("headline")),
      bio: optional(formData.get("bio")),
      city: optional(formData.get("city")),
      state: optional(formData.get("state")),
      country:
        optional(formData.get("country"))?.toUpperCase() ?? null,
      languages: list(formData.get("languages")).map(language),
      skills: list(formData.get("skills")),
      monthly_retainer_min: optional(
        formData.get("monthly_retainer_min"),
      ),
      currency:
        optional(formData.get("currency"))?.toUpperCase() ?? "INR",
      availability: String(
        formData.get("availability") ?? "available",
      ),
    }),
  );
}

export async function updateCategories(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const chosen = formData.getAll("category_ids").map(String);

  if (chosen.length > 5) {
    return { error: "Pick at most five beats." };
  }

  return attempt((token) => saveCategories(token, chosen));
}

export async function addSocialAccount(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const handle = String(formData.get("handle") ?? "").trim();

  if (!handle) {
    return { error: "Enter your handle." };
  }

  return attempt((token) =>
    addItem(token, "social-accounts", {
      platform: String(formData.get("platform") ?? "instagram"),
      handle: handle.replace(/^@/, ""),
      profile_url: optional(formData.get("profile_url")),
      claimed_followers: numeric(formData.get("claimed_followers")),
      claimed_engagement_rate: optional(
        formData.get("claimed_engagement_rate"),
      ),
    }),
  );
}

export async function addRate(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const price = optional(formData.get("price"));

  if (!price || Number(price) <= 0) {
    return { error: "Enter a price above zero." };
  }

  return attempt((token) =>
    addItem(token, "rates", {
      deliverable_type: String(
        formData.get("deliverable_type") ?? "reel",
      ),
      quantity: numeric(formData.get("quantity")) ?? 1,
      price,
      currency:
        optional(formData.get("currency"))?.toUpperCase() ?? "INR",
      notes: optional(formData.get("notes")),
    }),
  );
}

export async function addPortfolioItem(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const title = String(formData.get("title") ?? "").trim();

  if (!title) {
    return { error: "Give the piece a title." };
  }

  return attempt((token) =>
    addItem(token, "portfolio", {
      title,
      description: optional(formData.get("description")),
      platform: optional(formData.get("platform")),
      external_url: optional(formData.get("external_url")),
    }),
  );
}

export async function deleteItem(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const kind = String(formData.get("kind") ?? "");
  const id = String(formData.get("id") ?? "");

  if (
    kind !== "social-accounts" &&
    kind !== "portfolio" &&
    kind !== "rates"
  ) {
    return { error: "Nothing to remove." };
  }

  return attempt((token) => removeItem(token, kind, id));
}

export async function toggleVisibility(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const hide = String(formData.get("hide") ?? "") === "true";

  return attempt((token) => setVisibility(token, hide));
}

function numeric(value: FormDataEntryValue | null): number | null {
  const text = String(value ?? "").trim();

  if (!text) return null;

  const parsed = Number(text);

  return Number.isFinite(parsed) ? Math.floor(parsed) : null;
}
