import Link from "next/link";

import { t, type LocaleCode } from "@/lib/i18n";

export function BetaGateNotice({ locale }: { locale: LocaleCode }) {
  return (
    <p className="notice" role="status">
      {t(locale, "beta.notice")}{" "}
      <Link href={`/${locale}/invite`}>{t(locale, "beta.enterCode")}</Link>
    </p>
  );
}
