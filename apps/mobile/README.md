Expo React Native app (Stage 10). Consumes the same `@justnews/api-client` as
`frontend`. Not deployed continuously — real installs go through EAS Build.

## Local dev (Expo Go)

```bash
pnpm --filter @justnews/mobile start
```

## Env

EAS Build's cloud builds never read a local `.env` — only its own env vars,
set per-profile in `eas.json` (`development`/`preview`/`production`) via:

```bash
npx eas-cli env:set --environment development
```

## Building a real installable app

```bash
pnpm --filter @justnews/mobile build:android:dev       # dev client (internal)
pnpm --filter @justnews/mobile build:android:preview    # preview build (internal)
```

Both run `npx eas-cli build` under the hood — `eas-cli` isn't installed
globally, so don't call bare `eas`.

See `AGENTS.md`/`CLAUDE.md` in this directory for Expo-version-specific
guidance before writing code — the framework moves fast enough that stale
assumptions from training data are a real risk here.
