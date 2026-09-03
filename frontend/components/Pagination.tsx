import Link from "next/link";

import { t, type LocaleCode } from "@/lib/i18n";

export interface PaginationProps {
  locale: LocaleCode;
  /**
   * The page's own URL with every query parameter it needs except `cursor` -
   * `/en/search?q=climate`, say. The cursor is appended here rather than
   * assembled by each caller, so no page can drop a filter on the way to
   * page two.
   */
  baseHref: string;
  /**
   * From the API response, where the field is both nullable and optional.
   * Either absence means the same thing: this is the last page.
   */
  nextCursor: string | null | undefined;
  /** True once the reader is past the first page. */
  onLaterPage: boolean;
}

/**
 * Cursor pagination, as plain links.
 *
 * Offset pagination is prohibited (CLAUDE.md) and a ranked feed could not use
 * it anyway: the ranking changes between requests, so page two by offset
 * would repeat and skip items. The cursor names a position in a specific
 * result set instead.
 *
 * Server-rendered anchors rather than a client "load more": every one of
 * these surfaces already renders on the server, and a link costs no
 * JavaScript, works before hydration, and can be opened in a new tab. The
 * roadmap's prefetched client-side buffer is a latency optimisation for the
 * personalised feed specifically, and it belongs with the work that measures
 * regional latency - not in the fix that stops the feed dead-ending at 24.
 */
export function Pagination({ locale, baseHref, nextCursor, onLaterPage }: PaginationProps) {
  if (!nextCursor && !onLaterPage) return null;

  const separator = baseHref.includes("?") ? "&" : "?";
  const nextHref = nextCursor
    ? `${baseHref}${separator}cursor=${encodeURIComponent(nextCursor)}`
    : null;

  return (
    <nav className="pagination" aria-label={t(locale, "pagination.label")}>
      {nextHref && (
        <Link className="button button--primary" href={nextHref}>
          {t(locale, "pagination.next")}
        </Link>
      )}
      {/* Cursor pagination has no page numbers to go back through, so the way
          out is the top of the run rather than a previous page. */}
      {onLaterPage && (
        <Link className="button button--secondary" href={baseHref}>
          {t(locale, "pagination.latest")}
        </Link>
      )}
    </nav>
  );
}
