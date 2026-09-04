# JustNews — Pixel-Precise Frontend Redesign Specification

## Purpose

This document is a **correction and implementation specification** for the current JustNews frontend.

The current implementation has the right broad idea, but the visual result is too loose, too card-heavy, poorly proportioned, and uses movement/spacing that feels like generic AI-generated UI ("slop").

The goal is to replace that with a **precise, restrained, editorial interface**.

The implementation should preserve the existing functionality and data/backend behaviour unless explicitly required for the redesign.

---

# 1. Primary Design Target

The reference implementation should feel like:

> **A modern editorial publication, not a SaaS dashboard.**

The design language is:

- Editorial
- Minimal
- Quiet
- Premium
- Structured
- Highly readable
- Newspaper-inspired
- Purposeful
- Responsive

It should visually connect to **The Aquila Tribune** concept.

Do NOT create:

- Generic dashboard UI
- Excessive rounded cards
- Giant empty areas
- Random animations
- Excessive shadows
- Glassmorphism
- Purple/blue AI gradients
- Oversized navigation
- Inconsistent spacing
- Arbitrary component dimensions
- Horizontally overflowing desktop layouts

---

# 2. Reference Viewport

The current screenshot is approximately a **1792 × 898 px desktop viewport**.

The design must be responsive, but this viewport should be treated as the primary desktop calibration target.

Use a content coordinate system based on:

```text
Viewport width: 1792px
Viewport height: 898px
```

Do not design only for a generic 1440px screenshot and allow the layout to stretch arbitrarily.

---

# 3. Global Desktop Layout

The application should use a fixed-width navigation rail plus a fluid content area.

## Overall structure

```text
┌──────────────────────┬──────────────────────────────────────────┐
│                      │                                          │
│      SIDEBAR         │              MAIN CONTENT                │
│                      │                                          │
│      320px max       │              fluid                       │
│                      │                                          │
└──────────────────────┴──────────────────────────────────────────┘
```

### Recommended desktop dimensions

| Element | Dimension |
|---|---:|
| Viewport target | 1792 × 898 px |
| Sidebar width | **320px** |
| Sidebar inner width | **220–250px** |
| Sidebar left padding | **48px** |
| Sidebar right padding | **32px** |
| Main content left padding | **38–48px** |
| Main content right padding | **48px** |
| Main content max-width | **1440px** |
| Main top padding | **32–40px** |
| Main bottom padding | **64px** |

The content should never touch the viewport edges.

---

# 4. Sidebar — Exact Structure

The current sidebar is visually too large and creates excessive unused horizontal space.

The sidebar should be **compact, intentional, and vertically balanced**.

## Width

Desktop:

```text
width: 320px
```

At widths below 1200px:

```text
width: 260–280px
```

At widths below 900px:

Hide the desktop sidebar and use mobile/tablet navigation.

---

# 5. Sidebar Logo

Position:

```text
left: 48px
top: 38–42px
```

### JustNews wordmark

Recommended:

```text
Font: editorial serif
Size: 25–30px
Weight: 500–600
Line height: 1
```

Subtitle:

```text
A CLEARER TOMORROW
Size: 10–11px
Letter spacing: 2–2.5px
```

Do not make the logo huge.

---

# 6. Sidebar Navigation

Navigation begins approximately:

```text
top: 128px
```

Each primary navigation item:

```text
height: 64–70px
width: 205–225px
```

Recommended spacing:

```text
gap between primary items: 8px
```

### Primary items

```text
Home
Aquila
My Desk
```

Each item contains:

```text
[icon]  Title
        Description
```

### Icon

```text
20 × 20px
```

### Title

```text
16–17px
font-weight: 500–600
```

### Description

```text
12–13px
line-height: 1.3
```

---

# 7. Active Navigation State

The active navigation item should NOT look like a giant glowing button.

Use:

- Very subtle warm surface
- Thin accent edge
- Slightly stronger text
- No large shadow

Recommended:

```text
background: rgba(255,255,255,0.045)
border-left: 2px solid accent
border-radius: 5–7px
```

Animation:

```text
150–200ms ease-out
```

---

# 8. Sidebar Sections

After My Desk:

