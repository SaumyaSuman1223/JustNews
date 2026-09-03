import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ArticleCard } from "@/components/ArticleCard";
import { CoverageChips } from "@/components/CoverageChips";
import { getSaves, getStory } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getLocale, isLocaleCode, locales, t, tPlural } from "@/lib/i18n";
import { getSession } from "@/lib/session";

interface RouteParams {
  locale: string;
  id: string;
}

async function loadStory(id: string) {
  const storyId = Number(id);
  if (!Number.isInteger(storyId)) return null;
  const result = await getStory(storyId);
  return result.data;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<RouteParams>;
}): Promise<Metadata> {
  const { locale, id } = await params;
  const detail = await loadStory(id);
  if (!detail) {
    return { title: t(isLocaleCode(locale) ? locale : "en", "article.notFound") };
  }
  const leadImage = detail.articles[0]?.image_url;
  return {
    title: detail.story.title,
    alternates: { canonical: `/${locale}/story/${detail.story.id}` },
    // The lead article's own photo - same reasoning as the article page:
    // falls through to the generated default when there isn't one.
    ...(leadImage && { openGraph: { images: [{ url: leadImage }] } }),
  };
}

export default async function StoryPage({ params }: { params: Promise<RouteParams> }) {
  const { locale, id } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);

  const detail = await loadStory(id);
  if (!detail) notFound();

  const session = await getSession();
  const savedIds = session
    ? await getSaves({
        accessToken: session.accessToken,
        sessionId: await getBrowsingSessionId(),
      }).then((page) => new Set(page.data.items.map((item) => item.article.id)))
    : new Set<number>();

  // Grouped by language rather than listed flat: the point of this page is
  // that the same event reads differently depending on where it is reported
  // from, and a flat list buries that. Ordered by the coverage breakdown, so
  // the language carrying the story leads.
  const order = detail.coverage.map((entry) => entry.language);
  const byLanguage = order.map((language) => ({
    language,
    label: locales.find((locale) => locale.code === language)?.label ?? language,
    htmlLang: locales.find((locale) => locale.code === language)?.htmlLang ?? language,
    articles: detail.articles.filter((article) => article.language === language),
  }));

  let position = 0;

  return (
    <>
      <div className="page-header">
        <h1>{detail.story.title}</h1>
        {/* Two sentences rather than one with an appended clause: a fragment
            glued on the end only reads correctly in languages that put it
            there, and Hindi does not. */}
        <p>
          {tPlural(active.code, "story.coveredBy", detail.story.source_count)}
          {detail.story.language_count > 1 &&
            ` ${t(active.code, "story.reportedIn", { count: detail.story.language_count })}`}
        </p>
        <CoverageChips coverage={detail.coverage} locale={active.code} />
      </div>

      {byLanguage.map((group) => (
        <section key={group.language} className="coverage-group">
          <h2 className="coverage-group__heading">
            <span lang={group.htmlLang}>{group.label}</span>
            <span className="coverage-group__count">
              {tPlural(active.code, "story.reports", group.articles.length)}
            </span>
          </h2>
          <ul className="feed">
            {group.articles.map((article) => (
              <ArticleCard
                key={article.id}
                article={article}
                locale={active.code}
                surface="topic"
                position={position++}
                signedIn={Boolean(session)}
                saved={savedIds.has(article.id)}
                revalidatePath={`/${active.code}/story/${detail.story.id}`}
              />
            ))}
          </ul>
        </section>
      ))}
    </>
  );
}
