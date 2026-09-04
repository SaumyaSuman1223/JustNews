import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
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

function ChipListSkeleton() {
  return (
    <ul className="chip-list" aria-hidden="true">
      {Array.from({ length: 12 }, (_, index) => (
        <li key={index}>
          <div className="skeleton skeleton--chip" />
        </li>
      ))}
    </ul>
  );
}

export default async function TopicsPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);

  return (
    <>
      <div className="page-header">
        <h1>{t(active.code, "topics.heading")}</h1>
        <p>{t(active.code, "topics.intro")}</p>
      </div>
      <Suspense fallback={<ChipListSkeleton />}>
        <TopicsBody locale={active.code} />
      </Suspense>
    </>
  );
}

async function TopicsBody({ locale }: { locale: ReturnType<typeof getLocale>["code"] }) {
  const topics = await getTopics(locale);

  if (topics.degraded) {
    return (
      <p className="notice" role="status">
        {t(locale, "topics.degraded")}
      </p>
    );
  }

  return (
    <ul className="chip-list">
      {topics.data.map((topic) => (
        <li key={topic.id}>
          <Link className="chip" href={`/${locale}/desk/${encodeURIComponent(topic.id)}`}>
            {topic.label}
          </Link>
        </li>
      ))}
    </ul>
  );
}
