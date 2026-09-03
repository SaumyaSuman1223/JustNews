import Link from "next/link";

import { locales, t, type Locale } from "@/lib/i18n";

/**
 * Every option always linked to `/${code}` - the home page - regardless of
 * where the reader was. Reading an article in Spanish and switching to
 * Hindi dropped them at the front page with no way back to what they were
 * reading, on a control whose whole job is staying in place while the
 * language underneath it changes.
 *
 * `pathname` and `search` come from request headers the middleware sets on
 * every request (`middleware.ts`), because a Server Component has no other
 * way to read the URL it is rendering for - `usePathname` is client-only,
 * and making the whole masthead a Client Component to reach one control
 * would cost every page the JS it currently ships without.
 */
export function LocaleSwitcher({
  active,
  pathname,
  search,
}: {
  active: Locale;
  pathname: string;
  search: string;
}) {
  const rest = pathname.startsWith(`/${active.code}`)
    ? pathname.slice(active.code.length + 1)
    : "";

  return (
    <nav aria-label={t(active.code, "nav.language")}>
      <ul className="locale-switcher">
        {locales.map((option) => (
          <li key={option.code}>
            <Link
              href={`/${option.code}${rest}${search}`}
              lang={option.htmlLang}
              aria-current={option.code === active.code}
            >
              {option.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
