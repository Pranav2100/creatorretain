"use client";

import { useActionState, useState } from "react";

import { say } from "@/app/actions/messages";
import { noError } from "@/lib/forms";

/**
 * The first thing you say to somebody.
 *
 * A deliberately larger box than the one in a thread. This is
 * the message that decides whether a stranger accepts you, and a
 * single-line field invites a single line - which is exactly the
 * message that gets deleted unread.
 */
export function FirstMessage({
  to,
  name,
}: {
  to: string;
  name: string;
}) {
  const [state, action, pending] = useActionState(say, noError);
  const [draft, setDraft] = useState("");

  return (
    <form action={action} className="mt-7">
      <input type="hidden" name="to_workspace_id" value={to} />

      <textarea
        name="body"
        rows={6}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        maxLength={4000}
        placeholder={`Hello — we work with food creators in Pune and liked your last three reels. We are putting together a monthly retainer and wondered whether you would be interested.`}
        className="w-full resize-none rounded-lg border border-line bg-surface px-4 py-3.5 text-[15px] leading-relaxed text-ink outline-none placeholder:text-muted focus:border-pine"
      />

      <div className="mt-4 flex flex-wrap items-center gap-4">
        <button
          type="submit"
          disabled={pending || !draft.trim()}
          className="rounded-lg bg-pine px-5 py-2.5 text-[14px] text-on-pine transition-opacity hover:opacity-90 disabled:opacity-60"
        >
          {pending ? "Sending…" : `Send to ${name}`}
        </button>

        <span className="text-[12px] tabular-nums text-muted">
          {draft.length} of 4000
        </span>
      </div>

      {state.error && (
        <p
          role="alert"
          className="mt-4 border-l-2 border-pine pl-3 text-[13px] leading-relaxed text-ink"
        >
          {state.error}
        </p>
      )}
    </form>
  );
}
