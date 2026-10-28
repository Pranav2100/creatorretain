/**
 * Shared shape for the server actions that back a form.
 *
 * Deliberately not in the "use server" files: those may only
 * export async functions, so a plain constant alongside them
 * breaks the page at runtime rather than at build time.
 */
export type FormState = {
  error: string | null;

  /**
   * Said back after something worked.
   *
   * Most forms here need none: the page re-renders and the new
   * value is on screen, which is confirmation enough. This is
   * for the changes that leave nothing visible behind - a
   * password, which cannot be shown back to prove it took.
   */
  done?: string;
};

export const noError: FormState = { error: null };
