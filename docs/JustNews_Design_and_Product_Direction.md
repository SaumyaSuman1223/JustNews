# JustNews --- Product, Information Architecture & Design Direction

## 1. Product Vision

**JustNews should feel like a modern newspaper that has evolved into an
intelligent information workspace.**

The product should not feel like a conventional news portal or a generic
SaaS dashboard. It should combine:

-   Personalized news discovery
-   Editorial-style news presentation
-   Topic-based exploration
-   Multiple perspectives on important issues
-   Deeper understanding of subjects
-   Eventually, AI-assisted analysis to help users make better-informed
    decisions

### Core product progression

> **Home = What matters right now**\
> **Aquila = Discover the world**\
> **My Desk = Go deep into what I care about**\
> **Analysis = Understand an issue before making a decision**

The eventual philosophy is:

> **More than news. A wider perspective.**\
> **Know more. Decide better.**\
> **A clearer tomorrow.**

------------------------------------------------------------------------

# 2. Primary Information Architecture

The main product should have three primary destinations:

``` text
                         JUSTNEWS
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
        HOME             AQUILA            MY DESK
      "For You"       "The Aquila Tribune"   "Your Topics"
          │                 │                 │
          │                 │                 ├── Technology
          │                 │                 ├── AI
          │                 │                 ├── Markets
          │                 │                 ├── Science
          │                 │                 └── Custom Topics
          │                 │
          │                 └── Editorial Discovery
          │
          ├── Personalized Recommendations
          ├── Important Stories
          ├── Trending
          ├── Continue Reading
          └── Saved Stories
```

These should not simply be three different news feeds. Each section has
a distinct purpose.

  -----------------------------------------------------------------------
  Section                 Personality             Main Question
  ----------------------- ----------------------- -----------------------
  **Home**                Calm, personal,         What should I know
                          intelligent             right now?

  **Aquila**              Editorial, immersive,   What is happening in
                          curated                 the world?

  **My Desk**             Personal, analytical,   What do I want to
                          research-oriented       understand?

  **Analysis** (future)   Research-oriented,      What does it actually
                          decision-focused        mean?
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 3. Main Navigation / Feature Taskbar

## Recommended desktop navigation

Use a **minimal left-side vertical navigation rail** rather than a large
conventional top navigation bar.

Suggested structure:

``` text
JUSTNEWS

HOME
AQUILA
MY DESK

────────────

SAVED
SEARCH

────────────

SETTINGS
PROFILE
```

### Primary navigation

1.  **Home**
2.  **Aquila**
3.  **My Desk**

### Secondary navigation

4.  **Saved**
5.  **Search**
6.  **Settings**
7.  **Profile**

The navigation should feel like an **editorial instrument**, not a SaaS
dashboard.

Avoid interfaces dominated by:

-   Dashboard
-   Analytics
-   Reports
-   Widgets
-   Large colorful icons
-   Excessive rounded cards
-   Too many permanent navigation categories

The navigation should remain small, clear, and intentional.

------------------------------------------------------------------------

# 4. Mobile Navigation

On mobile, use a persistent bottom navigation bar.

``` text
┌─────────────────────────────────────────┐
│                                         │
│              PAGE CONTENT               │
│                                         │
├──────────┬──────────┬──────────┬────────┤
│  Home    │  Aquila  │ My Desk  │ Saved  │
│    ●     │          │          │        │
└──────────┴──────────┴──────────┴────────┘
```

Search can remain accessible from the top-right or through a secondary
menu.

The mobile experience should preserve the same hierarchy and visual
language as desktop.

------------------------------------------------------------------------

# 5. HOME --- The Personal News Briefing

## Purpose

Home should answer:

> **"I opened JustNews. What should I know?"**

It should not simply be another chronological news feed.

Home should feel like a **personal news briefing**.

## Recommended structure

### Header

``` text
JUSTNEWS

GOOD MORNING / GOOD AFTERNOON / GOOD EVENING

Here's what matters today.
```

A date, search control, notifications, and profile can sit in the
header.

### Hero / Top Story

A large editorial story should dominate the page.

Example:

``` text
THE BIG STORY

Nations move closer to
clean energy agreement

Short explanation of why this matters.

[Read full story →]
```

### Key Developments

Beside or below the hero:

