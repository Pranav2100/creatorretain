import Link from "next/link";
import { notFound } from "next/navigation";

import { Header } from "@/components/header";
import { money } from "@/lib/format";
import {
  DELIVERABLE_LABEL,
  getRetainer,
  STATUS_LABEL,
  type Deliverable,
  type Period,
  type RetainerDetail,
} from "@/lib/retainers";
import { requireWorkspace } from "@/lib/session";

import {
  AnswerButton,
  PendingBanner,
  RequestButton,
  ReviewForm,
  SubmitWorkForm,
} from "./forms";

const DAY = { day: "numeric", month: "short" } as const;

function span(start: string, end: string) {
  const from = new Date(start).toLocaleDateString("en-GB", DAY);
  const to = new Date(end).toLocaleDateString("en-GB", {
    ...DAY,
    year: "numeric",
  });

  return `${from} – ${to}`;
}

export default async function RetainerPage(
  props: PageProps<"/retainers/[id]">,
) {
  const { id } = await props.params;

  const { token, workspace, plan } = await requireWorkspace(
    `/retainers/${id}`,
  );

  const retainer = await getRetainer(token, id);

  if (!retainer) {
    notFound();
  }

  const mine = retainer.your_side;
  const other = mine === "brand" ? retainer.creator : retainer.brand;

  // Newest month first: the one needing attention is the one
  // running now, not the one that closed in January.
  const periods = [...retainer.periods].reverse();

  return (
    <>
      <Header
        workspace={workspace}
        plan={plan}
        current="retainers"
      />

      <main className="mx-auto w-full max-w-5xl flex-1 px-5 pb-24">
        <Link
          href="/retainers"
          className="mt-10 inline-block text-[13px] text-muted underline underline-offset-4 hover:text-ink"
        >
          All retainers
        </Link>

        <div className="mt-6 border-b border-line pb-8">
          <p className="text-[13px] text-muted">
            {mine === "brand" ? "You hired" : "Hired by"}
          </p>

          {/* The creator's side links out to whoever is hiring
              them. This is the screen where "who are these people?"
              actually gets asked - a pending offer is sitting right
              below it - so the answer belongs one click away. */}
          <h1 className="mt-1 font-display text-[2.6rem] leading-[1.05] tracking-tight text-ink">
            {mine === "creator" ? (
              <Link
                href={`/brands/${other.slug}`}
                className="underline decoration-line underline-offset-[8px] hover:decoration-ink"
              >
                {other.display_name}
              </Link>
            ) : (
              other.display_name
            )}
          </h1>

          <p className="mt-3 text-[16px] text-muted">
            {retainer.title}
          </p>

          <div className="mt-6 flex flex-wrap items-baseline gap-x-10 gap-y-3">
            <Fact label="Status">
              {STATUS_LABEL[retainer.status]}
            </Fact>

            <Fact label="Every month">
              <span className="tabular-nums">
                {money(retainer.monthly_amount, retainer.currency)}
              </span>
            </Fact>

            <Fact label="For">
              {retainer.specs
                .map(
                  (spec) =>
                    `${spec.quantity} × ${
                      DELIVERABLE_LABEL[spec.deliverable_type]
                    }`,
                )
                .join(", ")}
            </Fact>

            {retainer.status === "active" && (
              <Fact label="Renews on">
                day {retainer.anchor_day}
              </Fact>
            )}
          </div>

          {retainer.ended_reason && (
            <p className="mt-5 max-w-[56ch] border-l-2 border-line pl-3 text-[14px] leading-relaxed text-muted">
              {retainer.ended_reason}
            </p>
          )}
        </div>

        {retainer.message && retainer.status === "pending" && (
          <blockquote className="mt-8 max-w-[56ch] border-l-2 border-pine pl-4 text-[16px] leading-relaxed text-ink">
            {retainer.message}
          </blockquote>
        )}

        {retainer.terms && (
          <div className="mt-8 max-w-[62ch]">
            <h2 className="text-[13px] text-muted">Terms</h2>
            <p className="mt-1.5 text-[15px] leading-relaxed text-ink">
              {retainer.terms}
            </p>
          </div>
        )}

        {retainer.under_notice && (
          <NoticeBanner retainer={retainer} />
        )}

        {retainer.pending && (
          <PendingBanner
            retainerId={retainer.id}
            pending={retainer.pending}
            otherName={
              retainer.your_side === "brand"
                ? retainer.creator.display_name
                : retainer.brand.display_name
            }
          />
        )}

        <Actions retainer={retainer} />

        {periods.length > 0 && (
          <section className="mt-14">
            <h2 className="font-display text-[1.7rem] leading-tight tracking-tight text-ink">
              {periods.length === 1 ? "The first month" : "Months"}
            </h2>

            {periods.map((period) => (
              <PeriodBlock
                key={period.id}
                period={period}
                retainer={retainer}
              />
            ))}
          </section>
        )}

        {retainer.status === "active" && periods.length === 0 && (
          <p className="mt-10 max-w-[48ch] text-[15px] leading-relaxed text-muted">
            This starts on{" "}
            {new Date(retainer.start_date).toLocaleDateString(
              "en-GB",
              { day: "numeric", month: "long", year: "numeric" },
            )}
            . The first month appears then.
          </p>
        )}
      </main>
    </>
  );
}

/**
 * Notice has been served and the wind-down is running.
 *
 * Said plainly rather than left as a date in a corner: the work
 * and the money both continue until that day, and whoever did not
 * serve it needs to know how long they have.
 */
