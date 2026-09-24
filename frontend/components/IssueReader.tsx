"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  useSyncExternalStore,
  useTransition,
} from "react";
import type { CSSProperties, PointerEvent as ReactPointerEvent } from "react";

import { IssuePaper } from "@/components/IssuePaper";
import { ReaderUtility } from "@/components/ReaderUtility";
import type { Issue, IssueEdition, IssuePageContent } from "@/lib/api";
import { t, type LocaleCode } from "@/lib/i18n";

/** A deliberate swipe, not a graze - a common mobile-gallery convention, and
 * short enough to feel responsive without firing on an incidental touch. */
const SWIPE_THRESHOLD_PX = 56;

/**
 * The width every page is composed at. A page is laid out once at this
 * width and then scaled to fit the screen, the way a PDF viewer shows a
 * whole page - so the composition never depends on the window, and nothing
 * on it is ever cut off by the edge of the sheet (the fixed 3:2 box this
 * replaced clipped the deck and the rail at most window sizes).
 */
const DESIGN_WIDTH_PX = 1240;
/** A big screen may enlarge the page, but only so far - past this the type
 * reads as a poster rather than a paper. */
const MAX_SCALE = 1.35;
/** Below this width a page is not scaled at all: a phone reads one sheet at
 * full width and scrolls inside it, which is what a narrow screen is for. */
const FIT_QUERY = "(min-width: 64rem)";
/** Room kept clear around the sheet for its stacked edge and shadow. */
const FIT_MARGIN_PX = 20;
/**
 * The same measurement as the layout effect below, run inline as soon as the
 * stage has been parsed. Set the design width first, then read the height
 * the page has at that width, then scale - the order the effect reaches in
 * two passes.
 */
const FIT_SCRIPT = `(function(){
var stage=document.currentScript&&document.currentScript.parentElement;
if(!stage||!window.matchMedia("${FIT_QUERY}").matches)return;
var viewport=stage.querySelector(".aquila__viewport"),box=stage.querySelector(".aquila__fit-box"),book=stage.querySelector(".aquila__book");
if(!viewport||!box||!book)return;
box.style.setProperty("--fit-width","${DESIGN_WIDTH_PX}px");
box.style.setProperty("--fit-scale","1");
box.style.setProperty("--fit-height",book.offsetHeight+"px");
box.setAttribute("data-fit","");
var height=book.offsetHeight;
var scale=Math.min((viewport.clientWidth-${FIT_MARGIN_PX * 2})/${DESIGN_WIDTH_PX},(viewport.clientHeight-${FIT_MARGIN_PX * 2})/height,${MAX_SCALE});
box.style.setProperty("--fit-scale",String(scale));
box.style.setProperty("--fit-height",height+"px");
})()`;

/** Matches `--dur-turn` in globals.css; the fallback that ends a turn if the
 * animation never reports back (a hidden tab does not run it). */
const TURN_MS = 900;

type Turn = {
  /** The page the leaf carries - the old page going forward, the new one
   * coming back. */
  leaf: IssuePageContent;
  /** The page lying underneath while the leaf moves. */
  under: IssuePageContent;
  direction: "forward" | "back";
  id: number;
};

function subscribeFullscreen(onChange: () => void): () => void {
  document.addEventListener("fullscreenchange", onChange);
  return () => document.removeEventListener("fullscreenchange", onChange);
}

const noSubscribe = () => () => {};

