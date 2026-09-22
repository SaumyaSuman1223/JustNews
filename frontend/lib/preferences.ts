import { cookies } from "next/headers";

/**
 * The reader's display choices (fifth pass F8): theme and text size.
 *
 * Cookies rather than localStorage so the server can set them on <html>
 * before the first paint - no flash of the wrong theme. They hold nothing
 * about the reader beyond two display settings and never reach the API; the
 * layout already reads cookies for consent, so reading two more costs no
 * caching the page had.
 */
export const THEME_COOKIE = "jn_theme";
export const TEXT_SIZE_COOKIE = "jn_text_size";

export type ThemeChoice = "system" | "light" | "dark";
export type TextSizeChoice = "standard" | "large";

export async function getReaderPreferences(): Promise<{
  theme: ThemeChoice;
  textSize: TextSizeChoice;
}> {
  const store = await cookies();
  const theme = store.get(THEME_COOKIE)?.value;
  const textSize = store.get(TEXT_SIZE_COOKIE)?.value;
  return {
    theme: theme === "light" || theme === "dark" ? theme : "system",
    textSize: textSize === "large" ? "large" : "standard",
  };
}
