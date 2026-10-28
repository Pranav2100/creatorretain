import { redirect } from "next/navigation";

import { Header } from "@/components/header";
import { getAccount } from "@/lib/account";
import { requireWorkspace } from "@/lib/session";

import { DetailsForm, LeaveForm, PasswordForm } from "./forms";

export const metadata = { title: "Your account · CreatorRetain" };

/**
 * You, rather than the workspace you are acting for.
 *
 * Every other signed-in page in this app belongs to a workspace:
 * its settings, its profile, its retainers. This one belongs to a
 * person, which is why a member of somebody else's workspace has
 * something to open at all - before this, a member could see three
 * read-only panels and change nothing about themselves, not even a
 * surname typed wrong at signup.
 */
export default async function AccountPage() {
  const { token, workspace, plan } =
    await requireWorkspace("/account");

  const account = await getAccount(token);

  // The token resolved a workspace a moment ago, so this means it
  // has just expired rather than that anything is wrong.
  if (!account) {
    redirect("/login?next=/account");
  }

  return (
    <>
      <Header workspace={workspace} plan={plan} current="account" />

      <main className="mx-auto w-full max-w-3xl flex-1 px-5 pb-28">
        <h1 className="mt-12 font-display text-[2.6rem] leading-[1.05] tracking-tight text-ink">
          Your account
        </h1>

        <p className="mt-3 max-w-[54ch] text-[16px] leading-relaxed text-muted">
          This is you, not {workspace.display_name}. Changing it
          here changes it everywhere you sign in.
        </p>

        <Block
          title="Details"
          note="Your name as colleagues see it, and the address you sign in with."
        >
          <DetailsForm account={account} />
        </Block>

        <Block
          title="Password"
          note="Changing it signs out every other browser you are signed in on. This one stays."
        >
          <PasswordForm />
        </Block>

        {workspace.your_role !== "owner" && (
          <Block
            title="Leaving"
            note={`You were invited into ${workspace.display_name} rather than starting it.`}
          >
            <LeaveForm name={workspace.display_name} />
          </Block>
        )}

        {workspace.your_role === "owner" && (
          <Block
            title="Leaving"
            note="You started this workspace, so you cannot leave it."
          >
            <p className="max-w-[54ch] text-[14px] leading-relaxed text-muted">
              Hand {workspace.display_name} to someone else from
              Settings first, and the option will appear here.
            </p>
          </Block>
        )}
      </main>
    </>
  );
}

function Block({
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
