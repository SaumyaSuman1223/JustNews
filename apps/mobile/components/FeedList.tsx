import { FlatList, RefreshControl } from "react-native";

import { ArticleCard, type CardVariant } from "@/components/ArticleCard";
import type { Article } from "@/lib/api";
import type { LocaleCode } from "@/lib/i18n";
import type { Session } from "@/lib/session";
import { colors, space } from "@/lib/theme";

export interface FeedItem {
  article: Article;
  impressionId?: number | null;
}

export interface FeedListProps {
  items: FeedItem[];
  locale: LocaleCode;
  surface: "feed" | "explore";
  session: Session | null;
  refreshing: boolean;
  onRefresh: () => void;
}

const LEAD_COUNT = 1;

/**
 * The RN equivalent of frontend/components/FeedList.tsx's variantFor(): one
 * lead, then a run of secondaries. No "list" band by position here (that
 * component's third size) - a FlatList is one column on a phone width, so a
 * dense list-row band and a secondary band would look identical; the
 * distinction is deferred along with everything else this slice doesn't need.
 */
function variantFor(index: number): CardVariant {
  return index < LEAD_COUNT ? "lead" : "secondary";
}

export function FeedList({ items, locale, surface, session, refreshing, onRefresh }: FeedListProps) {
  return (
    <FlatList
      data={items}
      keyExtractor={(item) => String(item.article.id)}
      contentContainerStyle={{ paddingVertical: space[4] }}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.accent} />}
      renderItem={({ item, index }) => (
        <ArticleCard
          article={item.article}
          locale={locale}
          surface={surface}
          position={index}
          impressionId={item.impressionId}
          session={session}
          variant={variantFor(index)}
        />
      )}
    />
  );
}
