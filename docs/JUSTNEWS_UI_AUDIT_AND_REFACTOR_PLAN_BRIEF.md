# JustNews --- UI/UX Audit, Product Direction & Claude Code Refactor Planning Brief

## Purpose

This is the master planning brief for Claude Code. Use it to inspect the
existing JustNews repository and produce a proper implementation plan
before making major UI changes.

**Do not redesign JustNews blindly from scratch.** Preserve working
backend, database, authentication, recommendation, ingestion, APIs,
content pipeline and deployment architecture unless inspection reveals a
concrete bug or a genuinely necessary interface change.

The main problem being addressed is the **presentation layer,
information architecture, visual system and interaction design**.

------------------------------------------------------------------------

# 1. Product Vision

JustNews should evolve from a conventional news aggregator/feed into a
news-intelligence product focused on clarity.

Brand:

**JustNews --- A clearer tomorrow**

Supporting line:

**Same world. More clarity.**

The product should help users understand what matters rather than simply
expose them to more articles.

There are three distinct reading experiences:

-   **Home** --- What is happening? What matters right now?
-   **Aquila** --- What mattered? The world in context.
-   **My Desk** --- What do I want to understand?
-   **Search** --- Find what matters.

These must feel meaningfully different.

------------------------------------------------------------------------

# 2. Core Information Architecture

## Home

Purpose:

> **What matters right now.**

Home is the **live + personalized** experience.

Use three hierarchy levels:

### Level 1 --- What matters

Approximately 1--3 dominant stories.

### Level 2 --- What you should know

Approximately 5--10 important stories.

### Level 3 --- What else is happening

A denser stream of additional stories.

Do not make every article equally prominent.

The current Home has useful foundations such as source diversity, Daily
Brief, personalization/trending and overview statistics, but it
currently feels too much like a conventional news feed.

Improve hierarchy and editorial composition without destroying the
recommendation system.

------------------------------------------------------------------------

# 3. Aquila

Purpose:

> **The world in context.**

Aquila is the **scheduled editorial newspaper**.

Final branding:

**AQUILA TRIBUNE**

**THE WORLD IN CONTEXT**

Aquila should feel like the user is opening a real digital newspaper,
not another web feed.

This is the highest-priority redesign.

------------------------------------------------------------------------

# 4. My Desk

Purpose:

> **What do I want to understand?**

My Desk is the personalized topic workspace.

Eventually it should support:

-   topic selection
-   followed topics
-   topic news
-   summaries
-   multiple perspectives
-   topic history/context
-   saved/followed items
-   later, deeper analysis

**Analysis is a later feature.** Do not let it overcomplicate the
initial My Desk architecture.

The first meaningful version should establish:

1.  topic selection
2.  topic overview
3.  topic news
4.  perspective/context

The current implementation is primarily a sign-in gate and needs to
become an actual workspace after authentication.

------------------------------------------------------------------------

# 5. Search

Purpose:

> **Find what matters.**

Search is a separate utility.

Eventually support:

-   prominent search field
-   results
-   recent searches
-   source/date/topic/language filters
-   clear result hierarchy
-   multilingual search behavior

Do not overbuild Search before Home and Aquila are strong.

------------------------------------------------------------------------

# 6. Normal Navigation

Core navigation:

-   Home --- What matters right now.
-   Aquila --- The world in context.
-   My Desk --- Your topics. Deeper understanding.
-   Search --- Find what matters.

Secondary destinations may include:

-   Saved
-   Settings
-   Account

## Critical Aquila navigation rule

Do **not** use a permanent top navigation such as:

> News · Ideas · People · Perspectives

Do **not** make:

> INDIA \| WORLD \| BUSINESS \| SPORTS

a permanent website navigation bar.

These are **newspaper editorial sections/pages**, not the main
application navigation.

------------------------------------------------------------------------

# 7. Aquila Full-Screen Reader

Entering Aquila should feel like opening a newspaper.

Requirements:

-   full-screen reading workspace
-   newspaper is the dominant object
-   dark workspace around it
-   normal JustNews navigation hidden
-   navigation revealed when cursor approaches left edge

Workspace:

`#20211F`

Newspaper:

-   centered
-   square corners
-   subtle paper shadow
-   no rounded SaaS-card appearance

Suggested shadow:

`0 8px 30px rgba(0,0,0,0.12)`

------------------------------------------------------------------------

# 8. Final Aquila Visual Direction

Approved direction:

-   cream newspaper
-   refined editorial typography
-   restrained print character
-   sophisticated, calm and authoritative

Approximate balance:

-   70% contemporary editorial newspaper
-   30% physical print character

Avoid:

-   generic AI aesthetics
-   glassmorphism
-   neon
-   purple AI gradients
-   excessive cards
-   excessive borders
-   excessive animation
-   random grunge
-   CRT/RGB glitch
-   comic-book styling
-   decorative clutter

The design should communicate:

**authority + clarity + context + editorial judgment**

------------------------------------------------------------------------

# 9. Aquila Masthead

The masthead must read:

**AQUILA TRIBUNE**

Use a **large, high-contrast editorial serif**.

Suitable direction:

-   Bodoni
-   Didot
-   Cormorant Garamond Display
-   similar premium editorial serif

## Non-negotiable

**DO NOT USE SAMARKAN.**

Do not use Indian decorative/script/calligraphic fonts for the masthead.

Approximate size:

-   78--100px at \~1100px newspaper width
-   96--120px maximum on very large desktop

Subtitle:

**THE WORLD IN CONTEXT**

Subtitle:

-   uppercase
-   12--15px
-   3--5px letter spacing

------------------------------------------------------------------------

# 10. Aquila Header

Approximate approved structure:

### Top-left

``` text
A CLEARER
TOMORROW

VOL. 1 NO. 42
```

### Center

``` text
AQUILA TRIBUNE
THE WORLD IN CONTEXT
```

### Top-right

``` text
NEWS
PEOPLE
IDEAS
PERSPECTIVE

FRI, 5 SEPTEMBER 2025
NEW DELHI
```

Exact dates must come from application edition data, not hardcoded UI
strings.

------------------------------------------------------------------------

# 11. Three Daily Editions

Required schedule:

-   **06:00 AM --- Morning**
-   **02:00 PM --- Midday**
-   **10:00 PM --- Evening**

The selector should be restrained:

-   text-based
-   underline/active state
-   no large edition cards

The current live UI has shown a value like:

> 4:47 PM Midday Edition

This is wrong relative to the desired fixed schedule.

------------------------------------------------------------------------

# 12. Edition Source of Truth

Use one coherent source of truth containing concepts such as:

``` text
edition_date
edition_type
published_at
```

where:

``` text
edition_type = morning | midday | evening
```

All visible edition labels should be derived from this.

The live implementation has also displayed inconsistent metadata such
as:

> Vol. 1 No. 1 Saturday, September 5, 2026 Midday Edition

while the current date is September 6, 2026.

Claude must inspect where this data currently originates and propose the
smallest safe correction.

Do not unnecessarily redesign the backend.

------------------------------------------------------------------------

# 13. Aquila Page Structure

Page 1 is the front page.

Subsequent pages are editorial newspaper pages.

A reasonable structure:

1.  Front Page
2.  India
3.  World / Conflict, War and Peace
4.  Economy, Business and Finance
5.  Science and Technology
6.  Health
7.  Environment / Climate
8.  Arts, Culture, Entertainment and Media
9.  Sport
10. Perspectives / Ideas
11. Society
12. Optional additional context/editorial page

The current 9-page structure is a usable foundation. The issue is
presentation, not simply page count.

Pages must feel like newspaper pages, not category webpages.

------------------------------------------------------------------------

# 14. Aquila Front Page Grid

Target desktop proportions:

-   left editorial rail: 15--17%
-   main lead: 58--62%
-   right rail: 23--27%

Underlying grid:

-   approximately 12 columns
-   12--18px gutters
-   mostly invisible

Dimensions:

### 1440×900

-   newspaper: 1080--1180px wide
-   height: 700--790px

### 1920×1080

-   newspaper: 1300--1450px wide
-   height: 820--900px

Approximate ratio:

`1.45–1.55 : 1`

Page padding:

-   top/bottom 28--40px
-   left/right 34--48px

------------------------------------------------------------------------

