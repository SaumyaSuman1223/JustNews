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
  embedded = false,
}: {
  locale: LocaleCode;
  path: string;
  /** Overrides the generic line where a page can say something more specific. */
  title?: string;
  body?: string;
  /** Set where the prompt sits inside a page that already has its own h1
   * (My Desk's signed-out preview): a second h1 would give the document two
   * competing titles. */
  embedded?: boolean;
}) {
  const heading = title ?? t(locale, "signIn.title");
  const prompt = (
    <EmptyState
      title={heading}
      body={body ?? t(locale, "signIn.body")}
      action={{
        href: `/${locale}/login?next=${encodeURIComponent(path)}`,
        label: t(locale, "account.signIn"),
      }}
    />
  );

  if (embedded) return prompt;
  return (
    <div className="narrow">
      <h1 className="visually-hidden">{heading}</h1>
      {prompt}
    </div>
  );
}