``` text
KEY DEVELOPMENTS

01  AI regulation enters a new phase
02  Markets react to new policy signals
03  Breakthrough in fusion research
04  Major global development
05  Cultural / social development
```

### Personalized Feed

Tabs could include:

-   For You
-   Trending
-   Because You Read
-   Continue Reading
-   Saved

### Supporting modules

Potential modules include:

-   Trending Topics
-   Daily Brief
-   New developments
-   Recommended stories
-   Recently read
-   Continue reading
-   Saved stories
-   "Because you read..." recommendations

### Core principle

**Home = fast orientation.**

The user should be able to understand the most important developments
within a short amount of time.

------------------------------------------------------------------------

# 6. AQUILA --- The Aquila Tribune

## Concept

Aquila is not simply another feed.

It is the **digital newspaper / editorial publication** inside JustNews.

Its full name is:

# The Aquila Tribune

The visual and interaction model should resemble a modern newspaper or
magazine issue rather than a conventional scrolling website.

The key idea:

> **Aquila = "Here's how the world looks today."**

------------------------------------------------------------------------

# 7. Aquila Page-Turn Interaction

The user should be able to move through the publication like an issue of
a newspaper.

Possible controls:

``` text
←        Page 2 / 12        →
```

or:

``` text
PAGE 01
────────────────
THE WORLD TODAY

PAGE 02
────────────────
TECHNOLOGY

PAGE 03
────────────────
BUSINESS

PAGE 04
────────────────
SCIENCE
```

### Interaction

Desktop:

-   Mouse drag
-   Clickable page corners
-   Previous / next controls
-   Keyboard arrow navigation
-   Page thumbnails / contents

Mobile:

-   Horizontal swipe
-   Previous / next controls
-   Page indicator

The page-turn interaction should communicate **moving to another
editorial page**, rather than being a decorative animation.

Avoid making the newspaper excessively skeuomorphic. It should be a
**digital newspaper inspired by print**, not a literal scanned
newspaper.

------------------------------------------------------------------------

# 8. Aquila Publication Structure

A possible issue:

### Page 1 --- Front Page

**THE AQUILA TRIBUNE**

Date / edition

Major headline

Supporting stories

Editorial quote

Page navigation

### Page 2 --- World

Major global developments.

### Page 3 --- Technology

AI, computing, semiconductors, robotics, etc.

### Page 4 --- Business

Markets, companies, economics, finance.

### Page 5 --- Science

Research, space, medicine, climate science, etc.

### Page 6 --- Culture / Society

Culture, people, social developments, ideas.

### Page 7 --- The Brief

A concise collection of important developments.

Additional pages can be added later.

Each page can have a slightly different editorial composition while
maintaining the same overall design system.

------------------------------------------------------------------------

# 9. Aquila Editions --- Three Publications Per Day

The Aquila Tribune should be published **three times every day**.

## 6:00 AM --- The Morning Edition

Purpose:

> **Start informed.**

Focus:

-   Overnight developments
-   Global headlines
-   Important events expected during the day
-   What to watch today
-   Key stories that set the day's agenda

------------------------------------------------------------------------

## 2:00 PM --- The Midday Edition

Purpose:

> **Stay up to date.**

Focus:

-   Major developments since morning
-   Changing stories
-   New perspectives
-   Important updates
-   Emerging events
-   Midday briefing

------------------------------------------------------------------------

## 10:00 PM --- The Evening Edition

Purpose:

> **A deeper look.**

Focus:

-   What happened today
-   The day's most important developments
-   Deeper context
-   Different voices and perspectives
-   What changed
-   What to watch next
-   End-of-day overview

### Publishing schedule

  Time           Edition           Purpose
  -------------- ----------------- -----------------
  **6:00 AM**    Morning Edition   Start informed
  **2:00 PM**    Midday Edition    Stay up to date
  **10:00 PM**   Evening Edition   A deeper look

The three editions should feel like different moments in the same
publication rather than three unrelated feeds.

------------------------------------------------------------------------

# 10. Aquila Edition Philosophy

The publication should communicate:

> **Three moments. A more informed world.**

The editions create a natural rhythm:

``` text
6:00 AM
   │
   ▼
MORNING
What happened overnight?
What matters today?
   │
   ▼
2:00 PM
MIDDAY
What changed?
What is developing?
   │
   ▼
10:00 PM
EVENING
What happened today?
What does it mean?
What's next?
```

This also gives JustNews a strong recurring editorial identity.

