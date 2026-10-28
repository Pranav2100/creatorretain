"use client";

import { useActionState, useEffect, useRef, useState } from "react";

import {
  blockThem,
  letThemIn,
  say,
  turnThemAway,
} from "@/app/actions/messages";
import { noError } from "@/lib/forms";

const loud =
  "rounded-lg bg-pine px-5 py-2.5 text-[14px] text-on-pine transition-opacity hover:opacity-90 disabled:opacity-60";

const quiet =
  "rounded-lg border border-line bg-surface px-4 py-2.5 text-[14px] text-ink transition-colors hover:border-pine disabled:opacity-60";

function Problem({ message }: { message: string | null }) {
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
 * The box at the bottom.
 *
 * Return sends and shift-return makes a new line, which is what
 * every chat box does and therefore what fingers already expect.
 * The field is cleared by hand after a send rather than by
 * resetting the form, because resetting it would also wipe
 * anything typed while the last message was in flight.
 */
export function Composer({
  conversationId,
  name,
  open,
  awaitingAcceptance,
}: {
  conversationId: string;
  name: string;
  open: boolean;
  awaitingAcceptance: boolean;
}) {
  const [state, action, pending] = useActionState(say, noError);

  const box = useRef<HTMLTextAreaElement>(null);
  const [draft, setDraft] = useState("");

  // Cleared only once a send has come back without complaint.
  useEffect(() => {
    if (!pending && !state.error) {
      setDraft("");
    }
  }, [pending, state.error]);

  if (!open) {
    return (
      <p className="mt-8 border-t border-line pt-5 text-[14px] leading-relaxed text-muted">
        You cannot send anything more in this conversation.
      </p>
    );
  }

  return (
    <div className="mt-8 border-t border-line pt-5">
      {awaitingAcceptance && (
        <p className="mb-3 max-w-[52ch] text-[13px] leading-relaxed text-muted">
          {name} has not accepted your messages yet. You can send a
          couple more while you wait.
        </p>
      )}

      <form action={action}>
        <input
          type="hidden"
          name="conversation_id"
          value={conversationId}
        />

        <textarea
          ref={box}
          name="body"
          rows={2}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
          placeholder={`Write to ${name}`}
          maxLength={4000}
          className="w-full resize-none rounded-lg border border-line bg-surface px-3.5 py-3 text-[15px] leading-relaxed text-ink outline-none placeholder:text-muted focus:border-pine"
        />

        <div className="mt-2 flex items-center justify-between">
          <span className="text-[12px] text-muted">
            Return to send, shift and return for a new line
          </span>

          <button
            type="submit"
            disabled={pending || !draft.trim()}
            className={loud}
          >
            {pending ? "Sending…" : "Send"}
          </button>
        </div>
      </form>

      <Problem message={state.error} />
    </div>
  );
}

/**
 * What the recipient of a request is offered.
 *
 * Three answers, and the destructive two are not dressed up: the
 * person deciding whether to hear from a stranger is the one
 * person who should not have to hunt for the way out.
 */
export function RequestChoice({
  conversationId,
  workspaceId,
  name,
}: {
  conversationId: string;
  workspaceId: string;
  name: string;
}) {
  const [accepted, accept, accepting] = useActionState(
    letThemIn,
    noError,
  );
  const [declined, decline, declining] = useActionState(
    turnThemAway,
    noError,
  );
  const [blocked, block, blocking] = useActionState(
    blockThem,
    noError,
  );

  const [sure, setSure] = useState(false);

  return (
    <div className="mt-8 border-t border-line pt-5">
      <p className="max-w-[52ch] text-[15px] leading-relaxed text-ink">
        {name} wants to message you.
      </p>

      <p className="mt-1 max-w-[52ch] text-[13px] leading-relaxed text-muted">
        They cannot send more than a few until you answer, and they
        are not told whether you have read this.
      </p>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <form action={accept}>
          <input
            type="hidden"
            name="conversation_id"
            value={conversationId}
          />
          <button
            type="submit"
            disabled={accepting}
            className={loud}
          >
            {accepting ? "Accepting…" : "Accept"}
          </button>
        </form>

        <form action={decline}>
          <input
            type="hidden"
            name="conversation_id"
            value={conversationId}
          />
          <button
            type="submit"
            disabled={declining}
            className={quiet}
          >
            {declining ? "Deleting…" : "Delete"}
          </button>
        </form>

        {sure ? (
          <form
            action={block}
            className="flex flex-wrap items-center gap-2"
          >
            <input
              type="hidden"
              name="workspace_id"
              value={workspaceId}
            />
            <button
              type="submit"
              disabled={blocking}
              className={quiet}
            >
              {blocking ? "Blocking…" : `Yes, block ${name}`}
            </button>

            {/* React submits a plain button inside a form bound
                to a server action, so this stops it explicitly
                rather than quietly blocking somebody. */}
            <button
              type="button"
              onClick={(event) => {
                event.preventDefault();
                event.stopPropagation();
                setSure(false);
              }}
              className="text-[13px] text-muted underline underline-offset-4 hover:text-ink"
            >
              Cancel
            </button>
          </form>
        ) : (
          <button
            type="button"
            onClick={() => setSure(true)}
            className="text-[13px] text-muted underline underline-offset-4 hover:text-ink"
          >
            Block
          </button>
        )}
      </div>

      <Problem
        message={accepted.error ?? declined.error ?? blocked.error}
      />
    </div>
  );
}
