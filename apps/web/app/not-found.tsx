import Link from "next/link";

import { getToken } from "@/lib/session";

export const metadata = { title: "Not found · CreatorRetain" };

/**
 * What someone gets when a page is not theirs to see, or is not
 * there at all.
 *
 * Deliberately the same answer for both. A manager who types the
 * address of an account she does not run gets this; so does
 * anyone following a stale link. Saying "you do not have access
 * to this retainer" would be friendlier and would also confirm
 * that the retainer exists, which is the one thing the rule
 * exists to withhold.
 *
 * So instead of explaining, it offers somewhere to go. The links
 * differ by whether there is a session, because sending a signed
 * out visitor to Retainers only lands them on a sign-in form
 * they did not ask for.
 */
export default async function NotFound() {
  const signedIn = Boolean(await getToken());

  return (
    <main className="flex flex-1 items-center justify-center px-5 py-20">
      <div className="w-full max-w-[34rem]">
        <p className="text-[13px] tracking-wide text-muted">404</p>

        <h1 className="mt-2 font-display text-[2.6rem] leading-[1.05] tracking-tight text-ink">
          Nothing here
        </h1>

        <p className="mt-4 max-w-[46ch] text-[16px] leading-relaxed text-muted">
          This page does not exist, or it is not one you can open.
          If someone sent you the link, ask them to check it.
        </p>

        <div className="mt-7 flex flex-wrap items-center gap-x-6 gap-y-3 text-[15px]">
          {signedIn ? (
            <>
              <Link
                href="/retainers"
                className="rounded-lg bg-pine px-5 py-2.5 text-[14px] text-on-pine transition-opacity hover:opacity-90"
              >
                Your retainers
              </Link>
              <Link
                href="/account"
                className="text-muted underline underline-offset-4 hover:text-ink"
              >
                Your account
              </Link>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="rounded-lg bg-pine px-5 py-2.5 text-[14px] text-on-pine transition-opacity hover:opacity-90"
              >
                Sign in
              </Link>
              <Link
                href="/"
                className="text-muted underline underline-offset-4 hover:text-ink"
              >
                Back to the start
              </Link>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