------------------------------------------------------------------------

# 11. MY DESK --- Personal Topic Workspace

The personalized news section should be called:

# My Desk

This is more than a personalized feed.

The concept is:

> **"This is where I work with the information I care about."**

My Desk allows users to select and organize topics they want to follow.

Examples:

-   Artificial Intelligence
-   Semiconductors
-   Markets
-   Space
-   India
-   Renewable Energy
-   Robotics
-   Climate
-   Any other supported topic

------------------------------------------------------------------------

# 12. My Desk --- Topic Selection

At the top:

``` text
MY DESK

Your topics. A deeper understanding.

YOUR TOPICS

[ Artificial Intelligence ]
[ Semiconductors ]
[ Markets ]
[ Space ]
[ India ]
[ Renewable Energy ]

                         + Add Topic
```

Users should be able to:

-   Add topics
-   Remove topics
-   Reorder topics
-   Select a topic
-   Explore all selected topics
-   Eventually launch analysis for a topic

------------------------------------------------------------------------

# 13. My Desk --- Topic View

When the user selects a topic:

``` text
ARTIFICIAL INTELLIGENCE

The technologies, companies, policies
and people shaping the next era.
```

Possible tabs:

-   Latest
-   Perspectives
-   Timeline
-   Key Developments
-   Analysis (Soon)

### Latest

A focused feed of recent stories.

### Perspectives

Different groups' interpretations of the issue.

### Timeline

Important developments over time.

### Key Developments

A concise summary of the most significant changes.

### Analysis

Reserved for the future major feature.

------------------------------------------------------------------------

# 14. Perspectives --- A Core Differentiator

My Desk should not only show:

> "What happened?"

It should also show:

> **"How are different people and groups viewing what happened?"**

Possible perspective categories:

-   Industry View
-   Government View
-   Academic View
-   Investor View
-   Public View
-   Expert View
-   Consumer View

For example:

``` text
DIFFERENT PERSPECTIVES

Industry View
Innovation and economic opportunity.

Government View
Regulation, safety and public concerns.

Academic View
Long-term implications and evidence.

Public View
Hope, skepticism and ethical questions.
```

The exact perspective categories should depend on the topic.

The goal is not to force artificial political labels onto every story.
The goal is to expose **meaningful differences in interpretation**.

------------------------------------------------------------------------

# 15. Timeline / Development Tracking

For important topics, show how the story has evolved.

Example:

``` text
RECENT DEVELOPMENTS

Today      New model released
Sep 3      Regulation draft updated
Sep 2      Major investment announced
Sep 1      New benchmark released
Aug 30     Global AI summit concludes
```

This allows users to understand a subject as an evolving story rather
than isolated headlines.

------------------------------------------------------------------------

# 16. Future Analysis Feature

The analysis feature should **not be a top-level navigation item
initially**.

It should naturally emerge inside My Desk after the user chooses a
topic.

The long-term concept:

> **"Understand an issue before making a decision."**

For example, if the user chooses:

**Semiconductor Industry**

the system could eventually combine:

-   Latest news
-   Historical developments
-   Different perspectives
-   Company announcements
-   Government policy
-   Market reactions
-   Expert opinions
-   Conflicting claims
-   Trends
-   Relevant evidence

Then provide an analysis workspace.

Possible structure:

``` text
SEMICONDUCTOR INDUSTRY

WHAT IS HAPPENING?
────────────────────

KEY DEVELOPMENTS

1.
2.
3.

────────────────────

WHY IT MATTERS

...

────────────────────

DIFFERENT PERSPECTIVES

Industry
Government
Investors
Researchers
Consumers

────────────────────

WHAT COULD HAPPEN NEXT?

Scenario A
Scenario B
Scenario C

────────────────────

EVIDENCE

[Sources]

────────────────────

ASK ABOUT THIS ISSUE
```

The eventual goal is not merely:

> "AI summarizes the news."

It should become:

> **"JustNews helps me understand an issue from multiple perspectives so
> I can make better-informed decisions."**

This is a major future expansion and should influence the current
information architecture without overbuilding it now.

------------------------------------------------------------------------

# 17. Search

Search should be a prominent but minimal part of the interface because
JustNews is ultimately moving toward information exploration and
research.

Suggested top-right control:

``` text
⌕ Search
```

Opening it could produce:

