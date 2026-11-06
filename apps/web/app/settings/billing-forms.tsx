"use client";

import { useActionState } from "react";

import { subscribe, unsubscribe } from "@/app/actions/billing";
import type { Billing, PlanOffer } from "@/lib/billing";
import { noError } from "@/lib/forms";

const PLAN_LABEL: Record<string, string> = {
  free: "Free",
  pro: "Pro",
  business: "Business",
  managed: "Managed",
  verified: "Verified",
};

/** Whole rupees, grouped the Indian way. */
function rupees(amount: number): string {
  return `₹${amount.toLocaleString("en-IN")}`;
}

function when(iso: string | null): string {
  if (!iso) return "";

  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function Offer({ offer }: { offer: PlanOffer }) {
  const [state, action, going] = useActionState(subscribe, noError);

  return (
    <li className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2 border-b border-line py-3.5 first:border-t">
      <span className="min-w-0">
        <span className="text-[15px] text-ink">
          {PLAN_LABEL[offer.plan] ?? offer.plan}
        </span>
        {offer.current && (
          <span className="ml-2 text-[13px] text-pine">
            your plan
          </span>
        )}
        <span className="block text-[13px] text-muted">
          {offer.price !== null
            ? `${rupees(offer.price)} a month`
            : offer.plan === "free"
              ? "No charge"
              : "Arranged with us — get in touch"}
        </span>
      </span>

      {offer.purchasable && !offer.current && (
        <form action={action}>
          <input type="hidden" name="plan" value={offer.plan} />
          <button
            type="submit"
            disabled={going}
            className="rounded-lg bg-pine px-4 py-2 text-[14px] font-medium text-on-pine transition-colors hover:bg-pine-hover disabled:opacity-60"
          >
            {going ? "Taking you to pay" : "Choose"}
          </button>
        </form>
      )}

      {state.error && (
        <span className="w-full text-[13px] text-alarm">
          {state.error}
        </span>
      )}
    </li>
  );
}

export function PlanChooser({ billing }: { billing: Billing }) {
  const [state, cancel, cancelling] = useActionState(
    unsubscribe,
    noError,
  );

  const live = billing.subscription;

  return (
    <>
      {live && (
        <div className="mb-5 rounded-[14px] border border-line bg-surface p-4">
          <p className="text-[14px] text-ink">
            {live.status === "pending" &&
              "Waiting for your payment to go through."}
            {live.status === "active" &&
              `Paying ${live.amount ? rupees(live.amount) : ""} a month for ${PLAN_LABEL[live.plan] ?? live.plan}.`}
            {live.status === "past_due" &&
              "The last payment did not go through. Your plan runs until the date below."}
            {live.status === "cancelling" &&
              "This will not renew."}
          </p>

          {live.current_period_end && (
            <p className="mt-1 text-[13px] text-muted">
              {live.status === "cancelling"
                ? `Yours until ${when(live.current_period_end)}, then Free.`
                : `Next charge ${when(live.current_period_end)}.`}
            </p>
          )}

          {!live.cancelled && (
            <form action={cancel} className="mt-3">
              <button
                type="submit"
                disabled={cancelling}
                className="text-[13px] text-muted underline underline-offset-4 hover:text-ink disabled:opacity-60"
              >
                {cancelling
                  ? "Stopping"
                  : live.status === "pending"
                    ? // Nothing has been paid, so there is
                      // nothing to keep until the end of - this
                      // just clears it, and without it an
                      // abandoned checkout leaves the banner
                      // above claiming for ever that a payment
                      // is on its way.
                      "Forget this, I changed my mind"
                    : "Stop this renewing"}
              </button>
            </form>
          )}

          {state.done && (
            <p className="mt-2 text-[13px] text-pine">{state.done}</p>
          )}

          {state.error && (
            <p className="mt-2 text-[13px] text-alarm">
              {state.error}
            </p>
          )}
        </div>
      )}

      <ul>
        {billing.plans.map((offer) => (
          <Offer key={offer.plan} offer={offer} />
        ))}
      </ul>

      <p className="mt-5 max-w-[58ch] text-[13px] leading-relaxed text-muted">
        Payment is handled by our provider — nothing on this site
        ever sees your card. Your plan starts when they confirm
        the payment, and cancelling keeps what you have already
        paid for until it runs out.
      </p>
    </>
  );
}
