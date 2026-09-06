# JustNews — Second-Pass Live Website Audit & Redesign Brief

## Purpose

This is the **second-pass audit and implementation brief** for Claude Code after the first major redesign attempt.

The goal is to compare the currently deployed JustNews site against the product/design direction already established and correct the remaining issues.

This is **not** a request to blindly rewrite the application.

Claude must first inspect the current repository, deployed implementation, routes, components and existing work, then make a focused plan and implementation.

---

# 1. Overall Audit Verdict

The current site is functional and clean, but it still feels like:

> **a competent conventional news website**

rather than:

> **a distinctive news-intelligence product with a strong editorial identity.**

Approximate current visual quality: **~5.5/10**.

The biggest problem is not that the interface is ugly. It is that it is **too generic, repetitive and webpage-like**.

The same basic pattern is repeated:

```text
header
navigation
article
image
headline
source
footer
```

This creates a stale/template-driven feeling.

The product concept is substantially stronger than the current visual expression.

---

# 2. CRITICAL FIRST CHECK — DEPLOYMENT

Before changing the design further, verify that the changes Claude previously made are actually deployed.

The currently reviewed live implementation still showed older Aquila characteristics including:

- “The Aquila Tribune” rather than the approved “AQUILA TRIBUNE”
- permanent `News · Ideas · People · Perspectives`
- an edition time such as `4:47 PM Midday Edition`
- the old 9-page web-style structure

Therefore, Claude must first verify:

1. current Git commit
2. current branch
3. Vercel deployment
4. production build
5. deployed route
6. whether local changes actually reached production

Do not assume that a successful local implementation equals the deployed implementation.

---

# 3. THREE PRODUCT MODES

The entire product should now be understood as three distinct modes:

## HOME

**NOW**

> What’s happening?

Live + personalized.

## AQUILA

**TODAY**

> What mattered?

Scheduled + editorial + contextual.

## MY DESK

**ME**

> What do I care about?

Personalized + topic-focused.

## SEARCH

Utility:

> What am I looking for?

These experiences must not visually collapse into one generic news feed.

---

# 4. AQUILA — MAIN PROBLEM

Aquila is still the biggest gap.

The current implementation feels like:

> **news webpage + newspaper styling**

The target is:

> **actual digital newspaper reader**

The newspaper itself must become the dominant object.

Do not simply add more newspaper fonts, borders or beige colors to a normal webpage.

The **information architecture and interaction model must change**.

---

# 5. AQUILA TARGET EXPERIENCE

Entering Aquila should feel like opening a newspaper.

Conceptually:

```text
dark workspace
        ↓
large cream newspaper page
        ↓
editorial newspaper grid
        ↓
page-turn interaction
```

The browser/webpage should visually recede.

The newspaper should dominate the viewport.

Workspace: `#20211F`

Paper: `#F5F1E8`

Square newspaper corners.

Subtle shadow:

`0 8px 30px rgba(0,0,0,0.12)`

No rounded SaaS card appearance.

---

# 6. AQUILA MASTHEAD

Approved final identity:

```text
AQUILA TRIBUNE
THE WORLD IN CONTEXT
```

The masthead must be:

- large
- centered
- high-contrast editorial serif
- elegant
- newspaper-like

Use **Cormorant Garamond**.

Do not add Bodoni merely for variety unless repository inspection proves Cormorant cannot achieve the approved look.

## Non-negotiable

**DO NOT USE SAMARKAN.**

Do not use:

- Indian decorative scripts
- novelty fonts
- calligraphic fonts
- ornamental fonts

Masthead approximate size:

- 78–100px around 1100px newspaper width
- 96–120px maximum on very large desktop

Subtitle:

- 12–15px
- uppercase
- 3–5px letter spacing

---

# 7. AQUILA HEADER METADATA

Use the newspaper header structure:

## Left

```text
A CLEARER
TOMORROW

VOL. 1 NO. XX
```

## Center

```text
AQUILA TRIBUNE
THE WORLD IN CONTEXT
```

## Right

```text
NEWS
PEOPLE
IDEAS
PERSPECTIVE

DATE
CITY
```

The date and edition data must be derived from one source of truth.

