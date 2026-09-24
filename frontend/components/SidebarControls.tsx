"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { CloseIcon, MenuIcon, PanelIcon } from "@/components/icons";
import { t, type LocaleCode } from "@/lib/i18n";
import { secureFlag } from "@/lib/railPrefs";
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
    // Collapsed, a link is an icon and its tooltip is its only visible name;
    // expanded, the label is on screen and a tooltip would repeat it.
    for (const link of element.querySelectorAll<HTMLElement>("[data-label]")) {
      if (next) link.title = link.dataset.label ?? "";
      else link.removeAttribute("title");
    }
    setCollapsed(next);
    document.cookie = `${SIDEBAR_COOKIE}=${next ? "collapsed" : "open"}; path=/; max-age=${COOKIE_MAX_AGE}; samesite=lax${secureFlag()}`;
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

  const button = useRef<HTMLButtonElement>(null);
  const wasOpen = useRef(false);

  useEffect(() => {
    const element = sidebar();
    element?.toggleAttribute("data-open", open);
    document.documentElement.toggleAttribute("data-drawer-open", open);
    // Behind an open drawer the page is out of reach: `inert` takes it out
    // of the tab order and the accessibility tree, so Tab walks the drawer
    // and the button that closes it, not the feed under the scrim.
    for (const behind of document.querySelectorAll<HTMLElement>("#main, .tabbar")) {
      behind.inert = open;
    }
    if (open) {
      wasOpen.current = true;
      // The first control the drawer actually shows - the collapse button
      // is in the markup but hidden on a phone, and focusing it does nothing.
      const controls = element?.querySelectorAll<HTMLElement>("a[href], button, input") ?? [];
      Array.from(controls)
        .find((control) => control.offsetParent !== null)
        ?.focus();
    } else if (wasOpen.current) {
      // Back where the reader opened it from, rather than lost at the top.
      wasOpen.current = false;
      button.current?.focus();
    }
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
          ref={button}
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
