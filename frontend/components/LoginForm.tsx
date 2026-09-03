"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { defaultLocale, isLocaleCode, t, type LocaleCode } from "@/lib/i18n";
import { safeNext } from "@/lib/safeNext";
import { isSupabaseConfigured } from "@/lib/supabase/config";
import { createBrowserSupabaseClient } from "@/lib/supabase/client";

type Mode = "sign-in" | "sign-up";

/** Shortest password we will submit. Supabase's own default floor is 6; the
 *  form claimed 8 via minLength but also set noValidate, so nothing enforced
 *  it and a 6-character password was accepted against a field that said 8. */
const MIN_PASSWORD = 8;

/**
 * Supabase's messages are written for whoever is integrating it, not for the
 * person trying to get into their account. These are the ones a reader can
 * actually hit; anything unrecognised falls through unchanged rather than
 * being replaced by a vague catch-all that hides a real fault.
 */
function readable(message: string, locale: LocaleCode): string {
  const text = message.toLowerCase();
  if (text.includes("invalid login credentials")) {
    return t(locale, "login.error.credentials");
  }
  if (text.includes("email not confirmed")) {
    return t(locale, "login.error.unconfirmed");
  }
  if (text.includes("already registered") || text.includes("already been registered")) {
    return t(locale, "login.error.registered");
  }
  if (text.includes("for security purposes") || text.includes("rate limit")) {
    return t(locale, "login.error.rateLimit");
  }
  if (text.includes("failed to fetch") || text.includes("networkerror")) {
    return t(locale, "login.error.network");
  }
  // Matched on Supabase's English text, and returned as-is when nothing
  // matches: an untranslated real fault beats a translated vague one.
  return message;
}

export function LoginForm() {
  const { locale: routeLocale } = useParams<{ locale: string }>();
  const locale = isLocaleCode(routeLocale) ? routeLocale : defaultLocale;
  const router = useRouter();
  const searchParams = useSearchParams();
  const [mode, setMode] = useState<Mode>("sign-in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  if (!isSupabaseConfigured) {
    return (
      <div className="narrow">
        <div className="page-header">
          <h1>{t(locale, "login.title")}</h1>
        </div>
        <p className="notice" role="status">
          {t(locale, "login.unavailable")}
        </p>
        <p>
          <Link href={`/${locale}`}>{t(locale, "article.backToFront")}</Link>
        </p>
      </div>
    );
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    if (mode === "sign-up" && password.length < MIN_PASSWORD) {
      setError(t(locale, "login.minPassword", { count: MIN_PASSWORD }));
      return;
    }
    setPending(true);
    try {
      const supabase = createBrowserSupabaseClient();
      if (mode === "sign-in") {
        const { error: signInError } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (signInError) throw signInError;
        router.push(safeNext(searchParams.get("next"), `/${locale}`));
        router.refresh();
      } else {
        const { error: signUpError } = await supabase.auth.signUp({
          email,
          password,
          options: { emailRedirectTo: `${window.location.origin}/auth/callback?next=/${locale}` },
        });
        if (signUpError) throw signUpError;
        setNotice(t(locale, "login.checkEmail"));
        setMode("sign-in");
      }
    } catch (caught) {
      setError(
        caught instanceof Error
          ? readable(caught.message, locale)
          : t(locale, "login.error.generic"),
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="narrow">
      <div className="page-header">
        <h1>{t(locale, mode === "sign-in" ? "login.title" : "login.createHeading")}</h1>
        <p>
          {mode === "sign-in" ? (
            <>
              {t(locale, "login.newHere")}{" "}
              <button type="button" className="link-button" onClick={() => setMode("sign-up")}>
                {t(locale, "login.createHeading")}
              </button>
            </>
          ) : (
            <>
              {t(locale, "login.alreadyHaveOne")}{" "}
              <button type="button" className="link-button" onClick={() => setMode("sign-in")}>
                {t(locale, "login.title")}
              </button>
            </>
          )}
        </p>
      </div>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="notice" role="status">
          {notice}
        </p>
      )}

      <form className="form-panel" onSubmit={handleSubmit} noValidate>
        <div className="field">
          <label htmlFor="email">{t(locale, "login.email")}</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="password">{t(locale, "login.password")}</label>
          <input
            id="password"
            type="password"
            autoComplete={mode === "sign-in" ? "current-password" : "new-password"}
            minLength={MIN_PASSWORD}
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>
        <button type="submit" className="button button--primary" disabled={pending}>
          {pending
            ? t(locale, "login.pending")
            : t(locale, mode === "sign-in" ? "login.title" : "login.createSubmit")}
        </button>
      </form>
    </div>
  );
}