``` text
SEARCH JUSTNEWS

What are you interested in?

____________________________________

Recent Searches

AI regulation
NVIDIA
Indian economy
Renewable energy
Space exploration
```

Eventually search can become an entry point to:

-   Stories
-   Topics
-   Perspectives
-   Historical developments
-   Research / analysis

------------------------------------------------------------------------

# 18. Saved

Saved should be a lightweight secondary destination.

Possible organization:

``` text
SAVED

Articles
Topics
Collections
```

Users can save:

-   Individual stories
-   Topics
-   Important research
-   Potentially custom collections later

Saved should not compete visually with the three primary product areas.

------------------------------------------------------------------------

# 19. Do Not Put Every Category in the Main Navbar

Avoid:

``` text
HOME
WORLD
BUSINESS
TECH
SCIENCE
SPORTS
POLITICS
ENTERTAINMENT
...
```

This makes JustNews resemble a traditional news portal.

Instead:

``` text
HOME
AQUILA
MY DESK
```

Categories should live **inside the experiences**.

For example:

``` text
MY DESK

Technology
    AI
    Semiconductors
    Robotics

Finance
    Markets
    Banking
    Economics

Science
    Space
    Physics
    Biology
```

This keeps the main product hierarchy clean.

------------------------------------------------------------------------

# 20. Unified Visual Language

All sections should feel like the same publication.

Do not make:

-   Home = generic SaaS dashboard
-   Aquila = newspaper
-   My Desk = generic card-based analytics dashboard

Instead, establish one JustNews design system.

## Typography

Use:

### Serif typography

For:

-   Major headlines
-   Editorial titles
-   Large section titles
-   Quotes
-   Newspaper branding

### Sans-serif typography

For:

-   Navigation
-   Metadata
-   Timestamps
-   Labels
-   Controls
-   Small interface text

The combination should feel editorial but remain highly readable.

------------------------------------------------------------------------

# 21. Color Direction

Keep the palette restrained.

Suggested foundation:

``` text
Ink          — near black
Paper        — warm off-white / cream
Muted        — restrained gray
Accent       — one subtle brand accent
```

Avoid:

-   Rainbow category colors
-   Purple AI gradients
-   Excessive saturated colors
-   Visually noisy backgrounds

The interface should feel calm and trustworthy.

------------------------------------------------------------------------

# 22. Layout Principles

Use:

-   Strong editorial grids
-   Clear columns
-   Generous whitespace
-   Fine rules and separators
-   Strong hierarchy
-   Asymmetry where useful
-   Carefully controlled image sizes
-   Clear alignment
-   Comfortable reading widths

Avoid:

-   Excessive cards
-   Everything being inside a rounded rectangle
-   Huge shadows
-   Excessive glassmorphism
-   Unnecessary decorative elements
-   Cluttered dashboards

------------------------------------------------------------------------

# 23. Design Philosophy

The overall design direction can be described as:

# Modern Editorial Minimalism

It combines:

-   **Swiss / International Typographic Style**
-   **Minimalism**
-   **Bauhaus**
-   **Plakatstil**
-   **Scandinavian design**
-   **Editorial / newspaper design**

The objective is approximately:

> **80% editorial clarity + 20% physical/digital newspaper character**

The design should feel like a newspaper that has been thoughtfully
redesigned for the digital age.

------------------------------------------------------------------------

# 24. Aesthetic Inspirations

## International Typographic Style / Swiss Style

Use for:

-   Grid
-   Typography
-   Clarity
-   Structure
-   Objectivity
-   Whitespace
-   Asymmetry

## Minimalism

Use for:

-   Reduction
-   Decluttering
-   Focus
-   Simplicity
-   Removing unnecessary decoration

## Bauhaus

Use for:

-   Geometry
-   Functional design
-   Clean lines
-   Typography
-   Simple forms

## Plakatstil

Use for:

-   Bold headlines
-   Strong visual hierarchy
-   Negative space
-   Isolated imagery
-   Immediate communication

## Scandinavian Design

Use for:

-   Calmness
-   Functionality
-   Softness
-   Natural feeling
-   Pale / restrained palette

## Editorial / Newspaper Design

Use for:

-   Columns
-   Page hierarchy
-   Headlines
-   Pull quotes
-   Page numbers
-   Editorial storytelling
-   Page-as-spread composition

### Important

Do not copy any one aesthetic literally.

