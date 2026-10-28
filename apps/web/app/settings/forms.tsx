"use client";

import { useActionState, useEffect, useState } from "react";

import {
  clearLogo,
  dropMember,
  invite,
  sendAgain,
  setLogo,
  setRole,
  updateWorkspace,
  withdrawInvitation,
} from "@/app/actions/workspace";
import { noError } from "@/lib/forms";
import type { Member, SentInvitation } from "@/lib/team";
import {
  RANK,
  ROLE_LABEL,
  type WorkspaceRole,
  type WorkspaceSummary,
} from "@/lib/workspace";

const field =
  "rounded-lg border border-line bg-surface px-3 py-2.5 text-[15px] text-ink outline-none placeholder:text-muted focus:border-pine";

const input = `w-full ${field}`;

const quiet =
  "rounded-lg border border-line bg-surface px-4 py-2.5 text-[14px] text-ink transition-colors hover:border-pine disabled:opacity-60";

const loud =
  "rounded-lg bg-pine px-5 py-2.5 text-[14px] text-on-pine transition-opacity hover:opacity-90 disabled:opacity-60";

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

export function WorkspaceForm({
  workspace,
}: {
  workspace: WorkspaceSummary;
}) {
  const [state, action, pending] = useActionState(
    updateWorkspace,
    noError,
  );

  return (
    <form action={action}>
      <label className="block">
        <span className="mb-1.5 block text-[13px] text-muted">
          Name
        </span>
        <input
          name="display_name"
          defaultValue={workspace.display_name}
          maxLength={100}
          placeholder="TalentX Media"
          className={input}
        />
        <span className="mt-1 block text-[12px] text-muted">
          What creators see on an offer
        </span>
      </label>

      <label className="mt-4 block">
        <span className="mb-1.5 block text-[13px] text-muted">
          Registered name
        </span>
        <input
          name="legal_name"
          defaultValue={workspace.legal_name ?? ""}
          maxLength={200}
          placeholder="TalentX Media Private Limited"
          className={input}
        />
        <span className="mt-1 block text-[12px] text-muted">
          Optional. The name on your paperwork, if it differs
        </span>
      </label>

      <label className="mt-4 block">
        <span className="mb-1.5 block text-[13px] text-muted">
          About
        </span>
        {/* An example rather than an instruction. "Say who you
            work with" tells someone what to do and leaves them
            staring at an empty box; a paragraph they can write
            over shows them the length and the tone expected. */}
        <textarea
          name="bio"
          rows={4}
          maxLength={500}
          defaultValue={workspace.bio ?? ""}
          placeholder={
            "We are a Pune agency putting food and fitness brands " +
            "on monthly retainers with regional creators. Six years " +
            "in, around twenty creators on the books at any time. " +
            "We pay on the first of the month and we review work " +
            "within two days."
          }
          className={`${input} resize-y leading-relaxed`}
        />
      </label>

      <label className="mt-4 block">
        <span className="mb-1.5 block text-[13px] text-muted">
          Website
        </span>
        <input
          name="website_url"
          type="url"
          defaultValue={workspace.website_url ?? ""}
          placeholder="https://talentx.in"
          className={input}
        />
      </label>

      <Error message={state.error} />

      <button type="submit" disabled={pending} className={`${loud} mt-5`}>
        {pending ? "Saving" : "Save"}
      </button>
    </form>
  );
}

const MAX_LOGO_BYTES = 2 * 1024 * 1024;
const ACCEPTED = ["image/png", "image/jpeg", "image/webp", "image/gif"];

/**
 * The logo, picked from the person's own files.
 *
 * Its own form rather than a field on the one above, because an
 * upload is a single action that either worked or did not - it
 * should not sit unsaved next to a bio waiting for someone to
 * press Save, and it should not be undone by a later save of a
 * different field.
 *
 * The picked file is previewed from the browser's own copy before
 * it is sent, so choosing the wrong picture is obvious without a
 * round trip.
 */
