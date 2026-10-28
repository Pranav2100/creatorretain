import { type RetainerEvent } from "@/lib/retainers";

/**
 * Everything that has happened to this retainer, newest first.
 *
 * The API sends facts - who, which side, what kind - and the
 * sentence is built here, because the same event reads two ways
 * depending on who has the page open. "You asked to pause this"
 * and "Nina Cooks asked to pause this" are one row in the
 * database and must not be two.
 *
 * No JavaScript in this file on purpose. A history neither
 * changes while you look at it nor needs to; the live refresh
 * around it re-renders the whole page when it does.
 */

const WHEN = {
  day: "numeric",
  month: "short",
  year: "numeric",
} as const;

const AT = { hour: "numeric", minute: "2-digit" } as const;

/** How many rows before the rest fold away. */
const BEFORE_THE_FOLD = 14;

/**
 * Who did it, from the reader's side of the table.
 *
 * Both the person and the company where they differ, because
 * each answers a question the other leaves open. "TalentX asked
 * to pause this" hides which of the four people you deal with
 * actually did; "Mira Shah asked to pause this" leaves a reader
 * wondering who that is. Together they read like a signature.
 */
function actor(event: RetainerEvent): string {
  if (event.yours) {
    return "You";
  }

  const person = event.actor_person;
  const company = event.actor_name;

  if (!person) {
    return company ?? "Someone";
  }

  if (!company || company === person) {
    return person;
  }

  return `${person} (${company})`;
}

function sentence(event: RetainerEvent): string {
  const who = actor(event);
  const what = event.subject ?? "it";

  switch (event.kind) {
    case "offered":
      return `${who} offered this retainer`;
    case "accepted":
      return `${who} accepted`;
    case "declined":
      return `${who} declined`;
    case "offer_withdrawn":
      return `${who} withdrew the offer`;

    case "pause_requested":
      return `${who} asked to pause this`;
    case "resume_requested":
      return `${who} asked to start it up again`;
    case "request_rejected":
      return `${who} said no`;
    case "request_withdrawn":
      return `${who} took that request back`;
    case "paused":
      return `${who} agreed, and it paused`;
    case "resumed":
      return `${who} agreed, and it started up again`;

    case "notice_given":
      return `${who} gave notice`;
    case "ended":
      return "It ended";

    case "work_submitted":
      return `${who} submitted ${what}`;
    case "work_approved":
      return `${who} approved ${what}`;
    case "changes_requested":
      return `${who} asked for changes to ${what}`;
    case "work_rejected":
      return `${who} rejected ${what}`;
  }
}

/**
 * The trailing clause, where one event carries a date rather than
 * a quotation. Only notice does, so far.
 */
function detail(event: RetainerEvent): string | null {
  if (event.kind !== "notice_given" || !event.subject) {
    return null;
  }

  const finishes = new Date(event.subject).toLocaleDateString(
    "en-GB",
    WHEN,
  );

  return `Runs until ${finishes}.`;
}

function Row({
  event,
  echoes,
}: {
  event: RetainerEvent;
  /**
   * Whether the entry below this one already carries the same
   * words. Agreeing to a pause keeps the reason that was given
   * for asking, which makes each entry stand on its own in the
   * database but reads as a stutter when the two sit together.
   */
  echoes?: boolean;
}) {
  const when = new Date(event.at);
  const extra = detail(event);

  return (
    <li className="relative border-l border-line py-3 pl-5">
      {/* The dot sits on the rule rather than beside it, so the
          column reads as one thread instead of two. */}
      <span
        aria-hidden
        className={`absolute -left-[3px] top-[1.15rem] h-[5px] w-[5px] rounded-full ${
          event.about_work ? "bg-line" : "bg-pine"
        }`}
      />

      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <p
          className={`text-[15px] leading-snug ${
            event.about_work ? "text-muted" : "text-ink"
          }`}
        >
          {sentence(event)}
        </p>

        <p className="shrink-0 text-[13px] tabular-nums text-muted">
          {when.toLocaleDateString("en-GB", WHEN)}
          <span className="px-1.5 text-line">·</span>
          {when.toLocaleTimeString("en-GB", AT)}
        </p>
      </div>

      {extra && (
        <p className="mt-1 text-[13px] text-muted">{extra}</p>
      )}

      {event.note && !echoes && (
        <p className="mt-1.5 max-w-[58ch] border-l-2 border-line pl-3 text-[14px] leading-relaxed text-muted">
          {event.note}
        </p>
      )}
    </li>
  );
}

export function History({ events }: { events: RetainerEvent[] }) {
  if (events.length === 0) {
    return null;
  }

  // The list runs newest first, so "the one below" is the next
  // index along.
  const rows = events.map((event, index) => ({
    event,
    echoes:
      event.note !== null && events[index + 1]?.note === event.note,
  }));

  const recent = rows.slice(0, BEFORE_THE_FOLD);
  const older = rows.slice(BEFORE_THE_FOLD);

  return (
    <section className="mt-14">
      <h2 className="font-display text-[1.7rem] leading-tight tracking-tight text-ink">
        History
      </h2>

      <p className="mt-1.5 text-[14px] text-muted">
        Every change to this agreement, kept as it happened.
      </p>

      <ul className="mt-5">
        {recent.map((row) => (
          <Row
            key={row.event.id}
            event={row.event}
            echoes={row.echoes}
          />
        ))}
      </ul>

      {older.length > 0 && (
        <details className="group mt-2">
          <summary className="cursor-pointer list-none text-[13px] text-muted underline underline-offset-4 hover:text-ink">
            <span className="group-open:hidden">
              Show {older.length} earlier
              {older.length === 1 ? " entry" : " entries"}
            </span>
            <span className="hidden group-open:inline">
              Hide earlier entries
            </span>
          </summary>

          <ul className="mt-3">
            {older.map((row) => (
              <Row
                key={row.event.id}
                event={row.event}
                echoes={row.echoes}
              />
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
