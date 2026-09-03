"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

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
function readable(message: string): string {
  const text = message.toLowerCase();
  if (text.includes("invalid login credentials")) {
    return "That email and password don't match an account. Check both, or create an account.";
  }
  if (text.includes("email not confirmed")) {
    return "Confirm your email first - check your inbox for the link we sent when you signed up.";
  }
  if (text.includes("already registered") || text.includes("already been registered")) {
    return "There is already an account with that email. Sign in instead.";
  }
  if (text.includes("for security purposes") || text.includes("rate limit")) {
    return "Too many attempts just now. Wait a minute and try again.";
  }
  if (text.includes("failed to fetch") || text.includes("networkerror")) {
    return "We could not reach the sign-in service. Check your connection and try again.";
  }
  return message;
}

export function LoginForm() {
  const { locale } = useParams<{ locale: string }>();
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
          <h1>Sign in</h1>
        </div>
        <p className="notice" role="status">
          Accounts are not set up in this environment yet. Browsing, search and exploration all
          work without one - saved articles, history and a personalised feed need sign-in.
        </p>
        <p>
          <Link href={`/${locale}`}>Back to the front page</Link>
        </p>
      </div>
    );
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    if (mode === "sign-up" && password.length < MIN_PASSWORD) {
      setError(`Choose a password of at least ${MIN_PASSWORD} characters.`);
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
        setNotice("Check your email to confirm your account, then sign in.");
        setMode("sign-in");
      }
    } catch (caught) {
      setError(
        caught instanceof Error ? readable(caught.message) : "Something went wrong. Try again.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="narrow">
      <div className="page-header">
        <h1>{mode === "sign-in" ? "Sign in" : "Create an account"}</h1>
        <p>
          {mode === "sign-in" ? (
            <>
              New here?{" "}
              <button type="button" className="link-button" onClick={() => setMode("sign-up")}>
                Create an account
              </button>
            </>
          ) : (
            <>
              Already have one?{" "}
              <button type="button" className="link-button" onClick={() => setMode("sign-in")}>
                Sign in
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
          <label htmlFor="email">Email</label>
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
          <label htmlFor="password">Password</label>
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
          {pending ? "Please wait…" : mode === "sign-in" ? "Sign in" : "Create account"}
        </button>
      </form>
    </div>
  );
}
