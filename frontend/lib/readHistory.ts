/**
 * The articles this device opened recently, newest first - how Discover
 * personalises a reader who has no account (ADR 0015).
 *
 * A cookie rather than localStorage, so the server can rank For You from it
 * on the first request. It holds article ids and nothing else, and it exists
 * only with analytics consent. Unlike "Make it yours", which is the reader's
 * own stated preference, this is observed reading, which is what consent
 * covers. The server reads it per request and stores nothing from it;
 * withdrawing consent deletes it (lib/consent.ts).
 */
export const READ_HISTORY_COOKIE = "jn_reads";
export const MAX_READ_HISTORY = 30;

export function parseReadHistory(value: string | undefined): number[] {
  if (!value) return [];
  const ids: number[] = [];
  for (const part of value.split(".")) {
    const id = Number(part);
    if (Number.isSafeInteger(id) && id > 0 && !ids.includes(id)) ids.push(id);
  }
  return ids.slice(0, MAX_READ_HISTORY);
}

/** The history with `articleId` moved to the front. */
export function withRead(history: number[], articleId: number): number[] {
  return [articleId, ...history.filter((id) => id !== articleId)].slice(0, MAX_READ_HISTORY);
}

/** Dot-separated: a cookie value needs no escaping that way. */
export function serialiseReadHistory(history: number[]): string {
  return history.join(".");
}
