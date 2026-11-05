"use client";

import { useActionState, useEffect, useRef } from "react";

import {
  addRole,
  dropRole,
  editRole,
  giveRole,
  moveRole,
  takeRole,
} from "@/app/actions/roles";
import { noError } from "@/lib/forms";
import type { CustomRole, PermissionInfo } from "@/lib/roles";

/**
 * The permission checkboxes.
 *
 * A permission the person does not hold is shown but cannot be
 * ticked, with the reason beside it. Hiding it would be tidier
 * and worse: two people would see two different lists and
 * neither would know why, and the first thing anybody asks when
 * a setting is missing is whether it exists at all.
 */
function Choices({
  permissions,
  already,
  disabled,
}: {
  permissions: PermissionInfo[];
  already: string[];
  disabled?: boolean;
}) {
  return (
    <ul className="mt-4 space-y-2.5">
      {permissions.map((permission) => {
        const locked = !permission.held || disabled;

        return (
          <li key={permission.value}>
            <label
              className={
                locked
                  ? "flex cursor-not-allowed items-start gap-2.5"
                  : "flex cursor-pointer items-start gap-2.5"
              }
            >
              <input
                type="checkbox"
                name="permissions"
                value={permission.value}
                defaultChecked={already.includes(permission.value)}
                disabled={locked}
                className="mt-1 accent-pine disabled:opacity-40"
              />
              <span className="min-w-0">
                <span
                  className={
                    permission.held
                      ? "text-[14px] text-ink"
                      : "text-[14px] text-muted"
                  }
                >
                  {permission.label}
                </span>
                <span className="block text-[13px] leading-snug text-muted">
                  {permission.description}
                  {!permission.held && (
                    <span className="text-muted">
                      {" "}
                      — you do not have this yourself, so you cannot
                      put it in a role.
                    </span>
                  )}
                </span>
              </span>
            </label>
          </li>
        );
      })}
    </ul>
  );
}

export function NewRoleForm({
  permissions,
}: {
  permissions: PermissionInfo[];
}) {
  const [state, action, saving] = useActionState(addRole, noError);

  const box = useRef<HTMLDetailsElement>(null);
  const fields = useRef<HTMLFormElement>(null);

  // Put the form away once it has worked.
  //
  // Leaving it open with the name still in it reads as though
  // nothing happened - the new role appears in the list above,
  // but that is easy to miss when the form you are looking at
  // has not moved. Depends on the whole state object rather than
  // state.done, because a second success carrying the same
  // message is still a new object and still has to close the
  // form.
  //
  // Writing to the DOM rather than holding `open` in state: this
  // is synchronising an external thing with a result, which is
  // what effects are for, and setState here would be a cascading
  // render the lint rules rightly refuse.
  useEffect(() => {
    if (!state.done) return;

    fields.current?.reset();

    if (box.current) {
      box.current.open = false;
    }
  }, [state]);

  return (
    <>
      {/* Outside the details, so it survives the form closing -
          a confirmation inside something that has just collapsed
          is no confirmation at all. */}
      {state.done && (
        <p
          aria-live="polite"
          className="mt-4 text-[14px] text-pine"
        >
          {state.done}
        </p>
      )}

      <details
        ref={box}
        id="new-role"
        className="mt-3 rounded-[14px] border border-line bg-surface p-5"
      >
        <summary className="cursor-pointer text-[15px] text-ink">
          New role
        </summary>

        <form ref={fields} action={action} className="mt-4">
        <label
          htmlFor="new-role-name"
          className="block text-[13px] text-muted"
        >
          Name
        </label>
        <input
          id="new-role-name"
          name="name"
          maxLength={40}
          placeholder="Account Lead"
          className="mt-1.5 w-full rounded-lg border border-line bg-surface px-3 py-2.5 text-[15px] text-ink outline-none placeholder:text-muted focus:border-pine"
        />

        <Choices permissions={permissions} already={[]} />

        <button
          type="submit"
          disabled={saving}
          className="mt-5 rounded-lg bg-pine px-4 py-2.5 text-[14px] font-medium text-on-pine transition-colors hover:bg-pine-hover disabled:opacity-60"
        >
          {saving ? "Creating" : "Create role"}
        </button>

          {state.error && (
            <p className="mt-3 text-[13px] text-alarm">
              {state.error}
            </p>
          )}
        </form>
      </details>
    </>
  );
}

