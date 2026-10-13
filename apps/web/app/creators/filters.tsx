"use client";

import { useRouter } from "next/navigation";
import type { FormEvent } from "react";

import type { Category } from "@/lib/discovery";

type Props = {
  categories: Category[];
  current: Record<string, string>;
  advanced: boolean;
};

const PLATFORMS = [
  ["instagram", "Instagram"],
  ["youtube", "YouTube"],
  ["tiktok", "TikTok"],
  ["twitter", "X"],
  ["linkedin", "LinkedIn"],
] as const;

const REACH = [
  ["", "Any reach"],
  ["10000", "10k and up"],
  ["50000", "50k and up"],
  ["100000", "100k and up"],
  ["500000", "500k and up"],
] as const;

export function Filters({ categories, current, advanced }: Props) {
  const router = useRouter();

  function submit(event: FormEvent<HTMLFormElement>) {
    // Without this the browser puts every empty field in the URL.
    // Stripping them keeps a shared link readable and keeps the
    // API from receiving a filter nobody asked for.
    event.preventDefault();

    const data = new FormData(event.currentTarget);
    const query = new URLSearchParams();

    for (const [key, value] of data.entries()) {
      const text = String(value).trim();

      if (text) query.set(key, text);
    }

    const search = query.toString();
    router.push(search ? `/creators?${search}` : "/creators");
  }

  return (
    <form
      action="/creators"
      onSubmit={submit}
      className="mt-8 border-y border-line py-4"
    >
      <div className="flex flex-wrap items-end gap-x-3 gap-y-4">
        <Select
          name="category"
          label="Beat"
          value={current.category ?? ""}
          options={[
            ["", "Any beat"],
            ...categories.map(
              (c) => [c.slug, c.name] as [string, string],
            ),
          ]}
        />

        <Select
          name="platform"
          label="Platform"
          value={current.platform ?? ""}
          options={[["", "Anywhere"], ...PLATFORMS]}
        />

        <Select
          name="min_followers"
          label="Reach"
          value={current.min_followers ?? ""}
          options={REACH}
        />

        <Field
          name="country"
          label="Country"
          value={current.country ?? ""}
          placeholder="IN"
          size={4}
        />

        <Select
          name="availability"
          label="Taking work"
          value={current.availability ?? ""}
          options={[
            ["", "Any"],
            ["available", "Yes"],
            ["limited", "Limited"],
          ]}
        />

        <button
          type="submit"
          className="h-[38px] rounded-lg bg-pine px-4 text-[14px] text-white transition-opacity hover:opacity-90"
        >
          Search
        </button>
      </div>

      <div className="mt-4 flex flex-wrap items-end gap-x-3 gap-y-4">
        <Field
          name="city"
          label="City"
          value={current.city ?? ""}
          placeholder="Pune"
          locked={!advanced}
        />

        <Field
          name="max_monthly_retainer"
          label="Budget up to"
          value={current.max_monthly_retainer ?? ""}
          placeholder="50000"
          locked={!advanced}
        />

        <Field
          name="language"
          label="Language"
          value={current.language ?? ""}
          placeholder="hi"
          size={6}
          locked={!advanced}
        />

        <Field
          name="min_engagement_rate"
          label="Engagement from"
          value={current.min_engagement_rate ?? ""}
          placeholder="5"
          size={6}
          locked={!advanced}
        />

        <label className="flex h-[38px] items-center gap-2 text-[14px]">
          <input
            type="checkbox"
            name="verified_only"
            value="true"
            defaultChecked={current.verified_only === "true"}
            disabled={!advanced}
            className="accent-pine disabled:opacity-40"
          />
          <span className={advanced ? "text-ink" : "text-muted"}>
            Verified only
          </span>
        </label>
      </div>

      {!advanced && (
        <p className="mt-3 text-[13px] text-muted">
          These five narrow the list by place, price, language and
          proof. Pro unlocks them.
        </p>
      )}
    </form>
  );
}

function Select({
  name,
  label,
  value,
  options,
}: {
  name: string;
  label: string;
  value: string;
  options: readonly (readonly [string, string])[];
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[12px] text-muted">
        {label}
      </span>
      <select
        name={name}
        defaultValue={value}
        className="h-[38px] rounded-lg border border-line bg-white px-2.5 text-[14px] text-ink outline-none focus:border-pine"
      >
        {options.map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>
            {optionLabel}
          </option>
        ))}
      </select>
    </label>
  );
}

function Field({
  name,
  label,
  value,
  placeholder,
  size = 10,
  locked = false,
}: {
  name: string;
  label: string;
  value: string;
  placeholder?: string;
  size?: number;
  locked?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[12px] text-muted">
        {label}
      </span>
      <input
        name={name}
        defaultValue={value}
        placeholder={placeholder}
        size={size}
        disabled={locked}
        className="h-[38px] rounded-lg border border-line bg-white px-2.5 text-[14px] text-ink outline-none placeholder:text-muted/60 focus:border-pine disabled:bg-paper disabled:text-muted"
      />
    </label>
  );
}
