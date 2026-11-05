import Link from "next/link";
import { redirect } from "next/navigation";

import { getToken } from "@/lib/session";
import {
  getWorkspaceContext,
  landingFor,
  NO_WORKSPACE,
} from "@/lib/workspace";

import { LoginForm } from "./login-form";

export const metadata = { title: "Sign in · CreatorRetain" };

export default async function LoginPage(
  props: PageProps<"/login">,
) {
  const token = await getToken();

  // Whether the cookie still works, not merely whether there is
  // one. Holding a dead token used to bounce people to "/", which
  // shows the marketing page to anyone it cannot identify - so
  // being signed out led to an advert, and the Sign in link on it
  // led back here, round and round until the cookie expired. A
  // password changed in another browser leaves exactly that
  // cookie behind, which is how this was found.
  if (token) {
    const context = await getWorkspaceContext(token);

    if (context === NO_WORKSPACE) {
      redirect("/setup");
    }

    if (context) {
      redirect(landingFor(context.plan));
    }
  }

  const params = await props.searchParams;
  const requested = params.next;

  // Empty when they came here directly. Signing in then decides
  // where to land from the workspace itself, rather than this page
  // guessing - a creator sent to the creator list lands on a
  // refusal.
  const next =
    typeof requested === "string" && requested.startsWith("/")
      ? requested
      : "";

  return (
    <main className="flex flex-1 items-center justify-center px-5 py-16">
      <div className="w-full max-w-[22rem]">
        {/* The way out. Signing in was the only page in the app
            with no link off it at all - no way back to the
            marketing page and no way to the sign-up form - so
            arriving here by mistake left you stuck. Laid out
            like /signup, which already did this: the wordmark
            goes home, and the heading says what the page is
            rather than repeating the product name.

            It underlines on hover, which /signup now does too: a
            wordmark that is a link but looks exactly like a
            heading is only a way out for people who already
            guessed it was one. */}
        <Link
          href="/"
          className="font-display text-[1.6rem] tracking-tight text-ink decoration-pine underline-offset-[6px] hover:underline"
        >
          CreatorRetain
        </Link>

        <h1 className="mt-7 font-display text-[2rem] leading-[1.1] tracking-tight text-ink">
          Sign in
        </h1>
        <p className="mt-2 text-[15px] leading-relaxed text-muted">
          Where creators, brands and agencies work together.
        </p>

        <LoginForm next={next} />
      </div>
    </main>
  );
}
