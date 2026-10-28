"use client";

import Link from "next/link";
import { useActionState } from "react";

import { offerRetainer } from "@/app/actions/retainers";
import { noError } from "@/lib/forms";
import {
  DELIVERABLE_LABEL,
  type DeliverableType,
} from "@/lib/retainers";

// The seven the API accepts, in the order a brand thinks about
// them: the things that get posted first, then the services.
const TYPES: DeliverableType[] = [
  "reel",
  "video",
  "post",
  "story",
  "ugc",
  "editing",
  "strategy",
];

type Props = {
  creatorWorkspaceId: string;
  creatorName: string;
  suggestedTitle: string;
  suggestedAmount: string | null;
  currency: string;
};

export function OfferForm({
  creatorWorkspaceId,
  creatorName,
  suggestedTitle,
  suggestedAmount,
  currency,
}: Props) {
  const [state, action, pending] = useActionState(
    offerRetainer,
    noError,
  );

  return (
    <form action={action} className="mt-8 max-w-[34rem]">
      <input
        type="hidden"
        name="creator_workspace_id"
        value={creatorWorkspaceId}
      />
      <input type="hidden" name="currency" value={currency} />

      <label className="block">
        <span className="mb-1.5 block text-[13px] text-muted">
          What is this for
        </span>
        <input
          name="title"
          defaultValue={suggestedTitle}
          maxLength={120}
          required
          className="w-full rounded-lg border border-line bg-surface px-3 py-2.5 text-[15px] text-ink outline-none focus:border-pine"
        />
      </label>

      <label className="mt-5 block max-w-[14rem]">
        <span className="mb-1.5 block text-[13px] text-muted">
          Every month
        </span>
        <input
          name="monthly_amount"
          type="number"
          min={1}
          step={1}
          defaultValue={
            suggestedAmount ? Math.round(Number(suggestedAmount)) : ""
          }
          required
          className="w-full rounded-lg border border-line bg-surface px-3 py-2.5 text-[15px] tabular-nums text-ink outline-none focus:border-pine"
        />
        <span className="mt-1 block text-[12px] text-muted">
          {currency}, before any platform fee
        </span>
      </label>

      <fieldset className="mt-8">
        <legend className="text-[13px] text-muted">
          What they deliver each month
        </legend>

        <div className="mt-3 grid grid-cols-2 gap-x-4 sm:grid-cols-4">
          {TYPES.map((type) => (
            <label key={type} className="block">
              <span className="mb-1 block text-[13px] text-ink">
                {DELIVERABLE_LABEL[type]}
              </span>
              <input
                name={`quantity_${type}`}
                type="number"
                min={0}
                max={60}
                placeholder="0"
                className="w-full rounded-lg border border-line bg-surface px-2.5 py-2 text-[15px] tabular-nums text-ink outline-none placeholder:text-muted focus:border-pine"
              />
            </label>
          ))}
        </div>

        <p className="mt-3 text-[13px] leading-relaxed text-muted">
          Leave a box empty to skip it. These repeat every month
          until someone ends the retainer.
        </p>
      </fieldset>

      <label className="mt-8 block">
        <span className="mb-1.5 block text-[13px] text-muted">
          A note to {creatorName}
        </span>
        <textarea
          name="message"
          rows={3}
          placeholder={
            `We have been watching your reels for a while and the ` +
            `tone is right for our client. Happy to talk the brief ` +
            `through before you decide.`
          }
          className="w-full resize-y rounded-lg border border-line bg-surface px-3 py-2.5 text-[15px] leading-relaxed text-ink outline-none placeholder:text-muted focus:border-pine"
        />
      </label>

      <label className="mt-5 block">
        <span className="mb-1.5 block text-[13px] text-muted">
          Terms, if you have any
        </span>
        <textarea
          name="terms"
          rows={2}
          placeholder={
            "Drafts by the 20th, paid within seven days of the " +
            "month ending, usage limited to our own channels."
          }
          className="w-full resize-y rounded-lg border border-line bg-surface px-3 py-2.5 text-[15px] leading-relaxed text-ink outline-none placeholder:text-muted focus:border-pine"
        />
      </label>

      <label className="mt-5 block max-w-[10rem]">
        <span className="mb-1.5 block text-[13px] text-muted">
          Notice to end
        </span>
        <input
          name="notice_period_days"
          type="number"
          min={0}
          max={180}
          defaultValue={30}
          className="w-full rounded-lg border border-line bg-surface px-3 py-2.5 text-[15px] tabular-nums text-ink outline-none focus:border-pine"
        />
        <span className="mt-1 block text-[12px] text-muted">
          days
        </span>
      </label>

      {state.error && (
        <p
          role="alert"
          className="mt-6 border-l-2 border-pine pl-3 text-[14px] leading-relaxed text-ink"
        >
          {state.error}
        </p>
      )}

      <div className="mt-8 flex items-center gap-5">
        <button
          type="submit"
          disabled={pending}
          className="rounded-lg bg-pine px-5 py-3 text-[15px] text-on-pine transition-opacity hover:opacity-90 disabled:opacity-60"
        >
          {pending ? "Sending" : `Send to ${creatorName}`}
        </button>

        <Link
          href="/creators"
          className="text-[14px] text-muted underline underline-offset-4 hover:text-ink"
        >
          Cancel
        </Link>
      </div>

      <p className="mt-4 max-w-[42ch] text-[13px] leading-relaxed text-muted">
        Nothing starts until {creatorName} accepts. The first month
        begins the day they do.
      </p>
    </form>
  );
}
