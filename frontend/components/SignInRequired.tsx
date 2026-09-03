import { EmptyState } from "@/components/EmptyState";

// A page that renders only this still has to be a page: without a heading it
// is an axe `page-has-heading-one` violation, and for a screen reader it is a
// document with no title at all.
export function SignInRequired({
  locale,
  path,
  title = "Sign in to see this",
  body = "This page shows things tied to your account, so it needs you signed in first.",
}: {
  locale: string;
  path: string;
  title?: string;
  body?: string;
}) {
  return (
    <div className="narrow">
      <h1 className="visually-hidden">{title}</h1>
      <EmptyState
        title={title}
        body={body}
        action={{
          href: `/${locale}/login?next=${encodeURIComponent(path)}`,
          label: "Sign in",
        }}
      />
    </div>
  );
}