export function RoleRow({
  role,
  permissions,
  upward,
  downward,
}: {
  role: CustomRole;
  permissions: PermissionInfo[];
  /** The whole list reordered, with this role one place earlier. */
  upward: string[] | null;
  downward: string[] | null;
}) {
  const [editState, edit, saving] = useActionState(
    editRole,
    noError,
  );
  const [dropState, drop, dropping] = useActionState(
    dropRole,
    noError,
  );
  const [, move, moving] = useActionState(moveRole, noError);

  const panel = useRef<HTMLDetailsElement>(null);

  // Same reason as the new-role form: saving should visibly
  // finish. The edited name is already on the summary line, so
  // closing the panel puts it where it can be read.
  useEffect(() => {
    if (!editState.done) return;

    if (panel.current) {
      panel.current.open = false;
    }
  }, [editState]);

  const named = permissions.filter((p) =>
    role.permissions.includes(p.value),
  );

  return (
    <li className="border-b border-line first:border-t">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2 py-3.5">
        <details ref={panel} className="min-w-0 flex-1">
          <summary className="cursor-pointer text-[15px] text-ink">
            {role.name}
            <span className="ml-2 text-[13px] text-muted">
              {role.member_count === 1
                ? "1 person"
                : `${role.member_count} people`}
            </span>
          </summary>

          <p className="mt-1.5 text-[13px] leading-relaxed text-muted">
            {named.map((p) => p.label).join(" · ")}
          </p>

          {role.editable ? (
            <>
              <form action={edit} className="mt-4">
                <input
                  type="hidden"
                  name="role_id"
                  value={role.id}
                />
                <label className="block text-[13px] text-muted">
                  Name
                </label>
                <input
                  name="name"
                  defaultValue={role.name}
                  maxLength={40}
                  className="mt-1.5 w-full rounded-lg border border-line bg-surface px-3 py-2.5 text-[15px] text-ink outline-none focus:border-pine"
                />

                <Choices
                  permissions={permissions}
                  already={role.permissions}
                />

                <button
                  type="submit"
                  disabled={saving}
                  className="mt-5 rounded-lg bg-pine px-4 py-2 text-[14px] font-medium text-on-pine transition-colors hover:bg-pine-hover disabled:opacity-60"
                >
                  {saving ? "Saving" : "Save"}
                </button>

                {editState.error && (
                  <p className="mt-3 text-[13px] text-alarm">
                    {editState.error}
                  </p>
                )}
              </form>

              {/* A sibling of the edit form, not inside it -
                  nesting forms is invalid, and in React 19 a
                  button inside a form submits it whatever its
                  type says. */}
              <form action={drop} className="mt-4">
                <input
                  type="hidden"
                  name="role_id"
                  value={role.id}
                />
                <button
                  type="submit"
                  disabled={dropping}
                  className="text-[13px] text-muted underline underline-offset-4 hover:text-ink disabled:opacity-60"
                >
                  {dropping
                    ? "Deleting"
                    : role.member_count > 0
                      ? `Delete, and take it off ${role.member_count === 1 ? "1 person" : `${role.member_count} people`}`
                      : "Delete this role"}
                </button>

                {dropState.error && (
                  <p className="mt-2 text-[13px] text-alarm">
                    {dropState.error}
                  </p>
                )}
              </form>
            </>
          ) : (
            <p className="mt-3 text-[13px] leading-relaxed text-muted">
              This role can do things you cannot, so it is not
              yours to change.
            </p>
          )}
        </details>

        {editState.done && (
          <span
            aria-live="polite"
            className="w-full text-[13px] text-pine"
          >
            {editState.done}
          </span>
        )}

        {/* Ordering is presentation only - moving a role changes
            where it appears and nothing about what it can do. */}
        <span className="flex shrink-0 items-center gap-2">
          <form action={move}>
            {(upward ?? []).map((id) => (
              <input
                key={id}
                type="hidden"
                name="role_ids"
                value={id}
              />
            ))}
            <button
              type="submit"
              disabled={!upward || moving}
              aria-label={`Move ${role.name} up`}
              className="px-1 text-[13px] text-muted hover:text-ink disabled:opacity-30"
            >
              ↑
            </button>
          </form>

          <form action={move}>
            {(downward ?? []).map((id) => (
              <input
                key={id}
                type="hidden"
                name="role_ids"
                value={id}
              />
            ))}
            <button
              type="submit"
              disabled={!downward || moving}
              aria-label={`Move ${role.name} down`}
              className="px-1 text-[13px] text-muted hover:text-ink disabled:opacity-30"
            >
              ↓
            </button>
          </form>
        </span>
      </div>
    </li>
  );
}

/**
 * The roles one person holds, on their row in the Team list.
 *
 * Only shown for people the viewer outranks - the same rule the
 * server applies, so the interface does not offer something that
 * was always going to be refused.
 */
export function MemberRoles({
  userId,
  held,
  offerable,
}: {
  userId: string;
  held: CustomRole[];
  offerable: CustomRole[];
}) {
  const [giveState, give, giving] = useActionState(
    giveRole,
    noError,
  );
  const [takeState, take, taking] = useActionState(
    takeRole,
    noError,
  );

  const spare = offerable.filter(
    (role) => !held.some((h) => h.id === role.id),
  );

  if (held.length === 0 && spare.length === 0) {
    return null;
  }

  return (
    <span className="flex w-full flex-wrap items-center gap-2">
      {held.map((role) => (
        <form key={role.id} action={take}>
          <input type="hidden" name="user_id" value={userId} />
          <input type="hidden" name="role_id" value={role.id} />
          <button
            type="submit"
            disabled={taking}
            title={`Take ${role.name} back`}
            className="rounded-full border border-pine px-2.5 py-0.5 text-[12px] text-pine hover:bg-surface disabled:opacity-60"
          >
            {role.name} ×
          </button>
        </form>
      ))}

      {spare.length > 0 && (
        <form action={give} className="flex items-center">
          <input type="hidden" name="user_id" value={userId} />
          <select
            name="role_id"
            defaultValue=""
            disabled={giving}
            onChange={(event) =>
              event.currentTarget.form?.requestSubmit()
            }
            className="rounded-lg border border-line bg-surface px-2 py-1 text-[12px] text-muted outline-none focus:border-pine disabled:opacity-60"
          >
            <option value="" disabled>
              Add a role
            </option>
            {spare.map((role) => (
              <option key={role.id} value={role.id}>
                {role.name}
              </option>
            ))}
          </select>
        </form>
      )}

      {(giveState.error || takeState.error) && (
        <span className="w-full text-[13px] text-alarm">
          {giveState.error ?? takeState.error}
        </span>
      )}
    </span>
  );
}
