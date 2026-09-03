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

export default function RootLayout() {
  const [fontsLoaded] = useFonts({ PlayfairDisplay_600SemiBold, PlayfairDisplay_700Bold });

  // A blank frame instead of a flash of the wrong typeface - the RN
  // equivalent of frontend/globals.css's `font-display: swap` concern, just
  // solved by waiting rather than by a metric-matched fallback (out of scope
  // for a first slice; there is exactly one screen's worth of headlines to
  // get right here, not a whole site's worth of layout-shift budget).
  if (!fontsLoaded) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.ground }}>
        <ActivityIndicator color={colors.accent} />
      </View>
    );
  }

  return (
    <SessionProvider>
      <StatusBar style="dark" />
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
    </SessionProvider>
  );
}
