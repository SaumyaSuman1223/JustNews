import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { setDisplayPreferencesAction } from "@/lib/actions";
import { getLocale, isLocaleCode, t } from "@/lib/i18n";
import { getReaderPreferences } from "@/lib/preferences";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return { title: t(isLocaleCode(locale) ? locale : "en", "display.heading") };
}

/**
 * Theme and text size (fifth pass F8), for everyone - Settings needs an
 * account, and how a page looks should not. A plain form with a submit
 * button, so it works without JavaScript; choices are stored in two display
 * cookies (see lib/preferences.ts).
 */
export default async function DisplayPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  const { theme, textSize } = await getReaderPreferences();

  const themes = ["system", "light", "dark"] as const;
  const sizes = ["standard", "large"] as const;

  return (
    <div className="narrow">
      <div className="page-header">
        <h1>{t(active.code, "display.heading")}</h1>
        <p>{t(active.code, "display.intro")}</p>
      </div>

      <form action={setDisplayPreferencesAction} className="display-form">
        <fieldset className="display-form__group">
          <legend>{t(active.code, "display.theme")}</legend>
          {themes.map((value) => (
            <label key={value} className="display-form__option">
              <input type="radio" name="theme" value={value} defaultChecked={theme === value} />
              <span>{t(active.code, `display.theme.${value}`)}</span>
            </label>
          ))}
        </fieldset>

        <fieldset className="display-form__group">
          <legend>{t(active.code, "display.textSize")}</legend>
          {sizes.map((value) => (
            <label key={value} className="display-form__option">
              <input
                type="radio"
                name="textSize"
                value={value}
                defaultChecked={textSize === value}
              />
              <span>{t(active.code, `display.textSize.${value}`)}</span>
            </label>
          ))}
        </fieldset>

        <button type="submit" className="button button--primary">
          {t(active.code, "display.save")}
        </button>
      </form>
    </div>
  );
}