```text
margin-top: 28–32px
border-top: 1px
padding-top: 24px
```

Secondary navigation:

- Saved
- Search

Then another divider:

```text
margin-top: 28px
```

Bottom utility:

- Settings
- Profile

Do not allow these sections to float randomly.

---

# 9. Sidebar Search

The current search implementation is too large and visually awkward.

Do not place a full-width search form permanently in the sidebar.

Instead:

```text
⌕  Search
```

opens the search interface.

If an inline search field is absolutely necessary:

```text
width: 220px
height: 42px
```

Button:

```text
height: 42px
```

Avoid the current oversized horizontal input/button combination.

---

# 10. Sidebar Language Selector

The language selector should be compact.

```text
English
Español
हिन्दी
```

Each:

```text
height: 34–36px
padding: 0 10–12px
border-radius: 5px
```

Gap:

```text
6–8px
```

Only the active language receives the subtle accent treatment.

---

# 11. Main Content Container

The current screenshot allows content to become excessively wide.

Use:

```text
width: min(
    calc(100vw - sidebar - horizontal margins),
    1440px
)
```

For a 1792px viewport:

```text
Main usable width ≈ 1420–1450px
```

The main content should remain visually centered within the remaining space.

---

# 12. Global Page Header

The header should occupy approximately:

```text
height: 72–82px
```

Use a single horizontal rule underneath.

Structure:

```text
┌─────────────────────────────────────────────────────────┐
│ NEWS   PERSPECTIVES   PEOPLE   IDEAS        Search  ●  │
└─────────────────────────────────────────────────────────┘
```

### Header spacing

Navigation links:

```text
font-size: 11–12px
letter-spacing: 3px
```

Search:

```text
width: 280–320px
height: 38–42px
```

Profile:

```text
36–40px circle
```

Notification icon:

```text
20–22px
```

---

# 13. Main Page Grid

Do not use an arbitrary grid.

Use a deliberate editorial structure.

Recommended Home grid:

```text
┌─────────────────────────────────────┬──────────────┐
│                                     │              │
│            HERO STORY               │  GLANCE      │
│                                     │              │
│                                     │              │
├─────────────────────┬───────────────┤              │
│ Secondary stories   │ Key stories   │              │
└─────────────────────┴───────────────┴──────────────┘
│                                                   │
│                 PERSONAL FEED                     │
└───────────────────────────────────────────────────┘
```

Suggested column proportions:

```text
Main editorial area: 72–74%
Right rail: 26–28%
```

Gap:

```text
24–28px
```

---

# 14. Home Page Heading

Use:

```text
GOOD MORNING / GOOD AFTERNOON / GOOD EVENING
```

Then:

```text
Here's what matters today.
```

### Dimensions

Eyebrow:

```text
11–12px
letter-spacing: 3px
```

Main heading:

```text
48–60px desktop
line-height: 0.98–1.05
```

Do not exceed approximately 64px.

The heading should occupy no more than 2 lines.

---

# 15. Hero Story

The hero is the most important element on Home.

Recommended dimensions at 1792px viewport:

```text
width: 650–720px
height: 390–430px
```

Image should occupy the full hero surface.

Text overlay should sit inside a controlled content area.

### Hero internal padding

```text
32–40px
```

### Category

```text
10–11px
letter-spacing: 2px
```

### Hero headline

```text
38–48px
line-height: 0.98–1.05
```

### Summary

```text
16–18px
line-height: 1.4
max-width: 560px
```

### CTA

```text
height: 42–46px
padding: 0 18–22px
```

---

# 16. Hero Image Treatment

Image should not be stretched unnaturally.

Use:

```css
object-fit: cover;
object-position: center;
```

Recommended aspect ratio:

```text
16:9 to approximately 1.75:1
```

Add only a subtle readability gradient behind text.

Do not use a heavy black overlay across the whole image.

---

# 17. Secondary Story List

Next to the hero, use a vertical editorial list instead of cards.

Each item:

```text
height: 82–100px
```

Structure:

```text
CATEGORY
Headline
Time · Source
```

Optional thumbnail:

```text
90 × 64px
```

Divider:

```text
1px
```

