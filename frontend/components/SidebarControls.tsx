"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { CloseIcon, MenuIcon, PanelIcon } from "@/components/icons";
import { t, type LocaleCode } from "@/lib/i18n";
import { SIDEBAR_COOKIE } from "@/lib/sidebarCookie";

/** A year: the sidebar's width is a preference, not a session. */
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

function sidebar(): HTMLElement | null {
  return document.getElementById("sidebar");
}

/**
 * Collapse and expand, on a wide screen. The attribute is flipped on the
 * sidebar directly - an instant change with no server round trip - and the
 * cookie makes the next page render the same way.
 */
export function SidebarCollapse({
  locale,
  initialCollapsed,
}: {
  locale: LocaleCode;
  initialCollapsed: boolean;
}) {
  const [collapsed, setCollapsed] = useState(initialCollapsed);

  function toggle() {
    const element = sidebar();
    if (!element) return;
    const next = !collapsed;
    element.toggleAttribute("data-collapsed", next);
    setCollapsed(next);
    document.cookie = `${SIDEBAR_COOKIE}=${next ? "collapsed" : "open"}; path=/; max-age=${COOKIE_MAX_AGE}; samesite=lax`;
  }

  const label = t(locale, collapsed ? "sidebar.expand" : "sidebar.collapse");
  return (
    <button
      type="button"
      className="sidebar__collapse"
      onClick={toggle}
      aria-label={label}
      title={label}
      aria-controls="sidebar"
      aria-expanded={!collapsed}
    >
      <PanelIcon />
    </button>
  );
}

/**
 * The phone's top bar: a menu button that opens the sidebar as a drawer, and
 * the wordmark. The drawer closes on navigation, on Escape, and on the scrim.
 */
export function MobileTopBar({ locale }: { locale: LocaleCode }) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  // A link inside the drawer navigates; the drawer should not still be
  // covering the page that arrives.
  const [shownFor, setShownFor] = useState(pathname);
  if (shownFor !== pathname) {
    setShownFor(pathname);
    setOpen(false);
  }

  useEffect(() => {
    const element = sidebar();
    element?.toggleAttribute("data-open", open);
    document.documentElement.toggleAttribute("data-drawer-open", open);
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <header className="topbar">
        <button
          type="button"
          className="topbar__menu"
          onClick={() => setOpen((value) => !value)}
          aria-label={t(locale, open ? "sidebar.close" : "sidebar.open")}
          aria-controls="sidebar"
          aria-expanded={open}
        >
          {open ? <CloseIcon /> : <MenuIcon />}
        </button>
        <Link href={`/${locale}`} className="topbar__wordmark">
          Just<span>News</span>
        </Link>
      </header>
      {open && (
        // Pointer-only dismissal; the keyboard has Escape and the button.
        <div className="drawer-scrim" aria-hidden="true" onClick={() => setOpen(false)} />
      )}
    </>
  );
}
