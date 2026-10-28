"use client";

import Link from "next/link";
import { useActionState } from "react";

import { signUp } from "@/app/actions/signup";
import { noError } from "@/lib/forms";

export function SignUpForm({ as }: { as: string }) {
  const [state, action, pending] = useActionState(signUp, noError);

  return (
    <form action={action} className="mt-8">
      <input type="hidden" name="workspace_type" value={as} />

      <div className="flex gap-3">
        <Field
          name="first_name"
          label="First name"
          autoComplete="given-name"
        />
        <Field
          name="last_name"
          label="Last name"
          autoComplete="family-name"
        />
      </div>

      <Field
        name="email"
        label="Email"
        type="email"
        autoComplete="email"
        className="mt-4"
      />

      <Field
        name="password"
        label="Password"
        type="password"
        autoComplete="new-password"
        className="mt-4"
        hint="At least 8 characters, with a number and a symbol."
      />

      <Field
        name="confirm_password"
        label="Password again"
        type="password"
        autoComplete="new-password"
        className="mt-4"
      />

      {state.error && (
        <p
          role="alert"
          className="mt-5 border-l-2 border-pine pl-3 text-[13px] leading-relaxed text-ink"
        >
          {state.error}
        </p>
      )}

      <button
        type="submit"
        disabled={pending}
        className="mt-6 w-full rounded-lg bg-pine py-3 text-[15px] text-on-pine transition-opacity hover:opacity-90 disabled:opacity-60"
      >
        {pending ? "Creating your account" : "Create account"}
      </button>

      <p className="mt-5 text-center text-[13px] text-muted">
        Already here?{" "}
        <Link
          href="/login"
          className="text-ink underline underline-offset-4"
        >
          Sign in
        </Link>
      </p>
    </form>
  );
}

function Field({
  name,
  label,
  type = "text",
  autoComplete,
  className = "",
  hint,
}: {
  name: string;
  label: string;
  type?: string;
  autoComplete?: string;
  className?: string;
  hint?: string;
}) {
  return (
    <label className={`block flex-1 ${className}`}>
      <span className="mb-1.5 block text-[13px] text-muted">
        {label}
      </span>
      <input
        name={name}
        type={type}
        autoComplete={autoComplete}
        required
        className="w-full rounded-lg border border-line bg-surface px-3 py-2.5 text-[15px] text-ink outline-none transition-colors focus:border-pine"
      />
      {hint && (
        <span className="mt-1 block text-[12px] text-muted">
          {hint}
        </span>
      )}
    </label>
  );
}
