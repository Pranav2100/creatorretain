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

export function place(
  city: string | null,
  country: string | null,
): string {
  return [city, country].filter(Boolean).join(", ");
}