This is much cleaner than four independent cards.

---

# 18. "Today at a Glance"

Right rail panel:

```text
width: 280–330px
```

Padding:

```text 24px
```

Do not make this a giant card.

Use a simple editorial block.

Example:

```text
TODAY AT A GLANCE

124     new stories
32      sources
12      key topics
4       major perspectives
```

Use:

```text
large number: 25–30px
label: 12–14px
```

---

# 19. Trending Topics

Right rail:

```text
margin-top: 20–24px
```

List rows:

```text
height: 42–48px
```

Example:

```text
01   AI Regulation              52K
02   Clean Energy               38K
03   Global Markets              27K
```

Avoid pill-shaped topic tags everywhere.

---

# 20. Daily Brief

The Daily Brief should be visually distinct but restrained.

Recommended:

```text
padding: 24px
min-height: 180–220px
```

Use one image or subtle illustration only if it improves hierarchy.

CTA:

```text
height: 40–42px
```

---

# 21. Personalized Feed

The feed should begin after the hero area.

Tabs:

```text
For You
Trending
Because You Read
Continue Reading
Saved
```

Tab height:

```text
48–52px
```

Typography:

```text
14–15px
```

Active state:

- Dark text
- Thin bottom rule
- No filled pill

---

# 22. Story Cards

The current implementation has cards that are too tall, too rounded, and too visually independent.

Use restrained cards.

Recommended:

```text
width: 100%
height: 240–280px
```

Image:

```text
height: 115–135px
```

Content padding:

```text
16–18px
```

Border:

```text
1px solid warm-gray
```

Radius:

```text
4–8px maximum
```

Shadow:

```text
none
```

or extremely subtle.

---

# 23. Home Story Grid

At desktop:

```text
4 cards maximum per row
```

Recommended:

```text
gap: 16–20px
```

At 1440px and below:

```text
3 cards
```

At tablet:

```text
2 cards
```

At mobile:

```text
1 card
```

Do not force four cards into an area that makes headlines wrap awkwardly.

---

# 24. Current Screenshot Problem — Horizontal Overflow

The visible horizontal scrollbar in the current screenshot is unacceptable.

There should be:

```text
NO horizontal page scrolling
```

unless the component itself is deliberately horizontally scrollable.

Check:

- Sidebar width
- Main content width
- Grid minimum widths
- Image widths
- Card min-width
- Search field width
- Padding
- Flex children

Use:

```css
min-width: 0;
```

on grid/flex content where necessary.

Do not solve layout overflow by simply hiding the scrollbar.

---

# 25. Aquila Dimensions

Aquila is a special page.

The newspaper itself should be the dominant object.

At desktop:

```text
newspaper width: 900–1100px
newspaper height: 620–720px
```

depending on viewport.

The surrounding workspace should provide breathing room.

### Newspaper ratio

Target approximately:

```text
1.45–1.55 : 1
```

---

# 26. Aquila Workspace

Desktop:

```text
left sidebar: 280–320px
newspaper area: fluid
right edition/page panel: 260–300px
```

The newspaper should not touch either side panel.

Gap:

```text
20–28px
```

---

# 27. Aquila Newspaper Internal Margins

Inside the newspaper:

```text
top: 32–44px
left/right: 42–50px
bottom: 30–40px
```

Masthead:

```text
height: 70–90px
```

Headline:

```text
44–62px
```

Supporting headlines:

```text
24–34px
```

Body:

```text
14–17px
```

---

# 28. Aquila Page Controls

Bottom controls:

```text
height: 48–56px
```

Structure:

```text
←        1 / 12        →
```

Optional:

```text
View Contents
```

Do not use giant buttons.

---

# 29. Aquila Edition Selector

Right rail:

```text
width: 260–300px
```

Show:

```text
6:00 AM
Morning Edition

2:00 PM
Midday Edition

10:00 PM
Evening Edition
```

The active edition should have a subtle border/accent.

Do not use three oversized cards.

---

# 30. My Desk Dimensions

My Desk should prioritize information density without becoming a dashboard.

Desktop structure:

