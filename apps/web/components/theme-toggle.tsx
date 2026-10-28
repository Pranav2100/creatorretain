"use client";

import { useEffect } from "react";

import { THEME_KEY, type Theme } from "@/lib/theme";

function current(): Theme {
  return document.documentElement.getAttribute("data-theme") === "dark"
    ? "dark"
    : "light";
}

function apply(theme: Theme): void {
  document.documentElement.setAttribute("data-theme", theme);
}

export function ThemeToggle({
  className = "",
}: {
  className?: string;
}) {
  // Until somebody picks a side, the app follows the operating
  // system - including when the operating system changes its mind
  // halfway through the evening, which is when it usually does.
  // Once they pick, their choice outranks it and this stops
  // listening to it.
  useEffect(() => {
    const os = window.matchMedia("(prefers-color-scheme: dark)");

    const follow = () => {
      let chosen: string | null = null;

      try {
        chosen = localStorage.getItem(THEME_KEY);
      } catch {
        // Blocked site data. Following the system is the only
        // option left, which is what happens next anyway.
      }

      if (chosen === "light" || chosen === "dark") {
        return;
      }

      apply(os.matches ? "dark" : "light");
    };

    os.addEventListener("change", follow);

    return () => os.removeEventListener("change", follow);
  }, []);

  const flip = () => {
    const next: Theme = current() === "dark" ? "light" : "dark";

    apply(next);

    try {
      localStorage.setItem(THEME_KEY, next);
    } catch {
      // The theme still changed; it just will not be remembered
      // next time. Better than refusing to switch at all.
    }
  };

  return (
    <button
      type="button"
      onClick={flip}
      // Not "switch to dark": the label would have to know which
      // theme is on, which the server does not. This says what
      // the control is for and reads the same either way.
      aria-label="Switch between light and dark"
      title="Switch between light and dark"
      className={`shrink-0 text-muted transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-pine ${className}`}
    >
      <Sun />
      <Moon />
    </button>
  );
}

/* Shown in light mode: press it and the lights go out. */
function Sun() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className="when-light h-[17px] w-[17px]"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
    >
      <circle cx="12" cy="12" r="4.1" />
      <path d="M12 2.4v2.3M12 19.3v2.3M2.4 12h2.3M19.3 12h2.3M5.2 5.2l1.6 1.6M17.2 17.2l1.6 1.6M18.8 5.2l-1.6 1.6M6.8 17.2l-1.6 1.6" />
    </svg>
  );
}

/* Shown in dark mode. */
function Moon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className="when-dark h-[17px] w-[17px]"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M20.5 14.3A8.6 8.6 0 1 1 9.7 3.5a6.8 6.8 0 0 0 10.8 10.8Z" />
    </svg>
  );
}
