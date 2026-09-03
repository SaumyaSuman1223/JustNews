import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";

import { FeedList, type FeedItem } from "@/components/FeedList";
import { Banner, EmptyState } from "@/components/ui";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getExplore } from "@/lib/api";
import { defaultLocale } from "@/lib/i18n";
import { useSession } from "@/lib/session";
import { colors } from "@/lib/theme";

/**
 * Replicates frontend/app/[locale]/explore/page.tsx's ExploreBody: no beta
 * gate, works signed-out - `auth` may be null and getExplore already accepts
 * that (frontend/lib/api.ts's own signature). Blindspot rail and editions
 * chips are deferred (this slice's "core reading loop" is feed + explore +
 * article, not the differentiator surfaces yet).
 */
export default function ExploreScreen() {
  const { session, loading: sessionLoading } = useSession();
  const [items, setItems] = useState<FeedItem[]>([]);
  const [degraded, setDegraded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const sessionId = await getBrowsingSessionId();
    const auth = session ? { accessToken: session.accessToken, sessionId } : null;
    const page = await getExplore(auth, { locale: defaultLocale, languages: defaultLocale, pageSize: 24 });
    setItems(page.data.items.map((item) => ({ article: item.article, impressionId: item.impression_id })));
    setDegraded(page.degraded);
  }, [session]);

  useEffect(() => {
    if (sessionLoading) return;
    load().finally(() => setLoading(false));
  }, [sessionLoading, load]);

  function handleRefresh() {
    setRefreshing(true);
    load().finally(() => setRefreshing(false));
  }

  if (sessionLoading || loading) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.ground }}>
        <ActivityIndicator color={colors.accent} />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.ground }}>
      {degraded && <Banner>Live headlines are unavailable right now, so this may be out of date.</Banner>}
      {items.length === 0 ? (
        <EmptyState
          title="Nothing to explore yet"
          body="No sources we follow have published recently. Pull to refresh in a moment."
        />
      ) : (
        <FeedList
          items={items}
          locale={defaultLocale}
          surface="explore"
          session={session}
          refreshing={refreshing}
          onRefresh={handleRefresh}
        />
      )}
    </View>
  );
}
