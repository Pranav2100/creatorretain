"use client";

import Link from "next/link";
import { useEffect } from "react";

/**
 * What someone gets when something broke.
 *
 * It has to be a client component with a `reset` - that is the
 * contract Next gives this file - and it cannot read the session,
 * so the links are the two that work whatever state the person
 * is in.
 *
 * `reset` re-renders the part that failed without a full reload,
 * which is worth offering first: most of what lands here is a
 * request that timed out or an API that was restarting, and
 * trying again genuinely fixes those.
 *
 * The digest is shown because it is the only thing connecting
 * what the person saw to the line in the server log that
 * explains it. Without it a bug report is "it broke".
 */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // The browser console is where whoever is running this will
    // look first. The server already has the stack.
    console.error(error);
  }, [error]);

  return (
    <main className="flex flex-1 items-center justify-center px-5 py-20">
      <div className="w-full max-w-[34rem]">
        <p className="text-[13px] tracking-wide text-muted">
          Something went wrong
        </p>

        <h1 className="mt-2 font-display text-[2.6rem] leading-[1.05] tracking-tight text-ink">
          That did not load
        </h1>

        <p className="mt-4 max-w-[46ch] text-[16px] leading-relaxed text-muted">
          Nothing you did caused this, and nothing you were working
          on has been lost. Trying again usually works.
        </p>

        <div className="mt-7 flex flex-wrap items-center gap-x-6 gap-y-3">
          <button
            type="button"
            onClick={reset}
            className="rounded-lg bg-pine px-5 py-2.5 text-[14px] text-on-pine transition-opacity hover:opacity-90"
          >
            Try again
          </button>

          <Link
            href="/retainers"
            className="text-[15px] text-muted underline underline-offset-4 hover:text-ink"
          >
            Your retainers
          </Link>
        </div>

        {error.digest && (
          <p className="mt-10 border-t border-line pt-4 text-[12px] text-muted">
            If you report this, quote{" "}
            <span className="font-mono text-ink">{error.digest}</span>
            {" "}— it points at the exact line in the log.
          </p>
        )}
      </div>
    </main>
  );
}
