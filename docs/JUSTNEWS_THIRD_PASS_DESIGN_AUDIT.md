# JustNews — Third-Pass Live Website Design Audit & Next Redesign Brief

## Purpose

This document records the latest audit of the deployed JustNews website after the previous redesign changes.

The goal is no longer simple cleanup. The product now needs a stronger **experience-level redesign** so that it feels distinctive, editorial, intelligent and genuinely interesting rather than like a polished but basic news website.

The instruction to Claude Code is:

> Inspect the current repository and implementation first. Then produce a concrete plan to recompose Home, Aquila and My Desk around their distinct product purposes while preserving the existing backend, data, authentication, recommendation and ingestion systems unless a real technical reason requires change.

---

# 1. Overall Verdict

The current website is functional and cleaner than earlier versions, but it still feels too basic and template-driven.

Approximate assessment:

| Area | Current | Target |
|---|---:|---:|
| Functionality | 7/10 | 9/10 |
| Information architecture | 7/10 | 9/10 |
| Visual identity | 5/10 | 9/10 |
| Home | 5/10 | 9/10 |
| Aquila | 5/10 | 9.5/10 |
| My Desk | 3.5/10 | 9/10 |
| Search | 4/10 | 8/10 |
| Interaction design | 4/10 | 8.5/10 |
| Editorial quality | 5/10 | 9/10 |
| Overall | ~5/10 | ~9/10 |

The main issue is not that the UI is ugly.

The main issue is:

> **Everything still behaves like a website, while very little feels like a distinct experience.**

---

# 2. The Core Problem — Structural Flatness

The current interface is still driven by a repeated pattern:

```text
heading
↓
image
↓
headline
↓
summary
↓
source
↓
next story
```

This works functionally but produces a stale visual rhythm.

The user needs to feel:

- what is most important
- what is supporting information
- what is context
- what is changing
- what is personalized
- what is editorial

The product currently has these concepts semantically, but not strongly enough visually.

---

# 3. The Three Experiences Must Become Distinct

This is the most important product-level principle going forward.

## HOME — NOW

> **What’s happening?**

Live + personalized.

Home should feel dynamic, useful and immediately informative.

## AQUILA — TODAY

> **What mattered?**

Scheduled + editorial + contextual.

Aquila should feel like a digital newspaper edition.

## MY DESK — ME

> **What do I care about?**

Personalized + topic-focused.

My Desk should feel like a personal intelligence workspace.

## SEARCH — FIND

> **What am I looking for?**

Search should feel like a research utility.

If these experiences visually converge, JustNews loses its product identity.

---

# 4. Aquila — Still the Largest Gap

The current Aquila has improved structurally, but it still reads too much like a web page with newspaper styling.

The target is:

> **An actual digital newspaper reader.**

Not:

> A website called The Aquila Tribune.

The newspaper itself must become the dominant visual object.

---

# 5. Aquila — Full-Screen Reading Experience

Entering Aquila should immediately feel different from normal JustNews navigation.

Use:

```text
full viewport
↓
dark workspace
↓
large centered cream newspaper
```

Workspace:

`#20211F`

Newspaper:

- centered
- square corners
- cream newsprint
- subtle outer shadow
- editorial grid

The surrounding UI should disappear as much as practical.

---

# 6. Aquila — Masthead

Final masthead:

> **AQUILA TRIBUNE**

Subtitle:

> **THE WORLD IN CONTEXT**

Use a large high-contrast editorial serif.

Recommended:

- Cormorant Garamond
- comparable Bodoni/Didot-style serif only if necessary

### Explicit requirement

**Do not use Samarkan.**

Do not use decorative Indian script/calligraphy for the masthead.

The masthead should look like a premium broadsheet newspaper.

Approximate size:

- 78–100px around 1100px paper width
- 96–120px maximum on very large desktop

---

# 7. Aquila — Do Not Use Permanent Category Navigation

Remove permanent top navigation such as:

```text
News · Ideas · People · Perspectives
```

Do not turn:

```text
India | World | Business | Sports | Technology
```

into website-level tabs.

These are newspaper sections/pages.

The distinction is:

### JustNews navigation

