"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import * as api from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getSession } from "@/lib/session";

async function authOrNull() {
  const session = await getSession();
  if (!session) return null;
  return { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() };
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
    if (languages.length > 0) {
      await api.updateMe(auth, languages);
    }
    await Promise.all(topicIds.map((topicId) => api.followTopic(auth, topicId)));
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
