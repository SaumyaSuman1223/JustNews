/**
 * Ported from frontend/components/LoginForm.tsx's `readable()`. Supabase's
 * messages are written for whoever is integrating it, not for the person
 * trying to get into their account. These are the ones a reader can actually
 * hit; anything unrecognised falls through unchanged rather than being
 * replaced by a vague catch-all that hides a real fault.
 */
export function readableAuthError(message: string): string {
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

/** Same floor frontend/components/LoginForm.tsx enforces - see its comment:
 *  Supabase's own default is 6, this form asks for more. */
export const MIN_PASSWORD = 8;