```text
┌──────────────────────────────────────┬──────────────┐
│ Topic selector                       │ Overview     │
├──────────────────────────────────────┤              │
│ Topic header                         │ Perspectives │
│                                      │              │
│ Latest / Perspectives / Timeline     │ Timeline     │
│                                      │              │
└──────────────────────────────────────┴──────────────┘
```

Main:

```text
70–75%
```

Right rail:

```text
25–30%
```

---

# 31. My Desk Topic Chips

Topic selector should not become a giant pill collection.

Use compact tabs:

```text
All
Technology
Markets
Science
India
Energy
```

Height:

```text 34–38px
```

Gap:

```text 6–8px
```

Border radius:

```text 4–8px
```

---

# 32. My Desk Topic Cards

If visual topic cards are used:

```text
width: 160–190px
height: 85–105px
```

Keep them editorial and compact.

Do not use huge dashboard tiles.

---

# 33. My Desk Story List

Prefer editorial rows.

Each:

```text
height: 92–115px
```

Thumbnail:

```text
140 × 82px
```

Headline:

```text
18–22px
```

Metadata:

```text
11–12px
```

Bookmark:

```text
18–20px
```

---

# 34. Perspectives Module

Perspectives should be a structured list rather than colored circular widgets.

Example:

```text
DIFFERENT PERSPECTIVES

Industry View
Innovation and economic opportunity.

Government View
Regulation and public concerns.

Academic View
Evidence and long-term implications.

Public View
Hope, skepticism and ethical questions.
```

Each row:

```text
min-height: 58–68px
```

Use subtle dividers.

---

# 35. Timeline Module

Use a clean vertical timeline.

Timeline width:

```text
100%
```

Dot:

```text
7–9px
```

Line:

```text
1px
```

Text:

```text
12–14px
```

Avoid animated timelines that constantly move.

Animation should only occur when the user changes the timeline/filter.

---

# 36. Future Analysis Entry

For now:

```text
ANALYSIS — COMING SOON
```

It should be visually understated.

Suggested:

```text
padding: 22–26px
```

Include:

- What the future feature will do
- Why it is useful
- Optional "Notify me" action

Do not make it look like the primary CTA of the entire site yet.

---

# 37. Article / Story Page

Because JustNews should not store full publisher article text, the story page should be a **coverage page**, not a copied article.

Structure:

```text
CATEGORY

HEADLINE

Short JustNews summary

Hero image

WHY THIS MATTERS

COVERAGE
────────────────
Publisher A
Publisher B
Publisher C

PERSPECTIVES

TIMELINE

RELATED STORIES

READ ORIGINAL →
```

Every publisher link should be prominent.

Do not render or store the full publisher article body.

---

# 38. Animation System

The current movement should be dramatically reduced.

The interface should feel **stable**.

## Default

Most UI:

```text
150–220ms
```

Use:

```text
ease-out
```

## Panels

```text
220–300ms
```

## Major editorial transitions

```text
350–500ms
```

Only Aquila page turns may use more elaborate movement.

---

# 39. Forbidden Animation Patterns

Do NOT use:

- Elements flying in from random directions
- Every card animating on page load
- Large bounce animations
- Constant floating
- Excessive parallax
- Slow fades on every text block
- Repeated scale-up effects
- Excessive spring physics
- Animations that delay reading
- Animation on every hover

A page should feel composed even when completely static.

---

# 40. Hover Effects

Hover should be subtle.

Story:

```text
image scale: 1.00 → 1.015
```

Duration:

```text 180ms
```

Headline:

```text
slight opacity or underline transition
```

Do not enlarge cards dramatically.

---

# 41. Bookmark Animation

On click:

```text
120–180ms
```

Use a small fill/outline transition.

No bounce.

---

# 42. Page Navigation Animation

Home/Aquila/My Desk:

```text
200–280ms
```

Do not animate the sidebar itself.

Only content should transition.

---

# 43. Aquila Page Turn

This is the one place where stronger animation is appropriate.

Recommended:

```text
350–550ms
```

Interaction:

```text
drag → page follows cursor → release → page completes
```

Fallback:

```text
crossfade / slide
```

when reduced motion is enabled.

---

# 44. Reduced Motion

Respect:

```text
prefers-reduced-motion: reduce
```

