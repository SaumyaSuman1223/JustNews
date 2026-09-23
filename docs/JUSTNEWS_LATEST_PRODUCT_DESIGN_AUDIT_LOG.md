# JUSTNEWS --- Latest Product / Design Audit Log

## Logged: September 8, 2026

This document consolidates the current product direction, latest
live-site audit, design decisions, and implementation priorities for
JustNews.

## 1. Product Vision

**JustNews** should evolve beyond a conventional news aggregator into a
news-intelligence product focused on clarity.

**Brand** - JustNews - A clearer tomorrow - Same world. More clarity.

**Core experiences** - **Home** --- What matters right now? Live +
personalized news. - **Aquila** --- What mattered? Scheduled editorial
newspaper. - **My Desk** --- What do I want to understand? Personalized
topic workspace. - **Search** --- Find what matters. Search/research
gateway. - **Analysis** --- What does this mean for my decision? Future
expansion.

Analysis should remain a later expansion and should not drive the
initial UI architecture.

## 2. Core Product Principle

The site currently has good structural foundations but still carries too
much of the visual DNA of a conventional web feed.

The central design goal is:

> **Turn news articles into editorial objects.**

A story should have: - a role - visual weight - a relationship to other
stories - depth - context - potentially multiple perspectives

The interface should communicate **importance**, not merely article
count.

## 3. Navigation Architecture

### Home / My Desk / Search

Use a slim icon-only left rail: - approximately 52--60px - icons only -
active state - hover tooltips - keyboard accessibility - Search included
in the rail

The rail should feel like product chrome, not a conventional website
navbar.

### Aquila

Aquila should **not** use permanent global navigation.

It should behave like a full-screen newspaper reader.

Use a **right-edge sliding utility bar**: - hidden by default - appears
when the cursor approaches the right edge - overlays the
newspaper/workspace - does not cause page reflow - width: approximately
280--320px - opening: 200--280ms - closing: 250--400ms

Utility bar: - Contents - Pages - Edition - Reading controls - Other
reader utilities

The Aquila utility sidebar is separate from the newspaper's internal
editorial rail.

## 4. Aquila --- Final Design Direction

Aquila must feel like a **proper digital newspaper**, not a normal
webpage decorated with newspaper styling.

### Masthead

**AQUILA TRIBUNE**

**THE WORLD IN CONTEXT**

Recommended typography: - Masthead: **Cormorant Garamond** -
UI/metadata: **IBM Plex Sans** or restrained sans-serif - Editorial
headlines: Cormorant Garamond or equivalent

Do **not** use Samarkan or decorative Indian/calligraphic novelty fonts.

Approximate sizing: - Masthead: 78--100px at \~1100px paper width -
96--120px on very large desktop - subtitle: 12--15px uppercase -
subtitle letter spacing: 3--5px

## 5. Aquila Colour System

-   Workspace: `#20211F`
-   Paper: `#F5F1E8` or `#FBF9F4`
-   Ink: `#171717`
-   Secondary: `#333333`
-   Muted: `#77736C`
-   Rules: `#A8A197`
-   Accent: `#A52E2A`

Optional restrained secondary accents: - muted olive - muted blue -
ochre - terracotta

Overall balance:

> \~75% cream / 20% dark ink / 5% accent

Avoid: - neon - purple AI gradients - glassmorphism - excessive cards -
generic AI aesthetics - excessive borders - decorative visual noise

Paper: - square corners - subtle shadow: `0 8px 30px rgba(0,0,0,0.12)`

Target aesthetic:

> \~70% contemporary editorial newspaper + \~30% physical print
> character

## 6. Aquila Desktop Dimensions

At 1440×900: - paper width: \~1080--1180px - paper height: \~700--790px

At 1920×1080: - paper width: \~1300--1450px - paper height: \~820--900px

Target ratio: - approximately 1.45--1.55:1

Paper padding: - vertical: 28--40px - horizontal: 34--48px

Underlying grid: - \~12 columns - gutters: 12--18px - mostly invisible

Front page approximate widths: - left editorial rail: 15--17% - main
lead: 58--62% - right editorial rail: 23--27%

## 7. Aquila Front Page Composition

### Left editorial rail

Quote:

> Better information builds a better tomorrow.

--- JUSTNEWS

Then:

**IN FOCUS**

with: - image - headline - short summary - page reference

Do not turn this into a boxed magazine sidebar.