Do not hardcode `NEW DELHI`.

If a reliable edition locale/city exists, derive the dateline from it.

If no reliable city exists, omit the city rather than invent one.

---

# 8. AQUILA EDITION SYSTEM

Required editions:

- **06:00 AM — Morning**
- **02:00 PM — Midday**
- **10:00 PM — Evening**

Edition selector should be:

- restrained
- text-based
- subtle
- underline/active state

Do not use large cards.

Edition metadata should conceptually come from:

```text
edition_date
edition_type
published_at
locale / dateline
```

All UI labels should derive from that source.

Do not independently generate date/time/name in different components.

---

# 9. AQUILA MUST NOT HAVE PERMANENT WEBSITE NAVIGATION

Remove permanent top navigation such as:

```text
News · Ideas · People · Perspectives
```

Also do not make:

```text
INDIA | WORLD | BUSINESS | SPORTS
```

a permanent application navbar.

Those are **newspaper sections/pages**.

The reader should navigate them through the newspaper page system and contents controls.

---

# 10. AQUILA PAGE STRUCTURE

The current 9-page architecture is acceptable as a foundation.

Do not increase page count merely to make the project look more complete.

Potential pages:

1. Front Page
2. India
3. World / Conflict, War and Peace
4. Economy, Business and Finance
5. Science and Technology
6. Health
7. Environment / Climate
8. Arts, Culture, Entertainment and Media
9. Sport
10. Perspectives / Ideas
11. Society
12. Optional context/editorial page

The important thing is that each page feels like a **newspaper page**, not a category webpage.

---

# 11. AQUILA FRONT PAGE — REQUIRED EDITORIAL COMPOSITION

Use the approved three-column editorial hierarchy:

- left rail: 15–17%
- main lead: 58–62%
- right rail: 23–27%

Underlying grid:

- approximately 12 columns
- 12–18px gutters
- mostly invisible

## Left rail

Include:

> “Better information builds a better tomorrow.”  
> — JUSTNEWS

And:

### IN FOCUS

- halftone image
- headline
- short summary
- PAGE X

Do not box it like a magazine sidebar.

## Main lead

One dominant story.

Example:

```text
INDIA

Leaders Meet in New Delhi to Shape
a More Stable Asia

Short summary...

2–3 short context paragraphs...

[large halftone image]

Byline

CONTINUED ON PAGE 2
```

## Right editorial rail

Include secondary stories such as:

- Technology
- Economy
- Climate

Vary layouts:

- image above
- image beside
- image-left/text-right
- text-left/image-right
- text-dominant
- larger/smaller headline

Do not make every story a repeated card.

## Lower row

Approximately:

- Society
- Ideas
- Culture

Use varied weight.

Do not create four identical cards.

## Today's Highlights

Transform the existing “The brief” concept into:

**TODAY'S HIGHLIGHTS**

Compact numbered list with page references.

---

# 12. IMPORTANT — EDITORIAL RIGHT RAIL VS UTILITY RIGHT SIDEBAR

These are **two different things**.

## A. Newspaper editorial right rail

This is part of the newspaper itself.

It contains stories such as:

- Technology
- Economy
- Climate
- Today's Highlights

**KEEP IT INSIDE THE PAPER.**

## B. Reader utility sidebar

This is outside the newspaper.

It should contain:

- Contents
- Pages
- Edition
- navigation
- reader controls

It should be hidden until the user approaches the right edge.

This distinction is mandatory.

---

# 13. NEW AQUILA RIGHT-EDGE SLIDING UTILITY BAR

Replace any permanently visible right-side navigation/utility panel with a sliding bar.

Behavior:

1. User moves cursor near right viewport edge.
2. A hidden trigger area detects the cursor.
3. Utility panel slides in.
4. Panel overlays the workspace/newspaper.
5. Newspaper does not reflow.
6. Moving away closes it after a short delay.

Approximate:

- trigger zone: 20–28px
- panel width: 280–320px
- opening: 200–280ms
- closing: 250–400ms
- ease-out
- no bounce

Possible contents:

```text
CONTENTS

01 Front Page
02 India
03 World
04 Economy
05 Science & Technology
06 Health
07 Environment
08 Culture
09 Sport
...

EDITION
Morning
Midday
Evening

READING
Page controls
```

