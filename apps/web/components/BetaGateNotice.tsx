import Link from "next/link";

export function BetaGateNotice({ locale }: { locale: string }) {
  return (
    <p className="notice" role="status">
      JustNews is in private beta. You&rsquo;re signed in, but you&rsquo;ll need an invite code to
      unlock your personalised feed, saves and history.{" "}
      <Link href={`/${locale}/invite`}>Enter your code</Link>
    </p>
  );
}
