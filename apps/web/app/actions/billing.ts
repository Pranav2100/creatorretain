"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError } from "@/lib/api";
import { noError, type FormState } from "@/lib/forms";
import {
  cancelSubscription,
  startSubscription,
} from "@/lib/billing";
import { requireToken } from "@/lib/session";

function failed(caught: unknown): FormState {
  if (caught instanceof ApiError) {
    return { error: caught.message };
  }

  return { error: "Could not reach the server. Is the API running?" };
}

/**
 * Starts a subscription and sends the person off to pay.
 *
 * The redirect is the whole point: nothing in this application
 * ever sees a card. They leave, pay at the provider, and the
 * plan arrives when the provider says so - not when they come
 * back, and not because they clicked this.
 */
export async function subscribe(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const plan = String(formData.get("plan") ?? "");

  if (!plan) {
    return { error: "Pick a plan first." };
  }

  const token = await requireToken("/settings");

  let payUrl: string | null = null;

  try {
    const checkout = await startSubscription(token, plan);
    payUrl = checkout.pay_url;
  } catch (caught) {
    return failed(caught);
  }

  revalidatePath("/settings");

  if (payUrl) {
    // Outside redirect, so this throws - it must be after the
    // try, or the catch above would swallow Next's control-flow
    // exception and report a payment link as an error.
    redirect(payUrl);
  }

  return noError;
}

// No parameters: useActionState passes a previous state and the
// form data, and this needs neither. JavaScript ignores extra
// arguments and TypeScript allows a function that takes fewer,
// so declaring them only to ignore them would be noise.
export async function unsubscribe(): Promise<FormState> {
  const token = await requireToken("/settings");

  let ended: boolean;

  try {
    // What came back says which of the two things happened. A
    // checkout nobody paid for just stops; a paid plan keeps
    // running to the end of what it bought. Telling someone
    // their plan "will not renew" when they never paid for one
    // describes something that was never going to happen.
    ended = (await cancelSubscription(token)).status === "ended";
  } catch (caught) {
    return failed(caught);
  }

  revalidatePath("/settings");

  return {
    error: null,
    done: ended
      ? "That is cleared — you have not been charged."
      : "Your plan will not renew.",
  };
}