### Main lead

One dominant story containing: - section label - very large headline -
concise summary - 2--3 short context paragraphs - large halftone image -
byline - `CONTINUED ON PAGE X`

### Right editorial rail

Sections: - Technology - Economy - Climate

Do not render these as three identical cards.

Use varied editorial compositions.

### Lower row

Three stories: - Society - Ideas - Culture

Do not use four equal cards.

### Today's Highlights

Compact numbered list: - story title - page reference

Place it toward the far/right/lower-right area.

### Footer

**AQUILA TRIBUNE**

> People. Context. A More Informed Tomorrow.

**JUSTNEWS**

## 8. Aquila Page System

The existing 7--9 page structure is acceptable. Do not increase the
number of pages merely to make the product appear more substantial.

Potential sections: 1. Front Page 2. India 3. World / Conflict 4.
Economy 5. Science & Technology 6. Health 7. Environment 8. Culture 9.
Sport 10. Perspectives / Ideas 11. Society

Pages must feel like actual newspaper pages rather than category
webpages.

Reader controls: - page indicator such as `1 / 12` - Left/Right keyboard
navigation - Home/End - Esc

Page transition: - 350--550ms - subtle - no bounce

Mobile: - one page at a time - vertical scrolling inside the page -
horizontal swipe between pages - bottom navigation outside the paper

## 9. Aquila Edition Truth --- P0

This is a correctness issue, not merely a visual issue.

The production site was showing an old edition:

> Sunday, September 6, 2026 22:00 UTC

while the current date is September 8, 2026.

The site also exposed: - Morning --- 06:00 UTC - Midday --- 14:00 UTC -
Evening --- 22:00 UTC

Reader-facing UI should instead show: - **06:00 AM --- Morning** -
**02:00 PM --- Midday** - **10:00 PM --- Evening**

Do not expose UTC to readers.

Use a single source of truth: - `edition_date` - `edition_type` -
`published_at` - locale/dateline

Do not hardcode `NEW DELHI`.

Derive the dateline city from reliable edition locale/configuration. If
it cannot be determined reliably, omit it.

## 10. Aquila Navigation Bug

The production Aquila page still contains:

> News · Ideas · People · Perspectives

This makes the newspaper feel like a webpage with a newspaper skin.

Remove permanent website-style navigation from Aquila.

Normal newspaper sections should instead be represented as newspaper
pages/sections.

## 11. Halftone Image System

The desired image treatment is **not simply grayscale + noise**.

Correct conceptual pipeline:

``` text
Original publisher image
        ↓
Resize / crop
        ↓
Controlled tonal mapping
        ↓
Limited editorial palette
        ↓
Halftone dot screen
        ↓
Optional subtle ink variation
        ↓
Aquila image rendering
```

Paper texture should remain a **separate page-level layer**, not baked
into every image.

### Halftone mechanics

-   dark regions → larger/more dots
-   medium regions → medium dots
-   light regions → smaller/fewer dots

Approximate dot scale: - large images: 2--4px - small images: 1.5--3px

Palette: - black - cream - restrained red - optional olive/blue/ochre

Avoid: - bright CMYK appearance - pixel-art appearance - RGB glitch -
CRT scanlines - comic-book pop-art treatment - random grain

The image must preserve subject recognition and a strong crop/focal
point.

### Implementation direction

CSS grayscale/contrast alone is insufficient.

Possible approaches:

**First practical version:** route-scoped CSS/SVG visual treatment if it
provides sufficient quality and avoids infrastructure complexity.

**More capable final version:** WebGL/shader rendering for consistent
client-side halftone treatment, tonal mapping, palette reduction,
adjustable dot frequency, and different rendering profiles for
large/medium/small images.

Canvas pixel processing can run into CORS restrictions when working with
publisher-hosted images.

Therefore `AquilaImage` should have: - a reusable renderer - size
variants - graceful fallback if pixel access/rendering is unavailable

Do not unnecessarily introduce server-side image processing/storage.

Preserve the project's philosophy:

> Always link out. Never store publisher images.

## 12. Home --- Final Direction

Home is:

> **NOW**

Core question:

> **What matters right now?**

It should be live + personalized and should **not** feel like a
newspaper.

### Desired hierarchy

**1. What Matters / The Big Three**

One dominant story + two supporting stories.

The lead story should visually dominate: - large image - large
headline - concise why-it-matters explanation