Keep it quiet and functional.

---

# 14. HOME + MY DESK NAVIGATION — NEW ICON RAIL

For **Home and My Desk**, replace the large sidebar/navigation treatment with a slim icon rail.

Target width:

**approximately 52–60px**

Conceptually:

```text
│
│  Home
│  Aquila
│  My Desk
│  Search
│
│
│  Saved
│  Settings
│
```

But visually show **icons only**.

Requirements:

- fixed left side
- subtle
- active state
- hover tooltip
- keyboard accessible
- no large labels
- no excessive visual chrome

Suggested interaction:

- hover → tooltip
- click → navigate
- active page → restrained background/accent
- focus → visible keyboard focus state

This should make the product feel more like a distinctive application and less like a conventional website.

---

# 15. HOME — SERIOUS OVERHAUL REQUIRED

The Home page needs more than polish.

The current Home has good content but is still fundamentally a news-feed composition.

Current pattern feels like:

```text
headline
image
summary
source

headline
image
summary
source

headline
image
summary
source
```

This creates repetition and stale visual rhythm.

---

# 16. HOME TARGET STRUCTURE

## Header

Quiet, editorial:

```text
JUSTNEWS
A clearer tomorrow

Good evening.

HERE'S WHAT MATTERS TODAY.
```

Do not overload the header with every navigation destination.

---

# 17. HOME — THE BIG THREE

Create a dominant editorial section:

### THE BIG THREE

One major story + two supporting stories.

Conceptually:

```text
┌───────────────────────────────────────────────┐
│                                               │
│                BIGGEST STORY                  │
│                                               │
│             huge headline                    │
│             why it matters                    │
│                                               │
│             [large image]                     │
│                                               │
├────────────────────────┬──────────────────────┤
│ STORY 2                │ STORY 3              │
│                        │                      │
└────────────────────────┴──────────────────────┘
```

The first story should clearly dominate.

---

# 18. HOME — WHAT YOU SHOULD KNOW

After the Big Three:

Create a compact editorial grid of approximately 5–10 important stories.

Use varied compositions.

Avoid repeated identical cards.

---

# 19. HOME — MORE FROM THE WORLD

Then provide the broader news stream.

This is where density is appropriate.

The hierarchy should therefore be:

```text
WHAT MATTERS
      ↓
WHAT YOU SHOULD KNOW
      ↓
MORE FROM THE WORLD
```

This is much stronger than treating every article equally.

---

# 20. HOME — CONTENT SNIPPETS MUST BE SHORTER

Current article snippets can look scraped.

Prefer:

```text
HEADLINE

Why it matters / concise summary

SOURCE · TIME
```

Do not show large publisher descriptions unless they are genuinely useful.

The product should feel like it has **editorial intelligence**, not like it is exposing raw RSS text.

---

# 21. HOME — RAW LIVE-BLOG CONTENT MUST BE CLEANED

A particularly problematic pattern is content such as:

> “Updates from 5.30pm BST kick-off... Live scoreboard | Clockwatch | Mail Billy 4 min...”

This looks like raw publisher/live-blog content leaking into the UI.

Do not simply render raw descriptions everywhere.

Normalize content into:

- headline
- concise summary
- source
- time
- optional “why it matters”

If summarization is unavailable, truncate aggressively and intelligently.

Do not reproduce full third-party article bodies.

---

# 22. HOME — STATISTICS

Current metrics such as:

```text
6,450 articles
70 sources
14 languages
234 stories
```

can feel like generic SaaS dashboard cards.

Prefer either:

### Option A
Remove them from the primary reading flow.

### Option B
Render them as quiet editorial metadata:

```text
70 SOURCES
14 LANGUAGES
234 STORIES TODAY
```

Do not give them dominant dashboard-card styling.

---

# 23. MY DESK — SERIOUS OVERHAUL REQUIRED

The current My Desk is essentially a sign-in gate.

That is not enough.

My Desk needs a strong product identity:

> **personal intelligence workspace**

---

# 24. MY DESK TARGET

Header:

```text
MY DESK

Your topics.
Deeper understanding.
```

Then:

### YOUR TOPICS

Examples:

```text
AI
Semiconductors
India
Markets
Space
Climate
Politics
Energy
```

Use restrained topic chips/tabs.

---

# 25. MY DESK — WHAT CHANGED

Show important developments affecting selected topics.

Possible editorial composition:

```text
WHAT CHANGED

AI
major development...

MARKETS
major development...

SEMICONDUCTORS
major development...
```

Use varied hierarchy.

---

# 26. MY DESK — UNDERSTAND

Even before advanced Analysis exists, the page can provide:

- what is happening
- important developments
- source perspectives
- recent history
- context

Possible conceptual modules:

```text
UNDERSTAND THE TOPIC

What's happening
────────────────
5 important developments

Who is saying what
──────────────────
source/perspective comparison

What's changing
────────────────
recent development timeline
```

Do not implement the future advanced Analysis system prematurely.

---

# 27. MY DESK SHOULD FEEL PERSONAL

The user should feel:

> “This is my information workspace.”

not:

> “This is another page showing news.”

Use selected topics as the organizing principle.

---

# 28. SEARCH

Search can remain lower priority.

Current implementation is too minimal.

Target:

```text
SEARCH

What are you trying to understand?

┌──────────────────────────────────────┐
│ semiconductor tariffs                │
└──────────────────────────────────────┘

Recent searches

Results
────────

234 results

HEADLINE
SOURCE · TIME · TOPIC
```

Add useful filters eventually:

- source
- date
- topic
- language

Do this after Home/Aquila/My Desk.

---

# 29. GLOBAL HEADER

The global header currently carries too much:

- logo
- Home
- Aquila
- My Desk
- Search
- search field
- sign in
- language

This contributes to the stale website feeling.

The target interaction system should instead be:

### Home / My Desk
Slim icon rail.

### Aquila
Full-screen newspaper reader with no permanent global navigation.

### Search
Dedicated search interface accessible through the icon rail.

---

# 30. FOOTER

Avoid repeating the complete main navigation in the footer.

Make it quiet:

```text
JUSTNEWS
A clearer tomorrow.

Privacy · Feedback · Languages
```

The footer should not compete with editorial content.

---

# 31. EDITORIAL RHYTHM

The entire site needs more visual rhythm.

Avoid:

```text
title
content
title
content
title
content
```

Aim for:

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
- restrained rules

to create hierarchy.

---

# 32. DO NOT TURN EVERYTHING INTO CARDS

Avoid:

```text
┌────────────┐
│ story      │
└────────────┘

┌────────────┐
│ story      │
└────────────┘

┌────────────┐
│ story      │
└────────────┘
```

Cards should be used only where they provide real interaction or grouping value.

Editorial pages should primarily use:

- whitespace
- typography
- columns
- alignment
- image scale
- subtle rules

---

# 33. COLOR DIRECTION

Normal JustNews:

- warm white
- charcoal
- muted gray
- restrained red accent

Aquila:

- cream paper
- dark ink
- red
- restrained olive/ochre/blue accents
- dark workspace

Do not make the entire product beige.

Aquila should be visually special.

---

# 34. AQUILA HALFTONE

Every Aquila article image should receive the consistent halftone print treatment.

Approximate:

- large image dots: 2–4px
- small image dots: 1.5–3px

The effect should remain recognizable.

Do not create:

- pixel art
- RGB glitch
- CRT scanlines
- comic-book pop art
- random grain

Preferred conceptual pipeline:

```text
original image
      ↓
halftone treatment
      ↓
cached/efficient derivative or scoped rendering
      ↓
Aquila
```

A route-scoped CSS/SVG approach is acceptable as a pragmatic first version if it produces the required result and avoids unnecessary server-side image infrastructure.

Do not add storage/processing infrastructure simply for visual effects unless the repository demonstrates a real need.

---

# 35. AQUILA PAGE DIMENSIONS

Desktop targets:

### 1440×900
- paper width: 1080–1180px
- paper height: 700–790px

### 1920×1080
- paper width: 1300–1450px
- paper height: 820–900px

Ratio:

`1.45–1.55 : 1`

Page padding:

- vertical: 28–40px
- horizontal: 34–48px

