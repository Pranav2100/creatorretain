"use client";

import { useActionState, useState } from "react";

import { saveDetails, setPassword } from "@/app/actions/account";
import { leaveWorkspace } from "@/app/actions/workspace";
import type { Account } from "@/lib/account";
import { noError } from "@/lib/forms";

const field =
  "rounded-lg border border-line bg-surface px-3 py-2.5 text-[15px] text-ink outline-none placeholder:text-muted focus:border-pine";

const input = `w-full ${field}`;

const quiet =
  "rounded-lg border border-line bg-surface px-4 py-2.5 text-[14px] text-ink transition-colors hover:border-pine disabled:opacity-60";

const loud =
  "rounded-lg bg-pine px-5 py-2.5 text-[14px] text-on-pine transition-opacity hover:opacity-90 disabled:opacity-60";

function Said({
  error,
  done,
}: {
  error: string | null;
  done?: string;
}) {
  const message = error ?? done;

  if (!message) return null;

  return (
    <p
      role="status"
      className="mt-3 border-l-2 border-pine pl-3 text-[13px] leading-relaxed text-ink"
    >
      {message}
    </p>
  );
}

export function DetailsForm({ account }: { account: Account }) {
  const [state, action, pending] = useActionState(
    saveDetails,
    noError,
  );

  // The password box only appears once the email has actually
  // been changed. Asking for it up front on a form that mostly
  // gets used to fix a surname reads as though the whole page
  // were dangerous.
  const [email, setEmail] = useState(account.email);
  const moving = email.trim().toLowerCase() !== account.email;

  return (
    <form action={action}>
      <div className="flex flex-wrap gap-4">
        <label className="min-w-[12rem] flex-1 block">
          <span className="mb-1.5 block text-[13px] text-muted">
            First name
          </span>
          <input
            name="first_name"
            defaultValue={account.first_name}
            maxLength={100}
            className={input}
          />
        </label>

        <label className="min-w-[12rem] flex-1 block">
          <span className="mb-1.5 block text-[13px] text-muted">
            Last name
          </span>
          <input
            name="last_name"
            defaultValue={account.last_name}
            maxLength={100}
            className={input}
          />
        </label>
      </div>

      <label className="mt-4 block">
        <span className="mb-1.5 block text-[13px] text-muted">
          Email
        </span>
        <input
          name="email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          maxLength={320}
          className={input}
        />
        <span className="mt-1 block text-[12px] text-muted">
          What you sign in with
        </span>
      </label>

      <label className="mt-4 block">
        <span className="mb-1.5 block text-[13px] text-muted">
          Job title
        </span>
        <input
          name="job_title"
          defaultValue={account.job_title ?? ""}
          maxLength={80}
          placeholder="Talent Manager"
          className={input}
        />
        <span className="mt-1 block text-[12px] text-muted">
          What you do where you work
        </span>
      </label>

      <label className="mt-4 block">
        <span className="mb-1.5 block text-[13px] text-muted">
          Phone
        </span>
        <input
          name="phone"
          defaultValue={account.phone ?? ""}
          maxLength={20}
          placeholder="+91 98765 43210"
          className={input}
        />
      </label>

      {/* Said once, under both, rather than twice. */}
      <p className="mt-2 max-w-[52ch] text-[12px] leading-relaxed text-muted">
        Creators see your name, your title and how to reach you on
        every offer you send them. Both are needed before you can
        join someone else's workspace.
      </p>

      {moving && (
        <label className="mt-5 block border-l-2 border-pine pl-4">
          <span className="mb-1.5 block text-[13px] text-ink">
            Your password
          </span>
          <input
            name="current_password"
            type="password"
            autoComplete="current-password"
            className={`${field} w-full max-w-sm`}
          />
          <span className="mt-1 block text-[12px] text-muted">
            Needed to change the address you sign in with
          </span>
        </label>
      )}

      <div className="mt-5">
        <button type="submit" className={loud} disabled={pending}>
          {pending ? "Saving…" : "Save"}
        </button>
      </div>

      <Said error={state.error} done={state.done} />
    </form>
  );
}

export function PasswordForm() {
  const [state, action, pending] = useActionState(
    setPassword,
    noError,
  );

  return (
    <form action={action} className="max-w-sm">
      <label className="block">
        <span className="mb-1.5 block text-[13px] text-muted">
          Current password
        </span>
        <input
          name="current_password"
          type="password"
          autoComplete="current-password"
          className={input}
        />
      </label>

      <label className="mt-4 block">
        <span className="mb-1.5 block text-[13px] text-muted">
          New password
        </span>
        <input
          name="new_password"
          type="password"
          autoComplete="new-password"
          className={input}
        />
        <span className="mt-1 block text-[12px] text-muted">
          At least 8 characters, with a letter and a number
        </span>
      </label>

      <label className="mt-4 block">
        <span className="mb-1.5 block text-[13px] text-muted">
          New password again
        </span>
        <input
          name="confirm_password"
          type="password"
          autoComplete="new-password"
          className={input}
        />
      </label>

      <div className="mt-5">
        <button type="submit" className={loud} disabled={pending}>
          {pending ? "Changing…" : "Change password"}
        </button>
      </div>

      <Said error={state.error} done={state.done} />
    </form>
  );
}

export function LeaveForm({ name }: { name: string }) {
  const [state, action, pending] = useActionState(
    leaveWorkspace,
    noError,
  );

  // Asked for out loud before it happens. Leaving is not
  // reversible from this side - getting back in needs an
  // invitation from someone still inside.
  const [sure, setSure] = useState(false);

  if (!sure) {
    return (
      <>
        <button
          type="button"
          onClick={() => setSure(true)}
          className={quiet}
        >
          Leave {name}
        </button>
        <Said error={state.error} done={state.done} />
      </>
    );
  }

  return (
    <form action={action}>
      <p className="mb-3 max-w-[52ch] text-[14px] leading-relaxed text-ink">
        You will lose access to {name} and everything in it. Getting
        back in needs a new invitation from someone still there.
      </p>

      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" className={loud} disabled={pending}>
          {pending ? "Leaving…" : `Yes, leave ${name}`}
        </button>

        <button
          type="button"
          onClick={() => setSure(false)}
          className="text-[13px] text-muted underline underline-offset-4 hover:text-ink"
        >
          Cancel
        </button>
      </div>

      <Said error={state.error} done={state.done} />
    </form>
  );
}
