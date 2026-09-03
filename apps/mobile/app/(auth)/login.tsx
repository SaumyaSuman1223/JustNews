import { router } from "expo-router";
import { useState } from "react";
import { ScrollView, Text } from "react-native";

import { EmptyState, ErrorText, Field, PasswordField, PrimaryButton, Screen } from "@/components/ui";
import { readableAuthError } from "@/lib/authErrors";
import { isSupabaseConfigured, supabase } from "@/lib/supabase";
import { colors, space, type } from "@/lib/theme";

/**
 * Mirrors frontend/components/LoginForm.tsx's sign-in path and error
 * handling - not its JSX, which doesn't transfer to RN. Sign-up is a
 * separate screen here rather than a mode toggle: RN navigation makes "go to
 * a different screen" cheaper than the web form's client-side mode switch.
 */
export default function LoginScreen() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  if (!isSupabaseConfigured || !supabase) {
    return (
      <Screen>
        <EmptyState
          title="Accounts aren't set up in this build"
          body="Browsing, search and exploration all work without one - saved articles, history and a personalised feed need sign-in."
        />
      </Screen>
    );
  }

  async function handleSubmit() {
    setError(null);
    setPending(true);
    const { error: signInError } = await supabase!.auth.signInWithPassword({ email, password });
    setPending(false);
    if (signInError) {
      setError(readableAuthError(signInError.message));
      return;
    }
    router.replace("/");
  }

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ padding: space[4] }} keyboardShouldPersistTaps="handled">
        {error && <ErrorText>{error}</ErrorText>}
        <Field
          label="Email"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          textContentType="emailAddress"
          autoComplete="email"
        />
        <PasswordField
          label="Password"
          value={password}
          onChangeText={setPassword}
          textContentType="password"
          autoComplete="current-password"
        />
        <PrimaryButton label={pending ? "Signing in…" : "Sign in"} onPress={handleSubmit} disabled={pending} />
        <Text
          onPress={() => router.push("/(auth)/signup")}
          style={{ marginTop: space[4], textAlign: "center", color: colors.accent, fontSize: type.body }}
        >
          New here? Create an account
        </Text>
      </ScrollView>
    </Screen>
  );
}
