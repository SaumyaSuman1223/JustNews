"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { deleteAccountAction } from "@/lib/actions";
import { t, type LocaleCode } from "@/lib/i18n";
import { createBrowserSupabaseClient } from "@/lib/supabase/client";

export function DeleteAccountButton({ locale }: { locale: LocaleCode }) {
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [pending, setPending] = useState(false);

  async function handleDelete() {
    setPending(true);
    await deleteAccountAction();
    const supabase = createBrowserSupabaseClient();
    await supabase.auth.signOut();
    router.push(`/${locale}`);
    router.refresh();
  }

  if (!confirming) {
    return (
      <button type="button" className="button button--secondary" onClick={() => setConfirming(true)}>
        {t(locale, "account.delete")}
      </button>
    );
  }

  return (
    <div className="notice" role="alertdialog">
      <p style={{ marginBlockStart: 0 }}>{t(locale, "account.delete.warning")}</p>
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button type="button" className="button button--primary" disabled={pending} onClick={handleDelete}>
          {pending ? t(locale, "account.delete.pending") : t(locale, "account.delete.confirm")}
        </button>
        <button
          type="button"
          className="button button--secondary"
          disabled={pending}
          onClick={() => setConfirming(false)}
        >
          {t(locale, "account.delete.cancel")}
        </button>
      </div>
    </div>
  );
}
