"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { pulseQuery, type Pulse, type Watching } from "@/lib/pulse";

/**
 * Keeps a server-rendered page up to date with what everyone
 * else is doing.
 *
 * It polls two numbers and, when they move, asks Next to
 * re-render the route on the server. Nothing is fetched or
 * rendered here, which is the point: the page keeps one source
 * of truth and cannot drift into showing a banner from the poll
 * beside a status from the original render. Scroll position
 * survives, and so does anything half-typed into a form.
 *
 * Polling rather than a socket because the things being watched
 * change a handful of times a month. A connection held open per
 * tab to carry a pause request twice a quarter is a lot of
 * machinery for very little news, and this can be swapped for
 * one the day that stops being true - the pages would not have
 * to change, only this file.
 */

/** How often to ask, while the tab is in front of someone. */
const EVERY = 5000;

/** After this long with the tab hidden, stop asking entirely. */
const GIVE_UP_AFTER = 5 * 60 * 1000;

type Props = Watching & {
  /**
   * The pulse this page was rendered from.
   *
   * Passed in rather than taken from the first poll, because a
   * change landing in the second between rendering and asking
   * would otherwise become the baseline and never be noticed.
   * That window is small and entirely real: it is exactly where
   * one person clicks while the other's page is loading.
   */
  from: Pulse;
};

function mark(pulse: Pulse): string {
  return `${pulse.latest ?? ""}:${pulse.count}`;
}

export function Live({ from, ...watching }: Props) {
  const router = useRouter();

  const seen = useRef<string>(mark(from));
  const hiddenSince = useRef<number | null>(null);

  /**
   * Whether this document came back from the back-forward cache.
   *
   * It stays true for the life of the document, because the
   * client router cannot be trusted to re-render one that was
   * restored - asking it to politely does nothing. Anything this
   * page wants to show from here on has to come from a reload.
   */
  const restored = useRef(false);

  const [stale, setStale] = useState(false);

  // The query is rebuilt from the scopes rather than passed as a
  // string, so a page declares what it is showing and nothing
  // else has to agree on spelling.
  const query = pulseQuery(watching);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    async function ask() {
      if (cancelled) {
        return;
      }

      // A tab nobody is looking at does not need to be current;
      // it needs to be current by the time someone looks, which
      // the visibility handler below takes care of.
      if (document.visibilityState !== "visible") {
        const since = hiddenSince.current ?? Date.now();
        hiddenSince.current = since;

        if (Date.now() - since < GIVE_UP_AFTER) {
          timer = setTimeout(ask, EVERY);
        }

        return;
      }

      hiddenSince.current = null;

      try {
        const response = await fetch(`/api/pulse?${query}`, {
          cache: "no-store",
        });

        if (response.status === 401) {
          // Signed out. Stop; the next navigation will redirect.
          return;
        }

        const body = await response.json();

        // -1 is the server saying it could not tell. Treated as
        // "ask again", never as "nothing changed".
        if (body.count !== -1 && seen.current !== mark(body)) {
          seen.current = mark(body);

          if (restored.current) {
            window.location.reload();
            return;
          }

          setStale(true);

          router.refresh();

          // Long enough to be noticed, short enough not to sit
          // there once the new content has arrived.
          setTimeout(() => {
            if (!cancelled) {
              setStale(false);
            }
          }, 1600);
        }
      } catch {
        // Offline, or the API is restarting. Try again later.
      }

      if (!cancelled) {
        timer = setTimeout(ask, EVERY);
      }
    }

    function onVisible() {
      if (document.visibilityState === "visible") {
        clearTimeout(timer);
        ask();
      }
    }

    /**
     * Coming back with the browser's Back button.
     *
     * A page restored from the back-forward cache is a
     * photograph: no request is made, no effect runs again, and
     * what is on screen is whatever was there when the person
     * left. That is wrong anywhere, and worst on the way back
     * from paying - they leave to pay, press Back, and the page
     * tells them nothing has happened.
     *
     * Reloaded rather than refreshed, and only when something
     * really did change. router.refresh() asks the client router
     * to re-render, and the router on a restored page is part of
     * the same photograph - it was observed doing nothing here
     * while the page sat with its button still reading "Taking
     * you to pay". A reload owes nothing to that state.
     *
     * The cost of a reload is scroll position and anything
     * half-typed, which is why it is paid only when the reading
     * has moved. Coming back to a page where nothing happened
     * costs one request and changes nothing on screen.
     */
    async function onRestored(event: PageTransitionEvent) {
      if (!event.persisted || cancelled) {
        return;
      }

      restored.current = true;

      clearTimeout(timer);

      try {
        const response = await fetch(`/api/pulse?${query}`, {
          cache: "no-store",
        });

        if (response.ok) {
          const body = await response.json();

          if (body.count !== -1 && seen.current !== mark(body)) {
            window.location.reload();
            return;
          }
        }
      } catch {
        // Offline. Fall through and go back to polling.
      }

      if (!cancelled) {
        timer = setTimeout(ask, EVERY);
      }
    }

    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("pageshow", onRestored);
    timer = setTimeout(ask, EVERY);

    return () => {
      cancelled = true;
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("pageshow", onRestored);
    };
  }, [query, router]);

  // Something arriving on its own is startling without a word of
  // explanation, so the page says so briefly rather than quietly
  // rearranging itself under the reader.
  return (
    <div
      aria-live="polite"
      className={`pointer-events-none fixed bottom-5 left-1/2 z-50 -translate-x-1/2 rounded-full border border-line bg-surface px-4 py-1.5 text-[13px] text-muted shadow-sm transition-opacity duration-300 ${
        stale ? "opacity-100" : "opacity-0"
      }`}
    >
      Updated just now
    </div>
  );
}
