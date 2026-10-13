import { redirect } from "next/navigation";

import { getToken } from "@/lib/session";

import { LoginForm } from "./login-form";

export const metadata = { title: "Sign in · CreatorRetain" };

export default async function LoginPage(
  props: PageProps<"/login">,
) {
  // "/" works out where this workspace belongs, so an already
  // signed-in creator is not sent to the creator list either.
  if (await getToken()) {
    redirect("/");
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
        <h1 className="font-display text-[2.4rem] leading-[1.05] tracking-tight text-ink">
          CreatorRetain
        </h1>
        <p className="mt-2 text-[15px] leading-relaxed text-muted">
          Where creators, brands and agencies work together.
        </p>

        <LoginForm next={next} />
      </div>
    </main>
  );
}
