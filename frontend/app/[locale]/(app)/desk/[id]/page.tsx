import { notFound, permanentRedirect } from "next/navigation";

import { viewHref } from "@/lib/discoverView";
import { isLocaleCode } from "@/lib/i18n";

/**
 * Topic pages became Discover's topic view: one topic experience, with the
 * topic's Perspectives in its rail. Old links, bookmarks and search results
 * land there.
 */
export default async function TopicRedirect({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}) {
  const { locale, id } = await params;
  if (!isLocaleCode(locale)) notFound();
  permanentRedirect(viewHref(locale, { kind: "topic", topicId: decodeURIComponent(id) }));
}