**2. What You Should Know**

Approximately 5--10 important stories.

Use varied editorial compositions rather than identical cards.

**3. More From The World**

A denser stream for lower-priority items.

## 13. Home Header

Keep the header quiet.

Possible structure:

``` text
JUSTNEWS
A clearer tomorrow

Good morning/evening

HERE'S WHAT MATTERS TODAY.
```

The content should establish hierarchy before the article stream begins.

## 14. Daily Brief

The Daily Brief should become a mini-publication and bridge between Home
and Aquila.

Suggested structure:

``` text
TODAY'S BRIEF
September 8, 2026

THE WORLD IN 5 MINUTES

1. ...
2. ...
3. ...
4. ...
5. ...

READ THE BRIEF →
```

It should feel editorial, not like another generic card.

## 15. Home Metadata

Current statistics such as: - 8,267 articles - 117 sources - 14
languages - 289 stories

should remain **quiet metadata**.

Do not turn them into dashboard-style cards.

## 16. Home Story Text

Article snippets should be shortened.

Preferred:

``` text
HEADLINE

Why it matters: concise explanation.

SOURCE · TIME
```

Avoid exposing raw live-blog text such as:

> Updates from 5.30pm BST... Live scoreboard...

Normalize and truncate such text before presentation.

## 17. Home Editorial Importance Model

The UI should communicate why a story matters.

Potential ranking signals: - global/regional significance - recency -
number of sources - source diversity - topic relevance - velocity - user
relevance - impact - novelty

The product should rank **importance**, not simply recency or article
count.

## 18. Story Clustering --- Major Future Differentiator

Multiple publishers covering the same event should eventually become a
**story cluster**.

Example:

``` text
THE STORY

Major development in X

27 sources
11 countries
8 languages

Different outlets are emphasizing:
• ...
• ...
• ...

Timeline
09:20 — ...
11:40 — ...
14:15 — ...
```

This turns JustNews from an RSS-style aggregator into a
news-intelligence product.

## 19. Story Component System

Introduce reusable story types: - `LeadStory` - `FeatureStory` -
`StandardStory` - `BriefStory` - `ClusterStory` - `TimelineStory` -
`PerspectiveStory` - `ContextStory` - `AnalysisStory` --- future

This should replace the repeated generic article-card pattern.

## 20. My Desk --- Final Direction

My Desk represents:

> **ME**

Core question:

> **What do I care about?**

It should feel like a personal intelligence workspace, not a settings
page or pre-login preview.

### Signed-out experience

Suggested structure:

``` text
MY DESK

Your topics. Deeper understanding.

Build a personal news workspace.

Follow subjects you care about.
See what changed.
Compare perspectives.
Track developments over time.

CHOOSE YOUR TOPICS

AI
Markets
India
Space
Climate
Energy
Semiconductors
Politics

SIGN IN
```

Include one strong example topic to demonstrate value before sign-in.

### Signed-in experience

**YOUR TOPICS**

Use consumer-facing names: - AI - Markets - India - Space - Climate -
Energy - Semiconductors - Politics

Do not expose backend taxonomy wording as the primary UI.

**WHAT CHANGED**

Show important developments per topic with: - source count - language
count - update time - concise explanation

**UNDERSTAND THE TOPIC**

Future deeper topic experience should include: - what is happening -
source/perspective comparison - recent history - timeline - context

Analysis can eventually be layered into this.

## 21. Search --- Final Direction

Current Search is still mostly a skeleton.

Desired structure:

``` text
SEARCH JUSTNEWS

[ prominent search input ]

Recent searches

Results

Stories
Topics
Sources
Perspectives

Filters:
• source
• date
• topic
• language
```

Search should eventually become the gateway to deeper research and
understanding.

## 22. Visual Rhythm

The current site feels basic primarily because it repeatedly uses:

``` text
heading
↓
content
↓
heading
↓
content
```

This creates a feed/dashboard feeling.

Target rhythm:

> **BIG → SMALL → DENSE → SPACIOUS → VISUAL → TEXT → DENSE**

Use: - typography - whitespace - image scale - columns - alignment -
subtle rules

Do not rely on decorative effects.

## 23. Things to Avoid

Do not introduce: - gradients - glassmorphism - neon - 3D effects -
floating cards - animated backgrounds - excessive hover animations -
generic AI visual language - unnecessary borders - decorative noise

The product needs editorial personality, not visual clutter.

