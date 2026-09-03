import { NextResponse } from "next/server";

import { defaultLocale } from "@/lib/i18n";
import { safeNext } from "@/lib/safeNext";
import { createServerSupabaseClient } from "@/lib/supabase/server";
import { isSupabaseConfigured } from "@/lib/supabase/config";

/**
 * Where Supabase sends a reader after they click an email confirmation link.
 * Locale-agnostic on purpose - the confirmation email has no locale context
 * of its own, so this lands on the default locale unless told otherwise.
 */
export async function GET(request: Request): Promise<Response> {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  // Attacker-controlled: this route is reached from a link in an email.
  const next = safeNext(searchParams.get("next"), `/${defaultLocale}`);

  if (code && isSupabaseConfigured) {
    const supabase = await createServerSupabaseClient();
    await supabase.auth.exchangeCodeForSession(code);
  }
  return NextResponse.redirect(`${origin}${next}`);
}
