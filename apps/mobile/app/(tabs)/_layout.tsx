import { Tabs } from "expo-router";

import { colors } from "@/lib/theme";

/**
 * Two tabs only this slice - Feed and Explore. Saved/History/Search/Topics
 * are real follow-on tabs, not built yet (see the plan's "explicitly
 * deferred" list).
 */
export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface },
        headerTintColor: colors.text,
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
      }}
    >
      <Tabs.Screen name="index" options={{ title: "Feed", headerTitle: "JustNews" }} />
      <Tabs.Screen name="explore" options={{ title: "Explore" }} />
    </Tabs>
  );
}
