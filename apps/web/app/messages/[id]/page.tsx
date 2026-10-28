import Link from "next/link";
import { notFound } from "next/navigation";

import { Header } from "@/components/header";
import { Live } from "@/components/live";
import { getThread, type ChatMessage } from "@/lib/messages";
import { getPulse } from "@/lib/pulse";
import { requireWorkspace } from "@/lib/session";

import { Composer, RequestChoice } from "./forms";
import { MarkRead } from "./mark-read";

/**
 * One conversation, newest at the bottom.
 *
 * Opening it marks it read, which is what anybody expects of a
 * message they are looking at. Done on the server during the
 * render rather than from a button, because a thread you have
 * open and have not pressed anything on is still a thread you
 * have read.
 */
export default async function ThreadPage(
  props: PageProps<"/messages/[id]">,
) {
  const { id } = await props.params;

  const { token, workspace, plan } = await requireWorkspace(
    `/messages/${id}`,
  );

  const thread = await getThread(token, id);

  if (!thread) {
    notFound();
  }

  const pulse = await getPulse(token, { scopes: ["messages"] });

  return (
    <>
      <Header
        workspace={workspace}
        plan={plan}
        current="messages"
      />

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-5 pb-10">
        <div className="mt-8 border-b border-line pb-4">
          <Link
            href="/messages"
            className="text-[13px] text-muted underline underline-offset-4 hover:text-ink"
          >
            All messages
          </Link>

          <h1 className="mt-3 font-display text-[1.9rem] leading-tight tracking-tight text-ink">
            {thread.other.display_name}
          </h1>

          {/* Only brands and agencies have a public page at
              their slug. A creator is reached through discovery,
              by a profile id this page does not hold, so rather
              than link somewhere that is not there it links
              nowhere. */}
          {thread.other.workspace_type !== "creator" && (
            <Link
              href={`/brands/${thread.other.slug}`}
              className="mt-1 inline-block text-[13px] text-muted underline underline-offset-4 hover:text-ink"
            >
              See their page
            </Link>
          )}
        </div>

        {thread.messages.length === 0 ? (
          <p className="mt-10 text-[15px] text-muted">
            Nothing said yet.
          </p>
        ) : (
          <ol className="mt-6 flex flex-col gap-3">
            {thread.messages.map((message, index) => (
              <Bubble
                key={message.id}
                message={message}
                /* The sender's name only when it changes, so a
                   run of messages from one person reads as one
                   person talking rather than a form being filled
                   in repeatedly. */
                showSender={
                  index === 0 ||
                  thread.messages[index - 1].sender_person !==
                    message.sender_person
                }
                last={index === thread.messages.length - 1}
                seenAt={thread.seen_at}
              />
            ))}
          </ol>
        )}

        {thread.is_request ? (
          <RequestChoice
            conversationId={thread.id}
            workspaceId={thread.other.workspace_id}
            name={thread.other.display_name}
          />
        ) : (
          <Composer
            conversationId={thread.id}
            name={thread.other.display_name}
            open={thread.open}
            awaitingAcceptance={
              thread.started_by_me && thread.messages.length > 0
                ? !thread.seen_at && thread.messages.every((m) => m.mine)
                : false
            }
          />
        )}
      </main>

      {/* Not for a request: reading somebody's opening line is
          not agreeing to hear from them. */}
      {!thread.is_request && (
        <MarkRead
          conversationId={thread.id}
          newest={
            thread.messages[thread.messages.length - 1]?.id ?? null
          }
        />
      )}

      <Live scopes={["messages"]} from={pulse} />
    </>
  );
}

function stamp(value: string): string {
  return new Date(value).toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

function Bubble({
  message,
  showSender,
  last,
  seenAt,
}: {
  message: ChatMessage;
  showSender: boolean;
  last: boolean;
  seenAt: string | null;
}) {
  const seen =
    last &&
    message.mine &&
    seenAt !== null &&
    new Date(seenAt) >= new Date(message.at);

  return (
    <li
      className={`flex flex-col ${
        message.mine ? "items-end" : "items-start"
      }`}
    >
      {showSender && message.sender_person && (
        <span className="mb-1 px-1 text-[12px] text-muted">
          {message.mine
            ? message.sender_person
            : `${message.sender_person} · ${message.sender_name}`}
        </span>
      )}

      <div
        className={`max-w-[42ch] rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed ${
          message.mine
            ? "rounded-br-md bg-pine text-on-pine"
            : "rounded-bl-md border border-line bg-surface text-ink"
        }`}
      >
        {/* Kept as written: somebody who pressed return twice
            meant it, and collapsing their paragraphs into one
            line changes what they said. */}
        <p className="whitespace-pre-wrap break-words">
          {message.body}
        </p>
      </div>

      <span className="mt-1 px-1 text-[11px] tabular-nums text-muted">
        {stamp(message.at)}
        {seen && <span className="ml-2">Seen</span>}
      </span>
    </li>
  );
}
