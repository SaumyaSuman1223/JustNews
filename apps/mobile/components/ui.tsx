import { Link, router } from "expo-router";
import { useState, type ReactNode } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type TextInputProps,
} from "react-native";

import { colors, radius, space, type } from "@/lib/theme";

/**
 * A small primitive kit standing in for frontend/app/globals.css's `.button`,
 * `.field`, `.notice`/`.callout` and `.empty` classes - not a port (RN has no
 * CSS), just the same handful of shapes so every screen looks like one
 * product rather than each screen inventing its own controls.
 */

export function Screen({ children }: { children: ReactNode }) {
  return <View style={styles.screen}>{children}</View>;
}

export function PrimaryButton({
  label,
  onPress,
  disabled,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.button,
        styles.buttonPrimary,
        (disabled || pressed) && styles.buttonPressed,
      ]}
    >
      {disabled ? (
        <ActivityIndicator color={colors.ground} />
      ) : (
        <Text style={styles.buttonPrimaryText}>{label}</Text>
      )}
    </Pressable>
  );
}

export function SecondaryLink({ href, label }: { href: string; label: string }) {
  // Not `<Link asChild><Pressable>...` - verified live that this build's web
  // target drops the Pressable's own style entirely when wrapped that way
  // (only its inner Text survives the merge), leaving an unstyled anchor.
  // A plain Pressable calling router.push is the same pattern
  // ArticleCard.tsx already uses for navigation, so this isn't a second way
  // of doing the same thing.
  return (
    <Pressable
      onPress={() => router.push(href as never)}
      style={({ pressed }) => [styles.button, styles.buttonSecondary, pressed && styles.buttonPressed]}
    >
      <Text style={styles.buttonSecondaryText}>{label}</Text>
    </Pressable>
  );
}

/** An inline link inside running text - frontend/globals.css's `.link-button`
 * equivalent. `Link`'s own default style has no color or weight, so without
 * this it renders indistinguishable from its surrounding text. */
export function InlineLink({ href, label }: { href: string; label: string }) {
  return (
    <Link href={href} style={styles.inlineLink}>
      {label}
    </Link>
  );
}

export function Field({
  label,
  ...inputProps
}: { label: string } & TextInputProps) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput
        style={styles.fieldInput}
        placeholderTextColor={colors.textMuted}
        autoCapitalize="none"
        autoCorrect={false}
        {...inputProps}
      />
    </View>
  );
}

/** A password field with its own show/hide toggle - RN's TextInput has no
 * built-in reveal control the way a browser's does. */
export function PasswordField({ label, ...inputProps }: { label: string } & TextInputProps) {
  const [visible, setVisible] = useState(false);
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <View style={styles.passwordRow}>
        <TextInput
          style={[styles.fieldInput, styles.passwordInput]}
          placeholderTextColor={colors.textMuted}
          autoCapitalize="none"
          autoCorrect={false}
          secureTextEntry={!visible}
          {...inputProps}
        />
        <Pressable onPress={() => setVisible((value) => !value)} hitSlop={8}>
          <Text style={styles.passwordToggle}>{visible ? "Hide" : "Show"}</Text>
        </Pressable>
      </View>
    </View>
  );
}

export function ErrorText({ children }: { children: string }) {
  return <Text style={styles.error}>{children}</Text>;
}

/** For something the reader should notice but isn't wrong - the beta-gate
 * banner, a degraded-data banner. Not `.error`'s danger color: a banner isn't
 * a failure, it's a status. */
export function Banner({ children }: { children: ReactNode }) {
  return (
    <View style={styles.banner}>
      <Text style={styles.bannerText}>{children}</Text>
    </View>
  );
}

export function EmptyState({ title, body }: { title: string; body?: string }) {
  return (
    <View style={styles.empty}>
      <Text style={styles.emptyTitle}>{title}</Text>
      {body && <Text style={styles.emptyBody}>{body}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.ground,
  },
  button: {
    borderRadius: radius,
    paddingVertical: space[3],
    paddingHorizontal: space[4],
    alignItems: "center",
    justifyContent: "center",
  },
  buttonPrimary: {
    backgroundColor: colors.accent,
  },
  buttonPrimaryText: {
    color: colors.ground,
    fontSize: type.body,
    fontWeight: "600",
  },
  buttonSecondary: {
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  buttonSecondaryText: {
    color: colors.text,
    fontSize: type.body,
    fontWeight: "600",
  },
  buttonPressed: {
    opacity: 0.7,
  },
  field: {
    gap: space[1],
    marginBottom: space[4],
  },
  fieldLabel: {
    fontSize: type.meta,
    fontWeight: "600",
    color: colors.textMid,
  },
  fieldInput: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius,
    paddingVertical: space[3],
    paddingHorizontal: space[3],
    fontSize: type.body,
    color: colors.text,
    backgroundColor: colors.surface,
  },
  passwordRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: space[2],
  },
  passwordInput: {
    flex: 1,
  },
  passwordToggle: {
    color: colors.accent,
    fontSize: type.meta,
    fontWeight: "600",
  },
  error: {
    color: colors.danger,
    fontSize: type.body,
    marginBottom: space[3],
  },
  banner: {
    borderWidth: 1,
    borderColor: colors.border,
    borderLeftWidth: 3,
    borderLeftColor: colors.accent,
    borderRadius: radius,
    backgroundColor: colors.surface,
    padding: space[3],
    marginHorizontal: space[4],
    marginBottom: space[4],
  },
  bannerText: {
    color: colors.textMid,
    fontSize: type.body,
  },
  inlineLink: {
    color: colors.accent,
    fontWeight: "600",
    fontSize: type.body,
  },
  empty: {
    alignItems: "center",
    gap: space[3],
    padding: space[8],
  },
  emptyTitle: {
    fontSize: type.section,
    fontWeight: "600",
    color: colors.text,
    textAlign: "center",
  },
  emptyBody: {
    fontSize: type.body,
    color: colors.textMuted,
    textAlign: "center",
  },
});
