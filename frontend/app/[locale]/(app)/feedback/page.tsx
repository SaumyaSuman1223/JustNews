import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { SignInRequired } from "@/components/SignInRequired";
import { submitFeedbackAction } from "@/lib/actions";
import { isLocaleCode, t } from "@/lib/i18n";
import { getSession } from "@/lib/session";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return { title: t(isLocaleCode(locale) ? locale : "en", "feedback.heading") };
}

export default async function FeedbackPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ sent?: string }>;
}) {
  const { locale } = await params;
  if (!isLocaleCode(locale)) notFound();
  const { sent } = await searchParams;

  const session = await getSession();
  if (!session) {
    return (
      <SignInRequired
        locale={locale}
        path={`/${locale}/feedback`}
        body={t(locale, "feedback.signInRequired")}
      />
    );
  }

  return (
    <div className="narrow">
      <div className="page-header">
        <h1>{t(locale, "feedback.heading")}</h1>
        <p>{t(locale, "feedback.body")}</p>
      </div>

      {sent === "1" && <p role="status">{t(locale, "feedback.thanks")}</p>}
      {sent === "0" && (
        <p className="form-error" role="alert">
          {t(locale, "actions.save.failed")}
        </p>
      )}

      <form action={submitFeedbackAction.bind(null, locale)}>
        <input type="hidden" name="path" value={`/${locale}/feedback`} />
        <div className="field">
          <label htmlFor="feedback-message">{t(locale, "feedback.placeholder")}</label>
          <textarea id="feedback-message" name="message" required maxLength={2000} />
        </div>
        <button type="submit" className="button button--primary">
          {t(locale, "feedback.submit")}
        </button>
      </form>
    </div>
  );
}
