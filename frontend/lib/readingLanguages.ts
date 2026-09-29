import { isLocaleCode, type LocaleCode } from "@/lib/i18n";

/**
 * The languages a reader reads, chosen on Discover without an account.
 *
 * The interface language is the route's locale; what a reader *reads* is a
 * separate question - a Hindi speaker may want English menus and Hindi
 * headlines, or both languages in one feed. Signed in, the account's own
 * choice wins; this cookie is the answer for everyone else. It holds
 * language codes and nothing else, so, like the display cookies, it needs no
 * consent: it is the reader's stated preference, kept so the page honours it.
 */
export const READING_LANGUAGES_COOKIE = "jn_read";

export function parseReadingLanguages(value: string | undefined): LocaleCode[] {
  if (!value) return [];
  const codes: LocaleCode[] = [];
  for (const part of value.split(",")) {
    const code = part.trim();
    if (isLocaleCode(code) && !codes.includes(code)) codes.push(code);
  }
  return codes;
}
