"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { storeToken } from "@/app/actions/session";
import {
  acceptByToken,
  login,
  register,
  saveJoiningDetails,
} from "@/lib/api";

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
  const [jobTitle, setJobTitle] = useState("");
  const [phone, setPhone] = useState("");
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

    // Asked for here rather than left to a settings page nobody
    // visits: a creator weighing up an offer from this workspace
    // is shown both, so this is the moment they are worth
    // collecting.
    if (!jobTitle.trim()) {
      setError("Enter your job title at this workspace.");
      return;
    }

    if (!phone.trim()) {
      setError("Enter a phone number.");
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

      // Before accepting, not after: the workspace refuses
      // anyone it cannot introduce to a creator, so saving these
      // second would mean being turned away holding them.
      await saveJoiningDetails(accessToken, {
        job_title: jobTitle.trim(),
        phone: phone.trim(),
      });

      await acceptByToken(token, accessToken);

      // The session lives in an httpOnly cookie rather than
      // localStorage, so no script on the page can read it. Handing
      // the token to the server to store is not an escalation: it is
      // the same credential this browser just earned.
      await storeToken(accessToken);
      router.push("/creators");
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

        <Field
          label="Your job title here"
          value={jobTitle}
          onChange={setJobTitle}
          autoComplete="organization-title"
          placeholder="Talent Manager"
        />

        <Field
          label="Phone"
          value={phone}
          onChange={setPhone}
          type="tel"
          autoComplete="tel"
          placeholder="+91 98765 43210"
        />

        <p className="pt-1 text-[12px] leading-relaxed text-muted">
          Creators you work with will see your name, your title and
          how to reach you on every offer you send.
        </p>
      </div>

      {error && (
        <p
          role="alert"
          className="mt-4 border-l-2 border-l-alarm pl-3 text-[13px] leading-relaxed text-alarm"
        >
          {error}
        </p>
      )}

      <button
        type="button"
        onClick={submit}
        disabled={busy}
        className="mt-6 w-full rounded-lg bg-pine px-4 py-3 text-[15px] font-medium text-on-pine transition-colors hover:bg-pine-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-pine disabled:opacity-60"
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
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  autoComplete?: string;
  placeholder?: string;
}) {
  return (
    <label className="block flex-1">
      <span className="mb-1.5 block text-[13px] text-muted">{label}</span>
      <input
        type={type}
        value={value}
        autoComplete={autoComplete}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-line bg-paper px-3 py-2.5 text-[15px] text-ink outline-none transition-colors focus:border-pine focus:bg-surface"
      />
    </label>
  );
}
