/**
 * Locale registry.
 *
 * Duplicated from frontend/lib/i18n.ts rather than shared through a package:
 * it's fifty lines, and a new JS workspace package for that is over-
 * engineering for a first mobile slice. It MUST be kept in sync with
 * frontend/lib/i18n.ts and, ultimately, LAUNCH_LANGUAGES in
 * justnews_core.language - packages/core/tests/test_launch_languages.py
 * guards the web side of that; there is no equivalent guard for mobile yet.
 */

export const locales = [
  { code: "en", label: "English", htmlLang: "en" },
  { code: "es", label: "Español", htmlLang: "es" },
  { code: "hi", label: "हिन्दी", htmlLang: "hi" },
] as const;

export type Locale = (typeof locales)[number];
export type LocaleCode = Locale["code"];

export const defaultLocale: LocaleCode = "en";

export function isLocaleCode(value: string): value is LocaleCode {
  return locales.some((locale) => locale.code === value);
}

export function getLocale(code: string): Locale {
  return locales.find((locale) => locale.code === code) ?? locales[0];
}

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 31_536_000],
  ["month", 2_592_000],
  ["day", 86_400],
  ["hour", 3_600],
  ["minute", 60],
];

/**
 * Hand-rolled, English-only fallback for engines with no
 * Intl.RelativeTimeFormat - confirmed missing on at least one real Android
 * device's Hermes build in this slice's own device testing (crashed with
 * "undefined cannot be used as a constructor"), unlike the web preview's V8,
 * which has it. RN's Hermes ships a reduced ICU subset that doesn't always
 * include the newer Intl APIs, and which subset varies by build - the web
 * app has no equivalent gap since browsers can be relied on for this one.
 * English-only is an acceptable floor right now because defaultLocale is the
 * only locale this slice ever calls this with (language switching is
 * deferred) - it stops being acceptable the moment that changes.
 */
function formatRelativeTimeFallback(seconds: number): string {
  const future = seconds > 0;
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size) {
      const value = Math.round(Math.abs(seconds) / size);
      const plural = value === 1 ? unit : `${unit}s`;
      return future ? `in ${value} ${plural}` : `${value} ${plural} ago`;
    }
  }
  return future ? "in a moment" : "just now";
}

/** Locale-aware relative time, e.g. "3 hours ago". */
export function formatRelativeTime(iso: string, locale: LocaleCode): string {
  const seconds = Math.round((Date.parse(iso) - Date.now()) / 1000);
  if (typeof Intl.RelativeTimeFormat !== "function") {
    return formatRelativeTimeFallback(seconds);
  }
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size) return formatter.format(Math.round(seconds / size), unit);
  }
  return formatter.format(Math.round(seconds), "second");
}
