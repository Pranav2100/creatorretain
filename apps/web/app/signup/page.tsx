import Link from "next/link";
import { redirect } from "next/navigation";

import { getToken } from "@/lib/session";

import { SignUpForm } from "./signup-form";

export const metadata = { title: "Create an account · CreatorRetain" };

const INTRO: Record<string, string> = {
  creator: "Set up your profile and start taking retainers.",
  brand: "Find creators and put them on monthly retainers.",
  agency: "Hire creators for the brands you represent.",
};

export default async function SignUpPage(
  props: PageProps<"/signup">,
) {
  if (await getToken()) {
    redirect("/");
  }

  const params = await props.searchParams;
  const requested = params.as;
  const as =
    typeof requested === "string" && requested in INTRO
      ? requested
      : "";

  return (
    <main className="flex flex-1 items-center justify-center px-5 py-16">
      <div className="w-full max-w-[24rem]">
        <Link
          href="/"
          className="font-display text-[1.6rem] tracking-tight text-ink"
        >
          CreatorRetain
        </Link>

        <h1 className="mt-7 font-display text-[2rem] leading-[1.1] tracking-tight text-ink">
          {as === "creator"
            ? "Get hired on retainer"
            : "Create an account"}
        </h1>

        <p className="mt-2 text-[15px] leading-relaxed text-muted">
          {INTRO[as] ??
            "You will choose what kind of workspace to make next."}
        </p>

        <SignUpForm as={as} />
      </div>
    </main>
  );
}
