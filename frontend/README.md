Next.js App Router web client: rendering, routing, i18n/RTL, SEO. Deployed to
Vercel. Layering: `app/` (routes, Server Components, Server Actions in
`lib/actions.ts`) → `lib/` (API client, i18n, auth helpers) → `components/`.

## Env

Copy `.env.example` to `.env.local`:

```bash
cp .env.example .env.local
```

Vars: `API_URL` (the backend), `NEXT_PUBLIC_SITE_URL` (canonical origin, used
by the sitemap/structured data), `NEXT_PUBLIC_SUPABASE_URL` /
`NEXT_PUBLIC_SUPABASE_ANON_KEY` (Supabase Auth client-side). Separate from the
backend's env — see the root `.env.example`'s header comment for why.

## Commands

```bash
pnpm --filter @justnews/web dev         # dev server, localhost:3000
pnpm --filter @justnews/web typecheck
pnpm --filter @justnews/web lint
pnpm --filter @justnews/web build
pnpm --filter @justnews/web test:e2e    # Playwright
```

`packages/api-client` is the generated, typed API client this app imports —
never hand-edit it; see its own README.
