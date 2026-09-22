"use client";

import Link from "next/link";
import { useState } from "react";

import { t, type LocaleCode } from "@/lib/i18n";
import { createBrowserSupabaseClient } from "@/lib/supabase/client";

const MIN_PASSWORD = 8;

/**
 * Where the password-reset email lands (fifth pass F10): the auth callback
 * has already exchanged the link's code for a session, so this only has to
 * set the new password on it.
 */
export function NewPasswordForm({ locale }: { locale: LocaleCode }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (password.length < MIN_PASSWORD) {
      setError(t(locale, "login.minPassword", { count: MIN_PASSWORD }));
      return;
    }
    setPending(true);
    const { error: updateError } = await createBrowserSupabaseClient().auth.updateUser({
      password,
    });
    setPending(false);
    if (updateError) {
      setError(updateError.message);
      return;
    }
    setDone(true);
  }

  if (done) {
    return (
      <p className="notice" role="status">
        {t(locale, "login.reset.done")}{" "}
        <Link href={`/${locale}`}>{t(locale, "article.backToFront")}</Link>
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="field">
        <label htmlFor="new-password">{t(locale, "login.reset.newPassword")}</label>
        <input
          id="new-password"
          type="password"
          autoComplete="new-password"
          minLength={MIN_PASSWORD}
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </div>
      <button type="submit" className="button button--primary" disabled={pending}>
        {pending ? t(locale, "login.pending") : t(locale, "login.reset.save")}
      </button>
    </form>
  );
}