# 15. Aquila Front Page Editorial Composition

## Left editorial rail

Include:

> "Better information builds a better tomorrow."\
> --- JUSTNEWS

Also:

**IN FOCUS**

with:

-   halftone image
-   headline
-   short summary
-   page reference

Do not box this like a magazine sidebar.

## Main lead

Use one dominant story.

Structure:

``` text
INDIA

Leaders Meet in New Delhi to Shape
a More Stable Asia

Short summary...

2–3 short context paragraphs...

[large halftone image]

Byline
CONTINUED ON PAGE 2
```

The lead story must clearly dominate.

## Right rail

Possible topics:

-   Technology
-   Economy
-   Climate

Vary compositions:

-   image above text
-   image beside text
-   text dominant
-   image-left/text-right
-   text-left/image-right
-   larger/smaller headlines

Avoid repeated identical cards.

## Lower row

Use approximately three stories:

-   Society
-   Ideas
-   Culture

Do not use four equally dense cards.

## Today's Highlights

Transform or integrate the current "The brief" concept into:

**TODAY'S HIGHLIGHTS**

Use compact numbered items with page references.

------------------------------------------------------------------------

# 16. Aquila Footer

Suggested:

``` text
AQUILA TRIBUNE

People. Context. A More Informed Tomorrow.

JUSTNEWS
```

Keep compact.

------------------------------------------------------------------------

# 17. Typography System

### Masthead

Large high-contrast editorial serif.

### Headlines

High-quality editorial serif, e.g. Cormorant Garamond.

### Metadata/UI

IBM Plex Sans or similar restrained sans.

Approximate hierarchy:

  Element                     Size
  -------------------- -----------
  Masthead               78--100px
  Lead headline           48--64px
  Major headline          30--42px
  Secondary headline      20--30px
  Small headline          15--20px
  Body                    13--16px
  Section label           10--12px
  Metadata                 9--11px
  Caption                  8--10px

Lead line-height:

`0.90–1.00`

Section labels:

-   uppercase
-   red
-   1.2--2px letter spacing

------------------------------------------------------------------------

# 18. Color System

Workspace:

`#20211F`

Paper:

`#F5F1E8`

Optional brighter paper:

`#FBF9F4`

Primary ink:

`#171717`

Secondary:

`#333333`

Muted:

`#77736C`

Rules:

`#A8A197`

Primary accent:

`#A52E2A`

Optional restrained secondary print colors:

-   muted olive
-   muted blue
-   muted ochre
-   muted terracotta

Avoid bright digital colors.

Target balance:

-   \~75% cream
-   \~20% dark ink
-   \~5% accents

------------------------------------------------------------------------

# 19. Halftone Image System

**Every Aquila article image must use the consistent halftone print
treatment.**

Target:

-   recognizable photographs
-   limited tonal range
-   newspaper/screen-print appearance
-   black/cream foundation
-   restrained muted color accents

Approximate dot size:

-   large images: 2--4px
-   small images: 1.5--3px

Do not make it:

-   pixel art
-   RGB glitch
-   CRT scanlines
-   comic-book pop art
-   random grain
-   unreadable abstraction

Preferred conceptual pipeline:

``` text
original image
      ↓
halftone processing
      ↓
cached derivative
      ↓
Aquila rendering
```

Use responsive/lazy-loaded images and WebP/AVIF where appropriate.

Claude should inspect the existing image pipeline and introduce this
treatment at the safest reusable layer rather than damaging non-Aquila
images.

------------------------------------------------------------------------

# 20. Print Character

Rules should be restrained.

Reduce visible rules by roughly 25--35% from overly boxed layouts.

Use alignment, whitespace, typography and image placement to establish
the grid.

Subtle paper texture is acceptable.

Controlled print imperfections are acceptable only if they do not
damage:

-   alignment
-   legibility
-   hierarchy

No sloppy "fake newspaper" styling.

------------------------------------------------------------------------

# 21. Aquila Interactions

Primary interaction:

> **Turning pages**

Page-turn:

-   350--550ms
-   subtle
-   no bounce
-   no exaggerated physics

Keyboard:

-   Left Arrow → previous page
-   Right Arrow → next page
-   Home → first page
-   End → last page
-   Esc → close overlays

