"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError } from "@/lib/api";
import { noError, type FormState } from "@/lib/forms";
import {
  acceptRequest,
  blockWorkspace,
  declineRequest,
  markRead,
  sendMessage,
} from "@/lib/messages";
import { requireToken } from "@/lib/session";

function failed(caught: unknown): FormState {
  if (caught instanceof ApiError) {
    return { error: caught.message };
  }

  return { error: "Could not reach the server. Is the API running?" };
}

export async function say(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const token = await requireToken();

  const body = String(formData.get("body") ?? "").trim();
  const conversationId = String(
    formData.get("conversation_id") ?? "",
  );
  const toWorkspaceId = String(
    formData.get("to_workspace_id") ?? "",
  );

  if (!body) {
    return { error: "Write something first." };
  }

  let landed: string = conversationId;

  try {
    const thread = await sendMessage(token, {
      body,
      conversation_id: conversationId || undefined,
      to_workspace_id: conversationId
        ? undefined
        : toWorkspaceId || undefined,
    });

    landed = thread.id;
  } catch (caught) {
    return failed(caught);
  }

  revalidatePath("/messages");
  revalidatePath(`/messages/${landed}`);

  // A first message opens a thread that did not exist, so the
  // page the person is on is not the one they now want.
  if (!conversationId) {
    redirect(`/messages/${landed}`);
  }

  return noError;
}

export async function letThemIn(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const token = await requireToken();
  const id = String(formData.get("conversation_id") ?? "");

  try {
    await acceptRequest(token, id);
  } catch (caught) {
    return failed(caught);
  }

  revalidatePath("/messages");
  revalidatePath(`/messages/${id}`);

  return noError;
}

export async function turnThemAway(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const token = await requireToken();
  const id = String(formData.get("conversation_id") ?? "");

  try {
    await declineRequest(token, id);
  } catch (caught) {
    return failed(caught);
  }

  revalidatePath("/messages");

  // The thread is gone from their side, so staying on it would
  // leave them looking at something that no longer exists.
  redirect("/messages");
}

export async function blockThem(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const token = await requireToken();

  const workspaceId = String(formData.get("workspace_id") ?? "");
  const reason = String(formData.get("reason") ?? "").trim();

  try {
    await blockWorkspace(token, workspaceId, reason || undefined);
  } catch (caught) {
    return failed(caught);
  }

  revalidatePath("/messages");

  redirect("/messages");
}

export async function markThreadRead(id: string): Promise<void> {
  const token = await requireToken();

  await markRead(token, id);

  // The header's count is rendered on every page, so clearing a
  // thread has to invalidate more than the thread.
  revalidatePath("/", "layout");
}
