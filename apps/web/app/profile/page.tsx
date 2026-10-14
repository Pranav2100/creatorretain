import Link from "next/link";

import { Header } from "@/components/header";
import { listCategories } from "@/lib/discovery";
import { money, place, reach } from "@/lib/format";
import { countries, countryName, languages } from "@/lib/places";
import {
  getMyProfile,
  MISSING_LABEL,
  type MyProfile,
} from "@/lib/profile";
import { requireWorkspace } from "@/lib/session";
import { DELIVERABLE_LABEL } from "@/lib/retainers";

import {
  AddPortfolioForm,
  AddRateForm,
  AddSocialForm,
  BasicsForm,
  CategoriesForm,
  DeleteButton,
  VisibilityToggle,
} from "./forms";

export const metadata = { title: "Your profile · CreatorRetain" };

export default async function ProfilePage() {
  const { token, workspace, plan } = await requireWorkspace(
    "/profile",
  );

  const [profile, categories] = await Promise.all([
    getMyProfile(token),
    listCategories(),
  ]);

  return (
    <>
      <Header workspace={workspace} plan={plan} current="profile" />

      <main className="mx-auto w-full max-w-3xl flex-1 px-5 pb-28">
        <h1 className="mt-12 font-display text-[2.6rem] leading-[1.05] tracking-tight text-ink">
          Your profile
        </h1>

        {profile === null ? (
          <p className="mt-6 max-w-[48ch] text-[16px] leading-relaxed text-muted">
            Only creator workspaces have a profile. {workspace.display_name}{" "}
            is {workspace.workspace_type === "agency" ? "an" : "a"}{" "}
            {workspace.workspace_type} workspace, which hires creators
            rather than being one.
          </p>
        ) : (
          <>
            <Standing profile={profile} />

            <Section
              title="The basics"
              note="This is what a brand reads first."
            >
              <BasicsForm
                profile={profile}
                countries={countries()}
                languages={languages()}
              />
            </Section>

            <Section
              title="Your beats"
              note="Up to five. These are what brands filter by."
            >
              <CategoriesForm
                profile={profile}
                categories={categories}
              />
            </Section>

            <Section
              title="Where you post"
              note="Follower counts are what you say they are, for now. Verification comes later."
            >
              {profile.social_accounts.length > 0 && (
                <ul className="mb-2">
                  {profile.social_accounts.map((account) => (
                    <li
                      key={account.id}
                      className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-line py-3"
                    >
                      <span className="text-[15px] text-ink">
                        {account.handle}
                        <span className="ml-2 text-[13px] text-muted">
                          on {account.platform}
                        </span>
                      </span>

                      <span className="flex items-baseline gap-4">
                        <span className="tabular-nums text-[15px] text-ink">
                          {reach(account.claimed_followers)}
                          {account.claimed_engagement_rate && (
                            <span className="ml-2 text-[13px] text-muted">
                              {Number(account.claimed_engagement_rate)}%
                            </span>
                          )}
                        </span>

                        <DeleteButton
                          kind="social-accounts"
                          id={account.id}
                          label={`Remove ${account.handle}`}
                        />
                      </span>
                    </li>
                  ))}
                </ul>
              )}

              <AddSocialForm />
            </Section>

            <Section
              title="Your rates"
              note="Optional if you have set a monthly figure, but brands like seeing the breakdown."
            >
              {profile.rates.length > 0 && (
                <ul className="mb-2">
                  {profile.rates.map((rate) => (
                    <li
                      key={rate.id}
                      className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-line py-3"
                    >
                      <span className="text-[15px] text-ink">
                        {rate.quantity > 1 && `${rate.quantity} × `}
                        {DELIVERABLE_LABEL[rate.deliverable_type]}
                        {rate.notes && (
                          <span className="ml-2 text-[13px] text-muted">
                            {rate.notes}
                          </span>
                        )}
                      </span>

                      <span className="flex items-baseline gap-4">
                        <span className="tabular-nums text-[15px] text-ink">
                          {money(rate.price, rate.currency)}
                        </span>

                        <DeleteButton
                          kind="rates"
                          id={rate.id}
                          label="Remove rate"
                        />
                      </span>
                    </li>
                  ))}
                </ul>
              )}

              <AddRateForm currency={profile.currency} />
            </Section>

            <Section
              title="Work you are proud of"
              note="Not required to publish, but it is the last five points."
            >
              {profile.portfolio_items.length > 0 && (
                <ul className="mb-2">
                  {profile.portfolio_items.map((item) => (
                    <li
                      key={item.id}
                      className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-line py-3"
                    >
                      <span className="min-w-0 text-[15px] text-ink">
                        {item.external_url ? (
                          <a
                            href={item.external_url}
                            target="_blank"
                            rel="noreferrer"
                            className="underline decoration-line underline-offset-4 hover:decoration-ink"
                          >
                            {item.title}
                          </a>
                        ) : (
                          item.title
                        )}
                        {item.description && (
                          <span className="ml-2 text-[13px] text-muted">
                            {item.description}
                          </span>
                        )}
                      </span>

                      <DeleteButton
                        kind="portfolio"
                        id={item.id}
                        label={`Remove ${item.title}`}
                      />
                    </li>
                  ))}
                </ul>
              )}

              <AddPortfolioForm />
            </Section>

            <Section
              title="Visibility"
              note="Hiding keeps everything you have written; it just takes you out of search."
            >
              <VisibilityToggle hidden={profile.is_hidden} />
            </Section>
          </>
        )}
      </main>
    </>
  );
}

