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
  current?: "creators" | "retainers";
}) {
  // A creator workspace cannot browse discovery, so offering them
  // the link would only lead to a refusal.
  const canBrowse = plan.capabilities.includes("browse_creators");

  return (
    <header className="border-b border-line">
      <div className="mx-auto flex h-14 w-full max-w-5xl items-center justify-between px-5">
        <div className="flex items-baseline gap-6">
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
          </nav>
        </div>

        <div className="flex items-center gap-5 text-[13px]">
          <span className="text-muted">
            {workspace.display_name}
            <span className="ml-2 rounded border border-line px-1.5 py-0.5 text-[11px] text-pine">
              {PLAN_LABEL[plan.plan] ?? plan.plan}
            </span>
          </span>

          <form action={signOut}>
            <button
              type="submit"
              className="text-muted underline underline-offset-4 hover:text-ink"
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