/**
 * Reading an issue: which page you are on, and how you turn to the next one.
 *
 * Pages are fetched one at a time through a route handler rather than shipped
 * together, because a page logs the impressions it served (ADR 0012's
 * replayability requirement) - prefetching page 7 would claim a reader saw it
 * when they never turned to it.
 *
 * A turn is a leaf, not a fade: the page lifts from its outer edge and folds
 * over the spine, with the next page lying underneath it. Going back, the
 * previous page folds in from the spine the other way. Under reduced motion
 * there is no leaf at all - the page simply changes.
 *
 * Direction is a function of writing mode, not of "next means right": under
 * `dir="rtl"` a paper is turned the other way, so the arrows swap what they
 * point at and the leaf folds toward the right. The keys follow the same
 * rule, which is why ArrowLeft is not hard-wired to "previous".
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
  const [turn, setTurn] = useState<Turn | null>(null);
  const [fit, setFit] = useState<{ scale: number; height: number } | null>(null);

  const viewportRef = useRef<HTMLDivElement>(null);
  const bookRef = useRef<HTMLDivElement>(null);
  const turnCount = useRef(0);

  const isFullscreen = useSyncExternalStore(
    subscribeFullscreen,
    () => document.fullscreenElement !== null,
    () => false,
  );
  // iOS Safari has no Fullscreen API for documents; the button is simply
  // not offered there rather than offered and doing nothing.
  const canFullscreen = useSyncExternalStore(
    noSubscribe,
    () => document.fullscreenEnabled === true,
    () => false,
  );

  const pageCount = issue.page_count;
  const turning = turn !== null;

  const toggleFullscreen = useCallback(() => {
    if (document.fullscreenElement) {
      void document.exitFullscreen();
    } else {
      void document.documentElement.requestFullscreen().catch(() => {
        // Refused (an iframe without permission, a browser setting). The
        // reader works exactly as before, just not full screen.
      });
    }
  }, []);

  const goTo = useCallback(
    (next: number) => {
      if (next < 1 || next > pageCount || next === pageNo || turning) return;
      setFailed(false);
      startTransition(async () => {
        const response = await fetch(
          `/api/issues/${issue.id}/pages/${next}?locale=${encodeURIComponent(locale)}`,
        );
        if (!response.ok) {
          setFailed(true);
          return;
        }
        const incoming = (await response.json()) as IssuePageContent;
        const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        if (!still) {
          const direction = next > pageNo ? "forward" : "back";
          turnCount.current += 1;
          setTurn({
            leaf: direction === "forward" ? page : incoming,
            under: direction === "forward" ? incoming : page,
            direction,
            id: turnCount.current,
          });
        }
        setPage(incoming);
        setPageNo(next);
        setContentsOpen(false);
        // A narrow screen scrolls inside a page; the next one starts at its
        // top, the way turning a real page does.
        if (!window.matchMedia(FIT_QUERY).matches) window.scrollTo({ top: 0 });
      });
    },
    [issue.id, locale, page, pageCount, pageNo, turning],
  );

  // The end of a turn: the leaf is gone and the new page is the only page.
  // A timer as well as `animationend`, because a background tab never runs
  // the animation and the leaf must not be left standing over the page.
  useEffect(() => {
    if (!turn) return;
    const timer = window.setTimeout(() => setTurn(null), TURN_MS + 250);
    return () => window.clearTimeout(timer);
  }, [turn]);

  // Scale the page to fit whatever room the screen has. Measured, not
  // computed from the viewport, because the page's height is its content's:
  // a front page with a long lead is taller than a section page, and it is
  // the whole of it that has to fit.
  useLayoutEffect(() => {
    const viewport = viewportRef.current;
    const book = bookRef.current;
    if (!viewport || !book) return;
    const query = window.matchMedia(FIT_QUERY);

    function measure() {
      if (!viewport || !book) return;
      if (!query.matches) {
        setFit(null);
        return;
      }
      const height = book.offsetHeight;
      const scale = Math.min(
        (viewport.clientWidth - FIT_MARGIN_PX * 2) / DESIGN_WIDTH_PX,
        (viewport.clientHeight - FIT_MARGIN_PX * 2) / height,
        MAX_SCALE,
      );
      setFit((current) =>
        current && Math.abs(current.scale - scale) < 0.001 && current.height === height
          ? current
          : { scale, height },
      );
    }

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(viewport);
    observer.observe(book);
    query.addEventListener("change", measure);
    return () => {
      observer.disconnect();
      query.removeEventListener("change", measure);
    };
  }, []);

  // §11/§40's "swipeable Aquila pages": a horizontal drag of the finger
  // turns the page, the same way the arrow keys and buttons already do.
  // Scoped to `pointerType === "touch"` so mouse users - selecting text,
  // clicking a headline - are entirely unaffected; the mouse has the page
  // corners instead.
  const swipeStart = useRef<{ x: number; y: number } | null>(null);

  const onSwipeStart = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.pointerType !== "touch") return;
    swipeStart.current = { x: event.clientX, y: event.clientY };
  }, []);

  const onSwipeEnd = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      const start = swipeStart.current;
      swipeStart.current = null;
      if (event.pointerType !== "touch" || !start) return;

      const deltaX = event.clientX - start.x;
      const deltaY = event.clientY - start.y;
      // Must be a clearly horizontal gesture, well past an accidental
      // twitch - mobile Aquila still scrolls vertically inside a page
      // (§38), and a swipe recognised too eagerly would fight that scroll
      // instead of living beside it.
      if (Math.abs(deltaX) < SWIPE_THRESHOLD_PX || Math.abs(deltaX) < Math.abs(deltaY) * 1.5) {
        return;
      }
      // Same mirroring the keyboard arrows already do: swiping the content
      // toward the start of the writing direction turns forward, whichever
      // way that points under `dir`.
      const swipedTowardStart = deltaX < 0;
      const forward = dir === "rtl" ? !swipedTowardStart : swipedTowardStart;
      goTo(forward ? pageNo + 1 : pageNo - 1);
    },
    [dir, goTo, pageNo],
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
      if ((event.key === "f" || event.key === "F") && !event.metaKey && !event.ctrlKey) {
        toggleFullscreen();
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
  }, [dir, goTo, pageNo, pageCount, toggleFullscreen]);

  const fitStyle: CSSProperties | undefined = fit
    ? ({
        "--fit-scale": fit.scale,
        "--fit-width": `${DESIGN_WIDTH_PX}px`,
        "--fit-height": `${fit.height}px`,
      } as CSSProperties)
    : undefined;

  const under = turn ? turn.under : page;

  return (
    <div className="aquila">
      <div className="aquila__stage">
        <div className="aquila__viewport" ref={viewportRef}>
          {/* suppressHydrationWarning: FIT_SCRIPT below sets this box's
              attributes before React arrives, and the first measurement
              then sets the same values through state. */}
          <div
            className="aquila__fit-box"
            data-fit={fit ? "" : undefined}
            style={fitStyle}
            suppressHydrationWarning
          >
            <div className="aquila__fit">
              <div
                ref={bookRef}
                className="aquila__book"
                data-pending={pending || undefined}
                data-turning={turn?.direction}
                onPointerDown={onSwipeStart}
                onPointerUp={onSwipeEnd}
                onPointerCancel={() => {
                  swipeStart.current = null;
                }}
              >
                <div className="aquila__sheet">
                  <IssuePaper
                    issue={issue}
                    page={under}
                    locale={locale}
                    onGoTo={turning ? undefined : goTo}
                  />
                </div>

                {turn && (
                  <div
                    key={turn.id}
                    className={`aquila__leaf aquila__leaf--${turn.direction}`}
                    // A picture of a page mid-turn, not a second copy to
                    // read or tab through.
                    inert
                    onAnimationEnd={(event) => {
                      if (event.target === event.currentTarget) setTurn(null);
                    }}
                  >
                    <div className="aquila__leaf-face aquila__sheet">
                      <IssuePaper issue={issue} page={turn.leaf} locale={locale} />
                    </div>
                    <div className="aquila__leaf-face aquila__leaf-back" />
                  </div>
                )}

                {/* The page's own corners turn it, for a mouse: the outer
                    corner forward, the spine corner back. They repeat the
                    buttons below, so they are hidden from assistive tech and
                    left out of the tab order - one set of controls, not two. */}
                {pageNo > 1 && (
                  <button
                    type="button"
                    className="aquila__corner aquila__corner--back"
                    tabIndex={-1}
                    aria-hidden="true"
                    onClick={() => goTo(pageNo - 1)}
                  />
                )}
                {pageNo < pageCount && (
                  <button
                    type="button"
                    className="aquila__corner aquila__corner--forward"
                    tabIndex={-1}
                    aria-hidden="true"
                    onClick={() => goTo(pageNo + 1)}
                  />
                )}
              </div>
            </div>
          </div>
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
            disabled={pageNo <= 1 || pending || turning}
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
            disabled={pageNo >= pageCount || pending || turning}
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
          {canFullscreen && (
            <button
              type="button"
              className="aquila__contents-toggle aquila__fullscreen"
              onClick={toggleFullscreen}
              aria-pressed={isFullscreen}
            >
              {t(locale, isFullscreen ? "aquila.exitFullscreen" : "aquila.fullscreen")}
            </button>
          )}
        </nav>
        {/* The first fit, before hydration: without it the page paints at
            its natural size and jumps once the layout effect scales it. */}
        <script dangerouslySetInnerHTML={{ __html: FIT_SCRIPT }} />
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
