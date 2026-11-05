"use client";

import { useActionState, useState } from "react";

import {
  saveDetails,
  setNotify,
  setPassword,
} from "@/app/actions/account";
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
        join someone else&rsquo;s workspace.
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

/**
 * What we email you about.
 *
 * Each switch saves as it is flipped rather than waiting for a
 * Save button. Three checkboxes above a button is an invitation
 * to tick one, leave, and wonder next week why the emails kept
 * coming.
 *
 * There is no switch for security mail. That is deliberate and
 * the page says so, because an unexplained omission reads as an
 * oversight.
 */
function NotifySwitch({
  field,
  label,
  note,
  on,
}: {
  field: string;
  label: string;
  note: string;
  on: boolean;
}) {
  const [state, action, saving] = useActionState(
    setNotify,
    noError,
  );

  return (
    <li className="border-b border-line py-3.5 first:border-t">
      <form action={action}>
        <input type="hidden" name="field" value={field} />
        {/* An unticked checkbox sends nothing at all, so the
            state it is moving to travels beside it - written
            from the box itself as it is clicked rather than
            precomputed, so it is right however fast somebody
            clicks. */}
        <input
          type="hidden"
          name="on"
          defaultValue={on ? "false" : "true"}
        />

        <label className="flex cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            // defaultChecked, not checked. Controlled by the
            // server value, React resets the box to that value
            // the moment it is clicked and only moves it back
            // once the save has round-tripped - so every click
            // visibly snaps back first. Uncontrolled, the box
            // stays where it was put and the server value
            // catches up behind it.
            defaultChecked={on}
            disabled={saving}
            onChange={(event) => {
              const form = event.currentTarget.form;

              if (!form) return;

              const flag = form.elements.namedItem(
                "on",
              ) as HTMLInputElement | null;

              if (flag) {
                flag.value = event.currentTarget.checked
                  ? "true"
                  : "false";
              }

              form.requestSubmit();
            }}
            className="mt-1 accent-pine disabled:opacity-40"
          />
          <span className="min-w-0">
            <span className="text-[15px] text-ink">{label}</span>
            <span className="block text-[13px] leading-snug text-muted">
              {note}
            </span>
          </span>
        </label>

        {state.error && (
          <p className="mt-2 text-[13px] text-alarm">{state.error}</p>
        )}
      </form>
    </li>
  );
}

export function NotifyForm({ account }: { account: Account }) {
  return (
    <>
      <ul>
        <NotifySwitch
          field="notify_retainers"
          label="Retainers"
          note="An offer arrives, somebody accepts or declines, a pause or an ending needs you."
          on={account.notify_retainers}
        />
        <NotifySwitch
          field="notify_work"
          label="Work"
          note="Something is submitted, approved, or sent back for changes."
          on={account.notify_work}
        />
        <NotifySwitch
          field="notify_messages"
          label="Messages"
          note="A nudge when you have not read a conversation. Never one email per message."
          on={account.notify_messages}
        />
      </ul>

      <p className="mt-5 max-w-[58ch] text-[13px] leading-relaxed text-muted">
        We will always email you about your account itself — a
        password change, or sessions being signed out. That one
        has no switch on purpose: if it was not you who changed
        it, the email is the only warning you get.
      </p>
    </>
  );
}
