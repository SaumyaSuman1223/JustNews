import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { NewPasswordForm } from "@/components/NewPasswordForm";
import { SignInRequired } from "@/components/SignInRequired";
import { getLocale, isLocaleCode, t } from "@/lib/i18n";
import { getSession } from "@/lib/session";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return { title: t(isLocaleCode(locale) ? locale : "en", "login.reset.newHeading") };
}

export default async function NewPasswordPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const active = getLocale(locale);
  // Arriving without a session means the reset link expired or was already
  // used - signing in (or asking for a new link from there) is the way on.
  if (!(await getSession())) {
    return <SignInRequired locale={active.code} path={`/${active.code}/account/password`} />;
  }
  return (
    <div className="narrow auth-shell">
      <div className="auth-card">
        <div className="auth-card__header">
          <h1>{t(active.code, "login.reset.newHeading")}</h1>
        </div>
        <NewPasswordForm locale={active.code} />
      </div>
    </div>
  );
}
