import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getTopics } from "@/lib/api";
import { getLocale, isLocaleCode } from "@/lib/i18n";

export const metadata: Metadata = { title: "Topics" };

export default async function TopicsPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);

  const topics = await getTopics(active.code);

  return (
    <>
      <div className="page-header">
        <h1>Topics</h1>
        <p>Browse headlines by subject, using the IPTC Media Topics taxonomy.</p>
      </div>

      {topics.degraded ? (
        <p className="notice" role="status">
          Topics are unavailable right now.
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
