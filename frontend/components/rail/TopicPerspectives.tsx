"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Perspectives } from "@/components/Perspectives";
import type { PerspectiveGroup } from "@/lib/api";
import { t, type LocaleCode } from "@/lib/i18n";

/**
 * A topic's Perspectives in Discover's topic view: its recent reporting
 * grouped by who published it (ADR 0013). It moved here from the old topic
 * page. Fetched for whichever topic the view names, since the view changes
 * in the browser; absent when there is no topic, or nothing to group.
 */
export function TopicPerspectives({ locale }: { locale: LocaleCode }) {
  const topic = useSearchParams().get("topic");
  const [groups, setGroups] = useState<{ topic: string; groups: PerspectiveGroup[] } | null>(null);

  useEffect(() => {
    if (!topic) return;
    const controller = new AbortController();
    fetch(`/api/perspectives?topic=${encodeURIComponent(topic)}`, { signal: controller.signal })
      .then((response) => (response.ok ? (response.json() as Promise<PerspectiveGroup[]>) : []))
      .then((found) => setGroups({ topic, groups: found }))
      .catch(() => {
        // Aborted by a topic switch, or the API is away: the module stays out.
      });
    return () => controller.abort();
  }, [topic]);

  if (!topic || groups?.topic !== topic || groups.groups.length === 0) return null;
  return (
    <section className="rail-widget rail-widget--perspectives" aria-labelledby="rail-perspectives">
      <h2 className="rail-widget__title" id="rail-perspectives">
        {t(locale, "perspectives.railTitle")}
      </h2>
      <p className="rail-widget__sub">{t(locale, "perspectives.railNote")}</p>
      <Perspectives groups={groups.groups} locale={locale} headingLevel={3} />
    </section>
  );
}
