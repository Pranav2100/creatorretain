import Link from "next/link";

import { Header } from "@/components/header";
import { Live } from "@/components/live";
import { getInbox, type ConversationSummary } from "@/lib/messages";
import { getPulse } from "@/lib/pulse";
import { requireWorkspace } from "@/lib/session";

export const metadata = { title: "Messages · CreatorRetain" };

/**
 * Two piles, kept apart.
 *
 * The inbox is people you have agreed to hear from. Requests are
 * strangers asking. Nothing from the second counts towards the
 * unread badge on the first, which is the entire reason for
 * splitting them - a badge that strangers can raise is a badge
 * nobody trusts.
 */
export default async function MessagesPage(
  props: PageProps<"/messages">,
) {
  const { token, workspace, plan } =
    await requireWorkspace("/messages");

  const params = await props.searchParams;
  const showing = params.show === "requests";

  const [inbox, pulse] = await Promise.all([
    getInbox(token, showing),
    getPulse(token, { scopes: ["messages"] }),
  ]);

  return (
    <>
      <Header
        workspace={workspace}
        plan={plan}
        current="messages"
      />

      <main className="mx-auto w-full max-w-3xl flex-1 px-5 pb-24">
        <h1 className="mt-12 font-display text-[2.6rem] leading-[1.05] tracking-tight text-ink">
          Messages
        </h1>

        <nav className="mt-6 flex items-baseline gap-6 border-b border-line pb-3 text-[14px]">
          <Tab href="/messages" active={!showing}>
            Inbox
          </Tab>

          <Tab href="/messages?show=requests" active={showing}>
            Requests
            {inbox.requests_waiting > 0 && (
              <span className="ml-2 rounded-full bg-pine px-2 py-0.5 text-[11px] text-on-pine tabular-nums">
                {inbox.requests_waiting}
              </span>
            )}
          </Tab>
        </nav>

        {inbox.conversations.length === 0 ? (
          <p className="mt-8 max-w-[46ch] text-[16px] leading-relaxed text-muted">
            {showing
              ? "Nobody is waiting. Messages from people you have not spoken to before arrive here first."
              : "No conversations yet. Open a creator's page and write to them, and it will appear here."}
          </p>
        ) : (
          <ol className="mt-2">
            {inbox.conversations.map((conversation) => (
              <Row
                key={conversation.id}
                conversation={conversation}
              />
            ))}
          </ol>
        )}
      </main>

      <Live scopes={["messages"]} from={pulse} />
    </>
  );
}

function Tab({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={
        active
          ? "text-ink underline decoration-pine underline-offset-[10px]"
          : "text-muted hover:text-ink"
      }
    >
      {children}
    </Link>
  );
}

function when(value: string | null): string {
  if (!value) return "";

  const at = new Date(value);
  const now = new Date();

  const sameDay = at.toDateString() === now.toDateString();

  if (sameDay) {
    return at.toLocaleTimeString("en-GB", {
      hour: "numeric",
      minute: "2-digit",
    });
  }

  const days = Math.floor(
    (now.getTime() - at.getTime()) / 86_400_000,
  );

  if (days < 7) {
    return at.toLocaleDateString("en-GB", { weekday: "short" });
  }

  return at.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
  });
}

function Row({
  conversation,
}: {
  conversation: ConversationSummary;
}) {
  const unread = conversation.unread > 0;

  return (
    <li className="border-b border-line">
      <Link
        href={`/messages/${conversation.id}`}
        className="group flex items-baseline gap-4 py-4 outline-none focus-visible:bg-surface"
      >
        <div className="min-w-0 flex-1">
          <h2
            className={`text-[16px] leading-tight group-hover:underline group-hover:decoration-line group-hover:underline-offset-[6px] ${
              unread ? "text-ink" : "text-ink"
            }`}
          >
            {conversation.other.display_name}
          </h2>

          <p
            className={`mt-1 truncate text-[14px] ${
              unread ? "text-ink" : "text-muted"
            }`}
          >
            {conversation.preview ?? "No messages yet"}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-3">
          {unread && (
            <span className="rounded-full bg-pine px-2 py-0.5 text-[11px] tabular-nums text-on-pine">
              {conversation.unread}
            </span>
          )}

          <span className="text-[12px] tabular-nums text-muted">
            {when(conversation.last_message_at)}
          </span>
        </div>
      </Link>
    </li>
  );
}
