import type { Article } from "@/lib/api";
import type { RankReason } from "@/lib/rankReason";

/**
 * Which feed Discover is showing. Shared by the server (which renders the
 * first page) and the client (which switches views and scrolls for more), so
 * the two agree on what a URL means.
 *
 * - For You: `/{locale}`. The personal ranker for a reader with it; the
 *   reader's chosen interests otherwise; Top when there are neither.
 * - Top: `/{locale}?view=top`. What matters now, for everyone.
 * - A topic: `/{locale}?topic=medtop:...`.
 */
export type DiscoverView =
  | { kind: "for-you" }
  | { kind: "top" }
  | { kind: "topic"; topicId: string };

export interface DiscoverItem {
  article: Article;
  /** The impression this card was served under, for click attribution;
   * null wherever nothing was logged. */
  impressionId: number | null;
  why: RankReason | null;
}

export interface DiscoverPage {
  items: DiscoverItem[];
  nextCursor: string | null;
  degraded: boolean;
}

/** Topic ids are IPTC concept ids; anything else is not a topic. */
const TOPIC_ID = /^medtop:\d{8}$/;

export function parseView(params: {
  view?: string | null;
  topic?: string | null;
}): DiscoverView {
  if (params.topic && TOPIC_ID.test(params.topic)) {
    return { kind: "topic", topicId: params.topic };
  }
  if (params.view === "top") return { kind: "top" };
  return { kind: "for-you" };
}

export function viewKey(view: DiscoverView): string {
  return view.kind === "topic" ? `topic:${view.topicId}` : view.kind;
}

export function viewHref(locale: string, view: DiscoverView): string {
  if (view.kind === "top") return `/${locale}?view=top`;
  if (view.kind === "topic") return `/${locale}?topic=${encodeURIComponent(view.topicId)}`;
  return `/${locale}`;
}

export function viewQuery(view: DiscoverView): URLSearchParams {
  const query = new URLSearchParams();
  if (view.kind === "top") query.set("view", "top");
  if (view.kind === "topic") query.set("topic", view.topicId);
  return query;
}
