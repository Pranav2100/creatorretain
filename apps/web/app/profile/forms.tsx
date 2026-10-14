"use client";

import { useActionState, useState } from "react";

import {
  addPortfolioItem,
  addRate,
  addSocialAccount,
  deleteItem,
  toggleVisibility,
  updateBasics,
  updateCategories,
} from "@/app/actions/profile";
import type { ContentCategory } from "@/lib/discovery";
import { noError } from "@/lib/forms";
import { languageName, type Option } from "@/lib/places";
import type { MyProfile } from "@/lib/profile";
import { regionLabel, regionsFor } from "@/lib/regions";
import { DELIVERABLE_LABEL } from "@/lib/retainers";

const OTHER = "__other__";

const PLATFORMS = [
  ["instagram", "Instagram"],
  ["youtube", "YouTube"],
  ["tiktok", "TikTok"],
  ["twitter", "X"],
  ["linkedin", "LinkedIn"],
  ["facebook", "Facebook"],
] as const;

const DELIVERABLES = [
  "reel",
  "video",
  "post",
  "story",
  "ugc",
  "editing",
  "strategy",
] as const;

function Error({ message }: { message: string | null }) {
  if (!message) return null;

  return (
    <p
      role="alert"
      className="mt-3 border-l-2 border-pine pl-3 text-[13px] leading-relaxed text-ink"
    >
      {message}
    </p>
  );
}

// Split so a control that should size to its content can reuse the
// look without the w-full. Putting w-auto after w-full in a class
// string does nothing - they are the same specificity, so the
// stylesheet order decides and w-full wins.
const field =
  "rounded-lg border border-line bg-white px-3 py-2.5 text-[15px] text-ink outline-none placeholder:text-muted/60 focus:border-pine";

const input = `w-full ${field}`;

const quiet =
  "rounded-lg border border-line bg-white px-4 py-2.5 text-[14px] text-ink transition-colors hover:border-pine disabled:opacity-60";

const loud =
  "rounded-lg bg-pine px-5 py-2.5 text-[14px] text-white transition-opacity hover:opacity-90 disabled:opacity-60";