Controls:

-   simple arrows
-   36--44px
-   indicator such as `1 / 12`

------------------------------------------------------------------------

# 22. Aquila Sidebar

Normal JustNews navigation is hidden.

When cursor approaches left edge:

-   trigger within 20--28px of viewport edge
-   sidebar width 280--320px
-   overlay newspaper
-   does not force layout reflow
-   opening: \~200--280ms ease-out
-   closing: \~250--400ms

Suggested contents:

``` text
JUSTNEWS

Home
Aquila
My Desk
Search

Saved
Settings

Back to JustNews
```

------------------------------------------------------------------------

# 23. Contents Overlay

Provide a Contents control.

Approximate width:

280--360px

Show:

``` text
01  Front Page
02  India
03  World
04  Economy
05  Science & Technology
06  Health
07  Environment
08  Culture
09  Sport
...
```

Show active page clearly.

------------------------------------------------------------------------

# 24. Responsive Aquila

## Desktop

Newspaper dominates viewport.

## Tablet

Scale dimensions and typography while preserving hierarchy.

## Mobile

Do not squeeze desktop newspaper into a tiny viewport.

Use:

-   one newspaper page at a time
-   vertical scrolling inside the page
-   horizontal swipe between pages
-   bottom navigation outside the newspaper

------------------------------------------------------------------------

# 25. Current Live-Site Audit Findings

The current live implementation was reviewed across Home, Aquila, My
Desk and Search.

## Aquila

### Problem 1 --- Old design still dominates

Aquila still behaves like a conventional webpage/feed.

**Fix:** rebuild the presentation and interaction layer around the
newspaper metaphor.

### Problem 2 --- Permanent category navigation

Current `News · Ideas · People · Perspectives` style navigation
conflicts with the newspaper concept.

**Fix:** remove permanent web-style category navigation.

### Problem 3 --- Masthead mismatch

Current masthead does not match the approved editorial identity.

**Fix:** use the high-contrast editorial serif masthead.

**No Samarkan.**

### Problem 4 --- Too much web-page DNA

It feels like "news website + newspaper styling."

Target:

> actual digital newspaper reader

### Problem 5 --- Editorial grid is missing

The live page does not strongly communicate:

-   one dominant lead
-   left editorial rail
-   main lead
-   varied right rail
-   lower story row
-   newspaper hierarchy

**Fix:** implement the approved grid.

### Problem 6 --- Halftone is missing

The required consistent newspaper image treatment is not implemented.

**Fix:** introduce the halftone derivative pipeline.

### Problem 7 --- "The brief" is useful

Keep the concept and transform/integrate it as **Today's Highlights**.

### Problem 8 --- Nine pages are fine

Current nine-page structure is a valid foundation.

**Fix presentation, not page count for its own sake.**

### Problem 9 --- Edition time is wrong

Current UI can show values such as `4:47 PM Midday Edition`.

**Fix:** fixed schedule of 06:00 / 14:00 / 22:00.

### Problem 10 --- Edition date/version can be inconsistent

The displayed edition date has been inconsistent with the actual current
date.

**Fix:** one edition source of truth.

------------------------------------------------------------------------

# 26. Home Audit

Strengths to preserve:

-   JustNews branding
-   "A clearer tomorrow"
-   source diversity
-   Today at a glance
-   Daily Brief
-   For You
-   Trending
-   recommendation infrastructure

Problems:

-   too much feed-like repetition
-   too many similarly weighted stories
-   repeated card patterns
-   snippets can be too long/scraped-looking
-   insufficient editorial hierarchy

Fix with:

1.  What matters
2.  What you should know
3.  What else is happening

Preserve source diversity and recommendation logic.

------------------------------------------------------------------------

# 27. Home vs Aquila vs My Desk

This distinction is critical.

### Home

**Live + personalized**

Question:

> What is happening and what matters to me right now?

### Aquila

**Scheduled + editorial**

Question:

> What mattered, and what is the broader context?

### My Desk

**Personalized + topic-focused**

Question:

> What do I want to understand?

If they look alike, the product loses its identity.

------------------------------------------------------------------------

# 28. My Desk Audit

Current implementation largely shows a sign-in gate.