The objective is to combine the strongest principles into a **distinct
JustNews identity**.

------------------------------------------------------------------------

# 25. Core Design Principles

## 1. Typography First

Typography should carry much of the visual identity.

Use:

-   Strong serif headlines
-   Clean supporting sans-serif text
-   Clear hierarchy
-   Appropriate line lengths
-   Carefully controlled font sizes

------------------------------------------------------------------------

## 2. Minimal & Editorial

Use clean layouts, generous whitespace, and minimal distractions.

Focus attention on what matters.

------------------------------------------------------------------------

## 3. Readable & Focused

Information should be comfortable to read.

Use:

-   High contrast
-   Clean typography
-   Adequate spacing
-   Strong hierarchy
-   Sensible content density

------------------------------------------------------------------------

## 4. Purposeful Navigation

Every section must have a clear role.

The user should understand why they are in:

-   Home
-   Aquila
-   My Desk

Navigation should be consistent and intuitive.

------------------------------------------------------------------------

## 5. Consistent Experience

Maintain a unified visual language across:

-   Home
-   Aquila
-   My Desk
-   Articles
-   Search
-   Saved
-   Mobile
-   Desktop

------------------------------------------------------------------------

## 6. Built for Understanding

The interface should support a progression from:

> **Quick updates → Context → Perspectives → Deep understanding →
> Analysis**

The design should support thoughtful engagement with complex topics.

------------------------------------------------------------------------

# 26. Page-Specific Design Roles

## Home

**Personal briefing**

> What matters to me today?

Fast, personalized, approachable.

------------------------------------------------------------------------

## Aquila

**Editorial publication**

> What is happening in the world?

Immersive, curated, newspaper-inspired.

------------------------------------------------------------------------

## My Desk

**Research workspace**

> What do I want to understand?

Personal, organized, topic-focused.

------------------------------------------------------------------------

## Future Analysis

**Decision-support workspace**

> What does this information mean, and what should I consider?

Evidence-focused, transparent, analytical.

------------------------------------------------------------------------

# 27. Product Journey

The intended user journey is:

``` text
                         JUSTNEWS
                            │
                            ▼
                          HOME
                            │
                   "What matters today?"
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
           AQUILA                      MY DESK
              │                           │
       "Explore the world"       "Explore my interests"
              │                           │
              │                    ┌──────┴──────┐
              │                    ▼             ▼
              │                  NEWS      PERSPECTIVES
              │                                  │
              │                                  ▼
              │                              ANALYSIS
              │                                  │
              │                                  ▼
              │                         "Understand & decide"
              │
              └────────────────┐
                               ▼
                            STORIES
```

This is both a UI architecture and a product architecture.

------------------------------------------------------------------------

# 28. Recommended Current Navbar

For the current version of JustNews:

``` text
JUSTNEWS

⌂  HOME
◈  AQUILA
▤  MY DESK

────────────

♡  SAVED
⌕  SEARCH

────────────

⚙  SETTINGS
○  PROFILE
```

Do not add Analysis to the main navbar yet.

It should become a feature inside My Desk when the analysis system is
developed.

------------------------------------------------------------------------

# 29. Design Language for Claude / Impeccable

The following should be treated as the core design brief:

> **JustNews should feel like a modern newspaper that has evolved into
> an intelligent information workspace. Home is the personal briefing,
> The Aquila Tribune is the editorial publication, and My Desk is the
> user's research space.**
>
> **Use a modern editorial-minimalist visual language inspired by Swiss
> typography, Minimalism, Bauhaus, Plakatstil, Scandinavian design, and
> classic newspaper/editorial layouts.**
>
> **Prioritize typography, hierarchy, whitespace, readability,
> purposeful navigation, and consistency. Avoid generic SaaS dashboards,
> excessive cards, purple AI gradients, excessive rounded containers,
> heavy shadows, glassmorphism, and visual clutter.**
>
> **The experience should progress from quick updates to context,
> perspectives, deeper understanding, and eventually decision-support
> analysis.**

------------------------------------------------------------------------

# 30. Final Product Philosophy

The core idea behind JustNews can be summarized as:

``` text
JUSTNEWS

MORE THAN NEWS.
A WIDER PERSPECTIVE.

HOME
Know what matters.

AQUILA
See the world.

MY DESK
Understand what matters to you.

ANALYSIS
Understand before you decide.

A CLEARER TOMORROW.
```

