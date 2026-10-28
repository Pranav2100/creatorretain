/**
 * The pieces every loading screen is built from.
 *
 * A skeleton earns its place by being the shape of the thing
 * that is coming. A spinner says "wait"; a skeleton says "a list
 * of six things is about to appear here", and because the blocks
 * land where the real text lands, nothing jumps when the content
 * arrives. Guessing the shape wrongly is worse than a spinner,
 * so these mirror the real pages - same max-widths, same row
 * heights, same borders - and each route composes them rather
 * than inventing its own.
 *
 * The pulse itself is one CSS class, `bone`, in globals.css,
 * where it also honours anyone who has asked for less motion.
 */

import { ThemeToggle } from "@/components/theme-toggle";

export function Bone({
  className = "",
  style,
}: {
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <span
      aria-hidden="true"
      className={`bone block ${className}`}
      style={style}
    />
  );
}

/**
 * The top bar.
 *
 * Every page renders the header itself rather than inheriting it
 * from a layout, so navigating unmounts it along with everything
 * else. Without a bar this shape the whole chrome would vanish
 * and reappear on every move between pages, which reads as the
 * app breaking rather than loading.
 */
export function ChromeBone() {
  return (
    // data-theme-host for the same reason the real header carries
    // it: without it the floating control in the root layout
    // un-hides itself for exactly as long as the skeleton is up,
    // so the theme button hops to the corner and back on every
    // navigation.
    <div data-theme-host className="border-b border-line">
      <div className="mx-auto flex min-h-14 w-full max-w-5xl flex-wrap items-center justify-between gap-x-6 gap-y-1 px-5 py-2.5">
        <div className="flex min-w-0 flex-wrap items-center gap-x-5 gap-y-1 sm:gap-x-6">
          <Bone className="h-[15px] w-[7.5rem] rounded" />
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <Bone className="h-3 w-14 rounded" />
            <Bone className="h-3 w-16 rounded" />
            <Bone className="h-3 w-[4.5rem] rounded" />
            <Bone className="h-3 w-12 rounded" />
          </div>
        </div>

        <div className="flex min-w-0 items-center gap-4 sm:gap-5">
          <Bone className="h-3 w-24 rounded" />
          {/* The real control, not a placeholder for one. It does
              not depend on anything being loaded, so blanking it
              out would make it blink on every navigation for no
              reason - and it stays usable while you wait. */}
          <ThemeToggle />
          <Bone className="h-3 w-14 rounded" />
          <Bone className="h-3 w-12 rounded" />
        </div>
      </div>
    </div>
  );
}

/**
 * A whole loading page: the bar, then a main column of the width
 * the real page uses, then the page's own blocks.
 *
 * `width` is the only thing that varies between them, and it has
 * to match - a skeleton 5xl wide followed by a 3xl page shifts
 * everything sideways the moment it loads.
 */
export function PageBone({
  width = "5xl",
  title = "16rem",
  children,
}: {
  width?: "3xl" | "5xl" | "2xl";
  title?: string | null;
  children?: React.ReactNode;
}) {
  const column = {
    "2xl": "max-w-2xl",
    "3xl": "max-w-3xl",
    "5xl": "max-w-5xl",
  }[width];

  return (
    // Announced rather than silent: somebody on a screen reader
    // gets "Loading" instead of a page that has gone quiet.
    <div role="status" aria-busy="true" aria-label="Loading">
      <ChromeBone />

      <main className={`mx-auto w-full ${column} flex-1 px-5 pb-24`}>
        {title !== null && (
          /* Matches the mt-12 text-[2.6rem] display heading every
             page opens with. */
          <Bone
            className="mt-14 h-9 rounded"
            style={{ width: title }}
          />
        )}
        {children}
      </main>
    </div>
  );
}

/**
 * A list of rows, the shape the retainer list, the creator list
 * and the inbox all share: a block of text on the left, something
 * short and right-aligned on the right, a hairline between each.
 */
export function ListBone({
  rows = 5,
  tall = true,
  right = "4rem",
}: {
  rows?: number;
  tall?: boolean;
  right?: string | null;
}) {
  return (
    <ol className="mt-8">
      {Array.from({ length: rows }).map((_, index) => (
        <li
          key={index}
          className="border-b border-line first:border-t"
        >
          <div
            className={`flex items-baseline gap-4 ${tall ? "py-5" : "py-4"}`}
          >
            <div className="min-w-0 flex-1">
              {/* Widths step down the list so it reads as a list
                  of different things rather than a bar chart. */}
              <Bone
                className="h-5 rounded"
                style={{ width: `${58 - (index % 4) * 9}%` }}
              />
              <Bone
                className="mt-2 h-3 rounded"
                style={{ width: `${40 - (index % 3) * 7}%` }}
              />
              {tall && (
                <Bone className="mt-2.5 h-3 w-[7rem] rounded" />
              )}
            </div>

            {right !== null && (
              <div className="shrink-0" style={{ width: right }}>
                <Bone className="ml-auto h-4 w-full rounded" />
                <Bone className="mt-1.5 ml-auto h-3 w-2/3 rounded" />
              </div>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

/** A labelled input, the unit every form on the site is built of. */
export function FieldBone({ label = "6rem" }: { label?: string }) {
  return (
    <div className="mt-6">
      <Bone
        className="h-3 rounded"
        style={{ width: label }}
      />
      <Bone className="mt-2 h-[38px] w-full rounded-lg" />
    </div>
  );
}

/** A form: an intro line, some fields, something to press. */
export function FormBone({ fields = 4 }: { fields?: number }) {
  return (
    <>
      <Bone className="mt-6 h-3 w-[22rem] max-w-full rounded" />

      {Array.from({ length: fields }).map((_, index) => (
        <FieldBone key={index} label={`${5 + (index % 3) * 1.5}rem`} />
      ))}

      <Bone className="mt-8 h-[42px] w-[9rem] rounded-lg" />
    </>
  );
}

/** A bordered panel, used wherever the real page raises a card. */
export function CardBone({
  lines = 3,
  className = "",
}: {
  lines?: number;
  className?: string;
}) {
  return (
    <div
      className={`rounded-[14px] border border-line bg-surface p-5 ${className}`}
    >
      <Bone className="h-4 w-[40%] rounded" />
      {Array.from({ length: lines }).map((_, index) => (
        <Bone
          key={index}
          className="mt-3 h-3 rounded"
          style={{ width: `${88 - index * 13}%` }}
        />
      ))}
    </div>
  );
}