function NoticeBanner({ retainer }: { retainer: RetainerDetail }) {
  const theirs =
    retainer.notice_given_by_side !== retainer.your_side;

  const who = theirs
    ? retainer.your_side === "brand"
      ? retainer.creator.display_name
      : retainer.brand.display_name
    : "You";

  const finishes = retainer.end_date
    ? new Date(retainer.end_date).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : null;

  return (
    <section className="mt-6 rounded-lg border border-line bg-white px-5 py-4">
      <p className="text-[15px] leading-relaxed text-ink">
        {who} gave notice. This runs until{" "}
        <span className="tabular-nums">{finishes}</span>, and the
        work and the money carry on until then.
      </p>

      {retainer.ended_reason && (
        <p className="mt-2 max-w-[58ch] border-l-2 border-line pl-3 text-[14px] leading-relaxed text-muted">
          {retainer.ended_reason}
        </p>
      )}
    </section>
  );
}

function Actions({ retainer }: { retainer: RetainerDetail }) {
  const { id, status, your_side: side } = retainer;

  const buttons = [];

  if (status === "pending" && side === "creator") {
    buttons.push(
      <AnswerButton
        key="accept"
        retainerId={id}
        action="accept"
        label="Accept"
        tone="loud"
      />,
      <AnswerButton
        key="decline"
        retainerId={id}
        action="decline"
        label="Decline"
        asks="Why, if you want to say"
      />,
    );
  }

  if (status === "pending" && side === "brand") {
    buttons.push(
      <AnswerButton
        key="cancel"
        retainerId={id}
        action="cancel"
        label="Withdraw this offer"
      />,
    );
  }

  // A request already waiting is the only thing on offer: two
  // competing asks on one agreement is not a state worth having.
  const settled = retainer.pending === null;

  const other =
    side === "brand"
      ? retainer.creator.display_name
      : retainer.brand.display_name;

  if (status === "active" && settled) {
    if (!retainer.under_notice) {
      buttons.push(
        <RequestButton
          key="pause"
          retainerId={id}
          action="pause"
          otherName={other}
        />,
        <AnswerButton
          key="end"
          retainerId={id}
          action="end"
          label="Give notice"
          asks="Why it is ending"
        />,
      );
    }
  }

  if (status === "paused" && settled) {
    buttons.push(
      <RequestButton
        key="resume"
        retainerId={id}
        action="resume"
        otherName={other}
      />,
      <AnswerButton
        key="end"
        retainerId={id}
        action="end"
        label="Give notice"
        asks="Why it is ending"
      />,
    );
  }

  if (buttons.length === 0) {
    return null;
  }

  return (
    <div className="mt-8 flex flex-wrap items-start gap-3">
      {buttons}
    </div>
  );
}

function PeriodBlock({
  period,
  retainer,
}: {
  period: Period;
  retainer: RetainerDetail;
}) {
  return (
    <div className="mt-8 border-t border-line pt-5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h3 className="text-[15px] text-ink">
          Month {period.sequence}
          <span className="ml-3 text-[14px] text-muted">
            {span(period.period_start, period.period_end)}
          </span>
        </h3>

        <p className="text-[14px] text-muted">
          {period.state === "current" && "Running now · "}
          {period.state === "upcoming" && "Not started · "}
          {period.is_complete
            ? "All delivered"
            : `${period.outstanding_count} outstanding`}
          <span className="ml-3 tabular-nums text-ink">
            {money(period.amount, period.currency)}
          </span>
        </p>
      </div>

      <ul className="mt-3">
        {period.deliverables.map((item) => (
          <DeliverableRow
            key={item.id}
            item={item}
            retainer={retainer}
          />
        ))}
      </ul>
    </div>
  );
}

const STATE_LABEL: Record<string, string> = {
  pending: "Not started",
  submitted: "Waiting on review",
  revision_requested: "Changes asked for",
  approved: "Approved",
  rejected: "Rejected",
};

function DeliverableRow({
  item,
  retainer,
}: {
  item: Deliverable;
  retainer: RetainerDetail;
}) {
  const mine = retainer.your_side;
  const live = retainer.status === "active";

  const canSubmit =
    live &&
    mine === "creator" &&
    (item.status === "pending" ||
      item.status === "revision_requested");

  const canReview =
    live && mine === "brand" && item.status === "submitted";

  return (
    <li className="border-b border-line py-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <span className="text-[15px] text-ink">
          {DELIVERABLE_LABEL[item.deliverable_type]}{" "}
          <span className="text-muted">#{item.position}</span>
        </span>

        <span className="text-[13px] text-muted">
          {STATE_LABEL[item.status] ?? item.status}
          {item.submission_count > 1 &&
            ` · attempt ${item.submission_count}`}
        </span>
      </div>

      {item.submitted_url && (
        <p className="mt-1.5 text-[14px]">
          <a
            href={item.submitted_url}
            target="_blank"
            rel="noreferrer"
            className="text-ink underline decoration-line underline-offset-4 hover:decoration-ink"
          >
            {item.submitted_url}
          </a>
          {item.submitted_note && (
            <span className="ml-3 text-muted">
              {item.submitted_note}
            </span>
          )}
        </p>
      )}

      {item.review_note && (
        <p className="mt-1.5 max-w-[56ch] border-l-2 border-line pl-3 text-[14px] leading-relaxed text-muted">
          {item.review_note}
        </p>
      )}

      {canSubmit && (
        <SubmitWorkForm
          retainerId={retainer.id}
          deliverableId={item.id}
          resubmitting={item.status === "revision_requested"}
        />
      )}

      {canReview && (
        <ReviewForm
          retainerId={retainer.id}
          deliverableId={item.id}
        />
      )}
    </li>
  );
}

function Fact({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <p className="text-[12px] text-muted">{label}</p>
      <p className="mt-0.5 text-[15px] text-ink">{children}</p>
    </div>
  );
}
