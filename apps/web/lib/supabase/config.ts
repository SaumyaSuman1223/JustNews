/**
 * Whether Supabase Auth is actually wired up.
 *
 * Empty in local dev unless `.env` names a real project. Every auth-adjacent
 * code path checks this first and degrades - a signed-out empty state rather
 * than a crash - the same posture the rest of this app takes toward every
 * external dependency (ADR 0003).
 */
export const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
export const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export const isSupabaseConfigured = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);
