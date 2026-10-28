"use client";

import { useEffect } from "react";

import { markThreadRead } from "@/app/actions/messages";

/**
 * Marks the thread read once it is actually on screen.
 *
 * This used to happen inside the page's server render, which is
 * the wrong place for anything that changes something: a server
 * component re-renders whenever the live poller refreshes the
 * route, and Next renders it again when it prefetches a link to
 * it. Both are things nobody asked for, and both would clear
 * somebody's unread count.
 *
 * An effect runs only when the page is genuinely mounted in
 * front of a person. `newest` is the last message's id, so a
 * message arriving while the thread is open re-marks it - which
 * is right, because they are looking at it.
 */
export function MarkRead({
  conversationId,
  newest,
}: {
  conversationId: string;
  newest: string | null;
}) {
  useEffect(() => {
    markThreadRead(conversationId).catch(() => {
      // A read mark that fails to save is not worth interrupting
      // somebody mid-conversation over. The next open sets it.
    });
  }, [conversationId, newest]);

  return null;
}
