/**
 * Shared shape for the server actions that back a form.
 *
 * Deliberately not in the "use server" files: those may only
 * export async functions, so a plain constant alongside them
 * breaks the page at runtime rather than at build time.
 */
export type FormState = { error: string | null };

export const noError: FormState = { error: null };