When enabled:

- Remove page-turn physics
- Remove large transitions
- Remove image zoom
- Use simple opacity or instant state changes

---

# 45. Responsive Breakpoints

Use:

```text
≥ 1440px   Large desktop
1200–1439  Desktop
900–1199   Tablet / compact desktop
600–899    Tablet / large mobile
< 600px    Mobile
```

---

# 46. Mobile Layout

Never simply shrink the desktop layout.

Use:

```text
Single column
```

Bottom navigation:

```text
height: 68–78px
```

4 primary items:

```text
Home
Aquila
My Desk
Saved
```

Each touch target:

```text
minimum 44 × 44px
```

---

# 47. Mobile Typography

Recommended:

```text
Page title: 34–42px
Hero headline: 30–38px
Story headline: 19–24px
Body: 16–18px
Metadata: 11–12px
```

Avoid tiny newspaper text on mobile.

---

# 48. Mobile Aquila

The newspaper becomes a single page.

Target:

```text
width: calc(100vw - 24–32px)
```

Height should maintain the editorial page ratio.

Swipe:

```text
horizontal gesture
```

Controls should remain visible.

---

# 49. Mobile My Desk

Order:

```text
My Desk heading
↓
Topic selector
↓
Selected topic
↓
Latest
↓
Perspectives
↓
Timeline
↓
Analysis Coming Soon
```

Move right-rail desktop modules below the main content.

---

# 50. Surface & Shadow Rules

Default:

```text
No shadow
```

Use a shadow only where an element needs physical separation.

If used:

```text
0 4px 18px rgba(0,0,0,0.06)
```

Avoid:

```text
large dark shadows
```

The interface should look like an editorial publication, not floating glass panels.

---

# 51. Color Application

Primary:

```text
Ink: #171717
Paper: #F5F1E8
Bright Paper: #FBF9F4
Warm Gray: #D8D2C7
Muted Gray: #77736C
Charcoal: #20211F
Accent Brass: #A28B68
```

Use dark mode carefully.

The current screenshot's dark background can work for immersive Aquila workspace areas, but the actual newspaper should remain a warm paper surface.

Do not invert the entire product into a high-contrast black UI simply because one mockup uses a dark workspace.

---

# 52. Typography

Primary editorial serif:

```text
Cormorant Garamond
```

Interface sans:

```text
IBM Plex Sans
```

Alternatives can be evaluated, but the implementation should use a **maximum of one primary serif + one primary sans**.

Do not mix many font families.

---

# 53. Font Loading

Fonts should be loaded deliberately.

Avoid visible layout shifts.

Use:

```text
font-display: swap
```

Provide appropriate fallback stacks.

Headlines must not suddenly resize after the page has loaded.

---

# 54. Spacing Scale

Use only the established spacing scale:

```text
4
8
12
16
24
32
48
64
96 px
```

Do not introduce random values throughout the application unless required for exact alignment.

---

# 55. Border Radius

Editorial surfaces:

```text
0–4px
```

Interface controls:

```text
4–8px
```

Mobile interactive elements:

```text
6–12px
```

Avoid the common AI-generated design pattern where everything has:

```text
rounded-2xl
rounded-3xl
```

---

# 56. Image Ratios

Use predictable aspect ratios.

Hero:

```text
16:9 approximately
```

Story card:

```text
16:9
```

Story row:

```text
~1.7:1
```

Aquila editorial images:

Use aspect ratios dictated by the newspaper grid rather than forcing every image into the same card shape.

---

# 57. Content Density

The current screenshot feels crowded in some places and empty in others.

The target should have **controlled information density**.

Every viewport should have:

- One dominant focal point
- A clear secondary hierarchy
- Supporting information
- Comfortable whitespace

Do not make every component equally prominent.

---

# 58. Visual Hierarchy Rule

Use this hierarchy:

```text
1. Main story
2. Major supporting stories
3. Key developments
4. Topic/category
5. Metadata
6. Utility controls
```

A bookmark icon must never visually compete with a headline.

---

# 59. Component Behaviour

Components should remain predictable.

### Story

```text
Image
Category
Headline
Summary / metadata
Bookmark
```

