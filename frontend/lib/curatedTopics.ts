import type { LocaleCode } from "@/lib/i18n";

/**
 * A presentation-only editorial layer over IPTC concept ids (§24: "I care
 * about AI", not "I must choose an IPTC taxonomy"). The id stays the
 * canonical key (ADR 0006) - this only swaps the label shown for it, the
 * same way `service.label_for` already swaps in a translated label. Nothing
 * here is written to the database, and no id below is invented: every key is
 * one of the 17 top-level IPTC Media Topics concepts seeded in
 * `packages/core/src/justnews_core/taxonomy.py` - kept in sync by hand,
 * since the two lists live in different languages.
 *
 * A topic id with no entry here falls back to its own API label
 * (`curatedTopicLabel`'s third argument) rather than disappearing or
 * showing a placeholder - the only way this stays honest for ids nobody
 * has curated yet.
 */
const CURATED_LABELS: Record<string, Partial<Record<LocaleCode, string>>> = {
  "medtop:01000000": { en: "Culture", es: "Cultura", hi: "संस्कृति" },
  "medtop:02000000": { en: "Crime & Justice", es: "Crimen y justicia", hi: "अपराध और न्याय" },
  "medtop:03000000": { en: "Disasters", es: "Desastres", hi: "आपदाएँ" },
  "medtop:04000000": { en: "Markets", es: "Mercados", hi: "बाज़ार" },
  "medtop:05000000": { en: "Education", es: "Educación", hi: "शिक्षा" },
  "medtop:06000000": { en: "Climate", es: "Clima", hi: "जलवायु" },
  "medtop:07000000": { en: "Health", es: "Salud", hi: "स्वास्थ्य" },
  "medtop:08000000": { en: "Human Interest", es: "Interés humano", hi: "मानव रुचि" },
  "medtop:09000000": { en: "Labour", es: "Trabajo", hi: "श्रम" },
  "medtop:10000000": { en: "Lifestyle", es: "Estilo de vida", hi: "जीवनशैली" },
  "medtop:11000000": { en: "Politics", es: "Política", hi: "राजनीति" },
  "medtop:12000000": { en: "Religion", es: "Religión", hi: "धर्म" },
  "medtop:13000000": { en: "Tech & Science", es: "Tecnología y ciencia", hi: "तकनीक और विज्ञान" },
  "medtop:14000000": { en: "Society", es: "Sociedad", hi: "समाज" },
  "medtop:15000000": { en: "Sport", es: "Deporte", hi: "खेल" },
  "medtop:16000000": { en: "Conflict", es: "Conflicto", hi: "संघर्ष" },
  "medtop:17000000": { en: "Weather", es: "Tiempo", hi: "मौसम" },
  // Below the top level: real rows already in this corpus, curated by id
  // like everything above rather than exempted from it. Not exhaustive -
  // any topic id an admin adds beyond this list still renders, just with
  // its own API label until someone adds it here.
  "medtop:20000045": { en: "AI", es: "IA", hi: "एआई" },
};

export function curatedTopicLabel(id: string, fallback: string, locale: LocaleCode): string {
  return CURATED_LABELS[id]?.[locale] ?? fallback;
}

/** Same list, labels swapped in-place - so every downstream reader (tiles,
 * the add-topic picker, "what changed" headings) gets the curated label for
 * free without repeating the lookup at each call site. */
export function withCuratedLabels<T extends { id: string; label: string }>(
  topics: T[],
  locale: LocaleCode,
): T[] {
  return topics.map((topic) => ({
    ...topic,
    label: curatedTopicLabel(topic.id, topic.label, locale),
  }));
}
