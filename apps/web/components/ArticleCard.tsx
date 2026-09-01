"use client";

import Image from "next/image";
import Link from "next/link";

import { ArticleActions } from "@/components/ArticleActions";
import type { Article } from "@/lib/api";
import { formatRelativeTime, type LocaleCode } from "@/lib/i18n";

export interface ArticleCardProps {
  article: Article;
  locale: LocaleCode;
  /** Where this card was shown - logged with the click, for later analysis. */
  surface: "feed" | "explore" | "search" | "topic";
  position: number;
  /** Only a signed-in reader gets save / not-interested controls. */
  signedIn: boolean;
  saved?: boolean;
  /** Revalidated after a save/unsave/not-interested action. */
  revalidatePath: string;
  /** Extra context line under the metadata row, e.g. "Viewed 3 hours ago". */
  footnote?: string;
}

export function ArticleCard({
  article,
  locale,
  surface,
  position,
  signedIn,
  saved = false,
  revalidatePath,
  footnote,
}: ArticleCardProps) {
  function handleClick() {
    // Fire-and-forget: never block or delay the navigation this accompanies.
    // Anonymous visits are a no-op server-side (see the route).
    void fetch("/api/click", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ articleId: article.id, surface, position }),
      keepalive: true,
    });
  }

  return (
    <li className="card">
      {article.image_url && (
        <Image
          className="card__media"
          src={article.image_url}
          alt=""
          width={640}
          height={360}
          unoptimized
        />
      )}
      <div className="card__body">
        <h2 className="card__title">
          {/* The publisher link lives on the detail page, alongside related
              coverage - never fabricated full text, always a click away. */}
          <Link href={`/${locale}/a/${article.id}`} onClick={handleClick}>
            {article.title}
          </Link>
        </h2>
        {article.snippet && <p className="card__snippet">{article.snippet}</p>}
        <p className="card__meta">
          <span>{article.source_name}</span>
          <time dateTime={article.published_at}>
            {formatRelativeTime(article.published_at, locale)}
          </time>
          {article.language !== locale && <span className="badge">{article.language}</span>}
        </p>
        {footnote && <p className="card__footnote">{footnote}</p>}
        {signedIn && (
          <ArticleActions
            articleId={article.id}
            surface={surface}
            saved={saved}
            revalidatePath={revalidatePath}
          />
        )}
      </div>
    </li>
  );
}