```text
Home
Aquila
My Desk
Search
```

### Aquila newspaper navigation

```text
Front Page
India
World
Economy
Technology
Science
Culture
Sport
Perspectives
```

The second exists inside the newspaper/page system, not as the site's main navbar.

---

# 8. Aquila — Final Front Page Composition

Target approximate proportions:

- left editorial rail: 15–17%
- main lead area: 58–62%
- right editorial rail: 23–27%

Underlying grid:

- approximately 12 columns
- 12–18px gutters
- mostly invisible

The front page should contain:

## Left rail

- “Better information builds a better tomorrow.”
- attribution
- IN FOCUS
- halftone image
- headline
- summary
- PAGE X

No boxed magazine-card treatment.

## Main lead

One dominant story:

```text
INDIA

Large headline

Short summary

2–3 short context paragraphs

Large halftone image

Byline
CONTINUED ON PAGE X
```

## Right rail

Secondary stories such as:

- Technology
- Economy
- Climate

Use varied editorial composition instead of repeated cards.

## Lower row

Prefer approximately three major stories:

- Society
- Ideas
- Culture

Then a compact:

> TODAY’S HIGHLIGHTS

Use numbered stories with page references.

---

# 9. Aquila — Editorial Right Rail vs Utility Bar

These are two separate systems.

## Editorial right rail

Part of the paper.

Contains:

- Technology
- Economy
- Climate
- Today's Highlights

Keep it inside the newspaper.

## Utility right sidebar

Outside the paper.

Contains:

- Contents
- Pages
- Editions
- Reading controls

It should be hidden until the user approaches the right edge.

---

# 10. Aquila — Right-Edge Sliding Utility Bar

Target behavior:

1. Cursor approaches the right edge.
2. Hidden trigger detects it.
3. Utility panel slides in.
4. Panel overlays the workspace.
5. Newspaper does not reflow or resize.
6. Panel closes after a short delay when pointer leaves.

Suggested dimensions:

```text
trigger zone: 20–28px
panel width: 280–320px
open: 200–280ms
close: 250–400ms
```

Use smooth ease-out.

No bounce.

No dramatic spring physics.

Provide keyboard alternatives.

---

# 11. Aquila — Page Turning

Page turning is the signature interaction.

Support:

- previous/next buttons
- keyboard arrows
- optional drag
- contents selection
- mobile swipe

Controls:

```text
←     1 / 12     →
```

Approximately:

`36–44px`

Page-turn duration:

`350–550ms`

The animation should feel like turning a publication page, not like a carousel.

---

# 12. Aquila — Halftone Image Identity

Every Aquila article image should use the consistent halftone editorial treatment.

Target:

- newspaper/screen-print dots
- strong tonal structure
- black/cream foundation
- restrained muted red/olive/blue
- recognizable subjects

Approximate dot sizes:

- large images: 2–4px
- smaller images: 1.5–3px

Do not turn this into:

- RGB glitch
- CRT scanlines
- pixel art
- comic-book pop art
- random grain

Preferred conceptual pipeline:

```text
original publisher image
        ↓
controlled tonal range
        ↓
halftone treatment
        ↓
limited editorial palette
        ↓
Aquila rendering
```

Do not unnecessarily create a server-side asset processing/storage system just to achieve the effect. Inspect CORS/image constraints and use an appropriate client-side/scoped approach with graceful fallback.

---

# 13. Home — Serious Visual Overhaul

Home now has the correct semantic sections:

- What matters
- What you should know
- What else is happening

But the presentation still feels like a feed with headings.

The next design must make the hierarchy visual, not just semantic.

---

# 14. Home — The Big Three

Top editorial block:

> **THE BIG THREE**

Use:

- 1 dominant story
- 2 supporting stories

Suggested structure:

```text
┌──────────────────────────────────────────────┐
│                                              │
│              BIGGEST STORY                  │
│                                              │
│           large headline                    │
│           why it matters                    │
│                                              │
│           large image                       │
│                                              │
├──────────────────────┬───────────────────────┤
│ STORY 2              │ STORY 3              │
└──────────────────────┴───────────────────────┘
```

