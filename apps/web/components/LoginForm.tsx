"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { isSupabaseConfigured } from "@/lib/supabase/config";
import { createBrowserSupabaseClient } from "@/lib/supabase/client";

type Mode = "sign-in" | "sign-up";

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
    setPending(true);
    try {
      const supabase = createBrowserSupabaseClient();
      if (mode === "sign-in") {
        const { error: signInError } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (signInError) throw signInError;
        router.push(searchParams.get("next") ?? `/${locale}`);
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
      setError(caught instanceof Error ? caught.message : "Something went wrong.");
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

      <form onSubmit={handleSubmit} noValidate>
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
            minLength={8}
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
