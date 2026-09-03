import { useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, Image, Linking, ScrollView, StyleSheet, Text, View } from "react-native";

import { EmptyState, PrimaryButton } from "@/components/ui";
import { getArticle, type Article } from "@/lib/api";
import { defaultLocale, formatRelativeTime } from "@/lib/i18n";
import { colors, fonts, radius, space, type } from "@/lib/theme";

/**
 * Replicates frontend/app/[locale]/a/[id]/page.tsx's data logic minus
 * story/coverage/related (deferred). CLAUDE.md's rule against ever storing
 * or rendering full article text holds unchanged here - it's the same API
 * response as the web app reads, just a different renderer; the outbound
 * link is the primary action, same as the web card's "Read the full story".
 */
export default function ArticleScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [article, setArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    const articleId = Number(id);
    if (!Number.isInteger(articleId)) {
      setNotFound(true);
      setLoading(false);
      return;
    }
    getArticle(articleId).then((result) => {
      if (!result.data) {
        setNotFound(true);
      } else {
        setArticle(result.data);
      }
      setLoading(false);
    });
  }, [id]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.accent} />
      </View>
    );
  }

  if (notFound || !article) {
    return (
      <View style={styles.screen}>
        <EmptyState title="Article not found" body="It may have been removed." />
      </View>
    );
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={{ padding: space[4] }}>
      <View style={styles.meta}>
        <Text style={styles.source}>{article.source_name}</Text>
        <Text style={styles.metaText}>{formatRelativeTime(article.published_at, defaultLocale)}</Text>
        {article.language !== defaultLocale && (
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{article.language}</Text>
          </View>
        )}
      </View>
      <Text style={styles.title}>{article.title}</Text>
      {article.image_url && <Image source={{ uri: article.image_url }} style={styles.media} />}
      {article.snippet && <Text style={styles.snippet}>{article.snippet}</Text>}
      <View style={{ marginTop: space[6] }}>
        <PrimaryButton
          label={`Read the full story at ${article.source_name}`}
          onPress={() => Linking.openURL(article.url)}
        />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.ground,
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.ground,
  },
  meta: {
    flexDirection: "row",
    alignItems: "center",
    gap: space[2],
    marginBottom: space[2],
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
  title: {
    fontFamily: fonts.displayBold,
    fontSize: type.lead,
    lineHeight: type.lead * 1.25,
    color: colors.text,
    marginBottom: space[4],
  },
  media: {
    width: "100%",
    aspectRatio: 16 / 9,
    borderRadius: radius,
    backgroundColor: colors.surfaceSub,
    marginBottom: space[4],
  },
  snippet: {
    fontSize: type.body + 1,
    lineHeight: (type.body + 1) * 1.6,
    color: colors.textMid,
  },
});
