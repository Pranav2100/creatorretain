import { ThemeToggle } from "./theme-toggle";

/**
 * The theme control for pages with no bar of their own - signing
 * in, the invite screen, a 404, the error page.
 *
 * Rendered once in the root layout rather than added to each of
 * those pages, and hidden by a rule in globals.css whenever the
 * page does have a bar with the control already in it. The point
 * is that a page added later is covered without anybody having to
 * remember to cover it.
 */
export function ThemeCorner() {
  return (
    <div className="theme-corner fixed top-4 right-4 z-40">
      <ThemeToggle className="rounded-full border border-line bg-surface p-2" />
    </div>
  );
}
