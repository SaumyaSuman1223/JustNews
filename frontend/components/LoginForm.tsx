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
  const [googlePending, setGooglePending] = useState(false);

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

  async function handleGoogleSignIn() {
    setError(null);
    setGooglePending(true);
    try {
      const supabase = createBrowserSupabaseClient();
      const next = safeNext(searchParams.get("next"), `/${locale}`);
      const { error: oauthError } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`,
        },
      });
      // A real, unresolved provider-side error (e.g. Google not enabled on
      // this Supabase project) returns immediately. Success does not - the
      // browser is already navigating to Google, so there is nothing to
      // await beyond that.
      if (oauthError) throw oauthError;
    } catch (caught) {
      setError(
        caught instanceof Error
          ? readable(caught.message, locale)
          : t(locale, "login.error.generic"),
      );
      setGooglePending(false);
    }
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
    <div className="narrow auth-shell">
      <div className="auth-card">
        <Link href={`/${locale}`} className="wordmark auth-card__brand">
          Just<span>News</span>
        </Link>

        <div className="auth-card__header">
          <h1>{t(locale, mode === "sign-in" ? "login.title" : "login.createHeading")}</h1>
          <p>{t(locale, "login.intro")}</p>
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

        <button
          type="button"
          className="auth-oauth"
          disabled={googlePending || pending}
          onClick={handleGoogleSignIn}
        >
          <GoogleIcon />
          {googlePending ? t(locale, "login.pending") : t(locale, "login.google")}
        </button>

        <div className="auth-divider">{t(locale, "login.or")}</div>

        <form onSubmit={handleSubmit} noValidate>
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
          <button
            type="submit"
            className="button button--primary"
            disabled={pending || googlePending}
          >
            {pending
              ? t(locale, "login.pending")
              : t(locale, mode === "sign-in" ? "login.title" : "login.createSubmit")}
          </button>
        </form>

        <p className="auth-card__footer">
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
    </div>
  );
}

/** Google's own mark, per their brand guidelines - never a generic icon or a
 * literal "G" character standing in for it. */
function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.9c1.7-1.57 2.68-3.87 2.68-6.62Z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.8.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.95v2.33A9 9 0 0 0 9 18Z"
      />
      <path
        fill="#FBBC05"
        d="M3.95 10.7A5.4 5.4 0 0 1 3.67 9c0-.59.1-1.16.28-1.7V4.97H.95A9 9 0 0 0 0 9c0 1.45.35 2.83.95 4.03l3-2.33Z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.51.46 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .95 4.97l3 2.33C4.66 5.17 6.65 3.58 9 3.58Z"
      />
    </svg>
  );
}
