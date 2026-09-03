import AsyncStorage from "@react-native-async-storage/async-storage";
import { randomUUID } from "expo-crypto";

/**
 * Groups one browsing session's impressions and interactions together,
 * independent of identity - the same concept as frontend/lib/browsingSession.ts's
 * `jn_sid` cookie, set once by middleware.ts before any request runs. There
 * is no middleware layer here, so this generates and persists the id itself,
 * on first read, and reuses it after.
 */
const BROWSING_SESSION_KEY = "jn_sid";

let cached: string | null = null;

export async function getBrowsingSessionId(): Promise<string> {
  if (cached) return cached;
  const stored = await AsyncStorage.getItem(BROWSING_SESSION_KEY);
  if (stored) {
    cached = stored;
    return stored;
  }
  const generated = randomUUID();
  await AsyncStorage.setItem(BROWSING_SESSION_KEY, generated);
  cached = generated;
  return generated;
}