The product should make users feel that they are not merely consuming
headlines.

They are **building an understanding of the world**.


---

# 31. Detailed Visual Design System

The following specifications turn the design direction into an implementation-ready visual system.

## 31.1 Core Color Palette

JustNews should use a restrained editorial palette.

### Primary

| Token | Suggested value | Usage |
|---|---|---|
| **Ink** | `#171717` | Main text, headings, icons |
| **Soft Ink** | `#333333` | Secondary text |
| **Paper** | `#F5F1E8` | Main page background |
| **Paper Bright** | `#FBF9F4` | Cards, reading surfaces |
| **Warm Gray** | `#D8D2C7` | Borders and dividers |
| **Muted Gray** | `#77736C` | Metadata and tertiary text |
| **Deep Charcoal** | `#20211F` | Aquila dark workspace / immersive areas |
| **White** | `#FFFFFF` | High-contrast text/surfaces where required |

### Optional restrained accent

Use **one accent color at a time**, primarily for interactive states and important highlights.

Suggested starting accent:

- **Aquila Brass:** `#A28B68`

Use it sparingly for:

- Active navigation indicator
- Edition marker
- Important status
- Hover detail
- Small editorial highlights

Do not use the accent as a large background or flood the interface with it.

### Semantic colors

Semantic colors should remain muted rather than becoming the dominant visual language.

- Success: muted green
- Warning: muted amber
- Error: muted red
- Information: muted blue

The semantic colors should primarily communicate state, not decorate the UI.

---

# 32. Typography System

Typography is one of the most important parts of the JustNews identity.

## Display / Editorial Serif

Recommended primary display family:

**Cormorant Garamond**

Use for:

- Major headlines
- Aquila headlines
- Large Home headlines
- Editorial quotes
- Section titles
- Newspaper-style mastheads where appropriate

Alternative display choices that can be evaluated:

- Instrument Serif
- DM Serif Display
- Libre Baskerville
- Newsreader

Do not use several display fonts simultaneously. Select one primary editorial family.

## Interface Sans

Recommended interface family:

**IBM Plex Sans**

Use for:

- Navigation
- Buttons
- Metadata
- Search
- Timestamps
- Labels
- Filters
- Settings
- Small UI text

Alternative:

- Geist
- Source Sans 3
- Inter only where it is genuinely appropriate

The interface should not rely on a generic sans-serif for every piece of text.

## Typography hierarchy

Suggested hierarchy:

```text
Display XL
Hero / front-page headline

Display L
Major section headline

Display M
Story headline

Body L
Article introduction / important description

Body M
Normal reading text

Body S
Supporting information

Label
Category / source / timestamp

Micro
Edition / page number / metadata
```

Use typography, spacing, and weight to establish hierarchy rather than adding decorative containers.

---

# 33. Typography Rules

- Headlines should generally use sentence case or editorial title treatment rather than unnecessary ALL CAPS.
- Metadata can use small uppercase labels with letter spacing.
- Body text should have comfortable line height.
- Avoid overly narrow reading columns.
- Avoid using bold weight everywhere.
- Avoid excessive italics.
- Use serif + sans-serif contrast intentionally.
- Headlines should have strong hierarchy without becoming oversized everywhere.
- The Aquila Tribune masthead can use a custom/brand treatment distinct from ordinary headlines.

---

# 34. Grid & Formatting System

Use an editorial grid throughout the product.

## Desktop

Recommended:

- Persistent left navigation rail
- Main content grid
- Optional right information rail
- 12-column underlying grid where practical
- Generous outer margins
- Consistent horizontal alignment

Example:

```text
┌────────────┬──────────────────────────────────┬──────────────┐
│ Navigation │            Main Content          │ Information  │
│            │                                  │    Rail      │
│            │                                  │              │
└────────────┴──────────────────────────────────┴──────────────┘
```

## Home

Prioritize:

1. Greeting / context
2. Hero story
3. Key developments
4. Personalized feed
5. Supporting modules

## Aquila

Prioritize:

1. Masthead
2. Edition/date
3. Lead story
4. Supporting editorial columns
5. Page navigation

## My Desk

Prioritize:

1. Topic selection
2. Selected topic
3. Latest stories
4. Perspectives
5. Timeline
6. Future Analysis entry point

---

# 35. Spacing System

Use a consistent spacing scale instead of arbitrary margins.

