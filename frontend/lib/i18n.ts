/**
 * Locale registry.
 *
 * i18n is structural here, not a later retrofit (ADR 0005). The two things
 * that must be right from the first component are the direction flag - which
 * drives `dir` on <html> and therefore every logical CSS property - and the
 * fact that a locale is part of the route, not a cookie. Retrofitting either
 * into a finished layout costs several times what building with them costs.
 *
 * Every locale here is currently `ltr`, and the `dir` flag is deliberately
 * kept anyway: the layout is still written entirely in logical properties, so
 * adding an RTL language back is an entry in this list rather than a
 * stylesheet fork. That is the whole point of paying the cost up front.
 *
 * This list must match `LAUNCH_LANGUAGES` in justnews_core.language. A language
 * we ingest but do not list here is content no reader can reach, and a locale
 * listed here with no source behind it is an empty page. A test on the Python
 * side reads this file and fails when the two drift apart.
 */

export const locales = [
  { code: "en", label: "English", dir: "ltr", htmlLang: "en" },
  { code: "es", label: "Español", dir: "ltr", htmlLang: "es" },
  { code: "hi", label: "हिन्दी", dir: "ltr", htmlLang: "hi" },
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

/** Locale-aware relative time, e.g. "3 hours ago" / "منذ ٣ ساعات". */
export function formatRelativeTime(iso: string, locale: LocaleCode): string {
  const seconds = Math.round((Date.parse(iso) - Date.now()) / 1000);
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 31_536_000],
    ["month", 2_592_000],
    ["day", 86_400],
    ["hour", 3_600],
    ["minute", 60],
  ];
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) return formatter.format(Math.round(seconds / size), unit);
  }
  return formatter.format(Math.round(seconds), "second");
}
