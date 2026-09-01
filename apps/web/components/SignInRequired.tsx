import Link from "next/link";

export function SignInRequired({ locale, path }: { locale: string; path: string }) {
  return (
    <div className="narrow">
      <p className="empty">
        Sign in to see this.{" "}
        <Link href={`/${locale}/login?next=${encodeURIComponent(path)}`}>Sign in</Link>
      </p>
    </div>
  );
}
