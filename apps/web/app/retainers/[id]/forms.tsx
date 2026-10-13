"use client";

import { useActionState, useState } from "react";

import {
  answerRetainer,
  reviewWork,
  submitWork,
} from "@/app/actions/retainers";
import { noError } from "@/lib/forms";

function Error({ message }: { message: string | null }) {
  if (!message) return null;

  return (
    <p
      role="alert"
      className="mt-3 border-l-2 border-pine pl-3 text-[13px] leading-relaxed text-ink"
    >
      {message}
    </p>
  );
}

/**
 * Accept, decline, withdraw, pause, resume, end.
 *
 * `reason` is asked for only where it is read by the other side,
 * so routine actions stay one click.
 */
export function AnswerButton({
  retainerId,
  action,
  label,
  tone = "quiet",
  asks,
}: {
  retainerId: string;
  action: string;
  label: string;
  tone?: "loud" | "quiet";
  asks?: string;
}) {
  const [state, submit, pending] = useActionState(
    answerRetainer,
    noError,
  );
  const [open, setOpen] = useState(false);

  const classes =
    tone === "loud"
      ? "rounded-lg bg-pine px-4 py-2.5 text-[14px] text-white transition-opacity hover:opacity-90 disabled:opacity-60"
      : "rounded-lg border border-line px-4 py-2.5 text-[14px] text-ink transition-colors hover:bg-white disabled:opacity-60";

  if (asks && !open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={classes}
      >
        {label}
      </button>
    );
  }

  return (
    <form action={submit} className={asks ? "w-full" : ""}>
      <input type="hidden" name="retainer_id" value={retainerId} />
      <input type="hidden" name="action" value={action} />

      {asks && (
        <input
          name="reason"
          placeholder={asks}
          autoFocus
          className="mb-2 w-full rounded-lg border border-line bg-white px-3 py-2 text-[14px] text-ink outline-none focus:border-pine"
        />
      )}

      <button type="submit" disabled={pending} className={classes}>
        {pending ? "Working" : label}
      </button>

      <Error message={state.error} />
    </form>
  );
}

export function SubmitWorkForm({
  retainerId,
  deliverableId,
  resubmitting,
}: {
  retainerId: string;
  deliverableId: string;
  resubmitting: boolean;
}) {
  const [state, submit, pending] = useActionState(
    submitWork,
    noError,
  );

  return (
    <form action={submit} className="mt-3">
      <input type="hidden" name="retainer_id" value={retainerId} />
      <input
        type="hidden"
        name="deliverable_id"
        value={deliverableId}
      />

      <div className="flex flex-wrap gap-2">
        <input
          name="url"
          type="url"
          required
          placeholder="https://instagram.com/p/..."
          className="min-w-0 flex-1 rounded-lg border border-line bg-white px-3 py-2 text-[14px] text-ink outline-none placeholder:text-muted/60 focus:border-pine"
        />
        <input
          name="note"
          placeholder="Anything to add"
          className="min-w-0 flex-1 rounded-lg border border-line bg-white px-3 py-2 text-[14px] text-ink outline-none placeholder:text-muted/60 focus:border-pine"
        />
        {/* Quiet on purpose: this button repeats on every
            deliverable, and six loud ones in a column read as
            noise rather than as six decisions. */}
        <button
          type="submit"
          disabled={pending}
          className="rounded-lg border border-line bg-white px-4 py-2 text-[14px] text-ink transition-colors hover:border-pine disabled:opacity-60"
        >
          {pending
            ? "Sending"
            : resubmitting
              ? "Send again"
              : "Submit"}
        </button>
      </div>

      <Error message={state.error} />
    </form>
  );
}

export function ReviewForm({
  retainerId,
  deliverableId,
}: {
  retainerId: string;
  deliverableId: string;
}) {
  const [state, submit, pending] = useActionState(
    reviewWork,
    noError,
  );
  const [changes, setChanges] = useState(false);

  return (
    <form action={submit} className="mt-3">
      <input type="hidden" name="retainer_id" value={retainerId} />
      <input
        type="hidden"
        name="deliverable_id"
        value={deliverableId}
      />

      {changes ? (
        <div className="flex flex-wrap gap-2">
          <input type="hidden" name="decision" value="request_revision" />
          <input
            name="note"
            autoFocus
            required
            placeholder="What needs changing"
            className="min-w-0 flex-1 rounded-lg border border-line bg-white px-3 py-2 text-[14px] text-ink outline-none placeholder:text-muted/60 focus:border-pine"
          />
          <button
            type="submit"
            disabled={pending}
            className="rounded-lg bg-pine px-4 py-2 text-[14px] text-white transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            {pending ? "Sending" : "Send back"}
          </button>
          <button
            type="button"
            onClick={() => setChanges(false)}
            className="text-[13px] text-muted underline underline-offset-4 hover:text-ink"
          >
            Cancel
          </button>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="submit"
            name="decision"
            value="approve"
            disabled={pending}
            className="rounded-lg bg-pine px-4 py-2 text-[14px] text-white transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            {pending ? "Working" : "Approve"}
          </button>

          <button
            type="button"
            onClick={() => setChanges(true)}
            className="rounded-lg border border-line px-4 py-2 text-[14px] text-ink transition-colors hover:bg-white"
          >
            Ask for changes
          </button>
        </div>
      )}

      <Error message={state.error} />
    </form>
  );
}