## 24. Signature Product Gestures

Each surface should have a recognizable interaction.

-   **Aquila:** Turn the page
-   **Home:** Expand a story from headline into context
-   **My Desk:** Topic unfolds into deeper information
-   **Navigation:** Minimal icon rail
-   **Search:** Story cluster / research expansion

These interactions should feel purposeful rather than ornamental.

## 25. Latest Live-Site Audit

Audited production routes: - `/en` - `/en/aquila` - `/en/desk` -
`/en/search`

Production URL:

`https://just-news-pi.vercel.app/`

### Home current state

Current navigation: - Home - Aquila - My Desk - Search - search
headlines input - Sign in - languages

Current semantic sections: - What matters - What you should know - Today
at a glance - The Daily Brief - More from the world

Current data volume is roughly: - 8,267 articles - 117 sources - 14
languages - 289 stories

The structure is improved, but the visual result still feels feed-like.

Main problem:

> The page has editorial section names without sufficiently strong
> editorial hierarchy.

### Aquila current state

Current production shows: - Evening Edition Vol. 1 No. 5 - Aquila
Tribune - The world in context - News / Ideas / People / Perspectives -
stale September 6 edition timestamp - quote - In Focus - Today's
Highlights - featured story - Also Today - 1 / 7 - Contents - seven
pages

Main problem:

> It reads like a webpage describing a newspaper rather than a newspaper
> itself.

### My Desk current state

Current: - My Desk - Your topics. Deeper understanding. - sign-in gate -
What changed - topic developments - What you can follow - taxonomy-style
topic names

Main problem:

> It still feels like a pre-login preview/settings page.

### Search current state

Current: - Search - description - search input - Topic select - Language
select

Main problem:

> It is still visually and functionally bare.

## 26. Priority Roadmap

### P0 --- Correctness

**1. Fix Aquila edition truth** - stale edition date - UTC reader
display - edition resolution - locale/dateline handling

**2. Remove Aquila web-navigation remnants** - News - Ideas - People -
Perspectives

### P1 --- Product Differentiation

**3. Make Home an editorial front page**

Move from:

> feed with section headings

to:

> editorially weighted live front page

**4. Make Aquila a genuine digital newspaper**

Prioritize: - asymmetric layout - huge lead - real page anatomy -
internal editorial rails - page identity - continuation references -
page-turn interaction

**5. Make My Desk a genuine personal intelligence workspace**

Signed-out value proposition first; personalized workspace after
sign-in.

**6. Implement navigation behavior** - icon rail on Home/My
Desk/Search - right-edge utility bar on Aquila

### P2 --- Story System

Introduce: - Lead - Feature - Standard - Brief - Cluster - Perspective -
Timeline - Context - future Analysis

Then introduce story clustering as a major differentiator.

### P3 --- Interaction

Add meaningful motion: - page turning - story expansion - topic
expansion - perspective exploration - timeline transitions

Motion should communicate state and hierarchy, not exist merely for
decoration.

### P4 --- Visual Polish

After structural and semantic changes: - typography - halftone
rendering - image cropping - spacing - print texture - motion tuning -
responsive behavior - accessibility - QA matrix

## 27. Recommended Claude Code Workflow

Before broad implementation:

1.  Inspect the repository.
2.  Identify existing routing/layout/components.
3.  Identify existing backend/recommendation/ingestion/auth systems.
4.  Preserve those systems unless a change is genuinely required.
5.  Implement one surface at a time.
6.  Verify the live result after each major stage.
7.  Do not redesign everything simultaneously.

Recommended implementation chunks:

-   **A** --- Edition truth + masthead
-   **B** --- Full-screen Aquila reader shell
-   **C** --- Editorial grid + composition
-   **D** --- Typography + colour
-   **E** --- Halftone system
-   **F** --- Home three-level hierarchy
-   **G** --- My Desk polish + Search
-   **H** --- Print character, motion, responsive/accessibility QA

## 28. Final Direction

The next leap is not more features.

It is not more cards.

It is not more animation.

It is:

> **Turn news articles into editorial objects.**

JustNews should make the user feel that the system has already done the
first layer of thinking:

-   What matters?
-   Why does it matter?
-   How big is it?
-   Who else is reporting it?
-   What are the differing perspectives?
-   What changed?
-   What should I understand next?

That is the product distinction between **a news aggregator** and **a
news-intelligence platform**.
