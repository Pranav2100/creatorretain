import Link from "next/link";

import { signOut } from "@/app/actions/session";
import type { PlanState, WorkspaceSummary } from "@/lib/workspace";

const PLAN_LABEL: Record<string, string> = {
  free: "Free",
  pro: "Pro",
  business: "Business",
  managed: "Managed",
  verified: "Verified",
};

export function Header({
  workspace,
  plan,
  current,
}: {
  workspace: WorkspaceSummary;
  plan: PlanState;
  current?: "creators" | "retainers" | "profile" | "settings";
}) {
  // A creator workspace cannot browse discovery, so offering them
  // the link would only lead to a refusal.
  const canBrowse = plan.capabilities.includes("browse_creators");

  // Only creator workspaces have a profile to edit, so only they
  // get the link.
  const isCreator = workspace.workspace_type === "creator";

  return (
    <header className="border-b border-line">
      {/* Wraps rather than keeping one fixed-height row: an agency
          carries a nav tab more than a creator, which was enough to
          push Sign out off the right edge of a phone. */}
      <div className="mx-auto flex min-h-14 w-full max-w-5xl flex-wrap items-center justify-between gap-x-6 gap-y-1 px-5 py-2.5">
        <div className="flex items-baseline gap-5 sm:gap-6">
          <Link
            href={canBrowse ? "/creators" : "/retainers"}
            className="font-display text-[1.05rem] tracking-tight text-ink"
          >
            CreatorRetain
          </Link>

          <nav className="flex items-baseline gap-4 text-[13px]">
            {canBrowse && (
              <Tab href="/creators" active={current === "creators"}>
                Creators
              </Tab>
            )}
            <Tab href="/retainers" active={current === "retainers"}>
              Retainers
            </Tab>
            {isCreator && (
              <Tab href="/profile" active={current === "profile"}>
                Profile
              </Tab>
            )}
            <Tab href="/settings" active={current === "settings"}>
              Settings
            </Tab>
          </nav>
        </div>

        <div className="flex min-w-0 items-center gap-5 text-[13px]">
          <span className="flex min-w-0 items-center text-muted">
            <span className="truncate">{workspace.display_name}</span>
            <span className="ml-2 shrink-0 rounded border border-line px-1.5 py-0.5 text-[11px] text-pine">
              {PLAN_LABEL[plan.plan] ?? plan.plan}
            </span>
          </span>

          <form action={signOut} className="shrink-0">
            <button
              type="submit"
              className="whitespace-nowrap text-muted underline underline-offset-4 hover:text-ink"
            >
              Sign out
            </button>
          </form>
        </div>
      </div>
    </header>
  );
}

function Tab({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={
        active
          ? "text-ink underline decoration-pine underline-offset-[6px]"
          : "text-muted hover:text-ink"
      }
    >
      {children}
    </Link>
  );
}
