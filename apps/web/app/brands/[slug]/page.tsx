import Link from "next/link";
import { notFound } from "next/navigation";

import { Header } from "@/components/header";
import { getBrand, reviewSpeed, since } from "@/lib/brands";
import { requireWorkspace } from "@/lib/session";

export default async function BrandPage(
  props: PageProps<"/brands/[slug]">,
) {
  const { slug } = await props.params;

  const { token, workspace, plan } = await requireWorkspace(
    `/brands/${slug}`,
  );

  const brand = await getBrand(token, slug);

  if (!brand) {
    notFound();
  }

  const record = brand.track_record;
  const speed = reviewSpeed(record.typical_review_hours);
  const yours = brand.slug === workspace.slug;

  return (
    <>
      <Header workspace={workspace} plan={plan} />

      <main className="mx-auto w-full max-w-3xl flex-1 px-5 pb-24">
        {yours && (
          <p className="mt-8 border-l-2 border-pine pl-3 text-[14px] leading-relaxed text-muted">
            This is your page, as a creator sees it.{" "}
            <Link
              href="/settings"
              className="text-ink underline underline-offset-4"
            >
              Change what it says
            </Link>
            .
          </p>
        )}

        <div className="mt-10 flex items-start gap-5">
          {brand.logo_url && (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={brand.logo_url}
              alt=""
              className="h-16 w-16 shrink-0 rounded-lg border border-line object-cover"
            />
          )}

          <div className="min-w-0">
            <h1 className="font-display text-[2.4rem] leading-[1.05] tracking-tight text-ink">
              {brand.display_name}
            </h1>

            <p className="mt-2 text-[14px] text-muted">
              <span className="capitalize">
                {brand.workspace_type}
              </span>
              {brand.legal_name && ` · ${brand.legal_name}`}
              {brand.verification_status === "verified" && (
                <span className="ml-2 text-pine">Verified</span>
              )}
            </p>
          </div>
        </div>

        {brand.bio ? (
          <p className="mt-7 max-w-[58ch] text-[16px] leading-relaxed text-ink">
            {brand.bio}
          </p>
        ) : (
          <p className="mt-7 max-w-[58ch] text-[15px] leading-relaxed text-muted">
            They have not written anything about themselves yet.
          </p>
        )}

        {brand.website_url && (
          <a
            href={brand.website_url}
            target="_blank"
            rel="noreferrer"
            className="mt-4 inline-block text-[15px] underline decoration-line underline-offset-4 hover:decoration-ink"
          >
            {tidy(brand.website_url)}
          </a>
        )}

        {/* The half they cannot write themselves. Everything below
            is counted from what actually happened on the platform,
            which is the only part of this page a bad actor cannot
            simply type in. */}
        <section className="mt-12 border-t border-line pt-7">
          <h2 className="font-display text-[1.5rem] leading-tight tracking-tight text-ink">
            What we can see
          </h2>
          <p className="mt-1 mb-6 max-w-[58ch] text-[14px] leading-relaxed text-muted">
            Counted from their retainers on CreatorRetain. Nobody
            can edit these.
          </p>

          <dl className="flex flex-wrap gap-x-12 gap-y-6">
            <Fact label="On retainer right now">
              {record.live_retainers === 0
                ? "Nobody"
                : `${record.live_retainers} ${
                    record.live_retainers === 1
                      ? "creator"
                      : "creators"
                  }`}
            </Fact>

            <Fact label="Creators they have worked with">
              {record.creators_worked_with === 0
                ? "None yet"
                : record.creators_worked_with}
            </Fact>

            <Fact label="Here for">{since(record.member_since)}</Fact>

            <Fact label="Reviews work">
              {speed ?? "Not enough work reviewed yet"}
            </Fact>
          </dl>

          {speed && (
            <p className="mt-6 max-w-[58ch] text-[13px] leading-relaxed text-muted">
              Based on the last {record.reviews_counted}{" "}
              {record.reviews_counted === 1 ? "review" : "reviews"},
              measured from the moment work was submitted. The middle
              one, so a single forgotten review does not flatter or
              punish them.
            </p>
          )}

          {!speed && record.reviews_counted > 0 && (
            <p className="mt-6 max-w-[58ch] text-[13px] leading-relaxed text-muted">
              {record.reviews_counted} so far. We would rather say
              nothing than turn {record.reviews_counted} into a
              pattern.
            </p>
          )}
        </section>

        <p className="mt-12 max-w-[58ch] text-[14px] leading-relaxed text-muted">
          Something look wrong? Everything above except the counted
          figures is written by {brand.display_name} themselves.
        </p>
      </main>
    </>
  );
}

/** A web address reads better without the scheme shouting at you. */
function tidy(url: string): string {
  return url.replace(/^https?:\/\//, "").replace(/\/$/, "");
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
      <dt className="text-[13px] text-muted">{label}</dt>
      <dd className="mt-1 text-[17px] text-ink">{children}</dd>
    </div>
  );
}