The first story should be unmistakably dominant.

---

# 15. Home — Three-Level Hierarchy

After The Big Three:

## WHAT YOU SHOULD KNOW

Approximately 5–10 important stories in a varied editorial grid.

## MORE FROM THE WORLD

A denser stream of secondary stories.

The visual progression should be:

```text
WHAT MATTERS
      ↓
WHAT YOU SHOULD KNOW
      ↓
MORE FROM THE WORLD
```

---

# 16. Home — Story Component Variety

Stop using one repeated article-card structure.

Create several editorial story types.

### Lead

Large headline + large image.

### Feature

Large image + large headline.

### Standard

Medium image + headline.

### Brief

Text-only compact story.

### Cluster

One story connecting several sources.

This variety is essential for visual rhythm.

---

# 17. Home — Shorten Content Snippets

Long scraped-looking descriptions make the product feel like an RSS reader.

Prefer:

```text
HEADLINE

Why it matters / concise summary

SOURCE · TIME
```

Do not render unnecessarily long publisher descriptions.

If summarization is not available, truncate intelligently.

---

# 18. Home — Raw Live-Blog Content

Raw publisher/live-blog content should not dominate the UI.

Example of an undesirable pattern:

> “Updates from 5.30pm BST kick-off... Live scoreboard...”

Normalize or truncate into a clean JustNews presentation.

Prefer:

- concise summary
- source
- timestamp
- optional “why it matters”

Never reproduce full third-party article bodies where the content policy prohibits it.

---

# 19. Home — Statistics

Metrics such as:

```text
6,450 articles
70 sources
14 languages
234 stories
```

are useful but currently feel like dashboard KPIs.

Either remove them from the main reading flow or make them quiet editorial metadata:

```text
70 SOURCES
14 LANGUAGES
234 STORIES TODAY
```

Do not make them giant dashboard cards.

---

# 20. Home — Daily Brief

The Daily Brief is a strong concept and should be retained.

Make it feel like:

> **TODAY’S BRIEF**

For example:

```text
01  What changed overnight
02  Markets
03  Global affairs
04  Technology
05  India
```

Then:

> Read today's issue →

It can become a bridge between Home and Aquila.

---

# 21. Home — Source Diversity

Source diversity is a real product advantage.

The interface should surface this more intelligently.

Instead of only:

```text
BBC · 2h
```

an important story could communicate:

```text
THE STORY

7 sources
4 countries
3 perspectives
2 languages
```

This reinforces the JustNews value proposition:

> **Same world. More clarity.**

---

# 22. Story Clustering — Important Future Direction

When several publishers cover the same event, they should eventually be clustered.

Instead of:

```text
Story A
Story B
Story C
```

use:

```text
THE STORY

[story title]

7 sources are covering this story

BBC
Reuters
DW
CBC
...

What differs between them?
```

This becomes an important bridge to the future Analysis feature.

The product progression should become:

```text
NEWS
 ↓
STORY
 ↓
STORY CLUSTER
 ↓
SOURCES
 ↓
PERSPECTIVES
 ↓
TIMELINE
 ↓
UNDERSTANDING
 ↓
ANALYSIS
```

---

# 23. My Desk — Major Overhaul Required

Current My Desk remains too thin and feels closer to a sign-in/settings page than a product workspace.

The target is:

> **A personal intelligence workspace.**

Header:

```text
MY DESK

Your topics.
Deeper understanding.
```

---

# 24. My Desk — Topic Selection

The current taxonomy list is useful as backend classification, but it should not be the primary user experience.

Users should think:

> “I care about AI.”

not:

> “I must choose an IPTC taxonomy.”

Use a curated visual topic selection experience:

```text
AI
Markets
India
Space
Climate
Energy
Semiconductors
Politics
```

Support:

- add topic
- remove topic
- reorder topic
- follow topic

Keep the visual language editorial, not SaaS-tag heavy.

---

# 25. My Desk — What Changed

Show important developments for selected topics.

Example:

```text
WHAT CHANGED

AI
major development...

MARKETS
major development...

SEMICONDUCTORS
major development...
```

Use different visual weights.

---

# 26. My Desk — Understand

