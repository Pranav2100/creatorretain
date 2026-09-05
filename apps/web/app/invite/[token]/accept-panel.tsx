"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { acceptByToken, login, register } from "@/lib/api";

type Props = {
  token: string;
  email: string;
  workspace: string;
  requiresSignup: boolean;
};

export function AcceptPanel({
  token,
  email,
  workspace,
  requiresSignup,
}: Props) {
  const router = useRouter();

  const [signup, setSignup] = useState(requiresSignup);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    setError(null);

    if (signup && (!firstName.trim() || !lastName.trim())) {
      setError("Enter your first and last name.");
      return;
    }

    if (!password) {
      setError("Enter a password.");
      return;
    }

    if (signup && password !== confirm) {
      setError("Those passwords do not match.");
      return;
    }

    setBusy(true);

    try {
      if (signup) {
        await register({
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          email,
          password,
          confirm_password: confirm,
        });
      }

      const accessToken = await login(email, password);
      await acceptByToken(token, accessToken);

      window.localStorage.setItem("access_token", accessToken);
      router.push("/");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Something went wrong. Try again.",
      );
      setBusy(false);
    }
  }

  return (
    <div>
      <p className="mb-5 text-[13px] text-muted">
        Joining as <span className="text-ink">{email}</span>
      </p>

      <div className="space-y-3">
        {signup && (
          <div className="flex gap-3">
            <Field
              label="First name"
              value={firstName}
              onChange={setFirstName}
              autoComplete="given-name"
            />
            <Field
              label="Last name"
              value={lastName}
              onChange={setLastName}
              autoComplete="family-name"
            />
          </div>
        )}

        <Field
          label={signup ? "Choose a password" : "Password"}
          value={password}
          onChange={setPassword}
          type="password"
          autoComplete={signup ? "new-password" : "current-password"}
        />

        {signup && (
          <Field
            label="Confirm password"
            value={confirm}
            onChange={setConfirm}
            type="password"
            autoComplete="new-password"
          />
        )}
      </div>

      {error && (
        <p
          role="alert"
          className="mt-4 border-l-2 border-l-[#B4432F] pl-3 text-[13px] leading-relaxed text-[#B4432F]"
        >
          {error}
        </p>
      )}

      <button
        type="button"
        onClick={submit}
        disabled={busy}
        className="mt-6 w-full rounded-lg bg-pine px-4 py-3 text-[15px] font-medium text-white transition-colors hover:bg-[#24473a] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-pine disabled:opacity-60"
      >
        {busy ? "Joining…" : `Join ${workspace}`}
      </button>

      <button
        type="button"
        onClick={() => {
          setSignup(!signup);
          setError(null);
        }}
        className="mt-4 w-full text-[13px] text-muted underline underline-offset-4 hover:text-ink"
      >
        {signup
          ? "I already have an account"
          : "I need to create an account"}
      </button>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  autoComplete,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  autoComplete?: string;
}) {
  return (
    <label className="block flex-1">
      <span className="mb-1.5 block text-[13px] text-muted">{label}</span>
      <input
        type={type}
        value={value}
        autoComplete={autoComplete}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-line bg-paper px-3 py-2.5 text-[15px] text-ink outline-none transition-colors focus:border-pine focus:bg-white"
      />
    </label>
  );
}