### Topic

```text
Topic name
Story count
Optional image
```

### Navigation

```text
Icon
Title
Description
Active state
```

### Edition

```text
Time
Edition name
Description
Active state
```

Do not randomly add badges, gradients, or decorative elements.

---

# 60. Important Current Screenshot Corrections

The current screenshot specifically needs these fixes:

### Problem 1 — Sidebar is oversized

Fix:

```text
320px maximum
```

with controlled inner width.

### Problem 2 — Horizontal overflow

Fix the grid and flex sizing. There should be no accidental page scrollbar.

### Problem 3 — Hero is too visually dominant

Keep it dominant, but constrain it to approximately:

```text
650–720px × 390–430px
```

### Problem 4 — Cards feel generic

Replace excessive cards with:

- Editorial lists
- Rules
- Structured rows
- A few restrained cards

### Problem 5 — Typography hierarchy is inconsistent

Implement the typography system above.

### Problem 6 — Spacing is inconsistent

Use the defined 4/8/12/16/24/32/48/64/96 scale.

### Problem 7 — Movement feels like "AI slop"

Reduce animation drastically.

### Problem 8 — Search is oversized

Use a compact header search or search overlay.

### Problem 9 — Too much unused sidebar space

Vertically rebalance navigation and use the sidebar intentionally.

### Problem 10 — Layout feels stretched

Constrain main content to approximately:

```text
1440px max
```

---

# 61. Implementation Rule: Inspect Before Rebuilding

Before modifying the UI:

1. Inspect the existing component structure.
2. Identify the existing Home page component.
3. Identify global CSS/design tokens.
4. Identify responsive breakpoints.
5. Identify navigation components.
6. Identify story/card components.
7. Identify image handling.
8. Identify existing animations.
9. Identify the current data/API interfaces.

Do NOT rewrite backend functionality simply to achieve the visual redesign.

---

# 62. Implementation Rule: Preserve Functionality

Unless explicitly required, preserve:

- Existing API calls
- Authentication
- News fetching
- Personalization logic
- Story links
- Saved functionality
- Search functionality
- Existing routing
- Existing database integration

The redesign is primarily a **frontend visual and interaction correction**.

---

# 63. Quality Gate

Before considering the redesign complete, verify:

### Layout

- [ ] No accidental horizontal scrollbar
- [ ] No overlapping elements
- [ ] No unexplained empty space
- [ ] All major sections align to the same grid
- [ ] Desktop widths remain controlled

### Typography

- [ ] One editorial serif
- [ ] One interface sans
- [ ] Consistent hierarchy
- [ ] Headlines wrap naturally
- [ ] Metadata is visibly secondary

### Color

- [ ] Warm editorial paper palette
- [ ] Restrained accent
- [ ] No unnecessary gradients
- [ ] Adequate contrast

### Components

- [ ] Cards are restrained
- [ ] Borders are subtle
- [ ] Shadows are minimal
- [ ] Icons are consistent
- [ ] Buttons are not oversized

### Motion

- [ ] No excessive entrance animations
- [ ] No bouncing
- [ ] No unnecessary parallax
- [ ] Hover effects are subtle
- [ ] Aquila page turn is the main expressive animation
- [ ] Reduced-motion support works

### Responsive

- [ ] 1792px desktop looks balanced
- [ ] 1440px desktop works
- [ ] 1200px works
- [ ] Tablet works
- [ ] Mobile works
- [ ] No horizontal overflow at any breakpoint

---

# 64. Final Visual Target

The finished JustNews interface should communicate:

> **Quiet confidence.**

It should look as though a professional editorial design team designed it deliberately.

The user should notice:

1. Typography
2. Story hierarchy
3. Editorial composition
4. Photography
5. Whitespace

They should NOT notice:

- Framework styling
- Component libraries
- Animation gimmicks
- Random rounded cards
- Excessive borders
- UI clutter

---

# 65. Final Design Rule

When deciding between two implementations, prefer the one that is:

> **Simpler, quieter, more editorial, more readable, and more intentional.**

The interface should feel like:

> **A newspaper redesigned for the digital age — not a dashboard pretending to be a newspaper.**
