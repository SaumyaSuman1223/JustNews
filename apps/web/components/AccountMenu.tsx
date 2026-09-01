"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { createBrowserSupabaseClient } from "@/lib/supabase/client";

export function AccountMenu({
  locale,
  email,
}: {
  locale: string;
  email: string | null;
}) {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  if (!email) {
    return (
      <Link href={`/${locale}/login`} className="button button--secondary">
        Sign in
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
          <Link role="menuitem" href={`/${locale}/saved`} onClick={() => setOpen(false)}>
            Saved
          </Link>
          <Link role="menuitem" href={`/${locale}/history`} onClick={() => setOpen(false)}>
            History
          </Link>
          <Link role="menuitem" href={`/${locale}/settings`} onClick={() => setOpen(false)}>
            Settings
          </Link>
          <Link role="menuitem" href={`/${locale}/onboarding`} onClick={() => setOpen(false)}>
            Choose topics
          </Link>
          <button role="menuitem" type="button" onClick={signOut}>
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
