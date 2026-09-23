import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getLocale, isLocaleCode, t } from "@/lib/i18n";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return { title: t(isLocaleCode(locale) ? locale : "en", "how.heading") };
}

const SECTIONS = ["stories", "languages", "perspectives", "aquila", "ranking", "data"] as const;

/**
 * What the product's ideas are, in plain words (fifth pass F9): help and
 * documentation scored 1/4, and nothing anywhere explained story clustering,
 * Perspectives or what an Aquila edition is. Every sentence here describes
 * what the product does today - the ranking section names the heuristic
 * that actually runs, not the learned model that is still being built.
 */
export default async function HowItWorksPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);

  return (
    <article className="narrow how">
      <div className="page-header">
        <h1>{t(active.code, "how.heading")}</h1>
        <p>{t(active.code, "how.intro")}</p>
      </div>
      {SECTIONS.map((section) => (
        <section key={section} className="how__section">
          <h2>{t(active.code, `how.${section}.title`)}</h2>
          <p>{t(active.code, `how.${section}.body`)}</p>
        </section>
      ))}
      <p className="how__more">
        <Link href={`/${active.code}/privacy`}>{t(active.code, "nav.privacy")}</Link>
        {" · "}
        <Link href={`/${active.code}/feedback`}>{t(active.code, "nav.feedback")}</Link>
      </p>
    </article>
  );
}
