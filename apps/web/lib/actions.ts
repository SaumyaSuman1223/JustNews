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

export async function saveArticleAction(articleId: number, path: string): Promise<void> {
  const auth = await authOrNull();
  if (!auth) return;
  await api.saveArticle(auth, articleId);
  revalidatePath(path);
}

export async function unsaveArticleAction(articleId: number, path: string): Promise<void> {
  const auth = await authOrNull();
  if (!auth) return;
  await api.unsaveArticle(auth, articleId);
  revalidatePath(path);
}

export async function notInterestedAction(
  articleId: number,
  surface: string,
  path: string,
): Promise<void> {
  const auth = await authOrNull();
  if (!auth) return;
  await api.reportNotInterested(auth, { articleId, surface });
  revalidatePath(path);
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
 * Follows every topic the reader checked, then sends them into their new
 * feed - the onboarding topic picker's one job. Skippable entirely: a reader
 * who follows nothing just gets the unfiltered, reverse-chronological feed
 * until the Stage 7 exploration deck exists to do this by behaviour instead.
 */
export async function completeOnboardingAction(locale: string, formData: FormData): Promise<void> {
  const auth = await authOrNull();
  if (auth) {
    const topicIds = formData.getAll("topics").map(String);
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
