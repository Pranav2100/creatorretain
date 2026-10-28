import Link from "next/link";

import { signOut } from "@/app/actions/session";
import { ThemeToggle } from "@/components/theme-toggle";
import { getUnread } from "@/lib/messages";
import { getToken } from "@/lib/session";
import type { PlanState, WorkspaceSummary } from "@/lib/workspace";

const PLAN_LABEL: Record<string, string> = {
  free: "Free",
  pro: "Pro",
  business: "Business",
  managed: "Managed",
  verified: "Verified",
};

export async function Header({
  workspace,
  plan,
  current,
}: {
  workspace: WorkspaceSummary;
  plan: PlanState;
  current?:
    | "creators"
    | "retainers"
    | "messages"
    | "profile"
    | "settings"
    | "account";
}) {
  // Read here rather than passed in by every page. One cheap
  // aggregate per render, and the alternative - each page
  // remembering to fetch and forward it - is the kind of thing
  // that gets forgotten on exactly the page you were on when the
  // message arrived.
  const token = await getToken();
  const { unread, requests } = token
    ? await getUnread(token)
    : { unread: 0, requests: 0 };

  // Requests are deliberately not added in. A badge a stranger
  // can raise is a badge nobody trusts, so they show as a hollow
  // mark rather than a number.
  const waiting = requests > 0 && unread === 0;
  // A creator workspace cannot browse discovery, so offering them
  // the link would only lead to a refusal.
  const canBrowse = plan.capabilities.includes("browse_creators");

  // Only creator workspaces have a profile to edit, so only they
  // get the link.
  const isCreator = workspace.workspace_type === "creator";

  return (
    // data-theme-host says this page has somewhere to put the
    // theme control, which keeps the floating one in the root
    // layout out of the way. See globals.css.
    <header data-theme-host className="border-b border-line">
      {/* Wraps rather than keeping one fixed-height row: an agency
          carries a nav tab more than a creator, which was enough to
          push Sign out off the right edge of a phone. */}
      <div className="mx-auto flex min-h-14 w-full max-w-5xl flex-wrap items-center justify-between gap-x-6 gap-y-1 px-5 py-2.5">
        {/* Wraps within itself as well as against the right-hand
            side. A fifth tab was enough to push Settings off the
            edge of a phone, and a nav that cannot wrap just
            clips. */}
        <div className="flex min-w-0 flex-wrap items-baseline gap-x-5 gap-y-1 sm:gap-x-6">
          <Link
            href={canBrowse ? "/creators" : "/retainers"}
            className="font-display text-[1.05rem] tracking-tight text-ink"
          >
            CreatorRetain
          </Link>

          <nav className="flex flex-wrap items-baseline gap-x-4 gap-y-1 text-[13px]">
            {canBrowse && (
              <Tab href="/creators" active={current === "creators"}>
                Creators
              </Tab>
            )}
            <Tab href="/retainers" active={current === "retainers"}>
              Retainers
            </Tab>
            <Tab href="/messages" active={current === "messages"}>
              Messages
              {unread > 0 && (
                <span className="ml-1.5 rounded-full bg-pine px-1.5 py-0.5 text-[10px] tabular-nums text-on-pine">
                  {unread > 99 ? "99+" : unread}
                </span>
              )}
              {waiting && (
                <span
                  aria-label="Someone is waiting in requests"
                  className="ml-1.5 inline-block h-1.5 w-1.5 rounded-full border border-pine align-middle"
                />
              )}
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

        {/* This side is about the person rather than the
            workspace: which one they are acting for, the one page
            that is theirs, and the way out. */}
        <div className="flex min-w-0 items-center gap-4 text-[13px] sm:gap-5">
          <span className="flex min-w-0 items-center text-muted">
            <span className="truncate">{workspace.display_name}</span>
            <span className="ml-2 shrink-0 rounded border border-line px-1.5 py-0.5 text-[11px] text-pine">
              {PLAN_LABEL[plan.plan] ?? plan.plan}
            </span>
          </span>

          <ThemeToggle />

          <Link
            href="/account"
            className={
              current === "account"
                ? "shrink-0 text-ink underline decoration-pine underline-offset-[6px]"
                : "shrink-0 text-muted hover:text-ink"
            }
          >
            Account
          </Link>

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
