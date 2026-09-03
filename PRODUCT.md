# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Next.js App Router, TypeScript, hand-authored CSS (`frontend/app/globals.css`) — a token system (custom properties for color, type scale, spacing) plus semantic BEM-ish component classes (`.card__title`, `.masthead-nav`). **Not Tailwind**, despite the root `CLAUDE.md`'s stack table naming it — no Tailwind package, config, or utility classes exist anywhere in `frontend/`. Treat `CLAUDE.md` as stale on this one point; the actual system is the CSS file itself.

FastAPI/Python 3.12 backend (`backend/`), Supabase Postgres + pgvector, Supabase Auth. Full detail in root `CLAUDE.md` and `docs/ROADMAP.md`.

## Users

**Primary: the cross-lingual reader.** Diaspora, expat, bilingual professional — reads English plus one more language daily, today across two apps and two feeds that never show they're covering the same story. This is the wedge: cross-language story clustering (one shared multilingual embedding space) is the one thing this product does that Google News, Apple News and Ground News cannot do structurally. Every other capability is table stakes a large publisher already ships better.

**Secondary: the operator.** Runs the admin console (source health, moderation, takedowns) — Stage 4, not yet built.

**Tertiary: the beta invitee.** Not an "early adopter" — a data source. Their session must produce propensity-logged impressions or the ranker (Stage 6) has nothing to train on.

## Product Purpose

A personalised, multilingual news reader with the polish of a major publisher's site, ranked (once the ranker ships) by a model derived from FINDING (Yu et al., CIKM '23), running entirely on free-tier infrastructure. Read `docs/ROADMAP.md` for the twelve-stage plan of record; three arcs — build the newspaper (Arc I, in progress), make it personal (Arc II, not started), launch and grow (Arc III).

## Positioning

Cross-lingual story clustering in one shared vector space: articles about the same event, published in different languages, land as one story rather than duplicates. No monolingual aggregator can do this. It is the product's real differentiator and today is nearly invisible in the UI — reachable only after clicking into an article that happens to be clustered.

## Operating Context

- **Stage gates are load-bearing.** `CLAUDE.md`: "One stage at a time, in roadmap order. Nothing from a later stage leaks into an earlier one." Stage 3 (web app) is shipped; Stage 4 (admin/ops, private beta gate) is next; Stage 5 (heuristic ranker) and Stage 6 (the FINDING model) are Arc II, not started.
- **No live ranker exists yet.** The feed today is recency-ordered within the reader's chosen languages, filtered by IPTC topic on request. Any "personalised" surface built ahead of Stage 5 is UI/UX groundwork against realistic mock data, explicitly not real ranking — confirmed with the user for this work.
- Free-tier constraints shape everything: Render's API cold-starts after 15 min idle, Supabase's 500MB DB and 7-day auto-pause, GNews's 12-hour delay and 100 req/day cap, Vercel Hobby's non-commercial terms.
- Never store full article text — title, snippet (≤300 chars), image URL, source, author, canonical link only. Always link out to the publisher.

## Capabilities and Constraints

- Cursor pagination only, everywhere — offset pagination is prohibited (`CLAUDE.md`).
- Every article carries a language; every user carries chosen languages. No query returns content in a language the reader didn't ask for.
- CSS uses logical properties throughout (`margin-inline-start`, not `margin-left`) — RTL is a document-level property (`dir` on `<html>`), not a per-component fix. Three locales shipped today (`en`, `es`, `hi`), all LTR — the RTL claim has never been exercised against a real RTL locale.
- Topics are IPTC Media Topic concept IDs, never labels; labels are a presentation-layer lookup.
- No model inference in a request path (ADR 0004) — ranking, when it exists, runs offline; a request costs a Postgres query, not a forward pass.
- **Personalization UI built now must degrade honestly to mock/static data** and carry no claim of being live — this is explicit UX/interaction groundwork for Stage 5/6, not a preview of working ranking.

## Brand Commitments

- Name: **JustNews**, wordmark set as "Just" + accent-colored "News" (`.wordmark span`).
- Honesty statement (from `CLAUDE.md`, binding on all copy/UI/commits): training will implement FINDING's fine-grained interpolation and dynamic clustering over *simulated* clients replayed from production logs; serving is centralised. Never describe this as a federated production system, anywhere.
- Visual direction confirmed for this work: **push the current identity further, not replace it** — the serif-headline / near-black-on-off-white / one-accent / ordered-density direction in `docs/design/design-system.md` stays the anti-reference-free baseline. This is refinement, not redesign.

## Evidence on Hand

- A real, running codebase: ~30 shipped public routes (feed, explore, topics, search, saved, history, article, story, settings, onboarding, login, invite, editions), a working FastAPI backend, real ingested articles (RSS + GNews) in a live Supabase database. Not a mockup.
- `docs/design/design-system.md` — the agreed visual direction and its non-negotiables (typography, colour tokens, card size set, WCAG 2.2 AA, zero-CLS, self-explaining ranked cards).
- An `/impeccable critique` run from this session (`frontend/.impeccable/critique/`) scored the current UI 26/40, since substantially addressed: i18n, pagination, the account menu's fake ARIA role, action-button feedback, mobile masthead, locale switcher path-preservation. Two P1s remain, both backend-blocked: a ranked-card "why am I seeing this?" disclosure (needs a reason field on `FeedItemOut`, and Stage 5) and real undo on "Not interested" (needs a `DELETE` endpoint that doesn't exist).
- No user research, no usability testing, no analytics on real readers yet — the product is pre-beta (Stage 4, private beta gate, hasn't opened).

## Product Principles

1. **The headline is the interface.** Type carries hierarchy; a reader tells a lead story from a secondary one without reading a word (`design-system.md`).
2. **Density is ordered, not airy.** A fixed, small card-size set composes any ranker output; real news sites are dense because readers scan.
3. **Personalised must not mean arbitrary.** Named rails, stable slot shapes, and (once building for real) a disclosure on every ranked card explaining why it's there.
4. **Every script is first-class.** The audience is global; the system holds in Arabic and Chinese as well as English, structurally, not as a later retrofit.
5. **Fast is a design property.** A layout that can't render under 1.5s on a mid-range phone is a failed design regardless of how it looks.

## Accessibility & Inclusion

WCAG 2.2 AA, axe-clean in CI (`e2e/accessibility.spec.ts`, public routes only — signed-in coverage exists but is skipped pending real Supabase test credentials), full keyboard operability, `prefers-reduced-motion` honoured, per-script font stacks and leading (Devanagari overrides shipped; Arabic RTL mirroring implemented but unproven against a real locale).
