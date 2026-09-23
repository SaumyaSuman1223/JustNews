/**
 * "Make it yours": the topics a reader picked, before or without an account.
 *
 * A cookie, not localStorage, so the server can render For You from them on
 * the first request. It holds topic ids and nothing else - no identity, no
 * history - which is why it needs no consent: it is the reader's own stated
 * preference, stored so the page can honour it (the same footing as the
 * display-preference cookies). Signed in with access, a choice also becomes
 * topic follows, which the personal ranker reads.
 */
export const INTERESTS_COOKIE = "jn_interests";
/** Set once the reader saves or dismisses the card, so it stops asking. */
export const INTERESTS_DISMISSED_COOKIE = "jn_interests_done";
export const MAX_INTERESTS = 12;

const TOPIC_ID = /^medtop:\d{8}$/;

export function parseInterests(value: string | undefined): string[] {
  if (!value) return [];
  const ids: string[] = [];
  for (const part of value.split(",")) {
    const id = part.trim();
    if (TOPIC_ID.test(id) && !ids.includes(id)) ids.push(id);
  }
  return ids.slice(0, MAX_INTERESTS);
}
