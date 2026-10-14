import Link from "next/link";
import { notFound } from "next/navigation";

import { Header } from "@/components/header";
import { getCreator, type Rate } from "@/lib/discovery";
import { money, place, reach } from "@/lib/format";
import { countryName, languageName } from "@/lib/places";
import { requireWorkspace } from "@/lib/session";

const DELIVERABLE: Record<string, string> = {
  reel: "Reel",
  post: "Post",
  story: "Story",
  video: "Video",
  ugc: "UGC",
  editing: "Editing",
  strategy: "Strategy",
};

export default async function CreatorPage(
  props: PageProps<"/creators/[id]">,
) {
  const { id } = await props.params;

  const { token, workspace, plan } = await requireWorkspace(
    `/creators/${id}`,
  );

  const creator = await getCreator(token, id);

  if (!creator) {
    notFound();
  }

  const beat = creator.categories.map((c) => c.name).join(", ");
  const where = place(
    creator.city,
    creator.state,
    countryName(creator.country),
  );

  return (
    <>
      <Header
        workspace={workspace}
        plan={plan}
        current="creators"
      />

      <main className="mx-auto w-full max-w-5xl flex-1 px-5 pb-24">
        <Link
          href="/creators"
          className="mt-10 inline-block text-[13px] text-muted underline underline-offset-4 hover:text-ink"
        >
          All creators
        </Link>

        <div className="mt-6 border-b border-line pb-8">
          <h1 className="font-display text-[3rem] leading-[1.02] tracking-tight text-ink">
            {creator.display_name}
          </h1>

          {creator.headline && (
            <p className="mt-3 max-w-[52ch] text-[17px] leading-relaxed text-muted">
              {creator.headline}
            </p>
          )}

          <p className="mt-4 text-[13px] text-muted">
            {[beat, where].filter(Boolean).join(" · ")}
            {creator.verification_status === "verified" && (
              <span className="ml-2 text-pine">Verified</span>
            )}
          </p>
        </div>

        <div className="grid gap-12 py-10 md:grid-cols-[1fr_17rem]">
          <div className="min-w-0">
            {creator.bio && (
              <p className="max-w-[62ch] text-[16px] leading-[1.75] text-ink">
                {creator.bio}
              </p>
            )}

            <Section title="Where they post">
              <ul>
                {creator.platforms.map((account) => (
                  <li
                    key={account.platform}
                    className="flex items-baseline justify-between border-b border-line py-3.5"
                  >
                    <span className="text-[15px] text-ink">
                      {account.handle}
                      <span className="ml-2 text-[13px] text-muted">
                        on {account.platform}
                      </span>
                    </span>

                    <span className="tabular-nums text-[15px] text-ink">
                      {reach(account.followers)}
                      {account.engagement_rate && (
                        <span className="ml-3 text-[13px] text-muted">
                          {Number(account.engagement_rate)}% engaged
                        </span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </Section>

            {creator.portfolio_items.length > 0 && (
              <Section title="Work">
                <ul>
                  {creator.portfolio_items.map((item) => (
                    <li
                      key={item.title}
                      className="border-b border-line py-3.5"
                    >
                      <p className="text-[15px] text-ink">
                        {item.external_url ? (
                          <a
                            href={item.external_url}
                            target="_blank"
                            rel="noreferrer"
                            className="underline underline-offset-4 decoration-line hover:decoration-ink"
                          >
                            {item.title}
                          </a>
                        ) : (
                          item.title
                        )}
                      </p>
                      {item.description && (
                        <p className="mt-1 max-w-[58ch] text-[14px] leading-relaxed text-muted">
                          {item.description}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              </Section>
            )}

            {creator.skills.length > 0 && (
              <Section title="Does">
                <p className="text-[15px] leading-relaxed text-ink">
                  {creator.skills.join(", ")}
                </p>
              </Section>
            )}
          </div>

          <aside className="md:border-l md:border-line md:pl-8">
            <RateCard
              rates={creator.rates}
              retainer={creator.monthly_retainer_min}
              currency={creator.currency}
            />

            {creator.languages.length > 0 && (
              <div className="mt-8">
                <h2 className="text-[13px] text-muted">Speaks</h2>
                <p className="mt-1.5 text-[15px] text-ink">
                  {creator.languages.map(languageName).join(", ")}
                </p>
              </div>
            )}

            <div className="mt-8">
              <h2 className="text-[13px] text-muted">
                Taking work
              </h2>
              <p className="mt-1.5 text-[15px] text-ink">
                {creator.availability === "available"
                  ? "Yes"
                  : creator.availability === "limited"
                    ? "Limited"
                    : "Not right now"}
              </p>
            </div>

            <div className="mt-10 border-t border-line pt-6">
              {creator.can_contact ? (
                <Link
                  href={`/creators/${creator.id}/offer`}
                  className="block w-full rounded-lg bg-pine py-3 text-center text-[15px] text-white transition-opacity hover:opacity-90"
                >
                  Offer a retainer
                </Link>
              ) : (
                <p className="text-[14px] leading-relaxed text-muted">
                  Reaching out to creators is a Pro feature. Your plan
                  can browse and read profiles.
                </p>
              )}
            </div>
          </aside>
        </div>
      </main>
    </>
  );
}

function RateCard({
  rates,
  retainer,
  currency,
}: {
  rates: Rate[];
  retainer: string | null;
  currency: string;
}) {
  return (
    <div>
      <h2 className="text-[13px] text-muted">Starting rate</h2>

      <p className="mt-1.5 tabular-nums text-[1.5rem] leading-tight text-ink">
        {money(retainer, currency)}
      </p>
      <p className="text-[13px] text-muted">a month</p>

      {rates.length > 0 && (
        <ul className="mt-5">
          {rates.map((rate, index) => (
            <li
              key={`${rate.deliverable_type}-${rate.quantity}-${index}`}
              className="flex items-baseline justify-between border-t border-line py-2.5"
            >
              <span className="text-[14px] text-ink">
                {rate.quantity > 1 && `${rate.quantity} × `}
                {DELIVERABLE[rate.deliverable_type] ??
                  rate.deliverable_type}
              </span>
              <span className="tabular-nums text-[14px] text-ink">
                {money(rate.price, rate.currency)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-12">
      <h2 className="mb-1 text-[13px] text-muted">{title}</h2>
      {children}
    </section>
  );
}
