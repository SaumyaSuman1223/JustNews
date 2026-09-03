import { router } from "expo-router";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";

import type { Article } from "@/lib/api";
import { reportClick } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { formatRelativeTime, type LocaleCode } from "@/lib/i18n";
import type { Session } from "@/lib/session";
import { colors, fonts, radius, space, type } from "@/lib/theme";

/**
 * The RN equivalent of frontend/components/ArticleCard.tsx's CardVariant
 * union - same four sizes, same idea (the page decides the shape, not the
 * ranker), rebuilt with View/Image/Pressable/Text since none of the web
 * component's JSX or CSS classes transfer.
 */
export type CardVariant = "lead" | "secondary" | "list";

const MEDIA_ASPECT: Record<CardVariant, number> = {
  lead: 4 / 3,
  secondary: 16 / 9,
  list: 1,
};

export interface ArticleCardProps {
  article: Article;
  locale: LocaleCode;
  surface: "feed" | "explore";
  position: number;
  /** The impression this card was served under, if any - see
   * frontend/components/ArticleCard.tsx's identical comment: this is what
   * lets a tap be attributed to the exact serving policy later, and it
   * cannot be backfilled if lost. */
  impressionId?: number | null;
  session: Session | null;
  variant?: CardVariant;
}

export function ArticleCard({
  article,
  locale,
  surface,
  position,
  impressionId,
  session,
  variant = "secondary",
}: ArticleCardProps) {
  async function handlePress() {
    router.push(`/article/${article.id}`);
    // Fire-and-forget, same as the web card's handleClick - never blocks the
    // navigation it accompanies. A no-op when signed out, matching
    // frontend/app/api/click/route.ts: an anonymous tap has no impression to
    // correlate against yet.
    if (!session) return;
    const sessionId = await getBrowsingSessionId();
    void reportClick(
      { accessToken: session.accessToken, sessionId },
      { articleId: article.id, surface, position, impressionId },
    );
  }

  const isList = variant === "list";

  return (
    <Pressable onPress={handlePress} style={({ pressed }) => [styles.card, pressed && styles.pressed, isList && styles.cardRow]}>
      {article.image_url && (
        <Image
          source={{ uri: article.image_url }}
          style={[
            styles.media,
            { aspectRatio: MEDIA_ASPECT[variant] },
            isList && styles.mediaList,
          ]}
        />
      )}
      <View style={[styles.body, isList && styles.bodyList]}>
        <Text
          style={[styles.title, variant === "lead" ? styles.titleLead : styles.titleDefault]}
          numberOfLines={variant === "lead" ? 4 : 3}
        >
          {article.title}
        </Text>
        {variant !== "list" && article.snippet && (
          <Text style={styles.snippet} numberOfLines={variant === "lead" ? 4 : 2}>
            {article.snippet}
          </Text>
        )}
        <View style={styles.meta}>
          <Text style={styles.source}>{article.source_name}</Text>
          <Text style={styles.metaText}>{formatRelativeTime(article.published_at, locale)}</Text>
          {article.language !== locale && (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{article.language}</Text>
            </View>
          )}
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: "hidden",
    marginHorizontal: space[4],
    marginBottom: space[4],
  },
  // Thumbnail trails the headline, same reasoning as frontend/globals.css's
  // .card--list: the headline is what gets scanned, so it gets the reading
  // edge. Hardcoded LTR ("row-reverse" puts the JSX's second child - body -
  // on the visual left) rather than RN's I18nManager, matching the launch
  // locales: all three (en/es/hi) are LTR, same as the web app today. RTL
  // verification is deferred, same note as everywhere else this session.
  cardRow: {
    flexDirection: "row-reverse",
    alignItems: "flex-start",
  },
  pressed: {
    opacity: 0.85,
  },
  media: {
    width: "100%",
    backgroundColor: colors.surfaceSub,
  },
  mediaList: {
    width: 88,
    height: 88,
    borderRadius: radius,
    margin: space[3],
  },
  body: {
    padding: space[4],
    gap: space[2],
  },
  bodyList: {
    flex: 1,
    paddingLeft: 0,
  },
  title: {
    fontFamily: fonts.display,
    color: colors.text,
  },
  titleLead: {
    fontSize: type.lead,
    lineHeight: type.lead * 1.2,
  },
  titleDefault: {
    fontSize: type.card,
    lineHeight: type.card * 1.3,
  },
  snippet: {
    fontSize: type.body,
    color: colors.textMid,
    lineHeight: type.body * 1.5,
  },
  meta: {
    flexDirection: "row",
    alignItems: "center",
    gap: space[2],
    flexWrap: "wrap",
  },
  source: {
    fontSize: type.meta,
    fontWeight: "600",
    color: colors.textMid,
  },
  metaText: {
    fontSize: type.meta,
    color: colors.textMuted,
  },
  badge: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 3,
    paddingHorizontal: space[1],
  },
  badgeText: {
    fontSize: 10,
    color: colors.textMuted,
    textTransform: "uppercase",
  },
});
