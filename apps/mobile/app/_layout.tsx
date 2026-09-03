import {
  PlayfairDisplay_600SemiBold,
  PlayfairDisplay_700Bold,
  useFonts,
} from "@expo-google-fonts/playfair-display";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { ActivityIndicator, View } from "react-native";

import { SessionProvider } from "@/lib/session";
import { colors } from "@/lib/theme";

/**
 * Font loading and session loading are unrelated concerns that don't need to
 * gate on each other. This used to be one `if (!fontsLoaded) return <...>;`
 * that swapped the *entire* tree - SessionProvider included - for a bare
 * loading view, then mounted SessionProvider, the Stack, and the first
 * matched screen all in one commit once fonts resolved. That "replace the
 * whole subtree based on async state" shape is a known way to trigger
 * React's "state update on a component that hasn't mounted yet" warning,
 * seen on real-device testing - screens fired their own mount effects inside
 * the same commit that was still settling SessionProvider's.
 *
 * SessionProvider now mounts unconditionally, on the very first render, and
 * stays mounted for the app's lifetime. Only the *content* below it waits on
 * fonts, so nothing downstream mounts as part of a subtree swap.
 */
export default function RootLayout() {
  const [fontsLoaded] = useFonts({ PlayfairDisplay_600SemiBold, PlayfairDisplay_700Bold });

  return (
    <SessionProvider>
      <StatusBar style="dark" />
      {fontsLoaded ? (
        <Stack
          screenOptions={{
            headerStyle: { backgroundColor: colors.surface },
            headerTintColor: colors.text,
            contentStyle: { backgroundColor: colors.ground },
          }}
        >
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen name="(auth)/login" options={{ title: "Sign in" }} />
          <Stack.Screen name="(auth)/signup" options={{ title: "Create an account" }} />
          <Stack.Screen name="(auth)/invite" options={{ title: "You're invited" }} />
          <Stack.Screen name="article/[id]" options={{ title: "" }} />
        </Stack>
      ) : (
        // A blank frame instead of a flash of the wrong typeface - the RN
        // equivalent of frontend/globals.css's `font-display: swap` concern,
        // just solved by waiting rather than a metric-matched fallback (out
        // of scope for a first slice - one screen's worth of headlines, not
        // a whole site's layout-shift budget).
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.ground }}>
          <ActivityIndicator color={colors.accent} />
        </View>
      )}
    </SessionProvider>
  );
}
