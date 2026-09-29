import { notFound, permanentRedirect } from "next/navigation";

import { isLocaleCode } from "@/lib/i18n";

/**
 * My Desk became Discover's For You (docs/DISCOVER_PLAN.md): the reader's
 * topics now shape the front page itself instead of living in a separate
 * workspace. Old links and bookmarks land there; /desk/{id} goes to that
 * topic's view.
 */
export default async function DeskRedirect({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  permanentRedirect(`/${locale}`);
}
