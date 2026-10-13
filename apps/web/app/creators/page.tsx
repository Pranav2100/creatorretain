import Link from "next/link";
import { redirect } from "next/navigation";

import { Header } from "@/components/header";
import { Filters } from "@/app/creators/filters";
import {
  isBlocked,
  listCategories,
  searchCreators,
  type CreatorCard,
} from "@/lib/discovery";
import { money, place, reach } from "@/lib/format";
import { requireToken } from "@/lib/session";
import { getWorkspaceContext } from "@/lib/workspace";

export const metadata = { title: "Creators · CreatorRetain" };

// Everything the search endpoint accepts. Anything else in the URL
// is ignored rather than passed through.
const FILTERS = [
  "category",
  "platform",
  "min_followers",
  "max_followers",
  "country",
  "availability",
  "city",
  "language",
  "max_monthly_retainer",
  "min_engagement_rate",
  "verified_only",
] as const;

function readFilters(
  params: Awaited<PageProps<"/creators">["searchParams"]>,
): Record<string, string> {
  const current: Record<string, string> = {};

  for (const key of FILTERS) {
    const value = params[key];
    const text = Array.isArray(value) ? value[0] : value;

    if (typeof text === "string" && text.trim()) {
      current[key] = text.trim();
    }
  }

  return current;
}

export default async function CreatorsPage(
  props: PageProps<"/creators">,
) {
  const token = await requireToken("/creators");
  const context = await getWorkspaceContext(token);

  if (!context) {
    // The token outlived its 30 minutes. Sending them to sign in
    // beats showing a page of errors they cannot do anything about.
    redirect("/login?next=/creators");
  }

  const { workspace, plan } = context;
  const params = await props.searchParams;
  const current = readFilters(params);

  const query = new URLSearchParams(current);
  const [result, categories] = await Promise.all([
    searchCreators(token, query),
    listCategories(),
  ]);

  const advanced = plan.capabilities.includes("advanced_filters");
  const filtered = Object.keys(current).length > 0;

  return (
    <>
      <Header workspace={workspace} plan={plan} current="creators" />

      <main className="mx-auto w-full max-w-5xl flex-1 px-5 pb-24">
        <h1 className="mt-12 font-display text-[2.6rem] leading-[1.05] tracking-tight text-ink">
          Creators
        </h1>

        <Filters
          categories={categories}
          current={current}
          advanced={advanced}
        />

        {isBlocked(result) ? (
          <Locked message={result.blocked} />
        ) : (
          <>
            <p className="mt-5 text-[13px] text-muted">
              {result.total_matching === 0
                ? "Nobody matches that yet."
                : `${result.total_matching} ${
                    result.total_matching === 1 ? "creator" : "creators"
                  }${filtered ? " match" : " published"}`}
            </p>

            {result.results.length === 0 ? (
              <Empty filtered={filtered} />
            ) : (
              <>
                <div className="mt-1 flex items-baseline gap-4 border-b border-line pb-2 text-[12px] text-muted">
                  <span className="flex-1">Creator</span>
                  <span className="w-20 text-right sm:w-24">Reach</span>
                  <span className="w-24 text-right sm:w-28">
                    From, a month
                  </span>
                </div>

                <ol>
                  {result.results.map((creator) => (
                    <Row key={creator.id} creator={creator} />
                  ))}
                </ol>
              </>
            )}

            {result.capped && (
              <Stub
                hidden={result.total_matching - result.returned}
                shown={result.returned}
              />
            )}
          </>
        )}
      </main>
    </>
  );
}

function Row({ creator }: { creator: CreatorCard }) {
  const beat = creator.categories.map((c) => c.name).join(", ");
  const where = place(creator.city, creator.country);

  return (
    <li className="border-b border-line">
      <Link
        href={`/creators/${creator.id}`}
        className="group flex items-baseline gap-4 py-5 outline-none focus-visible:bg-white"
      >
        <div className="min-w-0 flex-1">
          <h2 className="font-display text-[1.45rem] leading-tight tracking-tight text-ink group-hover:underline group-hover:decoration-line group-hover:underline-offset-[6px]">
            {creator.display_name}
          </h2>

          <p className="mt-1 truncate text-[14px] text-muted">
            {creator.headline ?? beat}
          </p>

          <p className="mt-1.5 text-[13px] text-muted">
            {[beat, where].filter(Boolean).join(" · ")}
            {creator.verification_status === "verified" && (
              <span className="ml-2 text-pine">Verified</span>
            )}
            {creator.is_boosted && (
              <span className="ml-2 text-pine">Promoted</span>
            )}
          </p>
        </div>

        <div className="w-20 shrink-0 text-right tabular-nums sm:w-24">
          <span className="text-[15px] text-ink">
            {reach(creator.top_followers)}
          </span>
          <span className="mt-1 block text-[12px] text-muted">
            {creator.platforms[0]?.platform ?? "no account"}
          </span>
        </div>

        <div className="w-24 shrink-0 text-right tabular-nums sm:w-28">
          <span className="text-[15px] text-ink">
            {money(creator.monthly_retainer_min, creator.currency)}
          </span>
        </div>
      </Link>
    </li>
  );
}

/**
 * What a capped plan is not being shown.
 *
 * The true total is already known, so the honest thing is to say
 * how many are missing rather than pretend the list ended.
 */
function Stub({
  hidden,
  shown,
}: {
  hidden: number;
  shown: number;
}) {
  return (
    <div className="mt-7 border-t border-dashed border-line pt-5">
      <p className="text-[15px] text-ink">
        {hidden} more {hidden === 1 ? "creator matches" : "creators match"},
        not shown.
      </p>
      <p className="mt-1 max-w-[46ch] text-[14px] leading-relaxed text-muted">
        Free shows the first {shown} of any search. Pro shows every
        result and unlocks the filters above.
      </p>
    </div>
  );
}

function Locked({ message }: { message: string }) {
  return (
    <div className="mt-10 max-w-[46ch]">
      <h2 className="font-display text-[1.6rem] leading-tight text-ink">
        Not on this plan
      </h2>
      <p className="mt-2 text-[15px] leading-relaxed text-muted">
        {message}
      </p>
    </div>
  );
}

function Empty({ filtered }: { filtered: boolean }) {
  return (
    <div className="mt-10 max-w-[46ch]">
      <p className="text-[15px] leading-relaxed text-muted">
        {filtered
          ? "No creator matches every filter. Widen one and search again."
          : "No creator has published a profile yet."}
      </p>
    </div>
  );
}
