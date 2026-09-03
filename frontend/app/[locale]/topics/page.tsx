import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getTopics } from "@/lib/api";
import { getLocale, isLocaleCode, t } from "@/lib/i18n";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return { title: t(isLocaleCode(locale) ? locale : "en", "topics.heading") };
}

export default async function TopicsPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);

  const topics = await getTopics(active.code);

  return (
    <>
      <div className="page-header">
        <h1>{t(active.code, "topics.heading")}</h1>
        <p>{t(active.code, "topics.intro")}</p>
      </div>

      {topics.degraded ? (
        <p className="notice" role="status">
          {t(active.code, "topics.degraded")}
        </p>
      ) : (
        <ul className="chip-list">
          {topics.data.map((topic) => (
            <li key={topic.id}>
              <Link className="chip" href={`/${active.code}/topics/${encodeURIComponent(topic.id)}`}>
                {topic.label}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
