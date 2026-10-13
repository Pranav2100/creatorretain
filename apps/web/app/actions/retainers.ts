"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";

import { ApiError } from "@/lib/api";
import { noError, type FormState } from "@/lib/forms";
import {
  actOnRetainer,
  createRetainer,
  reviewDeliverable,
  submitDeliverable,
  type ReviewDecision,
} from "@/lib/retainers";
import { requireToken } from "@/lib/session";

/**
 * Runs an action and turns a refusal into something the form can
 * show. The API already writes these messages for people - "Upgrade
 * to Pro to..." - so passing the text straight through beats
 * inventing a second, vaguer copy of it on this side.
 */
async function attempt(
  work: () => Promise<unknown>,
): Promise<FormState> {
  try {
    await work();
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

export async function offerRetainer(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const token = await requireToken();

  const creatorWorkspaceId = String(
    formData.get("creator_workspace_id") ?? "",
  );
  const title = String(formData.get("title") ?? "").trim();
  const amount = String(formData.get("monthly_amount") ?? "").trim();
  const currency = String(formData.get("currency") ?? "INR");
  const message = String(formData.get("message") ?? "").trim();
  const terms = String(formData.get("terms") ?? "").trim();

  if (!title) {
    return { error: "Give the retainer a title." };
  }

  if (!amount || Number(amount) <= 0) {
    return { error: "Enter a monthly amount." };
  }

  const deliverables = readDeliverables(formData);

  if (deliverables.length === 0) {
    return {
      error: "Add at least one deliverable, with a quantity above zero.",
    };
  }

  let id: string | null = null;

  const state = await attempt(async () => {
    const retainer = await createRetainer(token, {
      creator_workspace_id: creatorWorkspaceId,
      title,
      monthly_amount: amount,
      currency,
      deliverables,
      message: message || null,
      terms: terms || null,
      notice_period_days: Number(
        formData.get("notice_period_days") ?? 30,
      ),
    });

    id = retainer.id;
  });

  if (state.error) {
    return state;
  }

  revalidatePath("/retainers");
  redirect(`/retainers/${id}`);
}

/**
 * The form sends one quantity per deliverable type. Anything left
 * blank or at zero is simply not part of the offer, rather than an
 * error to correct.
 */
function readDeliverables(formData: FormData) {
  const deliverables: { deliverable_type: string; quantity: number }[] =
    [];

  for (const [key, value] of formData.entries()) {
    if (!key.startsWith("quantity_")) continue;

    const quantity = Number(String(value).trim());

    if (!Number.isFinite(quantity) || quantity < 1) continue;

    deliverables.push({
      deliverable_type: key.slice("quantity_".length),
      quantity: Math.floor(quantity),
    });
  }

  return deliverables;
}

export async function answerRetainer(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const token = await requireToken();

  const id = String(formData.get("retainer_id") ?? "");
  const action = String(formData.get("action") ?? "") as
    | "accept"
    | "decline"
    | "cancel"
    | "pause"
    | "resume"
    | "end";

  const reason = String(formData.get("reason") ?? "").trim();

  const state = await attempt(() =>
    actOnRetainer(
      token,
      id,
      action,
      reason ? { reason } : undefined,
    ),
  );

  if (!state.error) {
    revalidatePath(`/retainers/${id}`);
    revalidatePath("/retainers");
  }

  return state;
}

export async function submitWork(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const token = await requireToken();

  const deliverableId = String(formData.get("deliverable_id") ?? "");
  const retainerId = String(formData.get("retainer_id") ?? "");
  const url = String(formData.get("url") ?? "").trim();
  const note = String(formData.get("note") ?? "").trim();

  if (!url) {
    return { error: "Paste a link to the work." };
  }

  const state = await attempt(() =>
    submitDeliverable(token, deliverableId, {
      url,
      note: note || null,
    }),
  );

  if (!state.error) {
    revalidatePath(`/retainers/${retainerId}`);
  }

  return state;
}

export async function reviewWork(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const token = await requireToken();

  const deliverableId = String(formData.get("deliverable_id") ?? "");
  const retainerId = String(formData.get("retainer_id") ?? "");
  const decision = String(
    formData.get("decision") ?? "",
  ) as ReviewDecision;
  const note = String(formData.get("note") ?? "").trim();

  if (decision === "request_revision" && !note) {
    return { error: "Say what needs changing." };
  }

  const state = await attempt(() =>
    reviewDeliverable(token, deliverableId, {
      decision,
      note: note || null,
    }),
  );

  if (!state.error) {
    revalidatePath(`/retainers/${retainerId}`);
  }

  return state;
}