export function LogoForm({ current }: { current: string | null }) {
  const [state, action, pending] = useActionState(setLogo, noError);

  const [preview, setPreview] = useState<string | null>(null);
  const [chosen, setChosen] = useState<string | null>(null);
  const [refused, setRefused] = useState<string | null>(null);

  /**
   * A new logo arriving from the server means the upload landed,
   * so the local preview has done its job and the Upload button
   * has nothing left to upload.
   *
   * Watching `current` rather than the action's result because
   * the result cannot tell success from "not submitted yet" -
   * both are simply "no error". The server changing its mind
   * about what the logo is can.
   */
  useEffect(() => {
    setPreview(null);
    setChosen(null);
    setRefused(null);
  }, [current]);

  // An object URL is held until it is let go of, so release the
  // old one whenever it is replaced or the form goes away.
  useEffect(() => {
    if (!preview) return;

    return () => URL.revokeObjectURL(preview);
  }, [preview]);

  const shown = preview ?? current;

  function choose(file: File | undefined) {
    setRefused(null);

    if (!file) return;

    // Checked again on the server from the actual bytes. This is
    // only so an obvious mistake is caught before the upload.
    if (!ACCEPTED.includes(file.type)) {
      setRefused(
        file.type === "image/svg+xml"
          ? "SVG files are not accepted. Use a PNG, JPEG or WebP."
          : "Choose a PNG, JPEG, WebP or GIF.",
      );
      return;
    }

    if (file.size > MAX_LOGO_BYTES) {
      setRefused("That image is over 2MB. Try a smaller one.");
      return;
    }

    setChosen(file.name);
    setPreview(URL.createObjectURL(file));
  }

  return (
    <div className="mt-8 border-t border-line pt-6">
      <p className="text-[13px] text-muted">Logo</p>

      <div className="mt-3 flex flex-wrap items-center gap-5">
        {shown ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={shown}
            alt=""
            className="h-16 w-16 shrink-0 rounded-lg border border-line object-cover"
          />
        ) : (
          <div
            aria-hidden="true"
            className="flex h-16 w-16 shrink-0 items-center justify-center rounded-lg border border-dashed border-line text-[11px] text-muted"
          >
            None
          </div>
        )}

        <form action={action} className="flex flex-wrap items-center gap-3">
          <label className={`${quiet} cursor-pointer`}>
            {current || preview ? "Choose another" : "Choose an image"}
            <input
              type="file"
              name="file"
              accept={ACCEPTED.join(",")}
              onChange={(event) => choose(event.target.files?.[0])}
              className="sr-only"
            />
          </label>

          {preview && (
            <>
              <span className="max-w-[16rem] truncate text-[13px] text-muted">
                {chosen}
              </span>
              <button
                type="submit"
                disabled={pending}
                className={loud}
              >
                {pending ? "Uploading" : "Upload"}
              </button>
            </>
          )}
        </form>

        {current && !preview && <RemoveLogo />}
      </div>

      <p className="mt-3 max-w-[58ch] text-[12px] leading-relaxed text-muted">
        PNG, JPEG, WebP or GIF, up to 2MB. Square works best.
      </p>

      {refused && (
        <p
          role="alert"
          className="mt-3 border-l-2 border-pine pl-3 text-[13px] leading-relaxed text-ink"
        >
          {refused}
        </p>
      )}

      <Error message={state.error} />
    </div>
  );
}

function RemoveLogo() {
  const [state, action, pending] = useActionState(
    clearLogo,
    noError,
  );

  return (
    <form action={action}>
      <button
        type="submit"
        disabled={pending}
        className="text-[13px] text-muted underline underline-offset-4 hover:text-ink disabled:opacity-60"
      >
        {pending ? "Removing" : "Remove"}
      </button>

      {state.error && (
        <span className="ml-2 text-[13px] text-ink">
          {state.error}
        </span>
      )}
    </form>
  );
}

export function InviteForm() {
  const [state, action, pending] = useActionState(invite, noError);

  return (
    <form action={action} className="mt-4">
      <div className="flex flex-wrap items-end gap-3">
        <label className="block min-w-[14rem] flex-1">
          <span className="mb-1.5 block text-[13px] text-muted">
            Email
          </span>
          <input
            name="email"
            type="email"
            placeholder="someone@youragency.com"
            className={input}
          />
        </label>

        <label className="block w-40">
          <span className="mb-1.5 block text-[13px] text-muted">
            As
          </span>
          <select name="role" defaultValue="manager" className={input}>
            <option value="member">Member</option>
            <option value="manager">Manager</option>
            <option value="admin">Admin</option>
          </select>
        </label>

        <button type="submit" disabled={pending} className={quiet}>
          {pending ? "Sending" : "Send invite"}
        </button>
      </div>

      {/* Three sentences for three roles, in the order someone
          reads them when deciding which to pick. */}
      <dl className="mt-3 max-w-[60ch] space-y-1.5 text-[13px] leading-relaxed">
        <div>
          <dt className="inline text-ink">Admin.</dt>{" "}
          <dd className="inline text-muted">
            Everything you can do, except handing the workspace on
            and paying for it.
          </dd>
        </div>
        <div>
          <dt className="inline text-ink">Manager.</dt>{" "}
          <dd className="inline text-muted">
            Runs the accounts you put them on — offers, pauses,
            reviewing work — and sees only those. Cannot invite,
            remove, or edit this page.
          </dd>
        </div>
        <div>
          <dt className="inline text-ink">Member.</dt>{" "}
          <dd className="inline text-muted">
            Sees every retainer and what is due, and changes
            nothing.
          </dd>
        </div>
      </dl>

      <Error message={state.error} />
    </form>
  );
}

