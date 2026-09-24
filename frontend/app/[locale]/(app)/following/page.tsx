import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/EmptyState";
import { FeedSkeleton } from "@/components/FeedSkeleton";
import { getFollowedStories } from "@/lib/api";
import { getLocale, isLocaleCode, t, tPlural } from "@/lib/i18n";
import { requireBetaAccess } from "@/lib/guards";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return { title: t(isLocaleCode(locale) ? locale : "en", "nav.following") };
}

/**
 * The stories a reader follows, each with what arrived since they last
 * opened it. This lived on My Desk until Discover replaced it; following a
 * story is only worth anything if the reader can find it again.
 */
export default async function FollowingPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);

  return (
    <>
      <div className="page-header">
        <h1>{t(active.code, "following.heading")}</h1>
      </div>
      <Suspense fallback={<FeedSkeleton layout="list" secondaries={0} />}>
        <FollowingBody locale={active.code} />
      </Suspense>
    </>
  );
}

async function FollowingBody({ locale }: { locale: ReturnType<typeof getLocale>["code"] }) {
  const access = await requireBetaAccess(locale, `/${locale}/following`, {
    // The page's own h1 already names it; the prompt says what it holds.
    title: t(locale, "account.signIn"),
    body: t(locale, "signIn.following.body"),
    embedded: true,
  });
  if (!access.ok) return access.element;

  const stories = await getFollowedStories(access.auth);
  if (stories.length === 0) {
    return (
      <EmptyState
        title={t(locale, "following.empty.title")}
        body={t(locale, "following.empty.body")}
        action={{ href: `/${locale}`, label: t(locale, "common.backToFeed") }}
      />
    );
  }

  // Most news first: a story that moved is the reason to open this page.
  const ordered = [...stories].sort((a, b) => b.new_reports - a.new_reports);
  return (
    <section>
      <p className="following__note">{t(locale, "following.note")}</p>
      <ul className="followed-stories">
        {ordered.map((story) => (
          <li key={story.story_id}>
            <Link href={`/${locale}/story/${story.story_id}`}>{story.title}</Link>
            <span
              className={
                story.new_reports > 0
                  ? "followed-stories__count followed-stories__count--new"
                  : "followed-stories__count"
              }
            >
              {story.new_reports > 0
                ? tPlural(locale, "following.new", story.new_reports)
                : t(locale, "following.upToDate")}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
