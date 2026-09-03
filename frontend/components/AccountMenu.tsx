"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { t, type LocaleCode } from "@/lib/i18n";
import { createBrowserSupabaseClient } from "@/lib/supabase/client";

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
    <div className="account-menu">
      <button
        type="button"
        className="account-menu__trigger"
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((value) => !value)}
      >
        {email}
      </button>
      {open && (
        <div className="account-menu__panel" role="menu">
          {!hasBetaAccess && (
            <Link role="menuitem" href={`/${locale}/invite`} onClick={() => setOpen(false)}>
              {t(locale, "account.enterInvite")}
            </Link>
          )}
          <Link role="menuitem" href={`/${locale}/saved`} onClick={() => setOpen(false)}>
            {t(locale, "account.saved")}
          </Link>
          <Link role="menuitem" href={`/${locale}/history`} onClick={() => setOpen(false)}>
            {t(locale, "account.history")}
          </Link>
          <Link role="menuitem" href={`/${locale}/settings`} onClick={() => setOpen(false)}>
            {t(locale, "account.settings")}
          </Link>
          <Link role="menuitem" href={`/${locale}/onboarding`} onClick={() => setOpen(false)}>
            {t(locale, "account.chooseTopics")}
          </Link>
          <button role="menuitem" type="button" onClick={signOut}>
            {t(locale, "account.signOut")}
          </button>
        </div>
      )}
    </div>
  );
}
