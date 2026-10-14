const SYMBOL: Record<string, string> = {
  INR: "₹",
  USD: "$",
  EUR: "€",
  GBP: "£",
  AED: "AED ",
  SGD: "S$",
};

/**
 * Reach, shortened the way media kits write it.
 *
 * 48,200 reads as 48.2k because that is how a creator describes
 * themselves and how a buyer compares two of them at a glance.
 */
export function reach(value: number | null): string {
  if (value === null) return "—";

  if (value >= 1_000_000) {
    return `${trim(value / 1_000_000)}m`;
  }

  if (value >= 1_000) {
    return `${trim(value / 1_000)}k`;
  }

  return String(value);
}

function trim(value: number): string {
  const rounded = value >= 100 ? Math.round(value) : Math.round(value * 10) / 10;

  return String(rounded);
}

export function money(
  amount: string | null,
  currency: string,
): string {
  if (amount === null) return "—";

  const value = Number(amount);

  if (Number.isNaN(value)) return "—";

  const symbol = SYMBOL[currency] ?? `${currency} `;

  return symbol + value.toLocaleString("en-IN", {
    maximumFractionDigits: 0,
  });
}

/**
 * A location as one line, narrowest part first.
 *
 * State sits in the middle because that is where it belongs in an
 * address, and an empty one is skipped rather than leaving a gap:
 * most countries outside the list in lib/regions have nothing
 * sensible to put there.
 */
export function place(
  city: string | null,
  state: string | null,
  country: string | null,
): string {
  return [city, state, country].filter(Boolean).join(", ");
}
