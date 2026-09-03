import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";

import { FeedList, type FeedItem } from "@/components/FeedList";
import { Banner, EmptyState, InlineLink, SecondaryLink } from "@/components/ui";
import { getArticles, getFeed, getMe } from "@/lib/api";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { defaultLocale } from "@/lib/i18n";
import { useSession } from "@/lib/session";
import { colors } from "@/lib/theme";

/**
 * Replicates frontend/app/[locale]/page.tsx's FeedBody branch: signed-in +
 * beta access gets the personalised /v1/feed; everyone else gets the
 * anonymous chronological /v1/articles, mapped to the same {article,
 * impressionId} shape so one render path serves both - the same
 * uniform-shape trick the web page uses.
 *
 * Locale is fixed to defaultLocale this slice - a language switcher is a
 * real follow-on, not in the core reading loop this slice covers.
 */
export default function FeedScreen() {
  const { session, loading: sessionLoading } = useSession();
  const [items, setItems] = useState<FeedItem[]>([]);
  const [hasBetaAccess, setHasBetaAccess] = useState(false);
  const [degraded, setDegraded] = useState(false);
  // Starts true, so the initial load has nothing to set synchronously -
  // only the finishing `setLoading(false)` runs, from inside the async
  // function's awaited continuation, not the effect's own call frame.
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const sessionId = await getBrowsingSessionId();
    const auth = session ? { accessToken: session.accessToken, sessionId } : null;
    const profile = auth ? await getMe(auth) : null;
    const beta = profile?.has_beta_access ?? false;
    setHasBetaAccess(beta);

    if (auth && beta) {
      const page = await getFeed(auth, { locale: defaultLocale, pageSize: 24 });
      setItems(page.data.items.map((item) => ({ article: item.article, impressionId: item.impression_id })));
      setDegraded(page.degraded);
    } else {
      const page = await getArticles({ languages: defaultLocale, pageSize: 24 });
      setItems(page.data.items.map((article) => ({ article, impressionId: null })));
      setDegraded(page.degraded);
    }
  }, [session]);

  useEffect(() => {
    if (sessionLoading) return;
    load().finally(() => setLoading(false));
  }, [sessionLoading, load]);

  // Pull-to-refresh is a user gesture, not effect-driven, so setting
  // `refreshing` synchronously here is the ordinary case the lint rule that
  // applies to effects doesn't concern itself with.
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
      {session && !hasBetaAccess && (
        <Banner>
          {"JustNews is in private beta. You’re signed in, but you’ll need an invite code to unlock your personalised feed. "}
          <InlineLink href="/(auth)/invite" label="Enter your code" />
        </Banner>
      )}
      {!session && (
        <Banner>
          <InlineLink href="/(auth)/login" label="Sign in" /> for a feed personalised to what you read.
        </Banner>
      )}
      {degraded && (
        <Banner>
          {hasBetaAccess
            ? "Your feed is unavailable right now, so this may be out of date."
            : "Live headlines are unavailable right now, so this may be out of date."}
        </Banner>
      )}
      {items.length === 0 ? (
        <EmptyState
          title="Nothing here yet"
          body="We are still gathering today's coverage. Explore is the same news without the personalisation."
        />
      ) : (
        <FeedList
          items={items}
          locale={defaultLocale}
          surface="feed"
          session={session}
          refreshing={refreshing}
          onRefresh={handleRefresh}
        />
      )}
      {items.length === 0 && <SecondaryLink href="/(tabs)/explore" label="Go to Explore" />}
    </View>
  );
}
