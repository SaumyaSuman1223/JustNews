"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { deleteAccountAction } from "@/lib/actions";
import { createBrowserSupabaseClient } from "@/lib/supabase/client";

export function DeleteAccountButton({ locale }: { locale: string }) {
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
        Delete my account
      </button>
    );
  }

  return (
    <div className="notice" role="alertdialog">
      <p style={{ marginBlockStart: 0 }}>
        This removes your saves, follows and profile permanently. Your reading history is kept
        but no longer linked to you. This cannot be undone.
      </p>
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button type="button" className="button button--primary" disabled={pending} onClick={handleDelete}>
          {pending ? "Deleting…" : "Yes, delete everything"}
        </button>
        <button
          type="button"
          className="button button--secondary"
          disabled={pending}
          onClick={() => setConfirming(false)}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