Suggested base scale:

```text
4px
8px
12px
16px
24px
32px
48px
64px
96px
```

Use smaller values for interface elements and larger values for editorial sections.

Whitespace is a core part of the visual identity.

---

# 36. Borders, Cards & Surfaces

Use borders more often than shadows.

Preferred:

```text
1px solid warm gray
```

Cards should generally be:

- Flat
- Lightly separated
- Editorial
- Rectangular or only subtly rounded

Avoid turning every story into a floating rounded card.

### Border radius

Use:

- 0–4px for editorial surfaces
- 6–10px for modern interface controls where useful
- Larger radii only for clearly interactive components such as mobile controls

The Aquila newspaper itself can have subtle physical-page treatment, but the surrounding interface should remain restrained.

---

# 37. Imagery

Photography should feel editorial rather than stock-like.

Prefer:

- Documentary photography
- Atmospheric landscapes
- Architecture
- People in context
- Scientific imagery
- Strong compositions
- Muted / naturally toned photographs

Avoid:

- Generic corporate stock photography
- Overly saturated images
- Excessive image decoration
- AI-looking imagery when real editorial imagery is available

Images should support the story hierarchy rather than compete with typography.

---

# 38. Iconography

Use a consistent minimal icon family.

Icons should be:

- Simple
- Mostly line-based
- Consistent in stroke weight
- Small and functional
- Secondary to typography

Primary navigation icons:

- Home
- Aquila / newspaper
- My Desk / layers
- Saved / bookmark
- Search
- Settings
- Profile

Do not use icons purely for decoration.

---

# 39. Animation Philosophy

Animation should communicate **state, hierarchy, and movement**, not provide decoration.

Core principle:

> **Motion should explain what changed.**

Avoid:

- Excessive bouncing
- Large entrance animations
- Constant floating elements
- Slow decorative transitions
- Excessive parallax
- Attention-seeking effects

Animations should generally feel calm, editorial, and precise.

---

# 40. General Motion Timing

Suggested timing:

### Micro interactions

`120–180ms`

For:

- Hover
- Icon state
- Bookmark
- Toggle
- Small opacity changes

### Standard transitions

`200–300ms`

For:

- Navigation changes
- Panels
- Menus
- Filters
- Cards entering/leaving

### Editorial transitions

`350–600ms`

For:

- Aquila page transitions
- Major content changes
- Full-screen overlays

Use easing that starts and ends smoothly. Avoid exaggerated spring physics unless the interaction genuinely benefits from it.

---

# 41. Aquila Page-Turn Animation

The Aquila page turn is the main signature interaction.

It should feel like turning a publication page without becoming a skeuomorphic gimmick.

### Desktop

Support:

- Dragging the page
- Click next / previous
- Keyboard arrows
- Optional corner interaction

Motion:

```text
Current page
     ↓
slight lift
     ↓
page rotates / slides
     ↓
next page revealed
     ↓
settle
```

The animation should be fast enough that it never interrupts reading.

### Mobile

Use:

- Horizontal swipe
- Previous / next controls

The gesture should have a clear relationship between finger movement and page movement.

Respect reduced-motion preferences by replacing complex page turns with a simple crossfade/slide.

---

# 42. Navigation Animations

When moving between Home, Aquila, and My Desk:

- Keep the navigation rail stable.
- Change the active indicator subtly.
- Transition the content rather than animating the entire application.
- Avoid dramatic page reload-style animations.

The user should always understand where they are.

---

# 43. Home Animations

Home should feel calm.

Recommended:

- Gentle content fade/slide when refreshing
- Subtle hero image transition when changing featured story
- Small bookmark animation
- Smooth tab switching
- Skeleton loading that matches the editorial grid

Avoid flashy dashboard animations.

---

# 44. My Desk Animations

Recommended:

- Smooth topic selection
- Subtle topic-card state changes
- Animated timeline progression
- Smooth expansion of perspectives
- Gentle loading states
- Clear transition into future Analysis

When adding/removing topics, the layout may smoothly reflow rather than abruptly jumping.

---

# 45. Search Interaction

Search should open quickly and feel focused.

Suggested sequence:

```text
⌕
  ↓
Search expands / overlay appears
  ↓
User types
  ↓
Suggestions appear
  ↓
Results grouped by:
Stories / Topics / Perspectives
```

Keep search interaction fast and lightweight.

