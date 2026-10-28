import { notFound, redirect } from "next/navigation";

import { Header } from "@/components/header";
import { getInbox } from "@/lib/messages";
import { requireWorkspace } from "@/lib/session";
import { API_URL } from "@/lib/api";

import { FirstMessage } from "./form";

export const metadata = { title: "New message · CreatorRetain" };

/**
 * Writing to somebody for the first time.
 *
 * If a thread already exists it sends you there instead: two
 * people have one conversation, and offering to start a second
 * would quietly split their history in half.
 */
export default async function NewMessagePage(
  props: PageProps<"/messages/new">,
) {
  const { token, workspace, plan } = await requireWorkspace(
    "/messages/new",
  );

  const params = await props.searchParams;
  const to = typeof params.to === "string" ? params.to : "";

  if (!to) {
    notFound();
  }

  if (to === workspace.id) {
    redirect("/messages");
  }

  // An existing thread wins over a new one, whichever pile it is
  // in - including a request this side has not answered yet.
  for (const requests of [false, true]) {
    const inbox = await getInbox(token, requests);
    const already = inbox.conversations.find(
      (c) => c.other.workspace_id === to,
    );

    if (already) {
      redirect(`/messages/${already.id}`);
    }
  }

  const response = await fetch(
    `${API_URL}/discovery/creators/${to}`,
    {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    },
  );

  // The name is a courtesy, not a requirement: a workspace this
  // page cannot read is still one you may write to.
  const name = response.ok
    ? ((await response.json()).display_name as string)
    : "them";

  return (
    <>
      <Header
        workspace={workspace}
        plan={plan}
        current="messages"
      />

      <main className="mx-auto w-full max-w-2xl flex-1 px-5 pb-24">
        <h1 className="mt-12 font-display text-[2.4rem] leading-[1.05] tracking-tight text-ink">
          Write to {name}
        </h1>

        <p className="mt-3 max-w-[50ch] text-[15px] leading-relaxed text-muted">
          You have not spoken before, so this arrives in their
          requests. They can accept it, ignore it, or block you —
          and until they answer you can send a couple more and no
          further.
        </p>

        <FirstMessage to={to} name={name} />
      </main>
    </>
  );
}
