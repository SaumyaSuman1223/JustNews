# 0011 — Three destinations, not a category navbar

- **Date:** 2026-09-04
- **Status:** accepted

## Context

The app grew a route per capability: `/` (ranked feed), `/explore`, `/topics`,
`/topics/[id]`, `/saved`, `/search`, `/history`. Each one is defensible on its
own and the set is incoherent as a product — a reader cannot say what `/explore`
is *for* versus the feed, and "Topics" names a data structure rather than
something a person wants to do.

The obvious fix is the one every news portal reaches for: put the sections in
the navbar. World, Business, Tech, Science, Sports, Politics. It is familiar,
it is what the wires do, and it is wrong for this product — it makes JustNews a
worse version of a category portal, competing on breadth against organisations
with a thousand journalists.

`docs/JustNews_Design_and_Product_Direction.md` proposes the alternative:
three destinations, each answering a different question, with categories living
*inside* the experiences rather than in the chrome.

## Options

**1. Category navbar.** World / Business / Tech / Science / … Familiar, zero
conceptual work. Fails because it makes the taxonomy the product, hides
personalisation entirely, and grows without limit — every new IPTC branch is a
lobbying campaign for navbar space. It also makes the ranked feed just one more
tab, which throws away the only thing here that is actually differentiated.

**2. Keep the capability routes, relabel them.** `/explore` becomes "Aquila",
`/topics` becomes "My Desk". No breakage, no redirect work. Rejected because
the URLs stop matching the vocabulary the product uses everywhere else, and
because relabelling does not fix that these surfaces have no distinct purpose —
it just renames the confusion.

**3. Three destinations by question, categories inside.** Chosen.

| Destination | Question it answers | Personality |
|---|---|---|
| **Home** | What should I know right now? | Calm, personal |
| **Aquila** | What is happening in the world? | Editorial, curated |
| **My Desk** | What do I want to understand? | Analytical, personal |

## Decision

Three primary destinations — **Home** (`/`), **Aquila** (`/aquila`), **My Desk**
(`/desk`) — with Saved and Search as secondary, and Settings and Profile as
tertiary. Categories are navigable inside My Desk and inside Aquila's pages,
never in the primary chrome.

`/explore` and `/topics` **308-redirect** to their replacements. Permanent, not
temporary: the old paths are not coming back, and a 308 preserves method and
tells crawlers to update. Deep routes (`/topics/[id]`) redirect to
`/desk/[id]`.

Analysis — the eventual decision-support surface — is deliberately **not** a
fourth destination. It emerges inside My Desk once a reader has chosen a topic,
because a top-level "Analysis" tab with nothing behind it is a promise the
product cannot keep yet.

## Consequences

- **Every navigation surface is rewritten**: the left rail, the mobile bottom
  bar, the footer, the sitemap, and the mobile app's deep links.
- **Redirects are permanent infrastructure.** `frontend/middleware.ts` carries
  the map, and it has to survive locale prefixes (`/es/explore` → `/es/aquila`).
- Three destinations is a hard cap that has to be *defended*. The pressure to
  add a fourth will be constant, and the answer is that a new capability belongs
  inside one of the three or it does not belong in the chrome.
- The IPTC taxonomy (ADR 0006) becomes navigation *content* rather than
  navigation *structure* — which is what it was always better suited to.
- Analytics get cleaner: `surface` in the interaction log now maps to a
  destination a reader could name, instead of to an implementation detail.