---

# 46. Responsive Design

## Desktop

Use:

- Persistent sidebar
- Multi-column editorial layouts
- Larger imagery
- Aquila page spread
- Rich topic overview

## Tablet

Use:

- Reduced navigation width
- Two-column layouts where possible
- Collapsible information rail
- Simplified Aquila spread

## Mobile

Use:

- Bottom navigation
- Single-column reading
- Swipeable Aquila pages
- Compact topic chips
- Full-width story imagery
- Larger touch targets
- Reduced information density

Never simply shrink the desktop UI onto a phone.

---

# 47. Accessibility

Accessibility is part of the visual design.

Ensure:

- Sufficient text contrast
- Keyboard navigation
- Visible focus states
- Semantic HTML
- Screen-reader-friendly labels
- Adequate touch target sizes
- Reduced-motion support
- No information conveyed only by color
- Readable font sizes
- Logical heading hierarchy

The newspaper aesthetic must never compromise readability.

---

# 48. Interaction Formatting Principles

Every component should answer:

1. What is this?
2. Why is it here?
3. What can I do with it?
4. What happened after I interacted with it?

Controls should provide clear feedback.

Examples:

### Bookmark

```text
Unselected → Selected
```

### Topic

```text
Available → Selected → Active
```

### Aquila page

```text
Page 1 / 12
```

### Edition

```text
6:00 AM — Morning Edition
2:00 PM — Midday Edition
10:00 PM — Evening Edition
```

---

# 49. Loading & Empty States

Loading states should preserve the layout.

Do not replace the page with a generic spinner whenever possible.

Prefer:

- Editorial skeletons
- Placeholder headline blocks
- Image placeholders
- Preserved grid structure

Empty states should explain what the user can do next.

Example:

```text
YOUR DESK IS EMPTY

Choose a few topics to build
your personal news workspace.

+ Add your first topic
```

---

# 50. Design Anti-Patterns to Avoid

Do not allow JustNews to drift into:

- Generic AI dashboard aesthetics
- Purple-blue AI gradients
- Excessive glassmorphism
- Excessive rounded cards
- Card grids everywhere
- Excessive shadows
- Huge navigation bars
- Rainbow category systems
- Overuse of icons
- Excessive animations
- Decorative motion with no purpose
- Overly realistic newspaper textures
- Fake paper physics everywhere
- Tiny unreadable newspaper text
- Dense information without hierarchy

The product should feel **quietly premium, editorial, intelligent, and trustworthy**.

---

# 51. Design System Summary

```text
VISUAL IDENTITY
Modern Editorial Minimalism

TYPOGRAPHY
Editorial Serif + Functional Sans

PALETTE
Warm Paper + Ink + Warm Gray + One Restrained Accent

LAYOUT
Editorial Grid + Whitespace + Strong Hierarchy

SURFACES
Flat / lightly bordered / minimal rounding

IMAGERY
Documentary + atmospheric + editorial

NAVIGATION
Minimal + purposeful

MOTION
Calm + meaningful + fast

AQUILA
Digital newspaper + page-turn interaction

HOME
Personal briefing

MY DESK
Personal research workspace

FUTURE ANALYSIS
Decision-support workspace
```

---

# 52. Implementation Priority

Do not implement every idea simultaneously.

### Phase 1 — Core shell

Build:

- Navigation
- Home
- Aquila
- My Desk
- Saved
- Search
- Responsive mobile navigation
- Typography and color system

### Phase 2 — Aquila

Build:

- Three daily editions
- Newspaper layouts
- Page navigation
- Page-turn interaction
- Contents/page selector
- Edition selector

### Phase 3 — My Desk

Build:

- Topic selection
- Topic feed
- Perspectives
- Timeline
- Key developments
- Saved topics

### Phase 4 — Refinement

Add:

- Motion system
- Accessibility refinement
- Responsive polish
- Loading states
- Empty states
- Micro-interactions

### Phase 5 — Future Analysis

Add:

- Topic analysis
- Evidence synthesis
- Scenario exploration
- Decision-support tools
- Source transparency
- Cross-perspective analysis

The Analysis feature should be developed last, but the current architecture should leave a clear place for it.

---

# 53. One-Sentence Design Brief

> **JustNews is a calm, editorial-first news platform that combines the personalization of a modern information workspace with the clarity and character of a thoughtfully redesigned newspaper.**
