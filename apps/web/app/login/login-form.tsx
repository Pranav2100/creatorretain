"use client";

import Link from "next/link";
import { useActionState } from "react";

import { signIn } from "@/app/actions/session";
import { noError } from "@/lib/forms";

export function LoginForm({ next }: { next: string }) {
  const [state, action, pending] = useActionState(signIn, noError);

  return (
    <form action={action} className="mt-10">
      <input type="hidden" name="next" value={next} />

      <label className="block">
        <span className="mb-1.5 block text-[13px] text-muted">
          Email
        </span>
        <input
          name="email"
          type="email"
          autoComplete="email"
          required
          className="w-full rounded-lg border border-line bg-paper px-3 py-2.5 text-[15px] text-ink outline-none transition-colors focus:border-pine focus:bg-surface"
        />
      </label>

      <label className="mt-4 block">
        <span className="mb-1.5 block text-[13px] text-muted">
          Password
        </span>
        <input
          name="password"
          type="password"
          autoComplete="current-password"
          required
          className="w-full rounded-lg border border-line bg-paper px-3 py-2.5 text-[15px] text-ink outline-none transition-colors focus:border-pine focus:bg-surface"
        />
      </label>

      {state.error && (
        <p
          role="alert"
          className="mt-4 border-l-2 border-pine pl-3 text-[13px] leading-relaxed text-ink"
        >
          {state.error}
        </p>
      )}

      <button
        type="submit"
        disabled={pending}
        className="mt-6 w-full rounded-lg bg-pine py-3 text-[15px] text-on-pine transition-opacity hover:opacity-90 disabled:opacity-60"
      >
        {pending ? "Signing in" : "Sign in"}
      </button>

      {/* The mirror of the one on /signup. Somebody who has not
          got an account yet was being asked to guess the URL. */}
      <p className="mt-5 text-center text-[13px] text-muted">
        New here?{" "}
        <Link
          href="/signup"
          className="text-ink underline underline-offset-4"
        >
          Create an account
        </Link>
      </p>
    </form>
  );
}
