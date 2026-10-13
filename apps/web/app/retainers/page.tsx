import Link from "next/link";
import { redirect } from "next/navigation";

import { Header } from "@/components/header";
import { money } from "@/lib/format";
import {
  listRetainers,
  STATUS_LABEL,
  type RetainerSummary,
} from "@/lib/retainers";
import { requireToken } from "@/lib/session";
import { getWorkspaceContext } from "@/lib/workspace";

export const metadata = { title: "Retainers · CreatorRetain" };

// Live agreements first, then offers waiting on someone, then the
// closed ones. A list sorted by creation date buries the thing you
// opened the page to deal with.
const ORDER: Record<string, number> = {
  active: 0,
  pending: 1,
  paused: 2,
  ended: 3,
  declined: 4,
  cancelled: 5,
};

export default async function RetainersPage() {
  const token = await requireToken("/retainers");
  const context = await getWorkspaceContext(token);

  if (!context) {
    redirect("/login?next=/retainers");
  }

  const { retainers } = await listRetainers(token);

  const sorted = [...retainers].sort(
    (a, b) =>
      (ORDER[a.status] ?? 9) - (ORDER[b.status] ?? 9) ||
      b.created_at.localeCompare(a.created_at),
  );

  return (
    <>
      <Header
        workspace={context.workspace}
        plan={context.plan}
        current="retainers"
      />

      <main className="mx-auto w-full max-w-5xl flex-1 px-5 pb-24">
        <h1 className="mt-12 font-display text-[2.6rem] leading-[1.05] tracking-tight text-ink">
          Retainers
        </h1>

        {sorted.length === 0 ? (
          <div className="mt-8 max-w-[46ch]">
            <p className="text-[16px] leading-relaxed text-muted">
              {context.workspace.workspace_type === "creator"
                ? "No one has offered you a retainer yet. Offers arrive here."
                : "You have not put anyone on retainer yet."}
            </p>

            {context.workspace.workspace_type !== "creator" && (
              <Link
                href="/creators"
                className="mt-4 inline-block text-[15px] text-pine underline underline-offset-4"
              >
                Find a creator
              </Link>
            )}
          </div>
        ) : (
          <ol className="mt-8">
            {sorted.map((retainer) => (
              <Row key={retainer.id} retainer={retainer} />
            ))}
          </ol>
        )}
      </main>
    </>
  );
}

function Row({ retainer }: { retainer: RetainerSummary }) {
  // You already know who you are; the useful name is the other one.
  const other =
    retainer.your_side === "brand"
      ? retainer.creator
      : retainer.brand;

  return (
    <li className="border-b border-line first:border-t">
      <Link
        href={`/retainers/${retainer.id}`}
        className="group flex items-baseline gap-4 py-5 outline-none focus-visible:bg-white"
      >
        <div className="min-w-0 flex-1">
          <h2 className="font-display text-[1.35rem] leading-tight tracking-tight text-ink group-hover:underline group-hover:decoration-line group-hover:underline-offset-[6px]">
            {other.display_name}
          </h2>

          <p className="mt-1 truncate text-[14px] text-muted">
            {retainer.title}
          </p>

          <p className="mt-1.5 text-[13px] text-muted">
            {STATUS_LABEL[retainer.status]}
            {retainer.status === "active" &&
              ` · ${retainer.periods_so_far} ${
                retainer.periods_so_far === 1 ? "month" : "months"
              } so far`}
          </p>
        </div>

        <div className="w-28 shrink-0 text-right tabular-nums">
          <span className="text-[15px] text-ink">
            {money(retainer.monthly_amount, retainer.currency)}
          </span>
          <span className="mt-1 block text-[12px] text-muted">
            {retainer.monthly_deliverable_count} a month
          </span>
        </div>
      </Link>
    </li>
  );
}