Even before advanced Analysis exists, My Desk can provide:

- what is happening
- key developments
- sources
- perspectives
- recent history
- context

Example:

```text
UNDERSTAND THE TOPIC

What's happening
5 important developments

Who is saying what
source/perspective comparison

What's changing
recent development timeline
```

This sets up the eventual Analysis feature naturally.

---

# 27. Search — Visual Redesign

Current Search is functional but visually bare.

Target:

```text
SEARCH JUSTNEWS

What are you trying to understand?

────────────────────────

Recent searches

AI regulation
Semiconductor tariffs
Indian economy

────────────────────────

RESULTS
```

Later add:

- source filter
- date filter
- topic filter
- language filter

Search should feel like a research entry point, not a database form.

---

# 28. Navigation Redesign — Home & My Desk

Replace the large side navigation with a slim icon rail.

Target width:

`52–60px`

Visually show icons only.

Suggested conceptual arrangement:

```text
│
│  Home
│  Aquila
│  My Desk
│  Search
│
│  Saved
│  Settings
│
```

Requirements:

- fixed left side
- subtle
- active state
- tooltip on hover
- keyboard accessible
- no large labels
- no bulky navigation cards

This should make the product feel like a distinct application shell rather than a normal website.

---

# 29. Navigation Redesign — Aquila

Aquila should NOT use the same icon rail as Home/My Desk during normal reading.

Use:

```text
full-screen newspaper
+
right-edge sliding utility bar
```

The utility bar contains navigation/reading tools, not editorial stories.

---

# 30. Global Header Reduction

The current global header carries too many competing elements:

- logo
- Home
- Aquila
- My Desk
- Search
- search field
- sign in
- languages

This contributes to the stale website feeling.

Move toward:

### Home / My Desk
Slim icon rail.

### Aquila
Full-screen reader.

### Search
Dedicated search experience.

The site should have less persistent UI chrome.

---

# 31. Footer

Do not repeat the main navigation in the footer.

Keep it quiet:

```text
JUSTNEWS

A clearer tomorrow.

Privacy · Feedback · Languages
```

---

# 32. Editorial Rhythm — Site-Wide

The entire site currently needs stronger spatial and typographic rhythm.

Avoid:

```text
heading
content
heading
content
heading
content
```

Use:

```text
BIG
↓
SMALL
↓
DENSE
↓
SPACIOUS
↓
VISUAL
↓
TEXT
↓
DENSE
```

Use:

- typography
- whitespace
- image scale
- columns
- alignment
- subtle rules

rather than decorative elements.

---

# 33. Stop Making Everything a Card

Avoid a sequence of rounded containers:

```text
┌──────────────┐
│ story        │
└──────────────┘

┌──────────────┐
│ story        │
└──────────────┘
```

Prefer editorial structures based on:

- whitespace
- typography
- alignment
- subtle rules
- image placement
- scale

Cards should exist only where they add actual grouping or interaction value.

---

# 34. The Site Needs “Moments”

The current design mostly provides pages.

The redesign should intentionally create memorable moments.

Examples:

## Opening Home

A strong editorial entrance.

## Opening Aquila

The newspaper appears as the main object.

## Turning a page

Physical publication feeling.

## Hovering a story

Small typographic/image response.

## Opening a topic

Topic content unfolds into focus.

## Seeing multiple perspectives

Sources arrange around the same story.

## Saving

Small but satisfying feedback.

## Returning later

Potential future “Since you were last here…” moment.

Do not create these moments with random animation. Build them through composition and interaction.

---

# 35. Signature Product Gestures

JustNews should have recognizable interaction signatures.

### Aquila

**Turn the page.**

### Home

**Expand a story / move from headline to context.**

### My Desk

**Open a topic and progressively reveal context.**

### Navigation

**Minimal icon rail.**

These should provide product personality without becoming gimmicky.

---

# 36. Visual Personality

Do NOT make the site “interesting” by adding:

- more gradients
- more colors
- more animations
- 3D effects
- glassmorphism
- floating cards
- excessive hover effects
- oversized rounded panels
- animated backgrounds

That makes it busier, not better.

The missing ingredients are:

> **composition + storytelling + interaction + hierarchy**

---

# 37. Typography

Maintain a disciplined type system.

### Editorial serif

Use for:

- Aquila masthead
- major headlines
- editorial emphasis

Recommended:

**Cormorant Garamond**

### Interface sans

Use for:

- metadata
- controls
- navigation
- timestamps

Recommended:

**IBM Plex Sans**

Do not use a large number of font families.

---

# 38. Colour System

## Normal JustNews

Use:

- warm white
- charcoal
- muted gray
- restrained red

## Aquila

Use:

- cream paper
- dark ink
- muted red
- restrained olive/ochre/blue
- dark reading workspace

Do not force the entire site to look like a newspaper.

Aquila should be the most explicitly print-oriented section.

---

# 39. Motion System

Motion must communicate state or navigation.

Normal micro-interactions:

`120–200ms`

Panels:

`200–300ms`

Aquila page turn:

`350–550ms`

Use calm easing.

Avoid:

- bounce
- excessive spring physics
- constant floating
- particles
- parallax
- animation on every card
- long loading transitions

Respect:

`prefers-reduced-motion`

---

# 40. Responsive Rules

## Desktop

Use rich editorial grids.

## Tablet

Reduce column complexity while preserving hierarchy.

## Mobile

Do not shrink the desktop layout literally.

Use:

- single-column content
- strong typography
- swipeable Aquila pages
- bottom navigation
- compact icon rail/navigation where appropriate

No accidental horizontal scrolling.

---

# 41. Content Source / Provenance

Source diversity is a major strength.

Preserve:

- source name
- publication time
- publisher link
- language
- perspective information when available

The redesign must not hide provenance in the name of aesthetics.

---

# 42. Backend Preservation

Do not unnecessarily rewrite:

- news ingestion
- database
- recommendation engine
- authentication
- APIs
- content pipeline
- admin dashboard
- existing data models
- deployment

The current major deficiencies are mostly in:

> **presentation + information architecture + interaction design**

Only modify backend systems when inspection identifies a real bug or required data contract.

---

# 43. Recommended Redesign Sequence

## Phase 0 — Deployment verification

Confirm the production deployment actually contains the intended code.

## Phase 1 — Navigation shell

Build:

- Home/My Desk icon rail
- Aquila right-edge utility bar
- removal of permanent Aquila category navigation

## Phase 2 — Aquila composition

Build:

- newspaper canvas
- masthead
- editorial grid
- left rail
- dominant lead
- varied right editorial rail
- lower stories
- Today's Highlights

## Phase 3 — Aquila reader

Build:

- full-screen workspace
- contents
- page controls
- page transitions
- keyboard controls
- edition selector
- mobile swipe

## Phase 4 — Home

Build:

- The Big Three
- What You Should Know
- More From The World
- multiple story types
- concise content summaries
- Daily Brief

## Phase 5 — My Desk

Build:

- topic selection
- What Changed
- Understand
- perspectives
- timeline/context

## Phase 6 — Content normalization

Fix:

- raw RSS text
- live-blog leakage
- excessive snippets
- inconsistent metadata

## Phase 7 — Search

Improve the search presentation and useful filters.

## Phase 8 — Product personality

Add:

- meaningful transitions
- story expansion
- topic unfolding
- perspective interactions
- subtle microinteractions

## Phase 9 — QA

Test:

- desktop
- tablet
- mobile
- keyboard
- accessibility
- reduced motion
- long headlines
- missing images
- missing metadata
- multilingual text
- different source names
- edition boundaries
- page transitions
- performance

---

# 44. Claude Code Planning Protocol

Before implementation:

1. Inspect the actual repository.
2. Verify the deployed production commit/branch.
3. Inspect Home, Aquila, My Desk and Search routes.
4. Inspect reusable layout and story components.
5. Inspect design tokens and font loading.
6. Inspect image loading and existing halftone work.
7. Inspect edition data and schedule generation.
8. Inspect source/content normalization.
9. Separate presentation logic from business logic.
10. Identify what can be preserved.
11. Identify what needs structural redesign.
12. Create a file-level implementation plan after repository inspection.
13. Implement in small, testable phases.
14. Run tests/build/type checks after each major phase.
15. Visually verify the deployed result after deployment.