---

# 36. AQUILA TYPOGRAPHY

Use:

### Masthead
Cormorant Garamond.

### Editorial headlines
Cormorant Garamond or appropriate editorial serif.

### UI/metadata
IBM Plex Sans or equivalent.

Approximate sizes:

| Element | Size |
|---|---:|
| Masthead | 78–100px |
| Lead headline | 48–64px |
| Major headline | 30–42px |
| Secondary headline | 20–30px |
| Small headline | 15–20px |
| Body | 13–16px |
| Section label | 10–12px |
| Metadata | 9–11px |
| Caption | 8–10px |

Lead line-height:

`0.90–1.00`

Section labels:

- uppercase
- restrained red
- 1.2–2px letter spacing

---

# 37. AQUILA INTERACTION

Page turning is the primary interaction.

Animation:

- 350–550ms
- subtle
- no bounce
- no exaggerated physics

Keyboard:

- Left Arrow → previous
- Right Arrow → next
- Home → first
- End → last
- Esc → close overlay

Controls:

- 36–44px
- simple
- page indicator such as `1 / 12`

---

# 38. MOBILE

## Home/My Desk

Icon rail should adapt appropriately.

Do not let navigation consume the majority of the screen.

## Aquila

Use:

- one newspaper page at a time
- vertical scroll inside page
- horizontal swipe between pages
- bottom navigation outside newspaper

Do not squeeze desktop newspaper into mobile.

---

# 39. ACCESSIBILITY

All new interaction patterns must remain accessible.

## Icon rail

- keyboard navigable
- tooltip should not be the only way to understand an icon
- visible focus state
- accessible labels

## Aquila sliding bar

- keyboard-accessible alternative
- does not rely exclusively on pointer proximity
- Escape closes
- focus management

## Page turning

- keyboard support
- reduced-motion support

## Motion

Respect:

`prefers-reduced-motion`

When reduced motion is enabled, replace page-turn/sidebar animations with immediate or very subtle transitions.

---

# 40. PERFORMANCE

Do not let the visual redesign create unacceptable performance regressions.

Inspect:

- image loading
- halftone processing
- layout shifts
- font loading
- page-turn implementation
- mobile performance

Use:

- lazy loading where appropriate
- responsive images
- WebP/AVIF where appropriate
- cached derivatives where appropriate

Do not add server-side image infrastructure without demonstrating the need.

---

# 41. ARCHITECTURE CONSTRAINTS

Preserve unless there is a concrete reason to change:

- backend
- database
- authentication
- recommendation engine
- ingestion
- content pipeline
- APIs
- admin
- existing data models
- deployment

Focus on:

> **presentation + information architecture + interaction**

Do not rewrite business logic merely because components are being redesigned.

---

# 42. NEW RECOMMENDED IMPLEMENTATION PRIORITY

The previous 8-chunk plan should now be updated to reflect the actual current-state gaps.

## Phase 0 — Verify deployment

Confirm the current production deployment corresponds to the intended code.

## Phase 1 — Navigation system

Implement:

- Home/My Desk icon rail
- Aquila right-edge utility rail
- removal of permanent Aquila top nav

## Phase 2 — Aquila structural rebuild

Do not merely polish.

Build:

- newspaper shell
- paper canvas
- masthead
- editorial grid
- lead
- left rail
- varied right editorial rail
- lower row
- Today's Highlights

## Phase 3 — Aquila reader

Implement:

- full-screen workspace
- edge-triggered right utility bar
- contents
- page navigation
- keyboard
- page transitions

## Phase 4 — Home redesign

Implement:

- The Big Three
- What You Should Know
- More From The World
- shorter article summaries
- stronger editorial rhythm

## Phase 5 — My Desk redesign

Implement:

- Your Topics
- What Changed
- Understand/context
- perspective-oriented topic presentation

## Phase 6 — Content normalization

Fix:

- raw RSS descriptions
- live-blog leakage
- overly long snippets
- inconsistent metadata

## Phase 7 — Search

Improve search UI and filtering.

## Phase 8 — Visual polish

Finalize:

- typography
- colors
- halftone
- spacing
- motion
- print character
- responsive behavior
- accessibility