That is acceptable as an authentication state but not as the final
experience.

After sign-in, target:

-   selected topics
-   topic summaries
-   latest developments
-   source/perspective diversity
-   history/context
-   saved/followed items

Build the topic workspace first.

Defer advanced Analysis.

------------------------------------------------------------------------

# 29. Search Audit

Current Search is too minimal.

Target eventually:

-   prominent search input
-   result list
-   source
-   date/time
-   topic/category
-   language
-   useful filters
-   recent searches

Do not over-engineer it before core experiences.

------------------------------------------------------------------------

# 30. Navigation Audit

Current site navigation can feel duplicated.

Final distinction:

### Normal JustNews

Clear global navigation.

### Aquila

Full-screen reader with hidden navigation and edge-triggered sidebar.

This should make Aquila feel like a newspaper, not simply another route.

------------------------------------------------------------------------

# 31. Content Presentation

Current snippets can feel too long and scraped.

Prefer:

``` text
HEADLINE

Why it matters / concise summary

SOURCE · TIME
```

Do not reproduce full third-party articles where prohibited.

Preserve:

-   source attribution
-   publisher identity
-   time/context
-   links to original publishers
-   perspective diversity

------------------------------------------------------------------------

# 32. What Must NOT Be Changed Unnecessarily

Do not rewrite merely for UI reasons:

-   backend architecture
-   database
-   authentication
-   recommendation logic
-   news ingestion
-   content pipeline
-   APIs
-   admin systems
-   data models
-   deployment architecture

Only change them when inspection identifies a real bug or necessary
contract.

------------------------------------------------------------------------

# 33. Recommended Priority Order

1.  Rebuild Aquila front page
2.  Implement final typography
3.  Implement halftone image pipeline
4.  Remove permanent Aquila category navigation
5.  Correct three-edition model
6.  Implement full-screen Aquila reader
7.  Improve Home hierarchy
8.  Build My Desk topic workspace
9.  Improve Search
10. Implement edge-triggered sidebar
11. Implement page-turn interaction
12. Add microinteractions
13. Add controlled print imperfections
14. Performance tuning
15. Future Analysis layer

------------------------------------------------------------------------

# 34. Claude Code Execution Protocol

Before editing:

## Step 1 --- Inspect repository

Identify:

-   framework
-   routing
-   app structure
-   components
-   styling
-   fonts
-   image loading
-   state management
-   data fetching
-   APIs
-   auth
-   Aquila implementation
-   Home
-   My Desk
-   Search

## Step 2 --- Inventory UI

Identify reusable:

-   layout components
-   article components
-   cards
-   navigation
-   typography
-   image components
-   buttons
-   modals
-   transitions
-   breakpoints

## Step 3 --- Map dependencies

Determine:

-   shared components
-   Aquila-specific components
-   business logic vs presentation logic
-   data-fetching boundaries
-   editorial content assembly

## Step 4 --- Audit design tokens

Identify existing:

-   colors
-   spacing
-   typography
-   breakpoints
-   shadows
-   radii
-   motion

Consolidate where useful.

## Step 5 --- Plan Aquila

Plan:

-   newspaper shell
-   masthead
-   editorial grid
-   story modules
-   halftone images
-   page navigation
-   contents
-   sidebar
-   edition selector
-   responsive behavior

## Step 6 --- Plan Home

Map existing components to the three-level hierarchy.

## Step 7 --- Plan My Desk

Define minimum topic workspace.

## Step 8 --- Plan Search

Define minimum useful search upgrade.

## Step 9 --- Plan testing

Include:

-   1440 desktop
-   1920 desktop
-   1280 desktop
-   tablet
-   mobile
-   keyboard
-   reduced motion
-   accessibility
-   missing images
-   long headlines
-   missing metadata
-   varying source names
-   multilingual content
-   edition boundaries
-   page transitions

## Step 10 --- Validate

Run existing:

-   tests
-   lint
-   type checks
-   production build

Do not assume a visual preview means the project is production-safe.

------------------------------------------------------------------------

# 35. What Claude Must Produce Before Implementation

Produce a proper implementation plan containing:

## A. Current architecture

What exists.

## B. Problems

What conflicts with this brief.

