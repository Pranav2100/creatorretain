import { redirect } from "next/navigation";

import { signOut } from "@/app/actions/session";
import { requireToken } from "@/lib/session";
import { getWorkspaceContext, NO_WORKSPACE } from "@/lib/workspace";

import { SetupForm } from "./setup-form";

export const metadata = { title: "Set up · CreatorRetain" };

const KINDS = ["creator", "brand", "agency"];

export default async function SetupPage(
  props: PageProps<"/setup">,
) {
  const token = await requireToken("/setup");
  const context = await getWorkspaceContext(token);

  // Already has one. A second workspace is not a thing you can
  // have, so there is nothing to set up.
  //
  // Tested against the sentinel rather than for truthiness:
  // NO_WORKSPACE is a non-empty string, so a plain `if (context)`
  // reads "has no workspace" as "has one" and bounces the person
  // straight back out of the only page that can help them.
  if (context && context !== NO_WORKSPACE) {
    redirect("/");
  }

  const params = await props.searchParams;
  const requested = params.as;
  const as =
    typeof requested === "string" && KINDS.includes(requested)
      ? requested
      : "";

  return (
    <main className="flex flex-1 items-center justify-center px-5 py-16">
      <div className="w-full max-w-[26rem]">
        <h1 className="font-display text-[2.1rem] leading-[1.1] tracking-tight text-ink">
          One more thing
        </h1>

        <p className="mt-2 text-[15px] leading-relaxed text-muted">
          Everything in CreatorRetain happens inside a workspace.
          Make yours.
        </p>

        <SetupForm initialKind={as} />

        <form action={signOut} className="mt-8">
          <button
            type="submit"
            className="text-[13px] text-muted underline underline-offset-4 hover:text-ink"
          >
            Sign out
          </button>
        </form>
      </div>
    </main>
  );
}
