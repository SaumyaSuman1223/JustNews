import { router } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, ScrollView, Text, View } from "react-native";

import { EmptyState, ErrorText, Field, PrimaryButton, Screen } from "@/components/ui";
import { getBrowsingSessionId } from "@/lib/browsingSession";
import { getMe, redeemInvite } from "@/lib/api";
import { useSession } from "@/lib/session";
import { colors, space, type } from "@/lib/theme";

/**
 * Mirrors frontend/app/[locale]/invite/page.tsx + InviteForm.tsx: check
 * has_beta_access first (an already-unlocked reader who lands here just gets
 * sent to the feed), otherwise a code field against the same
 * POST /v1/invites/redeem endpoint.
 */
export default function InviteScreen() {
  const { session, loading: sessionLoading } = useSession();
  const [checking, setChecking] = useState(true);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (sessionLoading) return;
    if (!session) {
      setChecking(false);
      return;
    }
    getBrowsingSessionId().then((sessionId) =>
      getMe({ accessToken: session.accessToken, sessionId }).then((profile) => {
        if (profile?.has_beta_access) {
          router.replace("/");
          return;
        }
        setChecking(false);
      }),
    );
  }, [session, sessionLoading]);

  if (sessionLoading || checking) {
    return (
      <Screen>
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}>
          <ActivityIndicator color={colors.accent} />
        </View>
      </Screen>
    );
  }

  if (!session) {
    return (
      <Screen>
        <EmptyState
          title="Sign in first"
          body="You need an account before a code can unlock anything on it."
        />
      </Screen>
    );
  }

  async function handleSubmit() {
    if (!session || !code) return;
    setError(null);
    setPending(true);
    const sessionId = await getBrowsingSessionId();
    const result = await redeemInvite({ accessToken: session.accessToken, sessionId }, code);
    setPending(false);
    if (!result.ok) {
      setError(result.message ?? "That code did not work.");
      return;
    }
    router.replace("/");
  }

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ padding: space[4] }} keyboardShouldPersistTaps="handled">
        <Text style={{ fontSize: type.body, color: colors.textMid, marginBottom: space[4] }}>
          JustNews is in private beta. Enter your invite code to unlock your personalised feed.
        </Text>
        {error && <ErrorText>{error}</ErrorText>}
        <Field label="Invite code" value={code} onChangeText={setCode} autoCapitalize="characters" />
        <PrimaryButton label={pending ? "Checking…" : "Unlock"} onPress={handleSubmit} disabled={pending || !code} />
      </ScrollView>
    </Screen>
  );
}
