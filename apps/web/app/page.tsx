import Link from "next/link";
import { redirect } from "next/navigation";

import { ThemeToggle } from "@/components/theme-toggle";
import { getToken } from "@/lib/session";
import {
  getWorkspaceContext,
  landingFor,
  NO_WORKSPACE,
} from "@/lib/workspace";

export const metadata = {
  title: "CreatorRetain · Hire creators by the month",
  description:
    "Put creators on monthly retainers instead of chasing them campaign by campaign.",
};

export default async function Home() {
  const token = await getToken();

  // Signed in, so this is not the page they want.
  if (token) {
    const context = await getWorkspaceContext(token);

    if (context === NO_WORKSPACE) redirect("/setup");
    if (context) redirect(landingFor(context.plan));
  }

  return (
    <>
      <header
        data-theme-host
        className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between px-5"
      >
        <span className="font-display text-[1.15rem] tracking-tight text-ink">
          CreatorRetain
        </span>

        <nav className="flex items-center gap-5 text-[14px]">
          <ThemeToggle />
          <Link href="/login" className="text-muted hover:text-ink">
            Sign in
          </Link>
          <Link
            href="/signup"
            className="rounded-lg bg-pine px-4 py-2 text-on-pine transition-opacity hover:opacity-90"
          >
            Get started
          </Link>
        </nav>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-5">
        <section className="pt-16 pb-20 sm:pt-24">
          <h1 className="max-w-[16ch] font-display text-[2.8rem] leading-[1.02] tracking-tight text-ink sm:text-[4.2rem]">
            Hire a creator every month, not every campaign.
          </h1>

          <p className="mt-6 max-w-[52ch] text-[17px] leading-[1.7] text-muted">
            Most brands rebuild the same relationship four times a
            year: find someone, agree a price, brief them, lose
            them. A retainer keeps it. Same creator, same rate, a
            fresh month of work that arrives on its own.
          </p>

          <div className="mt-9 flex flex-wrap items-center gap-4">
            <Link
              href="/signup?as=brand"
              className="rounded-lg bg-pine px-5 py-3 text-[15px] text-on-pine transition-opacity hover:opacity-90"
            >
              I want to hire creators
            </Link>

            <Link
              href="/signup?as=creator"
              className="rounded-lg border border-line bg-surface px-5 py-3 text-[15px] text-ink transition-colors hover:border-pine"
            >
              I&rsquo;m a creator
            </Link>
          </div>
        </section>

        {/* The agreement itself, in the product's own hand. A
            picture of the thing beats a description of it. */}
        <section className="border-y border-line py-10">
          <p className="text-[13px] text-muted">
            One retainer, as the app writes it
          </p>

          <div className="mt-5 flex flex-wrap items-baseline gap-x-10 gap-y-4">
            <Fact label="Creator">Nina Cooks</Fact>
            <Fact label="Every month">
              <span className="tabular-nums">₹40,000</span>
            </Fact>
            <Fact label="For">4 × Reel, 2 × Story</Fact>
            <Fact label="Renews on">day 12</Fact>
          </div>
        </section>

        <section className="py-20">
          <h2 className="font-display text-[2rem] leading-tight tracking-tight text-ink">
            How a retainer runs
          </h2>

          <ol className="mt-10 grid gap-10 sm:grid-cols-3">
            <Step
              month="Month 1"
              title="You agree it once"
              body="Pick a creator, say what you want every month and what you will pay. They accept, and the first month opens the same day."
            />
            <Step
              month="Month 2"
              title="It renews itself"
              body="On the same day next month a fresh set of deliverables appears, at the rate you agreed. Nobody renegotiates, nobody re-briefs."
            />
            <Step
              month="Month 3"
              title="Or it does not"
              body="Pause when a campaign goes quiet and the clock stops. End it and the record stays: every month, every piece of work, what was approved."
            />
          </ol>
        </section>

        <section className="grid gap-12 border-t border-line py-20 sm:grid-cols-2 sm:gap-16">
          <div>
            <h2 className="font-display text-[1.7rem] leading-tight tracking-tight text-ink">
              For brands and agencies
            </h2>

            <ul className="mt-5 space-y-3 text-[15px] leading-relaxed text-muted">
              <Point>
                Search creators by beat, platform, reach, language
                and what they charge.
              </Point>
              <Point>
                See a rate card before you talk to anyone.
              </Point>
              <Point>
                Approve work piece by piece, or send it back with a
                note.
              </Point>
              <Point>
                Bring your team in. Owners and admins sign
                retainers, everyone else can follow along.
              </Point>
            </ul>

            <Link
              href="/signup?as=brand"
              className="mt-7 inline-block text-[15px] text-pine underline underline-offset-4"
            >
              Start hiring
            </Link>
          </div>

          <div>
            <h2 className="font-display text-[1.7rem] leading-tight tracking-tight text-ink">
              For creators
            </h2>

            <ul className="mt-5 space-y-3 text-[15px] leading-relaxed text-muted">
              <Point>
                Income you can plan around, instead of a new pitch
                every month.
              </Point>
              <Point>
                Set your own rates and say what you are available
                for.
              </Point>
              <Point>
                Your profile goes live by itself once it is
                finished. No approval queue.
              </Point>
              <Point>
                Turn down an offer, pause a retainer, or walk away
                with notice. It is your name on it.
              </Point>
            </ul>

            <Link
              href="/signup?as=creator"
              className="mt-7 inline-block text-[15px] text-pine underline underline-offset-4"
            >
              Build your profile
            </Link>
          </div>
        </section>

        <section className="border-t border-line py-20">
          <h2 className="font-display text-[2rem] leading-tight tracking-tight text-ink">
            Free to look. Paid to hire.
          </h2>

          <p className="mt-4 max-w-[54ch] text-[16px] leading-relaxed text-muted">
            Creators are free, always. Brands and agencies browse
            free and pay when they put someone on retainer.
          </p>

          <div className="mt-9 grid gap-8 sm:grid-cols-2">
            <Tier
              name="Free"
              line="Have a look around."
              points={[
                "The first 10 results of any search",
                "Full creator profiles and rate cards",
                "Up to 10 people in your workspace",
              ]}
            />
            <Tier
              name="Pro"
              line="Actually hire someone."
              points={[
                "Every result, and filters for city, budget, language and engagement",
                "Contact creators and send retainers",
                "Campaigns and the work dashboard",
              ]}
            />
          </div>

          <p className="mt-8 text-[14px] text-muted">
            Prices are being finalised. Nothing is charged while
            that is true.
          </p>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-4 px-5 py-8 text-[13px] text-muted">
          <span className="font-display text-[1rem] text-ink">
            CreatorRetain
          </span>

          <span className="flex gap-5">
            <Link href="/login" className="hover:text-ink">
              Sign in
            </Link>
            <Link href="/signup" className="hover:text-ink">
              Create an account
            </Link>
          </span>
        </div>
      </footer>
    </>
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
      <p className="mt-0.5 text-[17px] text-ink">{children}</p>
    </div>
  );
}

function Step({
  month,
  title,
  body,
}: {
  month: string;
  title: string;
  body: string;
}) {
  return (
    <li className="border-t border-line pt-4">
      <p className="text-[13px] text-pine">{month}</p>
      <h3 className="mt-2 text-[17px] text-ink">{title}</h3>
      <p className="mt-2 text-[15px] leading-relaxed text-muted">
        {body}
      </p>
    </li>
  );
}

function Point({ children }: { children: React.ReactNode }) {
  return <li className="border-l border-line pl-4">{children}</li>;
}

function Tier({
  name,
  line,
  points,
}: {
  name: string;
  line: string;
  points: string[];
}) {
  return (
    <div className="border-t border-line pt-5">
      <h3 className="font-display text-[1.4rem] tracking-tight text-ink">
        {name}
      </h3>
      <p className="mt-1 text-[14px] text-muted">{line}</p>

      <ul className="mt-4 space-y-2.5 text-[15px] leading-relaxed text-muted">
        {points.map((point) => (
          <li key={point}>{point}</li>
        ))}
      </ul>
    </div>
  );
}
