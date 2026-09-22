"use client";

import { useEffect, useRef } from "react";

import type { Issue, IssueEdition } from "@/lib/api";
import { curatedTopicLabel } from "@/lib/curatedTopics";
import { t, type LocaleCode } from "@/lib/i18n";

/**
 * The reader's utility bar: contents, pages, editions.
 *
 * Audit §12 draws the distinction this component exists to honour. A
 * newspaper has an editorial right rail - Technology, Economy, Climate - and
 * that belongs *inside* the paper. What used to sit at the right of the
 * screen was not that: it was contents and edition controls, which are
 * reader furniture and belong outside the paper entirely.
 *
 * It was also permanently visible, which cost 280px of every viewport. That
 * is why the paper measured 1004px wide against §35's 1080-1180: the rail was
 * taking the width the newspaper needed. Moving it to an overlay is what lets
 * the paper be the size a paper should be.
 *
 * Opening does not reflow the paper (§13) - the panel is fixed and overlays
 * the workspace, so the page underneath does not re-compose while you look
 * for the contents.
 */
export function ReaderUtility({
  issue,
  editions,
  locale,
  pageNo,
  onGoTo,
  open,
  onOpenChange,
}: {
  issue: Issue;
  editions: IssueEdition[];
  locale: LocaleCode;
  pageNo: number;
  onGoTo: (page: number) => void;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const toggle = useRef<HTMLButtonElement>(null);
  // §13 asks for a close delay so crossing the edge briefly does not dismiss
  // it. Held in a ref rather than state: it is a timer, not something the
  // render depends on.
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      onOpenChange(false);
      toggle.current?.focus();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  useEffect(
    () => () => {
      if (closeTimer.current) clearTimeout(closeTimer.current);
    },
    [],
  );

  function hold() {
    if (closeTimer.current) clearTimeout(closeTimer.current);
  }

  function release() {
    hold();
    closeTimer.current = setTimeout(() => onOpenChange(false), 320);
  }

  return (
    <div
      className="reader-utility"
      data-open={open || undefined}
      onPointerEnter={() => {
        hold();
        onOpenChange(true);
      }}
      onPointerLeave={release}
    >
      <button
        type="button"
        ref={toggle}
        className="reader-utility__toggle"
        aria-expanded={open}
        aria-controls="reader-utility-panel"
        onClick={() => onOpenChange(!open)}
        onFocus={() => onOpenChange(true)}
      >
        <span className="visually-hidden">{t(locale, "aquila.contents")}</span>
        <svg
          viewBox="0 0 24 24"
          width="1.2em"
          height="1.2em"
          aria-hidden="true"
        >
          <path
            d="M5 7h14M5 12h14M5 17h9"
            stroke="currentColor"
            strokeWidth="1.6"
            fill="none"
            strokeLinecap="round"
          />
        </svg>
      </button>

      <aside
        id="reader-utility-panel"
        ref={panel}
        className="reader-utility__panel"
        aria-label={t(locale, "aquila.contents")}
      >
        <h2 className="reader-utility__heading">
          {t(locale, "aquila.contents")}
        </h2>
        <ol className="reader-utility__pages">
          {issue.sections.map((section) => (
            <li key={section.page_no}>
              <button
                type="button"
                onClick={() => onGoTo(section.page_no)}
                aria-current={section.page_no === pageNo ? "true" : undefined}
                tabIndex={open ? undefined : -1}
              >
                <span className="reader-utility__no">
                  {String(section.page_no).padStart(2, "0")}
                </span>
                {section.title == null
                  ? t(locale, "aquila.frontPage")
                  : section.topic_id
                    ? curatedTopicLabel(section.topic_id, section.title, locale)
                    : section.title}
              </button>
            </li>
          ))}
        </ol>

        <h2 className="reader-utility__heading">
          {t(locale, "aquila.editions")}
        </h2>
        <ul className="reader-utility__editions">
          {editions.map((edition) => (
            <li key={edition.id}>
              {/* A full navigation, not a fetch: a different edition is a
                  different issue, and its own URL is what makes it linkable
                  and archivable. */}
              <a
                href={`/${locale}/aquila?issue=${edition.id}`}
                aria-current={edition.id === issue.id ? "true" : undefined}
                tabIndex={open ? undefined : -1}
              >
                <span>
                  {t(
                    locale,
                    `aquila.edition.${edition.edition_slot}` as "aquila.edition.morning",
                  )}
                </span>
                <span className="reader-utility__time">
                  {t(locale, "aquila.editionTime", {
                    time: new Intl.DateTimeFormat(locale, {
                      hour: "2-digit",
                      minute: "2-digit",
                      hour12: false,
                      timeZone: "UTC",
                    }).format(new Date(edition.published_at)),
                  })}
                </span>
              </a>
            </li>
          ))}
        </ul>

        <p className="reader-utility__sign">{t(locale, "aquila.sign")}</p>
      </aside>
    </div>
  );
}
