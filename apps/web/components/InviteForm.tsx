"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { redeemInviteAction } from "@/lib/actions";

export function InviteForm() {
  const { locale } = useParams<{ locale: string }>();
  const router = useRouter();
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setPending(true);
    const result = await redeemInviteAction(code);
    setPending(false);
    if (!result.ok) {
      setError(result.message ?? "That code did not work.");
      return;
    }
    router.push(`/${locale}`);
    router.refresh();
  }

  return (
    <div className="narrow">
      <div className="page-header">
        <h1>You&rsquo;re invited</h1>
        <p>JustNews is in private beta. Enter your invite code to unlock your personalised feed.</p>
      </div>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      <form onSubmit={handleSubmit} noValidate>
        <div className="field">
          <label htmlFor="invite-code">Invite code</label>
          <input
            id="invite-code"
            type="text"
            autoComplete="off"
            required
            value={code}
            onChange={(event) => setCode(event.target.value)}
          />
        </div>
        <button type="submit" className="button button--primary" disabled={pending || !code}>
          {pending ? "Checking…" : "Unlock"}
        </button>
      </form>
    </div>
  );
}
