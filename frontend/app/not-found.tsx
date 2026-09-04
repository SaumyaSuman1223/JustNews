import Link from "next/link";

import { fontVariables } from "@/lib/fonts";
import { defaultLocale, getLocale, t } from "@/lib/i18n";

/**
 * The root 404, which is the one page in the app that cannot know the
 * reader's locale: Next renders it outside the `[locale]` segment, so there
 * are no params and no matched route to read a language off. The default
 * locale is the honest answer rather than a guess, and it is stated here so
 * the `lang` attribute and the copy always agree - they did not before, when
 * the markup said `lang="en"` regardless.
 */
export default function NotFound() {
  const fallback = getLocale(defaultLocale);

  return (
    <html lang={fallback.htmlLang} dir={fallback.dir} className={fontVariables}>
      <body>
        <div className="shell">
          <main id="main" className="empty" style={{ marginBlockStart: "4rem" }}>
            {/* Without the class this heading drops out of the display face
                and renders in the browser's default sans - the only heading
                in the app that did. */}
            <h1 className="empty__title">{t(fallback.code, "notFound.heading")}</h1>
            <p>
              <Link href={`/${fallback.code}`}>{t(fallback.code, "notFound.action")}</Link>
            </p>
          </main>
        </div>
      </body>
    </html>
  );
}
