"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { t, type LocaleCode } from "@/lib/i18n";
import { createBrowserSupabaseClient } from "@/lib/supabase/client";

/**
 * A disclosure, not a menu.
 *
 * This used to render `role="menu"` over six `role="menuitem"` children,
 * which is a promise to assistive tech: arrow keys move between items,
 * Escape closes, focus is managed. None of that existed - a screen reader
 * announced "menu, 6 items" and then behaved like a list of links, and a
 * keyboard user had no way to close it at all.
 *
 * The honest fix is the smaller widget. These are six navigation links, so
 * they are a list of links behind an `aria-expanded` button, which is a
 * pattern that needs no roving tabindex and no key handling beyond Escape.
 * The ARIA roles are gone rather than implemented, because implementing them
 * would add a keyboard model this control does not need.
 */
export function AccountMenu({
  locale,
  email,
  hasBetaAccess,
}: {
  locale: LocaleCode;
  email: string | null;
  hasBetaAccess: boolean;
}) {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;

    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      setOpen(false);
      // Focus goes back to the button that opened the panel. Without this it
      // lands on <body>, and a keyboard user has to tab from the top of the
      // page to get back to where they were.
      triggerRef.current?.focus();
    }

    function onPointerDown(event: PointerEvent) {
      if (containerRef.current?.contains(event.target as Node)) return;
      setOpen(false);
    }

    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [open]);

  if (!email) {
    return (
      <Link href={`/${locale}/login`} className="button button--secondary">
        {t(locale, "account.signIn")}
      </Link>
    );
  }

  async function signOut() {
    const supabase = createBrowserSupabaseClient();
    await supabase.auth.signOut();
    setOpen(false);
    router.push(`/${locale}`);
    router.refresh();
  }

  return (
    <div className="account-menu" ref={containerRef}>
      <button
        ref={triggerRef}
        type="button"
        className="account-menu__trigger"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        {email}
      </button>
      {open && (
        <ul className="account-menu__panel" aria-label={t(locale, "account.menu")}>
          {!hasBetaAccess && (
            <li>
              <Link href={`/${locale}/invite`} onClick={() => setOpen(false)}>
                {t(locale, "account.enterInvite")}
              </Link>
            </li>
          )}
          <li>
            <Link href={`/${locale}/saved`} onClick={() => setOpen(false)}>
              {t(locale, "account.saved")}
            </Link>
          </li>
          <li>
            <Link href={`/${locale}/history`} onClick={() => setOpen(false)}>
              {t(locale, "account.history")}
            </Link>
          </li>
          <li>
            <Link href={`/${locale}/settings`} onClick={() => setOpen(false)}>
              {t(locale, "account.settings")}
            </Link>
          </li>
          <li>
            <Link href={`/${locale}/onboarding`} onClick={() => setOpen(false)}>
              {t(locale, "account.chooseTopics")}
            </Link>
          </li>
          <li>
            <button type="button" onClick={signOut}>
              {t(locale, "account.signOut")}
            </button>
          </li>
        </ul>
      )}
    </div>
  );
}
