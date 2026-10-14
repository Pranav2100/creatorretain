/**
 * Countries and languages as pickable lists.
 *
 * The API stores ISO codes - "IN", "mr" - which is right for a
 * database and wrong for a person. Nobody should have to know that
 * Marathi is "mr" to say they speak it, so the codes stay in the
 * payload and names go on the screen.
 *
 * Names come from Intl rather than a hand-written table, so they
 * are spelled the way the browser spells them everywhere else.
 */

export type Option = { code: string; name: string };

// ISO 3166-1 alpha-2.
const COUNTRY_CODES = [
  "AE", "AF", "AL", "AM", "AO", "AR", "AT", "AU", "AZ", "BA",
  "BD", "BE", "BG", "BH", "BN", "BO", "BR", "BT", "BW", "BY",
  "CA", "CH", "CL", "CM", "CN", "CO", "CR", "CU", "CY", "CZ",
  "DE", "DK", "DO", "DZ", "EC", "EE", "EG", "ES", "ET", "FI",
  "FJ", "FR", "GB", "GE", "GH", "GR", "GT", "HK", "HR", "HU",
  "ID", "IE", "IL", "IN", "IQ", "IR", "IS", "IT", "JM", "JO",
  "JP", "KE", "KH", "KR", "KW", "KZ", "LB", "LK", "LT", "LU",
  "LV", "MA", "MD", "ME", "MK", "MM", "MN", "MT", "MU", "MV",
  "MX", "MY", "MZ", "NA", "NG", "NL", "NO", "NP", "NZ", "OM",
  "PA", "PE", "PH", "PK", "PL", "PT", "PY", "QA", "RO", "RS",
  "RU", "RW", "SA", "SE", "SG", "SI", "SK", "SN", "TH", "TN",
  "TR", "TT", "TW", "TZ", "UA", "UG", "US", "UY", "UZ", "VE",
  "VN", "YE", "ZA", "ZM", "ZW",
];

// ISO 639-1. India first, because that is where this starts, then
// the languages a creator here is most likely to also work in.
const LANGUAGE_CODES = [
  "en", "hi", "mr", "bn", "ta", "te", "kn", "ml", "gu", "pa",
  "ur", "or", "as", "ne", "si", "ar", "zh", "ja", "ko", "id",
  "ms", "th", "vi", "ru", "de", "fr", "es", "pt", "it", "nl",
  "tr", "fa", "sw", "pl", "uk",
];

function named(codes: string[], type: "region" | "language"): Option[] {
  let display: Intl.DisplayNames | null = null;

  try {
    display = new Intl.DisplayNames(["en"], { type });
  } catch {
    display = null;
  }

  return codes.map((code) => ({
    code,
    name: display?.of(code) ?? code,
  }));
}

export function countries(): Option[] {
  return named(COUNTRY_CODES, "region").sort((a, b) =>
    a.name.localeCompare(b.name),
  );
}

/**
 * Left in the order above rather than sorted: the languages a
 * creator on this platform is most likely to pick should not be
 * scattered through an alphabetical list of thirty-five.
 */
export function languages(): Option[] {
  return named(LANGUAGE_CODES, "language");
}

/**
 * A stored language value as a person would read it.
 *
 * Most values are ISO codes from the list above. Some are whatever
 * the creator typed into "Other", because thirty-five codes do not
 * cover everyone and a profile that cannot say "Tulu" is worse than
 * one that stores an unrecognised string. Intl throws on anything
 * that is not a structurally valid tag, so the raw text falls
 * through unchanged.
 */
export function languageName(value: string): string {
  if (!isLanguageCode(value)) return value;

  try {
    return (
      new Intl.DisplayNames(["en"], { type: "language" }).of(value) ??
      value
    );
  } catch {
    return value;
  }
}

/** "IN" is right for a database and wrong on a profile. */
export function countryName(code: string | null): string | null {
  if (!code) return null;

  try {
    return (
      new Intl.DisplayNames(["en"], { type: "region" }).of(code) ??
      code
    );
  } catch {
    return code;
  }
}

/** Two or three letters, the shape of every ISO 639-1 and -2 code. */
export function isLanguageCode(value: string): boolean {
  return /^[a-z]{2,3}$/i.test(value);
}
