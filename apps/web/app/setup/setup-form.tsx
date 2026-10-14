"use client";

import { useActionState, useEffect, useState } from "react";

import { setUpWorkspace } from "@/app/actions/signup";
import { noError } from "@/lib/forms";
import { checkUsername, type UsernameCheck } from "@/lib/signup";

const KINDS = [
  {
    value: "creator",
    title: "I'm a creator",
    blurb:
      "Build a profile, get found by brands, take monthly retainers.",
  },
  {
    value: "brand",
    title: "I'm a brand",
    blurb: "Find creators and hire them on monthly retainers.",
  },
  {
    value: "agency",
    title: "I'm an agency",
    blurb: "Hire creators on behalf of the brands you represent.",
  },
] as const;

export function SetupForm({ initialKind }: { initialKind: string }) {
  const [state, action, pending] = useActionState(
    setUpWorkspace,
    noError,
  );

  const [kind, setKind] = useState(initialKind || "creator");
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [touched, setTouched] = useState(false);
  const [check, setCheck] = useState<UsernameCheck | null>(null);

  // Suggest a handle from the name until they type their own, so
  // the common case is one field rather than two.
  const handle = touched ? username : slugify(name);

  useEffect(() => {
    if (handle.length < 3) {
      setCheck(null);
      return;
    }

    // Waits for a pause in typing rather than asking on every
    // keystroke.
    const timer = setTimeout(() => {
      checkUsername(handle)
        .then(setCheck)
        .catch(() => setCheck(null));
    }, 400);

    return () => clearTimeout(timer);
  }, [handle]);

  return (
    <form action={action} className="mt-8">
      <fieldset>
        <legend className="text-[13px] text-muted">
          What is this workspace for
        </legend>

        <div className="mt-3 grid gap-2">
          {KINDS.map((option) => (
            <label
              key={option.value}
              className={`block cursor-pointer rounded-lg border px-4 py-3 transition-colors ${
                kind === option.value
                  ? "border-pine bg-white"
                  : "border-line hover:bg-white/60"
              }`}
            >
              <input
                type="radio"
                name="workspace_type"
                value={option.value}
                checked={kind === option.value}
                onChange={() => setKind(option.value)}
                className="sr-only"
              />
              <span className="block text-[15px] text-ink">
                {option.title}
              </span>
              <span className="mt-0.5 block text-[13px] leading-relaxed text-muted">
                {option.blurb}
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <label className="mt-7 block">
        <span className="mb-1.5 block text-[13px] text-muted">
          {kind === "creator"
            ? "Your name, as brands will see it"
            : "Workspace name"}
        </span>
        <input
          name="display_name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
          maxLength={100}
          className="w-full rounded-lg border border-line bg-white px-3 py-2.5 text-[15px] text-ink outline-none focus:border-pine"
        />
      </label>

      <label className="mt-4 block">
        <span className="mb-1.5 block text-[13px] text-muted">
          Handle
        </span>
        <input
          name="username"
          value={handle}
          onChange={(event) => {
            setTouched(true);
            setUsername(event.target.value.toLowerCase());
          }}
          required
          minLength={3}
          maxLength={30}
          className="w-full rounded-lg border border-line bg-white px-3 py-2.5 text-[15px] text-ink outline-none focus:border-pine"
        />

        {check && handle.length >= 3 && (
          <span
            className={`mt-1.5 block text-[13px] ${
              check.available ? "text-pine" : "text-muted"
            }`}
          >
            {check.available
              ? `${handle} is free`
              : check.message}
            {!check.available && check.suggestions.length > 0 && (
              <span className="ml-1">
                Try{" "}
                {check.suggestions.slice(0, 3).map((suggestion, i) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => {
                      setTouched(true);
                      setUsername(suggestion);
                    }}
                    className="text-ink underline underline-offset-4"
                  >
                    {suggestion}
                    {i < Math.min(2, check.suggestions.length - 1)
                      ? ", "
                      : ""}
                  </button>
                ))}
              </span>
            )}
          </span>
        )}
      </label>

      {kind !== "creator" && (
        <label className="mt-4 block">
          <span className="mb-1.5 block text-[13px] text-muted">
            Registered company name, if you have one
          </span>
          <input
            name="legal_name"
            maxLength={200}
            className="w-full rounded-lg border border-line bg-white px-3 py-2.5 text-[15px] text-ink outline-none focus:border-pine"
          />
        </label>
      )}

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
        disabled={pending || check?.available === false}
        className="mt-6 w-full rounded-lg bg-pine py-3 text-[15px] text-white transition-opacity hover:opacity-90 disabled:opacity-60"
      >
        {pending ? "Setting up" : "Create workspace"}
      </button>

      <p className="mt-4 text-[13px] leading-relaxed text-muted">
        You can belong to one workspace at a time. This is the one
        you will work from.
      </p>
    </form>
  );
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "")
    .slice(0, 30);
}