---

# 45. Required Plan Output from Claude

Claude should produce a plan with:

## A. Current-state architecture

What exists now.

## B. Audit findings

What is good, what is weak, and what conflicts with this document.

## C. Component strategy

What can be reused, refactored or replaced.

## D. Route strategy

How Home, Aquila, My Desk and Search should be organized.

## E. Data strategy

Which existing data/API contracts can remain unchanged.

## F. Image strategy

How Aquila halftone treatment will work.

## G. Edition strategy

How 06:00 / 14:00 / 22:00 editions are represented and synchronized.

## H. Interaction strategy

How icon rail, right utility bar, page turns and story/topic interactions work.

## I. Responsive strategy

How desktop/tablet/mobile differ.

## J. Testing strategy

How visual, functional, accessibility and performance QA will be performed.

## K. Deployment strategy

How production will be verified after each major phase.

---

# 46. Acceptance Criteria — Aquila

A user should immediately think:

> **“I am reading a newspaper.”**

Not:

> “I am browsing a news website.”

Must have:

- AQUILA TRIBUNE masthead
- high-contrast editorial serif
- THE WORLD IN CONTEXT
- cream paper
- editorial grid
- dominant lead story
- open left editorial rail
- varied right editorial rail
- Today's Highlights
- halftone images
- page references
- continuation references where useful
- edition/date metadata
- three daily editions
- page turning
- full-screen reader
- right-edge utility bar
- no permanent category navbar

---

# 47. Acceptance Criteria — Home

Home must clearly communicate:

> **What matters right now.**

Must have:

- dominant editorial story
- two supporting stories
- What You Should Know
- More From The World
- multiple story types
- concise summaries
- strong source attribution
- Daily Brief
- visible but restrained personalization
- no uniform card wall

---

# 48. Acceptance Criteria — My Desk

My Desk must clearly communicate:

> **This is my information workspace.**

Must eventually have:

- topic selection
- topic hierarchy
- What Changed
- key developments
- perspectives
- timeline/context
- clear path toward future Analysis

It should not look like a taxonomy settings form.

---

# 49. Acceptance Criteria — Navigation

## Home/My Desk

- slim icon rail
- ~52–60px
- tooltips
- active states
- keyboard access

## Aquila

- no permanent global navbar
- right-edge utility panel
- overlay rather than layout shift
- keyboard alternative

---

# 50. Acceptance Criteria — Content

- no raw live-blog descriptions dominating the UI
- concise summaries
- source attribution visible
- original publisher link preserved
- no prohibited full article reproduction
- story relationships can eventually be represented as clusters

---

# 51. Acceptance Criteria — Performance

No unacceptable regressions caused by:

- halftone processing
- fonts
- animation
- responsive layout
- large image rendering

Use lazy loading and responsive images where appropriate.

---

# 52. Final Product Mental Model

```text
JUSTNEWS
A clearer tomorrow.

        HOME
        NOW
        What’s happening?
        Live + personalized.

        AQUILA
        TODAY
        What mattered?
        The world in context.
        Scheduled digital newspaper.

        MY DESK
        ME
        What do I care about?
        Personal topic workspace.

        SEARCH
        FIND
        What am I looking for?
        Research utility.
```

Overall philosophy:

> **Same world. More clarity.**

---

# 53. Final Instruction to Claude Code

Do not continue making tiny cosmetic adjustments to the existing interface.

The product is now at the point where it needs **experience-level recomposition**.

The next pass should make the product feel:

- intentional
- editorial
- intelligent
- memorable
- calm
- distinctive

The objective is not to add visual noise.

The objective is to make the existing product ideas **visible through composition, hierarchy, storytelling and interaction**.

Most importantly:

> **Do not destroy what already works. Recompose the experience around the product's actual strengths.**

Those strengths are:

- source diversity
- multilingual content
- recommendations
- scheduled Aquila editions
- newspaper presentation
- My Desk topic personalization
- eventual perspectives and Analysis

The next implementation should make those strengths unmistakable.
