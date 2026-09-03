import { t, type LocaleCode } from "@/lib/i18n";

export function SearchBox({ locale }: { locale: LocaleCode }) {
  return (
    <form className="search-box" action={`/${locale}/search`} role="search">
      <label className="visually-hidden" htmlFor="site-search">
        {t(locale, "search.label")}
      </label>
      <input
        id="site-search"
        type="search"
        name="q"
        placeholder={t(locale, "search.placeholder")}
      />
      <button type="submit">{t(locale, "search.submit")}</button>
    </form>
  );
}
