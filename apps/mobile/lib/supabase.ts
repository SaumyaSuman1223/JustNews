import "react-native-url-polyfill/auto";

import AsyncStorage from "@react-native-async-storage/async-storage";
import { createClient } from "@supabase/supabase-js";

/**
 * Whether Supabase Auth is actually wired up.
 *
 * Same posture as frontend/lib/supabase/config.ts: every auth-adjacent code
 * path checks this first and degrades to a signed-out state rather than
 * crashing (ADR 0003). `EXPO_PUBLIC_*` is Expo's inlined-at-build-time public
 * env prefix - the RN equivalent of Next's `NEXT_PUBLIC_*`.
 */
export const SUPABASE_URL = process.env.EXPO_PUBLIC_SUPABASE_URL;
export const SUPABASE_ANON_KEY = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY;

export const isSupabaseConfigured = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);

/**
 * There is no cookie/server-session split on mobile - one client, held for
 * the app's lifetime, with the SDK's own AsyncStorage-backed persistence and
 * refresh doing what frontend/middleware.ts does for the web app's cookies.
 *
 * `detectSessionInUrl: false` because there is no URL to detect a session
 * from outside a browser; `react-native-url-polyfill/auto` above is required
 * by supabase-js on RN, which has no native `URL` global.
 */
export const supabase = isSupabaseConfigured
  ? createClient(SUPABASE_URL!, SUPABASE_ANON_KEY!, {
      auth: {
        storage: AsyncStorage,
        autoRefreshToken: true,
        persistSession: true,
        detectSessionInUrl: false,
      },
    })
  : null;