## C. Proposed architecture

What routes/components/data boundaries change.

## D. Reuse strategy

What remains untouched.

## E. Migration strategy

How to introduce changes safely.

## F. File-level plan

Likely files to modify/create/deprecate, **after inspecting the repo**.

## G. Phased implementation

Small, testable milestones.

## H. Dependencies

Fonts, image-processing libraries, UI libraries, etc.

## I. Risk assessment

Especially:

-   image-processing cost
-   responsive newspaper layout
-   page transitions
-   edition synchronization
-   accessibility
-   performance
-   API compatibility

## J. Acceptance criteria

Concrete definition of done for each phase.

------------------------------------------------------------------------

# 36. Overall Acceptance Criteria

The redesign succeeds when:

-   JustNews clearly communicates **A clearer tomorrow**
-   Home feels live and personalized
-   Aquila unmistakably feels like a digital newspaper
-   My Desk feels like a topic workspace
-   Search feels like a utility
-   Aquila has no permanent website-style category navigation
-   Aquila uses the approved editorial-serif masthead
-   Samarkan is not used
-   every Aquila article image uses the consistent halftone treatment
-   three editions are represented correctly: 06:00 / 14:00 / 22:00
-   edition metadata comes from one source of truth
-   source attribution remains visible
-   responsive layouts work at desktop/tablet/mobile
-   keyboard and reduced-motion behavior work
-   performance remains acceptable
-   existing backend/recommendation/ingestion/auth systems remain stable

------------------------------------------------------------------------

# 37. Design Philosophy

Most important principle:

> **Clarity over decoration.**

Every design decision should clarify:

-   what matters
-   what happened
-   why it matters
-   what the user is reading
-   how stories relate
-   where the user can go next

The finished product should feel:

-   editorial
-   intelligent
-   calm
-   authoritative
-   human
-   modern
-   distinctive

It should not feel:

-   corporate SaaS
-   generic AI
-   social media
-   content farm
-   template-driven
-   overly futuristic

------------------------------------------------------------------------

# 38. Existing Strengths to Preserve

The current product already has valuable foundations:

-   JustNews branding
-   "A clearer tomorrow"
-   source diversity
-   multilingual direction
-   recommendation infrastructure
-   Daily Brief
-   Aquila multi-page concept
-   authentication
-   content ingestion
-   routing
-   deployment

The redesign should elevate these rather than discard them.

------------------------------------------------------------------------

# 39. Final Mental Model

``` text
JUSTNEWS
A clearer tomorrow.

HOME
What matters right now?
Live + personalized.

AQUILA
What mattered?
The world in context.
Scheduled digital newspaper.

MY DESK
What do I want to understand?
Personal topic workspace.

SEARCH
What am I looking for?
Utility.
```

Overall philosophy:

> **Same world. More clarity.**

------------------------------------------------------------------------

# 40. Final Instruction

**Do not immediately rewrite the codebase.**

First inspect the repository and then return a detailed plan explaining:

1.  What exists?
2.  What is wrong?
3.  What can be reused?
4.  What must be rebuilt?
5.  What should change first?
6.  How will Aquila be implemented?
7.  How will the halftone pipeline work?
8.  How will the three editions work?
9.  How will the full-screen reader work?
10. How will Home differ from Aquila?
11. How will My Desk evolve?
12. How will Search evolve?
13. What files/components are likely to change?
14. What are the technical risks?
15. How will changes be tested?
16. How will existing backend/data/recommendation systems be protected?

## Non-negotiables

-   **No Samarkan.**
-   **Aquila must not become a normal news feed.**
-   **No permanent top category navigation inside Aquila.**
-   **No excessive card grids.**
-   **No generic AI gradients/glassmorphism/neon.**
-   **Do not unnecessarily rewrite
    backend/recommendation/ingestion/auth.**
-   **Implement the consistent Aquila halftone image treatment.**
-   **Implement 06:00 / 14:00 / 22:00 editions.**
-   **Use one source of truth for edition metadata.**
-   **Preserve source attribution and provenance.**
-   **Make Aquila feel like a newspaper first and website second.**
-   **Preserve accessibility and responsive behavior.**
-   **Test the application after each major phase.**