## Phase 9 — QA/performance

Run full visual and technical QA.

---

# 43. CLAUDE CODE EXECUTION PROTOCOL

Before editing:

1. Inspect repository.
2. Confirm production/deployment state.
3. Inspect routes.
4. Inspect components.
5. Inspect styling.
6. Inspect existing fonts.
7. Inspect image pipeline.
8. Inspect edition data.
9. Inspect Home architecture.
10. Inspect My Desk architecture.
11. Identify reusable components.
12. Separate business logic from presentation logic.
13. Produce a file-level implementation plan.
14. Implement in small phases.
15. Run tests/build after each major phase.

Do not assume old audit assumptions still match the repository.

---

# 44. CLAUDE MUST PRODUCE A PLAN BEFORE MAJOR CHANGES

The plan should state:

- current architecture
- current problems
- reusable components
- components to replace
- new components
- route changes
- styling changes
- image strategy
- edition strategy
- navigation strategy
- responsive strategy
- accessibility strategy
- performance risks
- testing strategy
- deployment verification

Do not invent file paths before inspecting the repo.

---

# 45. ACCEPTANCE CRITERIA

## Aquila

A user should immediately recognize:

> “I am reading a newspaper.”

Not:

> “I am browsing another news website.”

The paper dominates the viewport.

The masthead is:

**AQUILA TRIBUNE**

with:

**THE WORLD IN CONTEXT**

No Samarkan.

No permanent category navbar.

Editorial grid is visible through composition, not excessive borders.

Every Aquila article image receives the halftone treatment.

Right utility bar is hidden until the user approaches the right edge.

---

## Home

A user should immediately understand:

> “These are the things that matter right now.”

The page must have:

1. dominant stories
2. supporting important stories
3. broader stream

It must not look like a uniform article feed.

---

## My Desk

A signed-in user should immediately understand:

> “This is my topic workspace.”

It should show:

- topics
- changes
- context
- perspectives

not merely a feed or sign-in gate.

---

## Navigation

Home/My Desk:

- slim icon rail
- icons only
- tooltips
- active state

Aquila:

- no permanent global nav
- right-edge sliding utility bar

---

## Content

No raw live-blog descriptions dominating cards.

No unnecessarily long scraped-looking snippets.

Source attribution remains visible.

---

## Performance

No major regressions from:

- halftone
- animations
- fonts
- responsive layouts

---

# 46. FINAL DESIGN PRINCIPLE

The most important rule:

> **Clarity over decoration.**

The interface should clarify:

- what matters
- what happened
- why it matters
- what the user is reading
- how stories relate
- where the user should go next

The site should feel:

- editorial
- intelligent
- calm
- authoritative
- human
- modern
- distinctive

It should not feel:

- corporate SaaS
- generic AI
- social media
- content farm
- template-driven
- overly futuristic

---

# 47. FINAL TARGET

The finished JustNews product should feel like:

```text
JUSTNEWS
A clearer tomorrow.

HOME
NOW
What’s happening?

AQUILA
TODAY
What mattered?
The world in context.

MY DESK
ME
What do I care about?

SEARCH
What am I looking for?
```

The visual system should make these differences obvious.

---

# 48. FINAL INSTRUCTION TO CLAUDE

**Treat this document as a second-pass correction brief.**

Do not blindly repeat the previous implementation.

First inspect what is actually present now.

Then identify:

1. Which requested changes were successfully implemented.
2. Which are only partially implemented.
3. Which are missing.
4. Which implementations are technically correct but visually wrong.
5. Which new changes are required based on this audit.

Then produce a concrete implementation plan.

The most important immediate goals are:

1. **Verify deployment.**
2. **Make Aquila genuinely newspaper-first.**
3. **Implement the right-edge sliding utility bar in Aquila.**
4. **Replace Home/My Desk side navigation with a small icon rail.**
5. **Seriously redesign Home.**
6. **Seriously redesign My Desk.**
7. **Normalize article content so raw publisher text does not dominate the UI.**
8. **Remove stale/repetitive card-based visual patterns.**
9. **Preserve existing backend/recommendation/ingestion/auth systems.**
10. **Finish with a real visual QA pass rather than assuming implementation = finished.**
