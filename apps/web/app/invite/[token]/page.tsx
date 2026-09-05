import { notFound } from "next/navigation";

import { getInvitation } from "@/lib/api";

import { AcceptPanel } from "./accept-panel";
import { ClosedPanel } from "./closed-panel";

function initials(name: string | null) {
  if (!name) return "?";

  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? "")
    .join("");
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default async function InvitePage(
  props: PageProps<"/invite/[token]">,
) {
  const { token } = await props.params;
  const invitation = await getInvitation(token);

  if (!invitation) {
    notFound();
  }

  const workspace = invitation.workspace_name ?? "a workspace";
  const inviter = invitation.invited_by_name ?? "Someone";
  const open = invitation.status === "pending" && !invitation.is_expired;

  return (
    <main className="flex flex-1 items-center justify-center bg-paper px-5 py-16">
      <div className="w-full max-w-[26rem]">
        <div className="rounded-t-[14px] border border-b-0 border-line bg-white px-7 pt-7 pb-8">
          <div className="mb-9 flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-pine text-[11px] font-medium tracking-wide text-white">
              {initials(invitation.workspace_name)}
            </span>
            <span className="text-sm text-muted">{workspace}</span>
          </div>

          <p className="text-[15px] leading-relaxed text-muted">
            {inviter} invited you to join
          </p>
          <h1 className="font-display text-[2.6rem] leading-[1.1] tracking-tight text-ink">
            {workspace}
          </h1>
          <p className="mt-3 text-[15px] text-muted">
            as {invitation.role === "admin" ? "an" : "a"}{" "}
            <span className="text-ink">{invitation.role}</span>
          </p>
        </div>

        <div className="notch" aria-hidden="true">
          <span />
        </div>

        <div className="rounded-b-[14px] border border-t-0 border-line bg-white px-7 pt-7 pb-8">
          {open ? (
            <AcceptPanel
              token={token}
              email={invitation.email}
              workspace={workspace}
              requiresSignup={invitation.requires_signup}
            />
          ) : (
            <ClosedPanel
              status={invitation.is_expired ? "expired" : invitation.status}
              workspace={workspace}
              inviter={inviter}
            />
          )}
        </div>

        {open && (
          <p className="mt-5 text-center text-[13px] text-muted">
            This invitation is open until {formatDate(invitation.expires_at)}.
          </p>
        )}
      </div>
    </main>
  );
}
