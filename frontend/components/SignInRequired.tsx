import { EmptyState } from "@/components/EmptyState";
import { t, type LocaleCode } from "@/lib/i18n";

// A page that renders only this still has to be a page: without a heading it
// is an axe `page-has-heading-one` violation, and for a screen reader it is a
// document with no title at all.
export function SignInRequired({
  locale,
  path,
  title,
  body,
}: {
  locale: LocaleCode;
  path: string;
  /** Overrides the generic line where a page can say something more specific. */
  title?: string;
  body?: string;
}) {
  const heading = title ?? t(locale, "signIn.title");

  return (
    <div className="narrow">
      <h1 className="visually-hidden">{heading}</h1>
      <EmptyState
        title={heading}
        body={body ?? t(locale, "signIn.body")}
        action={{
          href: `/${locale}/login?next=${encodeURIComponent(path)}`,
          label: t(locale, "account.signIn"),
        }}
      />
    </div>
  );
}
