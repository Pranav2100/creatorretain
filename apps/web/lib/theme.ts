/**
 * The theme, in the one place both sides can read it.
 *
 * Deliberately neither "use client" nor server-only. The script
 * below is built on the server and written into the document
 * head; the key is read by the toggle in the browser. Keeping
 * them in a client module meant the layout was importing a
 * client reference and calling it as a function, which the build
 * rejects - exports of a client module are not functions on the
 * server. So they live here, where neither side owns them.
 */

export const THEME_KEY = "creatorretain.theme";

export type Theme = "light" | "dark";

/**
 * Runs before anything paints.
 *
 * The page cannot be rendered in the right theme on the server:
 * which theme a person wants is in their browser, not in the
 * request. Deciding it in React instead would mean painting the
 * light theme first and correcting it a moment later, which is
 * the white flash every app with a dark mode has had at some
 * point. So this resolves the question synchronously, in the
 * head, before the body exists.
 *
 * Everything is inside a try: reading localStorage throws rather
 * than returning null in a browser with site data blocked, and a
 * theme preference is not worth a blank page.
 */
export function themeScript(): string {
  return `
(function () {
  try {
    var chosen = localStorage.getItem(${JSON.stringify(THEME_KEY)});

    if (chosen !== "light" && chosen !== "dark") {
      chosen = window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
    }

    document.documentElement.setAttribute("data-theme", chosen);
  } catch (e) {
    document.documentElement.setAttribute("data-theme", "light");
  }
})();
`.trim();
}
