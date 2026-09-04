"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import * as api from "@/lib/api";
import { BROWSING_SESSION_COOKIE, getBrowsingSessionId } from "@/lib/browsingSession";
import { CONSENT_COOKIE, type ConsentState } from "@/lib/consent";
import { getSession } from "@/lib/session";

async function authOrNull() {
  const session = await getSession();
  if (!session) return null;
  return { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() };
}

/**
 * The only place `jn_consent` is ever written - a reader's own choice, on
 * the banner or the Settings toggle, never a default middleware.ts assigns.
 * `httpOnly`: nothing client-side needs to read this cookie, since the
 * banner is server-rendered and both its buttons are plain `<form
 * action={...}>` submissions, not client state - one fewer thing a tampered
 * client value could lie to the server about.
 *
 * Also sets/deletes jn_sid directly here, synchronously, rather than only
 * relying on middleware.ts to notice the new consent cookie on some later
 * request. middleware.ts's own copy of this logic is what keeps the
 * invariant holding on every ordinary navigation afterward (and is what
 * actually enforces it - a tampered client could call this action with any
 * cookie state it likes, but every subsequent real request still passes
 * through middleware); this one is what makes the grant or withdrawal take
 * effect immediately, in the same response, rather than waiting on a
 * refresh whose exact timing relative to a Server Action isn't a contract
 * this code should depend on.
 *
 * `revalidatePath("/", "layout")` matches the pattern every other
 * account-wide action in this file already uses (redeemInviteAction) - the
 * root layout is what decides whether ConsentBanner renders at all.
 */
export async function setConsentAction(state: ConsentState): Promise<void> {
  const store = await cookies();
  store.set(CONSENT_COOKIE, state, {
    maxAge: 60 * 60 * 24 * 180,
    sameSite: "lax",
    httpOnly: true,
    path: "/",
  });
  if (state === "granted") {
    const existing = store.get(BROWSING_SESSION_COOKIE)?.value;
    store.set(BROWSING_SESSION_COOKIE, existing ?? crypto.randomUUID(), {
      maxAge: 60 * 60 * 24 * 30,
      sameSite: "lax",
      path: "/",
    });
  } else {
    store.delete(BROWSING_SESSION_COOKIE);
  }
  revalidatePath("/", "layout");
}

/**
 * The card actions report whether they worked.
 *
 * They returned void, so a failed save looked exactly like a successful one:
 * the button re-enabled, nothing changed, and the reader was left to guess
 * whether the click registered. `false` covers both a lost session and an API
 * that refused, because from the card's point of view those need the same
 * answer - say so, and let them try again.
 */
export async function saveArticleAction(articleId: number, path: string): Promise<boolean> {
  const auth = await authOrNull();
  if (!auth) return false;
  const ok = await api.saveArticle(auth, articleId);
  if (ok) revalidatePath(path);
  return ok;
}

export async function unsaveArticleAction(articleId: number, path: string): Promise<boolean> {
  const auth = await authOrNull();
  if (!auth) return false;
  const ok = await api.unsaveArticle(auth, articleId);
  if (ok) revalidatePath(path);
  return ok;
}

export async function submitFeedbackAction(locale: string, formData: FormData): Promise<void> {
  const auth = await authOrNull();
  const message = String(formData.get("message") ?? "");
  const path = String(formData.get("path") ?? "");
  const ok = auth
    ? await api.submitFeedback(auth, { message, locale, path: path || undefined })
    : false;
  redirect(`/${locale}/feedback?sent=${ok ? "1" : "0"}`);
}

export async function notInterestedAction(
  articleId: number,
  surface: string,
  path: string,
): Promise<boolean> {
  const auth = await authOrNull();
  if (!auth) return false;
  const ok = await api.reportNotInterested(auth, { articleId, surface });
  if (ok) revalidatePath(path);
  return ok;
}

export async function undoNotInterestedAction(
  articleId: number,
  surface: string,
  path: string,
): Promise<boolean> {
  const auth = await authOrNull();
  if (!auth) return false;
  const ok = await api.undoNotInterested(auth, { articleId, surface });
  if (ok) revalidatePath(path);
  return ok;
}

export async function followTopicAction(topicId: string, path: string): Promise<void> {
  const auth = await authOrNull();
  if (!auth) return;
  await api.followTopic(auth, topicId);
  revalidatePath(path);
}

export async function unfollowTopicAction(topicId: string, path: string): Promise<void> {
  const auth = await authOrNull();
  if (!auth) return;
  await api.unfollowTopic(auth, topicId);
  revalidatePath(path);
}

export async function followSourceAction(sourceId: number, path: string): Promise<boolean> {
  const auth = await authOrNull();
  if (!auth) return false;
  await api.followSource(auth, sourceId);
  revalidatePath(path);
  return true;
}

export async function unfollowSourceAction(sourceId: number, path: string): Promise<boolean> {
  const auth = await authOrNull();
  if (!auth) return false;
  await api.unfollowSource(auth, sourceId);
  revalidatePath(path);
  return true;
}

export async function updateLanguagesAction(languages: string[]): Promise<void> {
  const auth = await authOrNull();
  if (!auth) return;
  await api.updateMe(auth, languages);
  revalidatePath("/", "layout");
}

/** Bound to a `<form action>` - reads checked languages straight off the form. */
export async function updateLanguagesFormAction(formData: FormData): Promise<void> {
  await updateLanguagesAction(formData.getAll("languages").map(String));
}

/**
 * Saves the reader's chosen languages and follows every topic they checked,
 * then sends them into their new feed. Topics are skippable entirely - a
 * reader who follows none just gets the unfiltered feed until the Stage 7
 * exploration deck exists to infer interest from behaviour instead.
 * The API requires at least one language; the form pre-checks the reader's
 * current locale so there is always one checked by default, but nothing
 * here stops every box being unchecked - that case is simply a no-op update
 * (api.updateMe is skipped when the list is empty) rather than a form error.
 */
export async function completeOnboardingAction(locale: string, formData: FormData): Promise<void> {
  const auth = await authOrNull();
  if (auth) {
    const languages = formData.getAll("languages").map(String);
    const topicIds = formData.getAll("topics").map(String);
    // Number, not String: SourceOut.id is an integer everywhere else in the
    // API (FollowSourceButton, unfollowSourceAction), and a bare string id
    // would silently fail every later `===` comparison against it.
    const sourceIds = formData
      .getAll("sources")
      .map((value) => Number(value))
      .filter((id) => Number.isInteger(id));
    if (languages.length > 0) {
      await api.updateMe(auth, languages);
    }
    await Promise.all([
      ...topicIds.map((topicId) => api.followTopic(auth, topicId)),
      ...sourceIds.map((sourceId) => api.followSource(auth, sourceId)),
    ]);
  }
  redirect(`/${locale}`);
}

export async function redeemInviteAction(code: string): Promise<api.RedeemResult> {
  const auth = await authOrNull();
  if (!auth) return { ok: false, message: "Sign in first." };
  const result = await api.redeemInvite(auth, code);
  if (result.ok) revalidatePath("/", "layout");
  return result;
}

/**
 * Deletes this system's record of the reader (saves, follows; impressions
 * and interaction events are anonymised, not deleted - see
 * services.users.delete_account). Does not sign them out - Supabase's
 * session lives in the browser, so the client component calling this also
 * calls supabase.auth.signOut() itself right after.
 */
export async function deleteAccountAction(): Promise<boolean> {
  const auth = await authOrNull();
  if (!auth) return false;
  return api.deleteMe(auth);
}
