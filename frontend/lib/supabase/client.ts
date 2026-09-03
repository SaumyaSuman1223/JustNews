"use client";

import { createBrowserClient } from "@supabase/ssr";

import { SUPABASE_ANON_KEY, SUPABASE_URL, isSupabaseConfigured } from "./config";

/** For Client Components: the login form, the account menu. */
export function createBrowserSupabaseClient() {
  if (!isSupabaseConfigured) {
    throw new Error("Supabase is not configured - set NEXT_PUBLIC_SUPABASE_URL and _ANON_KEY.");
  }
  return createBrowserClient(SUPABASE_URL!, SUPABASE_ANON_KEY!);
}