/**
 * Whether they are live, and if not, what is standing in the way.
 *
 * There is no publish button in this product - a profile goes live
 * when it is finished - so this panel is the only place that fact
 * is visible. It has to be specific about what is missing or the
 * rule feels arbitrary.
 */
function Standing({ profile }: { profile: MyProfile }) {
  const missing = profile.missing_fields;
  const live = profile.is_discoverable;

  return (
    <section className="mt-8 border-y border-line py-6">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <p className="text-[17px] text-ink">
          {live
            ? "You are live in search."
            : profile.is_hidden
              ? "You are hidden from search."
              : "Not live yet."}
        </p>

        <p className="tabular-nums text-[14px] text-muted">
          {profile.completeness}% complete
        </p>
      </div>

      <div
        className="mt-3 h-px w-full bg-line"
        aria-hidden="true"
      >
        <div
          className="h-px bg-pine"
          style={{ width: `${profile.completeness}%` }}
        />
      </div>

      {missing.length > 0 ? (
        <p className="mt-4 max-w-[58ch] text-[15px] leading-relaxed text-muted">
          You go live on your own once you have added{" "}
          <span className="text-ink">
            {readable(missing.map((f) => MISSING_LABEL[f] ?? f))}
          </span>
          . There is no publish button.
        </p>
      ) : (
        <p className="mt-4 max-w-[58ch] text-[15px] leading-relaxed text-muted">
          {live ? (
            <>
              Brands can find you. Your profile is{" "}
              <Link
                href="/retainers"
                className="text-ink underline underline-offset-4"
              >
                ready for offers
              </Link>
              .
            </>
          ) : (
            "Everything required is filled in. Unhide to go back into search."
          )}
        </p>
      )}

      {profile.city && profile.country && (
        <p className="mt-2 text-[13px] text-muted">
          Shown as{" "}
          {place(
            profile.city,
            profile.state,
            countryName(profile.country),
          )}
          {profile.monthly_retainer_min &&
            ` · from ${money(profile.monthly_retainer_min, profile.currency)} a month`}
        </p>
      )}
    </section>
  );
}

function readable(items: string[]): string {
  if (items.length === 1) return items[0];

  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

function Section({
  title,
  note,
  children,
}: {
  title: string;
  note: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-12 border-t border-line pt-7">
      <h2 className="font-display text-[1.5rem] leading-tight tracking-tight text-ink">
        {title}
      </h2>
      <p className="mt-1 mb-5 max-w-[58ch] text-[14px] leading-relaxed text-muted">
        {note}
      </p>
      {children}
    </section>
  );
}