export function MemberRow({
  member,
  viewerRole,
  isYou,
}: {
  member: Member;
  viewerRole: string;
  isYou: boolean;
}) {
  const [roleState, roleAction, changing] = useActionState(
    setRole,
    noError,
  );
  const [dropState, dropAction, dropping] = useActionState(
    dropMember,
    noError,
  );

  // You can act on people below you, and nobody else. The owner
  // is nobody's junior, and nobody edits themselves here. Written
  // as one comparison rather than a list of pairs, so a fourth
  // role did not mean a fourth branch.
  const owner = member.role === "owner";
  const mayAct =
    !owner &&
    !isYou &&
    RANK[viewerRole as WorkspaceRole] > RANK[member.role];

  return (
    <li className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2 border-b border-line py-3">
      <span className="min-w-0 text-[15px] text-ink">
        {member.first_name} {member.last_name}
        {isYou && (
          <span className="ml-2 text-[13px] text-muted">you</span>
        )}
        <span className="ml-2 block text-[13px] text-muted sm:ml-2 sm:inline">
          {member.email}
        </span>
      </span>

      <span className="flex items-center gap-4">
        {mayAct ? (
          <form action={roleAction} className="flex items-center">
            <input
              type="hidden"
              name="member_id"
              value={member.id}
            />
            <select
              name="role"
              defaultValue={member.role}
              disabled={changing}
              onChange={(event) =>
                event.currentTarget.form?.requestSubmit()
              }
              className="rounded-lg border border-line bg-surface px-2.5 py-1.5 text-[13px] text-ink outline-none focus:border-pine disabled:opacity-60"
            >
              <option value="member">Member</option>
              <option value="manager">Manager</option>
              <option value="admin">Admin</option>
            </select>
          </form>
        ) : (
          <span className="text-[13px] text-muted">
            {ROLE_LABEL[member.role]}
          </span>
        )}

        {mayAct && (
          <form action={dropAction}>
            <input
              type="hidden"
              name="member_id"
              value={member.id}
            />
            <button
              type="submit"
              disabled={dropping}
              className="text-[13px] text-muted underline underline-offset-4 hover:text-ink disabled:opacity-60"
            >
              {dropping ? "Removing" : "Remove"}
            </button>
          </form>
        )}
      </span>

      {(roleState.error || dropState.error) && (
        <span className="w-full text-[13px] text-ink">
          {roleState.error ?? dropState.error}
        </span>
      )}
    </li>
  );
}

export function InvitationRow({
  invitation,
}: {
  invitation: SentInvitation;
}) {
  const [cancelState, cancelAction, cancelling] = useActionState(
    withdrawInvitation,
    noError,
  );
  const [resendState, resendAction, resending] = useActionState(
    sendAgain,
    noError,
  );

  return (
    <li className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2 border-b border-line py-3">
      <span className="min-w-0 text-[15px] text-ink">
        {invitation.email}
        <span className="ml-2 text-[13px] text-muted">
          {ROLE_LABEL[invitation.role]}
        </span>
      </span>

      <span className="flex items-center gap-4">
        <form action={resendAction}>
          <input
            type="hidden"
            name="invitation_id"
            value={invitation.id}
          />
          <button
            type="submit"
            disabled={resending}
            className="text-[13px] text-muted underline underline-offset-4 hover:text-ink disabled:opacity-60"
          >
            {resending ? "Sending" : "Send again"}
          </button>
        </form>

        <form action={cancelAction}>
          <input
            type="hidden"
            name="invitation_id"
            value={invitation.id}
          />
          <button
            type="submit"
            disabled={cancelling}
            className="text-[13px] text-muted underline underline-offset-4 hover:text-ink disabled:opacity-60"
          >
            {cancelling ? "Cancelling" : "Cancel"}
          </button>
        </form>
      </span>

      {(cancelState.error || resendState.error) && (
        <span className="w-full text-[13px] text-ink">
          {cancelState.error ?? resendState.error}
        </span>
      )}
    </li>
  );
}
