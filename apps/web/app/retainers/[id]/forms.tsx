"use client";

import { useActionState, useState } from "react";

import {
  answerRequest,
  answerRetainer,
  requestChange,
  reviewWork,
  submitWork,
  withdrawRequest,
} from "@/app/actions/retainers";
import { noError } from "@/lib/forms";
import type { ChangeAction, PendingChange } from "@/lib/retainers";

const loud =
  "rounded-lg bg-pine px-4 py-2.5 text-[14px] text-white transition-opacity hover:opacity-90 disabled:opacity-60";

const quiet =
  "rounded-lg border border-line px-4 py-2.5 text-[14px] text-ink transition-colors hover:bg-white disabled:opacity-60";

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
 * Accept, decline, withdraw, end.
 *
 * `reason` is asked for only where it is read by the other side,
 * so routine actions stay one click. Pausing and resuming are not
 * here: those need the other side to agree, which is a different
 * shape entirely.
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

  const classes = tone === "loud" ? loud : quiet;

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

const ASKING: Record<ChangeAction, string> = {
  pause: "pause this",
  resume: "start it up again",
};

const ASKED: Record<ChangeAction, string> = {
  pause: "to pause this",
  resume: "to start it up again",
};

/**
 * Asking the other side to pause or resume.
 *
 * Worded as a request because that is what it is - nothing
 * happens until they answer - and a button labelled "Pause" that
 * does not pause anything is a small lie.
 */
export function RequestButton({
  retainerId,
  action,
  otherName,
}: {
  retainerId: string;
  action: ChangeAction;
  otherName: string;
}) {
  const [state, submit, pending] = useActionState(
    requestChange,
    noError,
  );
  const [open, setOpen] = useState(false);

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={quiet}
      >
        Ask to {ASKING[action]}
      </button>
    );
  }

  return (
    <div className="w-full max-w-md">
      <form action={submit}>
        <input type="hidden" name="retainer_id" value={retainerId} />
        <input type="hidden" name="action" value={action} />

        <input
          name="reason"
          autoFocus
          placeholder={`Why, so ${otherName} can decide`}
          className="mb-2 w-full rounded-lg border border-line bg-white px-3 py-2 text-[14px] text-ink outline-none placeholder:text-muted/60 focus:border-pine"
        />

        <button type="submit" disabled={pending} className={loud}>
          {pending ? "Sending" : `Ask ${otherName}`}
        </button>
      </form>

      {/* Outside the form on purpose: a type="button" inside one
          whose action is a server action still submits it. */}
      <button
        type="button"
        onClick={() => setOpen(false)}
        className="mt-2 text-[13px] text-muted underline underline-offset-4 hover:text-ink"
      >
        Cancel
      </button>

      <Error message={state.error} />
    </div>
  );
}

/**
 * The banner for a request nobody has answered yet.
 *
 * Reads differently depending on which side of it you are: the
 * one who asked can only wait or take it back, the other gets the
 * decision. Showing both sets to both people would be the quickest
 * way to make approval meaningless.
 */