export function BasicsForm({
  profile,
  countries,
  languages,
}: {
  profile: MyProfile;
  countries: Option[];
  languages: Option[];
}) {
  const [state, action, pending] = useActionState(
    updateBasics,
    noError,
  );

  // Controlled, so they show what is saved rather than whatever the
  // DOM happened to keep. An uncontrolled select only takes its
  // defaultValue on mount, which leaves it showing "Choose a
  // country" after a save that definitely set one.
  const [country, setCountry] = useState(profile.country ?? "");
  const [region, setRegion] = useState(profile.state ?? "");
  const [spoken, setSpoken] = useState<string[]>(profile.languages);

  const regions = regionsFor(country);

  return (
    <form action={action}>
      <label className="block">
        <span className="mb-1.5 block text-[13px] text-muted">
          Headline
        </span>
        <input
          name="headline"
          defaultValue={profile.headline ?? ""}
          maxLength={120}
          placeholder="Home cooking and street food, Pune"
          className={input}
        />
      </label>

      <label className="mt-4 block">
        <span className="mb-1.5 block text-[13px] text-muted">
          Bio
        </span>
        <textarea
          name="bio"
          rows={4}
          defaultValue={profile.bio ?? ""}
          placeholder="What you make, who it is for, how long you have been at it."
          className={`${input} resize-y leading-relaxed`}
        />
      </label>

      {/* Country, then the region inside it, then the city inside
          that. Narrowing down in that order is how an address is
          written and how the region list knows what to offer. */}
      <div className="mt-4 flex flex-wrap gap-3">
        <label className="block min-w-[12rem] flex-1">
          <span className="mb-1.5 block text-[13px] text-muted">
            Country
          </span>
          <select
            name="country"
            value={country}
            onChange={(event) => {
              setCountry(event.target.value);
              // Maharashtra is not a thing in the UK. Changing
              // country throws away a region that no longer exists.
              setRegion("");
            }}
            className={input}
          >
            <option value="">Choose a country</option>
            {countries.map((option) => (
              <option key={option.code} value={option.code}>
                {option.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block min-w-[12rem] flex-1">
          <span className="mb-1.5 block text-[13px] text-muted">
            {regionLabel(country)}
          </span>

          {regions.length > 0 ? (
            <select
              name="state"
              value={region}
              onChange={(event) => setRegion(event.target.value)}
              className={input}
            >
              <option value="">
                Choose a {regionLabel(country).toLowerCase()}
              </option>
              {regions.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          ) : (
            // No trustworthy list for this country, so let them
            // type rather than offer a dropdown missing their home.
            <input
              name="state"
              value={region}
              onChange={(event) => setRegion(event.target.value)}
              maxLength={100}
              placeholder={
                country ? "Type it in" : "Pick a country first"
              }
              disabled={!country}
              className={`${input} disabled:bg-transparent disabled:text-muted`}
            />
          )}
        </label>

        <label className="block min-w-[10rem] flex-1">
          <span className="mb-1.5 block text-[13px] text-muted">
            City
          </span>
          <input
            name="city"
            defaultValue={profile.city ?? ""}
            maxLength={100}
            placeholder="Pune"
            className={input}
          />
        </label>
      </div>

      <LanguagePicker
        options={languages}
        spoken={spoken}
        onChange={setSpoken}
      />

      <label className="mt-4 block">
        <span className="mb-1.5 block text-[13px] text-muted">
          What you do
        </span>
        <input
          name="skills"
          defaultValue={profile.skills.join(", ")}
          placeholder="recipe development, food styling"
          className={input}
        />
      </label>

      <div className="mt-4 flex flex-wrap gap-3">
        <label className="block w-48">
          <span className="mb-1.5 block text-[13px] text-muted">
            Starting monthly rate
          </span>
          <input
            name="monthly_retainer_min"
            type="number"
            min={0}
            step={1}
            defaultValue={
              profile.monthly_retainer_min
                ? Math.round(Number(profile.monthly_retainer_min))
                : ""
            }
            className={`${input} tabular-nums`}
          />
          <span className="mt-1 block text-[12px] text-muted">
            The least you would take for a month of work
          </span>
        </label>

        <label className="block w-24">
          <span className="mb-1.5 block text-[13px] text-muted">
            Currency
          </span>
          <input
            name="currency"
            defaultValue={profile.currency}
            maxLength={3}
            className={`${input} uppercase`}
          />
        </label>

        <label className="block w-44">
          <span className="mb-1.5 block text-[13px] text-muted">
            Taking work
          </span>
          <select
            name="availability"
            defaultValue={profile.availability}
            className={input}
          >
            <option value="available">Yes</option>
            <option value="limited">Limited</option>
            <option value="unavailable">Not right now</option>
          </select>
        </label>
      </div>

      <Error message={state.error} />

      <button type="submit" disabled={pending} className={`${loud} mt-5`}>
        {pending ? "Saving" : "Save"}
      </button>
    </form>
  );
}

const MAX_LANGUAGES = 12;

/**
 * Languages, picked from a list with a way out of it.
 *
 * Thirty-five codes do not cover a country with more than a hundred
 * living languages, so "Other" is not a nicety here - without it a
 * creator who works in Tulu has no honest answer to give. Chosen
 * languages are chips rather than a second list, so the question
 * "what have I said?" is answered by looking.
 */
function LanguagePicker({
  options,
  spoken,
  onChange,
}: {
  options: Option[];
  spoken: string[];
  onChange: (next: string[]) => void;
}) {
  const [typing, setTyping] = useState(false);
  const [draft, setDraft] = useState("");

  const full = spoken.length >= MAX_LANGUAGES;

  function add(raw: string) {
    // Commas separate the list in the payload, so they cannot
    // survive inside one entry.
    const text = raw.replace(/,/g, " ").trim().replace(/\s+/g, " ");

    if (!text || full) return;

    // Someone typing "Hindi" into Other means "hi", not a second
    // entry sitting next to it.
    const known = options.find(
      (option) => option.name.toLowerCase() === text.toLowerCase(),
    );

    const value = known ? known.code : text;

    if (
      spoken.some((item) => item.toLowerCase() === value.toLowerCase())
    ) {
      return;
    }

    onChange([...spoken, value]);
  }

  const unpicked = options.filter(
    (option) => !spoken.includes(option.code),
  );

  return (
    <fieldset className="mt-5">
      <legend className="text-[13px] text-muted">
        Languages you work in
      </legend>

      <input type="hidden" name="languages" value={spoken.join(",")} />

      {spoken.length > 0 && (
        <ul className="mt-2.5 flex flex-wrap gap-2">
          {spoken.map((value) => (
            <li key={value}>
              <button
                type="button"
                onClick={() =>
                  onChange(spoken.filter((item) => item !== value))
                }
                aria-label={`Remove ${languageName(value)}`}
                className="group flex items-baseline gap-2 rounded-lg border border-pine bg-white px-3 py-1.5 text-[14px] text-ink"
              >
                {languageName(value)}
                <span
                  aria-hidden="true"
                  className="text-muted group-hover:text-ink"
                >
                  ×
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-2.5 flex flex-wrap items-start gap-2">
        <select
          value=""
          disabled={full}
          onChange={(event) => {
            const picked = event.target.value;

            if (picked === OTHER) {
              setTyping(true);
              return;
            }

            if (picked) add(options.find((o) => o.code === picked)!.name);
          }}
          className={`${field} min-w-[13rem] disabled:text-muted`}
        >
          <option value="">
            {spoken.length > 0 ? "Add another" : "Add a language"}
          </option>

          {unpicked.map((option) => (
            <option key={option.code} value={option.code}>
              {option.name}
            </option>
          ))}

          <option value={OTHER}>Other…</option>
        </select>

        {typing && (
          <span className="flex items-start gap-2">
            <input
              value={draft}
              autoFocus
              maxLength={40}
              placeholder="Tulu, Bhojpuri, Sign language"
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                // Enter here means "add this one", not "save the
                // whole profile".
                if (event.key !== "Enter") return;

                event.preventDefault();
                add(draft);
                setDraft("");
              }}
              className={`${field} min-w-[13rem]`}
            />

            <button
              type="button"
              onClick={() => {
                add(draft);
                setDraft("");
                setTyping(false);
              }}
              className={quiet}
            >
              Add
            </button>
          </span>
        )}
      </div>

      {full && (
        <p className="mt-2 text-[12px] text-muted">
          That is as many as a brand will read. Remove one to swap it.
        </p>
      )}
    </fieldset>
  );
}

export function CategoriesForm({
  profile,
  categories,
}: {
  profile: MyProfile;
  categories: ContentCategory[];
}) {
  const [state, action, pending] = useActionState(
    updateCategories,
    noError,
  );

  const [chosen, setChosen] = useState<string[]>(
    profile.categories
      .map((c) => categories.find((all) => all.slug === c.slug)?.id)
      .filter((id): id is string => Boolean(id)),
  );

  const full = chosen.length >= 5;

  return (
    <form action={action}>
      <div className="flex flex-wrap gap-2">
        {categories.map((category) => {
          const on = chosen.includes(category.id);

          return (
            <label
              key={category.id}
              className={`cursor-pointer rounded-lg border px-3 py-1.5 text-[14px] transition-colors ${
                on
                  ? "border-pine bg-white text-ink"
                  : full
                    ? "border-line text-muted/60"
                    : "border-line text-muted hover:bg-white"
              }`}
            >
              <input
                type="checkbox"
                name="category_ids"
                value={category.id}
                checked={on}
                disabled={!on && full}
                onChange={(event) =>
                  setChosen(
                    event.target.checked
                      ? [...chosen, category.id]
                      : chosen.filter((id) => id !== category.id),
                  )
                }
                className="sr-only"
              />
              {category.name}
            </label>
          );
        })}
      </div>

      <p className="mt-3 text-[13px] text-muted">
        {chosen.length} of 5 picked.{" "}
        {full
          ? "Unpick one to swap it."
          : "Brands search by these."}
      </p>

      <Error message={state.error} />

      <button type="submit" disabled={pending} className={`${loud} mt-4`}>
        {pending ? "Saving" : "Save beats"}
      </button>
    </form>
  );
}

export function AddSocialForm() {
  const [state, action, pending] = useActionState(
    addSocialAccount,
    noError,
  );

  return (
    <form action={action} className="mt-4">
      <div className="flex flex-wrap gap-3">
        <label className="block w-40">
          <span className="mb-1.5 block text-[13px] text-muted">
            Platform
          </span>
          <select name="platform" className={input}>
            {PLATFORMS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <label className="block min-w-[9rem] flex-1">
          <span className="mb-1.5 block text-[13px] text-muted">
            Handle
          </span>
          <input name="handle" placeholder="ninacooks" className={input} />
        </label>

        <label className="block w-36">
          <span className="mb-1.5 block text-[13px] text-muted">
            Followers
          </span>
          <input
            name="claimed_followers"
            type="number"
            min={0}
            placeholder="48200"
            className={`${input} tabular-nums`}
          />
        </label>

        <label className="block w-32">
          <span className="mb-1.5 block text-[13px] text-muted">
            Engagement %
          </span>
          <input
            name="claimed_engagement_rate"
            type="number"
            min={0}
            max={100}
            step="0.1"
            placeholder="4.3"
            className={`${input} tabular-nums`}
          />
        </label>
      </div>

      <Error message={state.error} />

      <button type="submit" disabled={pending} className={`${quiet} mt-4`}>
        {pending ? "Adding" : "Add account"}
      </button>
    </form>
  );
}

export function AddRateForm({ currency }: { currency: string }) {
  const [state, action, pending] = useActionState(addRate, noError);

  return (
    <form action={action} className="mt-4">
      <div className="flex flex-wrap gap-3">
        <label className="block w-40">
          <span className="mb-1.5 block text-[13px] text-muted">
            For
          </span>
          <select name="deliverable_type" className={input}>
            {DELIVERABLES.map((value) => (
              <option key={value} value={value}>
                {DELIVERABLE_LABEL[value]}
              </option>
            ))}
          </select>
        </label>

        <label className="block w-28">
          <span className="mb-1.5 block text-[13px] text-muted">
            How many
          </span>
          <input
            name="quantity"
            type="number"
            min={1}
            defaultValue={1}
            className={`${input} tabular-nums`}
          />
        </label>

        <label className="block w-36">
          <span className="mb-1.5 block text-[13px] text-muted">
            Price
          </span>
          <input
            name="price"
            type="number"
            min={1}
            className={`${input} tabular-nums`}
          />
        </label>

        <input type="hidden" name="currency" value={currency} />

        <label className="block min-w-[9rem] flex-1">
          <span className="mb-1.5 block text-[13px] text-muted">
            Note
          </span>
          <input
            name="notes"
            placeholder="Up to 60 seconds"
            className={input}
          />
        </label>
      </div>

      <Error message={state.error} />

      <button type="submit" disabled={pending} className={`${quiet} mt-4`}>
        {pending ? "Adding" : "Add rate"}
      </button>
    </form>
  );
}

export function AddPortfolioForm() {
  const [state, action, pending] = useActionState(
    addPortfolioItem,
    noError,
  );

  return (
    <form action={action} className="mt-4">
      <div className="flex flex-wrap gap-3">
        <label className="block min-w-[12rem] flex-1">
          <span className="mb-1.5 block text-[13px] text-muted">
            Title
          </span>
          <input
            name="title"
            placeholder="Street food series, Pune"
            className={input}
          />
        </label>

        <label className="block min-w-[12rem] flex-1">
          <span className="mb-1.5 block text-[13px] text-muted">
            Link
          </span>
          <input
            name="external_url"
            type="url"
            placeholder="https://instagram.com/p/..."
            className={input}
          />
        </label>
      </div>

      <label className="mt-3 block">
        <span className="mb-1.5 block text-[13px] text-muted">
          What it was
        </span>
        <input
          name="description"
          placeholder="Six reels for a regional brand"
          className={input}
        />
      </label>

      <Error message={state.error} />

      <button type="submit" disabled={pending} className={`${quiet} mt-4`}>
        {pending ? "Adding" : "Add piece"}
      </button>
    </form>
  );
}

export function DeleteButton({
  kind,
  id,
  label,
}: {
  kind: "social-accounts" | "portfolio" | "rates";
  id: string;
  label: string;
}) {
  const [state, action, pending] = useActionState(
    deleteItem,
    noError,
  );

  return (
    <form action={action} className="inline">
      <input type="hidden" name="kind" value={kind} />
      <input type="hidden" name="id" value={id} />

      <button
        type="submit"
        disabled={pending}
        aria-label={label}
        className="text-[13px] text-muted underline underline-offset-4 hover:text-ink disabled:opacity-60"
      >
        {pending ? "Removing" : "Remove"}
      </button>

      {state.error && (
        <span className="ml-2 text-[13px] text-ink">
          {state.error}
        </span>
      )}
    </form>
  );
}

export function VisibilityToggle({ hidden }: { hidden: boolean }) {
  const [state, action, pending] = useActionState(
    toggleVisibility,
    noError,
  );

  return (
    <form action={action}>
      <input
        type="hidden"
        name="hide"
        value={hidden ? "false" : "true"}
      />

      <button type="submit" disabled={pending} className={quiet}>
        {pending
          ? "Saving"
          : hidden
            ? "Show my profile again"
            : "Hide my profile"}
      </button>

      <Error message={state.error} />
    </form>
  );
}
