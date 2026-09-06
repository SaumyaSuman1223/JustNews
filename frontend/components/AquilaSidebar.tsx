"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { t, type LocaleCode } from "@/lib/i18n";

/**
 * The way out of the reader.
 *
 * Aquila has no application chrome - that is the point of the route group it
 * lives in - but "no chrome" cannot mean "no exit". So the navigation is a
 * narrow strip at the inline-start edge holding a single control, and the
 * panel of links only exists while the reader is asking for it.
 *
 * Three ways in, because an edge that only responds to hover is unusable
 * without a mouse and invisible to a screen reader: the strip opens on
 * pointer entry, the button opens on click, and the button opens on keyboard
 * focus. Escape closes it and returns focus to the button, so a reader who
 * opened it by accident is never trapped inside it.
 */
export function AquilaSidebar({ locale }: { locale: LocaleCode }) {
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      setOpen(false);
      button.current?.focus();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const links: { href: string; label: string }[] = [
    { href: `/${locale}`, label: t(locale, "nav.home") },
    { href: `/${locale}/desk`, label: t(locale, "nav.desk") },
    { href: `/${locale}/search`, label: t(locale, "nav.search") },
    { href: `/${locale}/saved`, label: t(locale, "nav.saved") },
  ];

  return (
    <div
      className="reader-nav"
      data-open={open || undefined}
      onPointerEnter={() => setOpen(true)}
      onPointerLeave={() => setOpen(false)}
    >
      <button
        type="button"
        ref={button}
        className="reader-nav__toggle"
        aria-expanded={open}
        aria-controls="reader-nav-panel"
        onClick={() => setOpen((value) => !value)}
        onFocus={() => setOpen(true)}
      >
        <span className="visually-hidden">{t(locale, "nav.primary")}</span>
        <svg viewBox="0 0 24 24" width="1.2em" height="1.2em" aria-hidden="true">
          <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="1.6" fill="none" />
        </svg>
      </button>

      {/* Rendered in both states rather than mounted on open: a panel that
          only exists while open cannot be described by aria-controls, and the
          transition has nothing to animate from. `hidden` is not used because
          the panel slides - visibility is the CSS's job here. */}
      <nav
        id="reader-nav-panel"
        className="reader-nav__panel"
        aria-label={t(locale, "nav.primary")}
      >
        <p className="reader-nav__wordmark">
          Just<span>News</span>
        </p>
        <ul>
          {links.map((link) => (
            <li key={link.href}>
              <Link href={link.href} tabIndex={open ? undefined : -1}>
                {link.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
