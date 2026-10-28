import Link from "next/link";

import { Header } from "@/components/header";
import { Live } from "@/components/live";
import { API_URL } from "@/lib/api";
import { getPulse } from "@/lib/pulse";
import { listMembers, listSentInvitations } from "@/lib/team";
import { requireWorkspace } from "@/lib/session";
import { canEdit } from "@/lib/workspace";

import {
  InvitationRow,
  InviteForm,
  LogoForm,
  MemberRow,
  WorkspaceForm,
} from "./forms";

export const metadata = { title: "Settings · CreatorRetain" };

const PLAN_LABEL: Record<string, string> = {
  free: "Free",
  pro: "Pro",
  business: "Business",
  managed: "Managed",
  verified: "Verified",
};

async function whoAmI(token: string): Promise<string | null> {
  const response = await fetch(`${API_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!response.ok) return null;

  return (await response.json()).id;
}

export default async function SettingsPage() {
  const { token, workspace, plan } =
    await requireWorkspace("/settings");

  const editable = canEdit(workspace.your_role);

  const [members, invitations, userId, pulse] = await Promise.all([
    listMembers(token),
    listSentInvitations(token),
    whoAmI(token),
    getPulse(token, { scopes: ["workspace"] }),
  ]);

  const pending = (invitations ?? []).filter(
    (invitation) => invitation.status === "pending",
  );

  return (
    <>
      <Header workspace={workspace} plan={plan} current="settings" />

      <main className="mx-auto w-full max-w-3xl flex-1 px-5 pb-28">
        <h1 className="mt-12 font-display text-[2.6rem] leading-[1.05] tracking-tight text-ink">
          Settings
        </h1>

        <p className="mt-3 max-w-[58ch] text-[15px] leading-relaxed text-muted">
          You are {article(workspace.your_role)}{" "}
          <span className="text-ink">{workspace.your_role}</span> of{" "}
          {workspace.display_name}.
        </p>

        {workspace.workspace_type !== "creator" && (
          <p className="mt-2 max-w-[58ch] text-[15px] leading-relaxed text-muted">
            Creators can read this as{" "}
            <Link
              href={`/brands/${workspace.slug}`}
              className="text-ink underline underline-offset-4"
            >
              your public page
            </Link>
            .
          </p>
        )}

        <Section
          title="Who you are"
          note="A creator deciding whether to take your offer has only this to go on."
        >
          {editable ? (
            <>
              <WorkspaceForm workspace={workspace} />
              <LogoForm current={workspace.logo_url} />
            </>
          ) : (
            <Written workspace={workspace} />
          )}
        </Section>

        <Section
          title="Plan"
          note="What this workspace is allowed to do."
        >
          <p className="text-[15px] text-ink">
            {PLAN_LABEL[plan.plan] ?? plan.plan}
            {plan.plan !== plan.configured_plan && (
              <span className="ml-2 text-[13px] text-muted">
                your {PLAN_LABEL[plan.configured_plan]} plan has
                lapsed
              </span>
            )}
          </p>

          <ul className="mt-3 text-[14px] leading-relaxed text-muted">
            <Limit
              label="Creators in a search"
              value={plan.limits.discovery_results}
            />
            <Limit
              label="Retainers at once"
              value={plan.limits.active_retainers}
            />
            <Limit
              label="People on the team"
              value={plan.limits.team_members}
            />
          </ul>

          <p className="mt-4 max-w-[58ch] text-[14px] leading-relaxed text-muted">
            Changing plan is not wired up to payment yet, so there is
            nothing to press here. It is the next thing after this.
          </p>
        </Section>

        <Section
          title="Team"
          note="Everyone who can act on behalf of this workspace."
        >
          {members === null ? (
            <p className="max-w-[58ch] text-[15px] leading-relaxed text-muted">
              Only the owner and admins can see who else is here.
            </p>
          ) : (
            <>
              <ul>
                {members
                  .filter((member) => member.status === "active")
                  .map((member) => (
                    <MemberRow
                      key={member.id}
                      member={member}
                      viewerRole={workspace.your_role}
                      isYou={member.user_id === userId}
                    />
                  ))}
              </ul>

              {pending.length > 0 && (
                <>
                  <h3 className="mt-7 text-[13px] text-muted">
                    Invited, not yet in
                  </h3>
                  <ul>
                    {pending.map((invitation) => (
                      <InvitationRow
                        key={invitation.id}
                        invitation={invitation}
                      />
                    ))}
                  </ul>
                </>
              )}

              {editable && <InviteForm />}
            </>
          )}
        </Section>
      </main>

      {/* An invitation accepted in someone else's browser should
          appear here without anyone reloading to find out. */}
      <Live scopes={["workspace"]} from={pulse} />
    </>
  );
}

function article(role: string): string {
  return role === "admin" || role === "owner" ? "the" : "a";
}

function Limit({
  label,
  value,
}: {
  label: string;
  value: number | null;
}) {
  return (
    <li className="flex items-baseline justify-between border-b border-line py-2">
      <span>{label}</span>
      <span className="tabular-nums text-ink">
        {value === null ? "No limit" : value}
      </span>
    </li>
  );
}

/**
 * What a Member sees in place of the form: the same facts, with no
 * boxes to type in, rather than a form that refuses on submit.
 */
function Written({
  workspace,
}: {
  workspace: {
    display_name: string;
    legal_name: string | null;
    bio: string | null;
    website_url: string | null;
    logo_url: string | null;
  };
}) {
  return (
    <div className="text-[15px] leading-relaxed text-ink">
      {workspace.logo_url && (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={workspace.logo_url}
          alt=""
          className="mb-4 h-16 w-16 rounded-lg border border-line object-cover"
        />
      )}

      <p>{workspace.display_name}</p>

      {workspace.legal_name && (
        <p className="mt-1 text-[14px] text-muted">
          {workspace.legal_name}
        </p>
      )}

      {workspace.bio && (
        <p className="mt-3 max-w-[58ch]">{workspace.bio}</p>
      )}

      {workspace.website_url && (
        <a
          href={workspace.website_url}
          target="_blank"
          rel="noreferrer"
          className="mt-3 inline-block text-[14px] underline decoration-line underline-offset-4 hover:decoration-ink"
        >
          {workspace.website_url}
        </a>
      )}

      <p className="mt-5 max-w-[58ch] text-[14px] text-muted">
        Only the owner and admins can change this.
      </p>
    </div>
  );
}

function Section({
  title,
  note,
  children,
}: {
  title: string;
  note: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-12 border-t border-line pt-7">
      <h2 className="font-display text-[1.5rem] leading-tight tracking-tight text-ink">
        {title}
      </h2>
      <p className="mt-1 mb-5 max-w-[58ch] text-[14px] leading-relaxed text-muted">
        {note}
      </p>
      {children}
    </section>
  );
}