export function PendingBanner({
  retainerId,
  pending,
  otherName,
}: {
  retainerId: string;
  pending: PendingChange;
  otherName: string;
}) {
  const [answer, submitAnswer, answering] = useActionState(
    answerRequest,
    noError,
  );
  const [taken, submitTake, withdrawing] = useActionState(
    withdrawRequest,
    noError,
  );
  const [saying, setSaying] = useState(false);

  return (
    <section className="mt-6 rounded-lg border border-pine bg-white px-5 py-4">
      <p className="text-[15px] leading-relaxed text-ink">
        {pending.yours
          ? `You asked ${otherName} ${ASKED[pending.action]}.`
          : `${otherName} has asked ${ASKED[pending.action]}.`}{" "}
        <span className="text-muted">
          {pending.yours
            ? "Nothing changes until they agree."
            : "Nothing changes until you agree."}
        </span>
      </p>

      {pending.reason && (
        <p className="mt-2 max-w-[58ch] border-l-2 border-line pl-3 text-[14px] leading-relaxed text-muted">
          {pending.reason}
        </p>
      )}

      {pending.yours ? (
        <form action={submitTake} className="mt-4">
          <input
            type="hidden"
            name="retainer_id"
            value={retainerId}
          />
          <button
            type="submit"
            disabled={withdrawing}
            className={quiet}
          >
            {withdrawing ? "Taking it back" : "Take it back"}
          </button>

          <Error message={taken.error} />
        </form>
      ) : (
        /* The yes and the no are separate forms, and the buttons
           that only flip a toggle sit outside both of them.
           A plain type="button" inside a form whose action is a
           server action still submits it, which made "Say no"
           quietly send the rejection it was only meant to offer. */
        <div className="mt-4 flex flex-wrap items-center gap-2">
          {saying ? (
            <>
              <form
                action={submitAnswer}
                className="flex min-w-0 flex-1 flex-wrap items-center gap-2"
              >
                <input
                  type="hidden"
                  name="retainer_id"
                  value={retainerId}
                />
                <input type="hidden" name="answer" value="reject" />

                <input
                  name="reason"
                  autoFocus
                  placeholder="Why not, if you want to say"
                  className="min-w-0 flex-1 rounded-lg border border-line bg-white px-3 py-2 text-[14px] text-ink outline-none placeholder:text-muted/60 focus:border-pine"
                />

                <button
                  type="submit"
                  disabled={answering}
                  className={quiet}
                >
                  {answering ? "Sending" : "Send the no"}
                </button>
              </form>

              <button
                type="button"
                onClick={() => setSaying(false)}
                className="text-[13px] text-muted underline underline-offset-4 hover:text-ink"
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              <form action={submitAnswer}>
                <input
                  type="hidden"
                  name="retainer_id"
                  value={retainerId}
                />
                <input
                  type="hidden"
                  name="answer"
                  value="approve"
                />

                <button
                  type="submit"
                  disabled={answering}
                  className={loud}
                >
                  {answering ? "Working" : "Agree"}
                </button>
              </form>

              <button
                type="button"
                onClick={() => setSaying(true)}
                className={quiet}
              >
                Say no
              </button>
            </>
          )}

          <Error message={answer.error} />
        </div>
      )}
    </section>
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

  const hidden = (
    <>
      <input type="hidden" name="retainer_id" value={retainerId} />
      <input
        type="hidden"
        name="deliverable_id"
        value={deliverableId}
      />
    </>
  );

  /* The toggles live outside the form for the same reason as in
     PendingBanner: a type="button" inside a form bound to a
     server action still submits it, which here meant "Ask for
     changes" fired a review with no decision attached. */
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      {changes ? (
        <>
          <form
            action={submit}
            className="flex min-w-0 flex-1 flex-wrap gap-2"
          >
            {hidden}
            <input
              type="hidden"
              name="decision"
              value="request_revision"
            />
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
          </form>

          <button
            type="button"
            onClick={() => setChanges(false)}
            className="text-[13px] text-muted underline underline-offset-4 hover:text-ink"
          >
            Cancel
          </button>
        </>
      ) : (
        <>
          <form action={submit}>
            {hidden}
            <input type="hidden" name="decision" value="approve" />
            <button
              type="submit"
              disabled={pending}
              className="rounded-lg bg-pine px-4 py-2 text-[14px] text-white transition-opacity hover:opacity-90 disabled:opacity-60"
            >
              {pending ? "Working" : "Approve"}
            </button>
          </form>

          <button
            type="button"
            onClick={() => setChanges(true)}
            className="rounded-lg border border-line px-4 py-2 text-[14px] text-ink transition-colors hover:bg-white"
          >
            Ask for changes
          </button>
        </>
      )}

      <Error message={state.error} />
    </div>
  );
}
