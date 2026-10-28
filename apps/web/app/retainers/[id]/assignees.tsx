"use client";

import { useActionState, useState } from "react";

import {
  putOnAccount,
  takeOffAccount,
} from "@/app/actions/retainers";
import { noError } from "@/lib/forms";
import type { Assignee } from "@/lib/retainers";
import type { Member } from "@/lib/team";

/**
 * Who runs this account, and - for whoever is allowed to decide -
 * the means to change it.
 *
 * Shown on the hiring side only. Which of the agency's people
 * handles a creator is an internal arrangement; the creator has
 * a named contact for the things that concern them, and does not
 * need the staffing chart behind it.
 *
 * This is not a cosmetic list. Putting somebody on an account is
 * what lets a Manager see it at all, so the wording says that
 * out loud rather than leaving the consequence to be discovered.
 */

const quiet =
  "rounded-lg border border-line bg-surface px-3 py-2 text-[13px] text-ink transition-colors hover:border-pine disabled:opacity-60";

const field =
  "rounded-lg border border-line bg-surface px-3 py-2 text-[14px] text-ink outline-none focus:border-pine";

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

function Remove({
  retainerId,
  person,
}: {
  retainerId: string;
  person: Assignee;
}) {
  const [state, action, pending] = useActionState(
    takeOffAccount,
    noError,
  );

  return (
    <form action={action} className="shrink-0">
      <input type="hidden" name="retainer_id" value={retainerId} />
      <input type="hidden" name="user_id" value={person.user_id} />

      <button
        type="submit"
        disabled={pending}
        className="text-[13px] text-muted underline underline-offset-4 hover:text-ink disabled:opacity-60"
      >
        {pending ? "Removing…" : "Remove"}
      </button>

      <Problem message={state.error} />
    </form>
  );
}

export function Assignees({
  retainerId,
  people,
  team,
  mayAssign,
}: {
  retainerId: string;
  people: Assignee[];
  /** Everyone in the workspace, for the picker. Empty when the
      reader is not allowed to see the team. */
  team: Member[];
  mayAssign: boolean;
}) {
  const [state, action, pending] = useActionState(
    putOnAccount,
    noError,
  );

  const [adding, setAdding] = useState(false);

  const on = new Set(people.map((p) => p.user_id));
  const spare = team.filter(
    (m) => !on.has(m.user_id) && m.status === "active",
  );

  return (
    <section className="mt-8 max-w-[62ch]">
      <h2 className="text-[13px] text-muted">Who runs this</h2>

      {people.length === 0 ? (
        <p className="mt-1.5 text-[15px] leading-relaxed text-muted">
          Nobody yet. A manager can only see the accounts they are
          put on.
        </p>
      ) : (
        <ul className="mt-1.5">
          {people.map((person) => (
            <li
              key={person.user_id}
              className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-line py-2.5 first:border-t"
            >
              <span className="min-w-0 text-[15px] text-ink">
                {person.name}
                {person.job_title && (
                  <span className="text-muted">
                    , {person.job_title}
                  </span>
                )}
              </span>

              {mayAssign && (
                <Remove
                  retainerId={retainerId}
                  person={person}
                />
              )}
            </li>
          ))}
        </ul>
      )}

      {mayAssign && spare.length > 0 && (
        <div className="mt-3">
          {adding ? (
            <form
              action={action}
              className="flex flex-wrap items-center gap-2"
            >
              <input
                type="hidden"
                name="retainer_id"
                value={retainerId}
              />

              <select
                name="user_id"
                defaultValue=""
                className={field}
              >
                <option value="" disabled>
                  Pick someone
                </option>
                {spare.map((member) => (
                  <option
                    key={member.user_id}
                    value={member.user_id}
                  >
                    {member.first_name} {member.last_name}
                  </option>
                ))}
              </select>

              <button
                type="submit"
                disabled={pending}
                className={quiet}
              >
                {pending ? "Adding…" : "Put them on it"}
              </button>

              {/* Outside no form of its own, but inside this one:
                  React submits a plain button inside a form bound
                  to a server action, so this cancels explicitly
                  rather than quietly assigning somebody. */}
              <button
                type="button"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  setAdding(false);
                }}
                className="text-[13px] text-muted underline underline-offset-4 hover:text-ink"
              >
                Cancel
              </button>
            </form>
          ) : (
            <button
              type="button"
              onClick={() => setAdding(true)}
              className={quiet}
            >
              Put someone on this
            </button>
          )}

          <Problem message={state.error} />
        </div>
      )}
    </section>
  );
}
