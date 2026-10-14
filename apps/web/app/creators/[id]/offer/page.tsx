import Link from "next/link";
import { notFound } from "next/navigation";

import { Header } from "@/components/header";
import { getCreator } from "@/lib/discovery";
import { requireWorkspace } from "@/lib/session";

import { OfferForm } from "./offer-form";

export const metadata = { title: "Offer a retainer · CreatorRetain" };

export default async function OfferPage(
  props: PageProps<"/creators/[id]/offer">,
) {
  const { id } = await props.params;

  const { token, workspace, plan } = await requireWorkspace(
    `/creators/${id}/offer`,
  );

  const creator = await getCreator(token, id);

  if (!creator) {
    notFound();
  }

  const allowed = plan.capabilities.includes("create_retainer");

  return (
    <>
      <Header
        workspace={workspace}
        plan={plan}
        current="creators"
      />

      <main className="mx-auto w-full max-w-5xl flex-1 px-5 pb-24">
        <Link
          href={`/creators/${id}`}
          className="mt-10 inline-block text-[13px] text-muted underline underline-offset-4 hover:text-ink"
        >
          Back to {creator.display_name}
        </Link>

        <h1 className="mt-6 font-display text-[2.4rem] leading-[1.05] tracking-tight text-ink">
          Put {creator.display_name} on retainer
        </h1>

        {allowed ? (
          <OfferForm
            creatorWorkspaceId={creator.workspace_id}
            creatorName={creator.display_name}
            suggestedTitle={`${creator.display_name} monthly content`}
            suggestedAmount={creator.monthly_retainer_min}
            currency={creator.currency}
          />
        ) : (
          <div className="mt-6 max-w-[46ch]">
            <p className="text-[16px] leading-relaxed text-muted">
              Hiring a creator on a monthly retainer is a Pro
              feature. Your workspace can browse and read profiles
              on its current plan.
            </p>
          </div>
        )}
      </main>
    </>
  );
}
