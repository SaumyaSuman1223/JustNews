import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";

import { InviteForm } from "@/components/InviteForm";
import { getMe } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { isLocaleCode } from "@/lib/i18n";
import { getSession } from "@/lib/session";

export const metadata: Metadata = { title: "Redeem your invite" };

export default async function InvitePage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();

  const session = await getSession();
  if (!session) redirect(`/${locale}/login?next=${encodeURIComponent(`/${locale}/invite`)}`);

  const profile = await getMe({
    accessToken: session.accessToken,
    sessionId: await getBrowsingSessionId(),
  });
  if (profile?.has_beta_access) redirect(`/${locale}`);

  return <InviteForm />;
}
