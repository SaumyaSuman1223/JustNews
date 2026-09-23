"use client";

import { useEffect, useRef } from "react";

import { t, type LocaleCode } from "@/lib/i18n";

/** A story on the page: the card's own headline link. */
const STORY_SELECTOR = ".card__title a, .story__title a";

/**
 * Keyboard shortcuts for reading (fifth pass F8), everywhere cards appear:
 *
 *   j / k   next / previous story (focus moves to its headline)
 *   s       save the focused story, when signed in
 *   /       jump to search
 *   ?       this list
 *
 * Opening a story is Enter, which a focused link already does - no second
 * key for the same thing. Nothing fires while typing in a field or with a
 * modifier held, so the shortcuts never fight the browser, a screen reader
 * or text entry. The list is a native <dialog>: focus moves into it, Esc
 * closes it, and focus returns to where it was.
 */
export function ReaderShortcuts({ locale }: { locale: LocaleCode }) {
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) return;
      const target = event.target as HTMLElement | null;
      if (
        target &&
        (target.isContentEditable ||
          ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) ||
          target.closest("dialog[open]"))
      ) {
        return;
      }

      if (event.key === "?") {
        event.preventDefault();
        dialog.current?.showModal();
        return;
      }
      if (event.key === "/") {
        const search = document.querySelector<HTMLInputElement>(
          "#search-q, input[type='search']",
        );
        if (search) {
          event.preventDefault();
          search.focus();
        }
        return;
      }

      const stories = Array.from(document.querySelectorAll<HTMLAnchorElement>(STORY_SELECTOR));
      if (stories.length === 0) return;
      const current = stories.findIndex((link) => link === document.activeElement);

      if (event.key === "j" || event.key === "k") {
        event.preventDefault();
        const next =
          event.key === "j"
            ? Math.min(current + 1, stories.length - 1)
            : Math.max(current === -1 ? 0 : current - 1, 0);
        const link = stories[next];
        link?.focus();
        link?.scrollIntoView({ block: "center", behavior: "smooth" });
        return;
      }

      if (event.key === "s" && current >= 0) {
        const save = stories[current]
          ?.closest(".card, .story")
          ?.querySelector<HTMLButtonElement>("[data-shortcut='save']");
        if (save && !save.disabled) {
          event.preventDefault();
          save.click();
        }
      }
    }

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const rows: [string, string][] = [
    ["j", t(locale, "shortcuts.next")],
    ["k", t(locale, "shortcuts.previous")],
    ["Enter", t(locale, "shortcuts.open")],
    ["s", t(locale, "shortcuts.save")],
    ["/", t(locale, "shortcuts.search")],
    ["?", t(locale, "shortcuts.help")],
  ];

  return (
    <dialog ref={dialog} className="shortcuts" aria-labelledby="shortcuts-heading">
      <h2 id="shortcuts-heading">{t(locale, "shortcuts.heading")}</h2>
      <dl className="shortcuts__list">
        {rows.map(([key, label]) => (
          <div key={key}>
            <dt>
              <kbd>{key}</kbd>
            </dt>
            <dd>{label}</dd>
          </div>
        ))}
      </dl>
      <form method="dialog">
        <button type="submit" className="button button--secondary">
          {t(locale, "shortcuts.close")}
        </button>
      </form>
    </dialog>
  );
}
