"use client";

import { useCallback, useEffect, useState, useTransition } from "react";

import { IssuePaper } from "@/components/IssuePaper";
import { ReaderUtility } from "@/components/ReaderUtility";
import type { Issue, IssueEdition, IssuePageContent } from "@/lib/api";
import { t, type LocaleCode } from "@/lib/i18n";

/**
 * Reading an issue: which page you are on, and how you turn to the next one.
 *
 * Pages are fetched one at a time through a route handler rather than shipped
 * together, because a page logs the impressions it served (ADR 0012's
 * replayability requirement) - prefetching page 7 would claim a reader saw it
 * when they never turned to it.
 *
 * Direction is a function of writing mode, not of "next means right": under
 * `dir="rtl"` a paper is turned the other way, so the arrows swap what they
 * point at. The keys follow the same rule, which is why ArrowLeft is not
 * hard-wired to "previous".
 */
export function IssueReader({
  issue,
  firstPage,
  editions,
  locale,
  dir,
}: {
  issue: Issue;
  firstPage: IssuePageContent;
  editions: IssueEdition[];
  locale: LocaleCode;
  dir: "ltr" | "rtl";
}) {
  const [pageNo, setPageNo] = useState(1);
  const [page, setPage] = useState<IssuePageContent>(firstPage);
  const [pending, startTransition] = useTransition();
  const [failed, setFailed] = useState(false);
  const [contentsOpen, setContentsOpen] = useState(false);

  const pageCount = issue.page_count;

  const goTo = useCallback(
    (next: number) => {
      if (next < 1 || next > pageCount || next === pageNo) return;
      setFailed(false);
      startTransition(async () => {
        const response = await fetch(
          `/api/issues/${issue.id}/pages/${next}?locale=${encodeURIComponent(locale)}`,
        );
        if (!response.ok) {
          setFailed(true);
          return;
        }
        setPage((await response.json()) as IssuePageContent);
        setPageNo(next);
        setContentsOpen(false);
      });
    },
    [issue.id, locale, pageCount, pageNo],
  );

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      // Ignore while someone is typing, so arrow keys in the search field do
      // not turn the page under them.
      const target = event.target as HTMLElement | null;
      if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return;
      if (event.key === "Escape") {
        setContentsOpen(false);
        return;
      }
      // A reader with no chrome needs its own shortcuts. `c` for contents is
      // the one an e-reader would use; the arrows follow writing direction,
      // which is why ArrowLeft is not hard-wired to "previous".
      if (event.key === "c" || event.key === "C") {
        setContentsOpen((open) => !open);
        return;
      }
      // §21: Home and End reach the ends of the issue. These do not mirror
      // under RTL - "first page" is the first page whichever way the paper
      // is read, unlike the arrows, which follow writing direction.
      if (event.key === "Home") {
        event.preventDefault();
        goTo(1);
        return;
      }
      if (event.key === "End") {
        event.preventDefault();
        goTo(pageCount);
        return;
      }
      const forward = dir === "rtl" ? "ArrowLeft" : "ArrowRight";
      const back = dir === "rtl" ? "ArrowRight" : "ArrowLeft";
      if (event.key === forward) goTo(pageNo + 1);
      if (event.key === back) goTo(pageNo - 1);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dir, goTo, pageNo, pageCount]);

  return (
    <div className="aquila">
      <div className="aquila__stage">
        <div className="aquila__sheet" data-pending={pending || undefined}>
          <IssuePaper issue={issue} page={page} locale={locale} onGoTo={goTo} />
        </div>

        {failed && (
          <p className="form-error" role="alert">
            {t(locale, "aquila.pageFailed")}
          </p>
        )}

        <nav
          className="aquila__controls"
          aria-label={t(locale, "aquila.pagination")}
        >
          <button
            type="button"
            className="aquila__arrow"
            onClick={() => goTo(pageNo - 1)}
            disabled={pageNo <= 1 || pending}
            aria-label={t(locale, "aquila.previous")}
          >
            <Chevron direction="back" />
          </button>
          <p className="aquila__folio" aria-live="polite">
            {t(locale, "aquila.pageOf", { page: pageNo, total: pageCount })}
          </p>
          <button
            type="button"
            className="aquila__arrow"
            onClick={() => goTo(pageNo + 1)}
            disabled={pageNo >= pageCount || pending}
            aria-label={t(locale, "aquila.next")}
          >
            <Chevron direction="forward" />
          </button>
          <button
            type="button"
            className="aquila__contents-toggle"
            onClick={() => setContentsOpen((open) => !open)}
            aria-expanded={contentsOpen}
          >
            {t(locale, "aquila.contents")}
          </button>
        </nav>
      </div>

      <ReaderUtility
        issue={issue}
        editions={editions}
        locale={locale}
        pageNo={pageNo}
        onGoTo={goTo}
        open={contentsOpen}
        onOpenChange={setContentsOpen}
      />
    </div>
  );
}

/** Points along the inline axis, so it mirrors with the document. */
function Chevron({ direction }: { direction: "back" | "forward" }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="1.1em"
      height="1.1em"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      style={{ transform: direction === "forward" ? undefined : "scaleX(-1)" }}
    >
      <path d="m9 5 7 7-7 7" />
    </svg>
  );
}
