import { router } from "expo-router";
import { useState } from "react";
import { ScrollView, Text } from "react-native";

import { Banner, ErrorText, Field, PasswordField, PrimaryButton, Screen } from "@/components/ui";
import { MIN_PASSWORD, readableAuthError } from "@/lib/authErrors";
import { supabase } from "@/lib/supabase";
import { colors, space, type } from "@/lib/theme";

export default function SignUpScreen() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit() {
    setError(null);
    setNotice(null);
    if (password.length < MIN_PASSWORD) {
      setError(`Choose a password of at least ${MIN_PASSWORD} characters.`);
      return;
    }
    setPending(true);
    const { error: signUpError } = await supabase!.auth.signUp({ email, password });
    setPending(false);
    if (signUpError) {
      setError(readableAuthError(signUpError.message));
      return;
    }
    setNotice("Check your email to confirm your account, then sign in.");
  }

  return (
    <Screen>
      <ScrollView contentContainerStyle={{ padding: space[4] }} keyboardShouldPersistTaps="handled">
        {error && <ErrorText>{error}</ErrorText>}
        {notice && <Banner>{notice}</Banner>}
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
          textContentType="newPassword"
          autoComplete="new-password"
        />
        <PrimaryButton
          label={pending ? "Creating account…" : "Create account"}
          onPress={handleSubmit}
          disabled={pending}
        />
        <Text
          onPress={() => router.push("/(auth)/login")}
          style={{ marginTop: space[4], textAlign: "center", color: colors.accent, fontSize: type.body }}
        >
          Already have one? Sign in
        </Text>
      </ScrollView>
    </Screen>
  );
}
