import Link from "next/link";

import { fontVariables } from "@/lib/fonts";
import { defaultLocale, getLocale, t } from "@/lib/i18n";

/**
 * The root 404, which is the one page in the app that cannot know the
 * reader's locale: Next renders it outside the `[locale]` segment, so there
 * are no params and no matched route to read a language off. The default
 * locale is the honest answer rather than a guess, and it is stated here so
 * the `lang` attribute and the copy always agree.
 *
 * It had no title and one link. A reader who mistyped an address needs the
 * two ways back a news site offers: its front page, and its search.
 */
export default function NotFound() {
  const fallback = getLocale(defaultLocale);
  const code = fallback.code;

  return (
    <html lang={fallback.htmlLang} dir={fallback.dir} className={fontVariables}>
      <head>
        <title>{`${t(code, "notFound.heading")} · JustNews`}</title>
      </head>
      <body>
        <div className="shell not-found">
          <Link href={`/${code}`} className="wordmark not-found__wordmark">
            Just<span>News</span>
          </Link>
          <main id="main" className="not-found__body">
            <h1 className="not-found__title">{t(code, "notFound.heading")}</h1>
            <p className="not-found__note">{t(code, "notFound.body")}</p>
            <form className="not-found__search" action={`/${code}/search`} role="search">
              <label className="visually-hidden" htmlFor="not-found-q">
                {t(code, "search.placeholder")}
              </label>
              <input
                id="not-found-q"
                className="input"
                type="search"
                name="q"
                placeholder={t(code, "search.placeholder")}
              />
              <button type="submit" className="button button--primary">
                {t(code, "search.submit")}
              </button>
            </form>
            <p>
              <Link href={`/${code}`}>{t(code, "notFound.action")}</Link>
            </p>
          </main>
        </div>
      </body>
    </html>
  );
}
