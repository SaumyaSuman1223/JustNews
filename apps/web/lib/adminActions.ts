"use server";

import { revalidatePath } from "next/cache";

import * as api from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getSession } from "@/lib/session";

async function adminAuthOrNull() {
  const session = await getSession();
  if (!session) return null;
  // The route itself re-checks the role server-side (get_admin_session) -
  // this action does not need to duplicate that check to be safe, only to
  // avoid calling out with no token at all.
  return { accessToken: session.accessToken, sessionId: await getBrowsingSessionId() };
}

export async function takedownArticleAction(formData: FormData): Promise<void> {
  const auth = await adminAuthOrNull();
  if (!auth) return;
  const articleId = Number(formData.get("articleId"));
  const reason = String(formData.get("reason") ?? "");
  await api.takedownArticle(auth, articleId, reason);
  revalidatePath("/admin/articles");
}

export async function restoreArticleAction(articleId: number): Promise<void> {
  const auth = await adminAuthOrNull();
  if (!auth) return;
  await api.restoreArticle(auth, articleId);
  revalidatePath("/admin/articles");
}

export async function setUserRoleAction(formData: FormData): Promise<void> {
  const auth = await adminAuthOrNull();
  if (!auth) return;
  const userId = String(formData.get("userId"));
  const role = String(formData.get("role"));
  await api.setUserRole(auth, userId, role);
  revalidatePath("/admin/users");
}

export async function createInviteAction(formData: FormData): Promise<void> {
  const auth = await adminAuthOrNull();
  if (!auth) return;
  const note = String(formData.get("note") ?? "");
  const maxUses = Number(formData.get("maxUses") ?? 1);
  await api.createInvite(auth, { note, maxUses });
  revalidatePath("/admin/invites");
}
