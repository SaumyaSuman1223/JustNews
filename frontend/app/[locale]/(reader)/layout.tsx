import type { ReactNode } from "react";
import { notFound } from "next/navigation";

import { AquilaSidebar } from "@/components/AquilaSidebar";
import { getLocale, isLocaleCode, t } from "@/lib/i18n";

/**
 * The reader: a full-screen workspace with a paper on it.
 *
 * No rail, no mobile tab bar, no site footer. Everything the application
 * shell puts around a page is what stopped Aquila reading as a publication,
 * so this layout deliberately provides almost nothing - a dark ground, a way
 * out at the edge, and a `<main>` for the skip link to land in.
 *
 * The route group means the URL is untouched: this is still `/en/aquila`.
 */
export default async function ReaderLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);

  return (
    <div className="reader">
      <a className="skip-link" href="#main">
        {t(active.code, "skip.toContent")}
      </a>
      <AquilaSidebar locale={active.code} />
      <main id="main" tabIndex={-1} className="reader__main">
        {children}
      </main>
    </div>
  );
}
