# JustNews — Admin Dashboard Design & Analytics Specification

## 1. Purpose

The JustNews Admin Dashboard is a **private, admin-only control and intelligence center** for the owner/operator of JustNews.

It is NOT part of the normal user-facing product.

Its purpose is to answer:

> **What is JustNews receiving, what are users doing, how well is the recommendation system performing, and where is the product failing or improving?**

The dashboard should provide detailed statistics, high-quality visualizations, operational monitoring, recommendation evaluation, content-quality analysis, and user/product analytics.

The design should remain consistent with the JustNews visual identity, but it may be **denser and more analytical** than the public-facing website.

---

# 2. Core Admin Questions

The dashboard should allow the administrator to quickly answer:

### News ingestion

- How many stories are being received?
- From which sources?
- Which sources are active/inactive?
- Which categories are receiving the most stories?
- How many duplicate stories are being detected?
- How fresh is the incoming news?
- Are feeds/API sources failing?
- Which languages are being received?
- How much news is arriving per hour/day?

### Users

- How many users are registered?
- How many are active?
- How many new users joined?
- What is DAU / WAU / MAU?
- How long are users returning?
- Which topics are users interested in?
- What do users click/read/save?
- Where are users dropping off?

### Recommendation quality

- How often are recommended stories clicked?
- Which recommendations are ignored?
- Which topics perform best?
- Which sources perform best?
- How accurate are recommendations?
- How much exploration vs exploitation is occurring?
- Are recommendations becoming more personalized?
- Are users giving positive/negative feedback?

### Product health

- Is the site working?
- Are ingestion pipelines healthy?
- Are APIs failing?
- Are pages slow?
- Are recommendation jobs running?
- Are there unusual changes in traffic or content?

### Content quality

- Are duplicate stories increasing?
- Are headlines malformed?
- Are stories missing images?
- Are source links broken?
- Are categories being assigned correctly?
- Are stories stale?
- Are multiple perspectives being represented?

---

# 3. Admin Information Architecture

Use a dedicated admin shell.

```text
JUSTNEWS ADMIN

Overview
News Intelligence
Sources
Users
Recommendations
Content Quality
Aquila Editions
System Health
Experiments
Reports
Settings
```

The most important sections should be:

1. **Overview**
2. **News Intelligence**
3. **Users**
4. **Recommendations**
5. **Content Quality**
6. **System Health**

Secondary tools:

7. Sources
8. Aquila Editions
9. Experiments
10. Reports
11. Settings

---

# 4. Admin Dashboard Personality

The public JustNews interface is:

> Editorial + calm + minimal.

The admin interface should be:

> **Editorial + analytical + information-dense + precise.**

Do NOT turn it into a generic enterprise dashboard.

Avoid:

- 20 colorful metric cards
- Giant rounded containers
- Rainbow charts
- Excessive gradients
- Decorative 3D graphics
- Unnecessary animations
- Huge numbers everywhere
- Charts without labels
- Pie-chart overload

The administrator should feel that they are looking at a **professional newsroom intelligence system**.

---

# 5. Admin Layout

## Desktop target

Primary calibration viewport:

```text
1440 × 900 px
```

Also test:

```text
1920 × 1080 px
1280 × 800 px
```

## Layout

```text
┌────────────────────┬─────────────────────────────────────────┐
│                    │                                         │
│   ADMIN SIDEBAR    │             ADMIN CONTENT               │
│                    │                                         │
│                    │                                         │
└────────────────────┴─────────────────────────────────────────┘
```

Sidebar:

```text
width: 250–280px
```

Main:

```text
fluid
max-width: 1500px
```

Main padding:

```text
32–40px
```

---

# 6. Admin Sidebar

Suggested:

```text
JUSTNEWS
ADMIN

────────────────

Overview

News Intelligence
Sources

Users

Recommendations
Content Quality

Aquila Editions

────────────────

System Health
Experiments
Reports

────────────────

Settings
Back to JustNews
```

The active section should use the same restrained active-state language as the public product.

---

# 7. Admin Header

Header height:

```text
64–72px
```

Left:

```text
Page title
Short description
```

Right:

```text
Date range
Refresh
Admin profile
```

Example:

```text
NEWS INTELLIGENCE
Understand the flow and quality of incoming news.

                         Last 24 hours  ▼
                         ↻ Refresh
                         Admin ●
```

---

# 8. Global Date Filter

The date range is critical.

Provide:

```text
Last 24 hours
Last 7 days
Last 30 days
Last 90 days
Custom
```

This should affect all applicable visualizations.

Also show the timezone used for reporting.

---

# 9. Overview Page

The Overview page should answer:

> **"How is JustNews doing right now?"**

Recommended top-level structure:

```text
┌────────────────────────────────────────────────────────────┐
│ ADMIN OVERVIEW                                             │
│                                                           │
│ [Users] [Stories] [Clicks] [Recommendation Quality]       │
├───────────────────────────────┬────────────────────────────┤
│ News Ingestion                │ User Activity              │
│                              │                            │
├───────────────────────────────┼────────────────────────────┤
│ Recommendation Performance    │ Content Quality            │
│                              │                            │
├───────────────────────────────┴────────────────────────────┤
│ System Health / Alerts                                     │
└────────────────────────────────────────────────────────────┘
```

---

# 10. KPI Cards

Use a small number of high-value KPI cards.

Maximum:

```text
4–6 cards above the fold
```

Card dimensions:

```text
height: 110–135px
```

Typical width:

```text
220–280px
```

Example:

```text
ACTIVE USERS
12,482

↑ 8.4% vs previous period
```

Recommended KPIs:

### Users

- DAU
- WAU
- MAU
- New users

### Content

- Stories received
- Stories published
- Active sources

### Engagement

- Story opens
- Publisher click-through rate
- Save rate

### Recommendation

- Recommendation CTR
- Positive feedback rate
- Coverage/diversity score

### Operations

- Ingestion success rate
- Failed feeds
- API errors

---

# 11. KPI Design

Each KPI must show:

```text
Metric name
Current value
Change vs previous period
Optional target
```

Example:

```text
RECOMMENDATION CTR

18.4%

↑ 2.1%
vs previous 7 days
```

Use arrows and text, not color alone.

---

# 12. News Intelligence Page

This is one of the most important admin areas.

It should answer:

> **"What news is JustNews receiving?"**

Top KPIs:

- Stories received
- Stories accepted
- Stories rejected
- Duplicate rate
- Sources active
- Languages
- Categories
- Average freshness

---

# 13. News Volume Chart

Primary visualization:

### Stories received over time

Line or area chart.

X-axis:

```text
Time
```

Y-axis:

```text
Number of stories
```

Allow:

```text
hourly
daily
weekly
```

For a 24-hour view, hourly resolution should be available.

Use vertical markers for:

- Ingestion outages
- Aquila publication times
- Major system events

---

# 14. News Category Distribution

Show category volume.

Preferred visualization:

### Horizontal bar chart

Example:

```text
Technology       █████████████████
World            ███████████████
Business         ███████████
Science          ███████
Politics         ██████
Culture          ████
Sports           ███
```

Horizontal bars are preferable to dozens of pie slices.

---

# 15. News Source Performance

Table:

```text
SOURCE             STORIES   ACTIVE   FRESHNESS   FAIL RATE
Reuters              842       ✓       14 min       0.2%
BBC                  621       ✓       18 min       0.4%
The Hindu            483       ✓       22 min       0.8%
...
```

Columns can include:

- Source
- Stories received
- Stories accepted
- Duplicate rate
- Average freshness
- Failure rate
- Last successful fetch
- Languages
- Categories

---

# 16. Source Health Visualization

Use a compact status indicator:

```text
● Healthy
● Delayed
● Degraded
● Failed
```

Do not depend only on color.

Include text labels.

---

# 17. News Freshness

Show:

```text
Average story age at ingestion
Median age
95th percentile age
```

Visualization:

### Histogram

```text
0–15 min
15–30 min
30–60 min
1–3 hours
3–6 hours
6+ hours
```

This tells the administrator whether JustNews is actually receiving timely news.

---

# 18. Duplicate Detection

Track:

```text
Stories received
Unique stories
Duplicates
Duplicate percentage
```

Visualization:

```text
Total incoming
      ↓
Deduplication
      ↓
Unique stories
```

Also provide duplicate rate over time.

---

# 19. Language Distribution

Show:

```text
English
Hindi
Spanish
...
```

Prefer horizontal bars or a compact table.

Include:

- Story count
- Percentage
- Change over time

---

# 20. Topic / Taxonomy Distribution

Visualize incoming stories by taxonomy.

Examples:

- Technology
- Business
- Science
- World
- Politics
- Society
- Culture
- Sports

Allow drilling into subcategories.

Example:

```text
Technology
 ├── Artificial Intelligence
 ├── Semiconductors
 ├── Robotics
 └── Cybersecurity
```

---

# 21. Users Page

The Users page should focus on **aggregate behaviour and product analytics**, not unnecessary personal surveillance.

Top KPIs:

- Total users
- New users
- DAU
- WAU
- MAU
- Retention
- Sessions
- Average stories viewed

---

# 22. User Growth Chart

Line chart:

```text
New users / day
```

Allow switching between:

```text
New users
Active users
Returning users
```

---

# 23. DAU / WAU / MAU

Show three trends.

```text
DAU
WAU
MAU
```

Use the same time axis.

This reveals whether growth is translating into recurring usage.

---

# 24. Retention

Show cohort retention.

Example:

```text
COHORT RETENTION

             D1    D7    D30
Week 1       42%   19%    8%
Week 2       45%   21%    9%
Week 3       47%   23%   10%
```

Use a heatmap carefully.

Do not use dozens of colors.

---

# 25. User Topic Interest

Show which topics users select or engage with.

Example:

```text
Artificial Intelligence    32%
Markets                    21%
Technology                 18%
India                      14%
Science                    9%
Space                      6%
```

Allow:

```text
Selected
Clicked
Saved
Repeatedly viewed
```

These are different signals and should not be mixed into one metric.

---

# 26. User Funnel

Track:

```text
Visit
 ↓
Sign up
 ↓
Select topics
 ↓
View recommendation
 ↓
Open story
 ↓
Click publisher
 ↓
Save / return
```

Show conversion rates between steps.

This is much more useful than only tracking page views.

---

# 27. Recommendation Dashboard

This is a critical admin section.

Purpose:

> **Evaluate whether the recommendation system is actually working.**

Top metrics:

- Recommendation impressions
- Recommendation clicks
- CTR
- Publisher click-through rate
- Save rate
- Dismiss rate
- Positive feedback
- Negative feedback
- Coverage
- Diversity
- Novelty
- Exploration rate
- Personalization lift

---

# 28. Recommendation Funnel

Visualize:

```text
Recommendations shown
        ↓
Story opened
        ↓
Publisher clicked
        ↓
Saved
        ↓
Positive feedback
```

Show percentage conversion at every step.

---

# 29. Recommendation CTR

Primary chart:

```text
Recommendation CTR over time
```

Allow comparison:

```text
Today
7 days
30 days
```

Also compare:

```text
Personalized recommendations
Popular recommendations
Exploration recommendations
```

---

# 30. Recommendation Quality by Topic

Table:

```text
TOPIC          IMPRESSIONS   CTR    SAVE RATE
AI               14,820     21.4%    5.8%
Markets           9,320     18.2%    4.2%
Space             6,120     15.1%    3.7%
Science           4,821     13.8%    3.2%
```

This identifies weak topic recommendations.

---

# 31. Recommendation Quality by Source

Show which publishers produce recommendations that users actually engage with.

Metrics:

- Impression count
- Open rate
- Publisher click rate
- Save rate
- Feedback score

Do not equate source popularity with recommendation quality.

---

# 32. Recommendation Quality by User Segment

If privacy and sample sizes permit, compare aggregate cohorts such as:

- New users
- Returning users
- Users with many selected topics
- Users with sparse preferences

Avoid exposing unnecessary individual-level behavioural data.

---

# 33. Personalization Lift

One of the most useful future metrics:

```text
Personalized CTR
       vs
Generic / baseline CTR
```

Example:

```text
Baseline CTR       9.8%
Personalized CTR  17.4%

Lift              +77.6%
```

This directly evaluates whether personalization is adding value.

---

# 34. Exploration vs Exploitation

Because the recommendation system may eventually use exploration:

Track:

```text
Exploration impressions
Exploitation impressions
```

Recommended visualization:

```text
Exploration     10%
Exploitation    90%
```

Also show CTR for each.

Do not optimize exploration away simply because its CTR is lower; its purpose is to discover new interests.

---

# 35. Recommendation Diversity

A recommendation system should not show the same kind of story repeatedly.

Track:

### Topic diversity

How many different topics appear?

### Source diversity

How many different publishers appear?

### Perspective diversity

How many meaningful perspectives are represented?

### Novelty

How different are recommendations from recently viewed content?

---

# 36. Recommendation Coverage

Measure:

> What percentage of the available relevant content can the recommender surface?

Example:

```text
Available relevant stories: 4,820
Stories recommended: 1,940

Coverage: 40.2%
```

Break this down by topic.

---

# 37. Recommendation Feedback

Track explicit feedback:

```text
👍 Helpful
👎 Not useful
Not interested
More like this
Less like this
```

Visualization:

```text
Helpful          62%
Neutral          24%
Not useful       14%
```

Also show trend over time.

---

# 38. Recommendation Debug View

Provide a detailed internal view for a selected recommendation.

Example:

```text
RECOMMENDATION

Story:
AI regulation enters a new phase

Score:
0.842

Factors:

Topic match             +0.32
Recent interest         +0.21
Source quality          +0.12
Recency                 +0.10
Popularity              +0.06
Exploration             +0.04

Penalty:

Already seen            -0.08
```

This is extremely useful for debugging the ranker.

Only admins should see this.

---

# 39. Content Quality Page

Purpose:

> **"Is the news content entering JustNews clean and useful?"**

Metrics:

- Duplicate rate
- Missing images
- Missing summaries
- Broken links
- Bad headlines
- Missing categories
- Classification confidence
- Stale stories
- Source failures

---

# 40. Content Quality Score

Create a composite quality score only if the components are clearly documented.

Example:

```text
CONTENT QUALITY

92.4 / 100
```

Break down:

```text
Freshness       94
Completeness    91
Classification  93
Deduplication   96
Link health     88
```

Never hide the underlying metrics behind a single score.

---

# 41. Broken Links

Show:

```text
Broken publisher links
Redirect failures
HTTP failures
Timeouts
```

Table:

```text
Source
URL/domain
Error
First detected
Last detected
Occurrences
```

Provide filtering.

---

# 42. Missing / Bad Metadata

Track:

- Missing headline
- Missing image
- Missing description
- Missing author
- Missing source
- Missing timestamp
- Invalid language
- Invalid category

Use a trend chart and sortable table.

---

# 43. Aquila Editions Admin

Create a dedicated section to monitor the three daily publications.

```text
AQUILA EDITIONS

06:00 AM   Morning     ✓ Published
02:00 PM   Midday      ✓ Published
10:00 PM   Evening     Scheduled
```

For each edition show:

- Number of stories
- Categories represented
- Sources represented
- Publication status
- Generation time
- Failed stories
- Page count

---

# 44. Aquila Edition Analytics

Compare editions.

```text
                 MORNING   MIDDAY   EVENING

Stories             42        46        51
Sources             28        31        34
Avg freshness       38m       24m       21m
Story opens         ...
Publisher CTR       ...
```

This helps determine which edition is most useful.

---

# 45. System Health

System Health should be operational, not decorative.

Monitor:

- API availability
- News ingestion
- RSS/API sources
- Database
- Authentication
- Recommendation jobs
- Aquila generation
- Scheduled publishing
- Search
- Error rate
- Response latency

---

# 46. System Health Status

Top-level status:

```text
SYSTEM HEALTH

● All systems operational
```

Then:

```text
News ingestion       ● Healthy
Database             ● Healthy
Recommendations      ● Healthy
Aquila scheduler     ● Healthy
Authentication       ● Healthy
Search               ● Healthy
```

Use explicit labels.

---

# 47. Ingestion Pipeline

Show pipeline stages:

```text
SOURCE
  ↓
FETCH
  ↓
NORMALIZE
  ↓
DEDUPLICATE
  ↓
CLASSIFY
  ↓
RANK
  ↓
PUBLISH
```

Each stage should show:

- Throughput
- Failure rate
- Average processing time

This gives the administrator a complete operational view.

---

# 48. Error Monitoring

Track:

- Error count
- Error rate
- Error type
- Affected service
- First occurrence
- Last occurrence

Provide:

```text
Recent Errors

12:41  RSS timeout
12:38  Classification failure
12:31  Publisher link timeout
```

Clicking an error should reveal details.

---

# 49. Experiments

Eventually support recommendation experiments.

Example:

```text
EXPERIMENT

Personalized Ranker V2

Control       50%
Variant       50%

CTR
Control       14.2%
Variant       17.8%

Save Rate
Control        3.4%
Variant        4.1%
```

Track:

- Experiment status
- Sample size
- Metrics
- Start date
- End date
- Confidence / statistical methodology
- Winner status

Do not declare a winner from tiny samples.

---

# 50. Reports

Allow the admin to generate periodic reports.

Possible reports:

### Daily

- News received
- User activity
- Recommendation performance
- System health

### Weekly

- Growth
- Retention
- Recommendation quality
- Content quality
- Top topics
- Source performance

### Monthly

- Product growth
- Recommendation evolution
- Topic trends
- System reliability
- Major issues

---

# 51. Charts — Visual Design

Charts must follow the JustNews design system.

Use:

- Off-white background
- Dark typography
- Thin grid lines
- Restrained accent
- Minimal legends
- Direct labels where possible

Avoid:

- Rainbow palettes
- 3D charts
- Heavy chart backgrounds
- Excessive gradients
- Decorative chart animations

---

# 52. Chart Types

Use the correct chart for the question.

### Line

For:

- Trends
- Users
- Stories
- CTR
- Errors

### Horizontal bar

For:

- Categories
- Sources
- Topics
- Languages

### Stacked bar

For:

- Story composition
- Exploration vs exploitation
- Source/category distribution

### Heatmap

For:

- Retention
- Hour/day activity
- Topic engagement

### Histogram

For:

- Freshness
- Session duration
- Recommendation scores

### Table

For:

- Source health
- Errors
- Detailed recommendation evaluation
- Operational records

Avoid pie charts unless the number of categories is extremely small.

---

# 53. Chart Dimensions

Desktop standard chart:

```text
height: 280–360px
```

Large chart:

```text
height: 380–450px
```

Small supporting chart:

```text
height: 180–240px
```

Charts should never become so short that labels become unreadable.

---

# 54. Dashboard Cards

Admin cards should be less decorative than public cards.

Recommended:

```text
border: 1px solid #D8D2C7
border-radius: 6–8px
background: #FBF9F4
padding: 20–24px
```

No heavy shadow.

---

# 55. Admin Typography

Use the same family system as JustNews:

### Serif

For:

- Page title
- Major analytical section title
- Important editorial metric heading

### Sans

For:

- Data labels
- Tables
- Filters
- Navigation
- Chart labels
- Controls

Recommended:

```text
Editorial serif: Cormorant Garamond
Interface sans: IBM Plex Sans
```

Keep charts and dense analytics primarily in the sans-serif.

---

# 56. Admin Colors

Use the same foundation:

```text
Ink              #171717
Paper            #F5F1E8
Bright Paper     #FBF9F4
Warm Gray        #D8D2C7
Muted Gray       #77736C
Deep Charcoal    #20211F
Accent Brass     #A28B68
```

For data visualization, use a restrained sequential/semantic palette.

Do not allow chart colors to become decorative.

---

# 57. Data Tables

Tables should be highly readable.

Header:

```text
10–12px
uppercase
letter-spacing: 1.5–2px
```

Rows:

```text
48–56px
```

Borders:

```text
1px
```

Hover:

```text
subtle background change
```

Allow:

- Sorting
- Filtering
- Pagination
- Search
- Column selection where useful

---

# 58. Filters

Use compact controls.

Example:

```text
Date       Last 7 days ▼
Topic      All topics ▼
Source     All sources ▼
Language   All languages ▼
```

Height:

```text
36–40px
```

Do not use giant pill controls.

---

# 59. Admin Animations

Admin interfaces should be even more restrained than the public site.

Default:

```text
120–200ms
```

Use animation for:

- Filter changes
- Chart updates
- Panel opening
- Table sorting feedback
- Status changes

Do not animate charts excessively every time data loads.

---

# 60. Dashboard Loading

Use skeleton layouts that preserve:

- Card dimensions
- Chart dimensions
- Table structure

Never make the whole dashboard flash blank.

---

# 61. Alerts

Alerts should be prioritized.

Levels:

```text
INFO
NOTICE
WARNING
CRITICAL
```

Example:

```text
WARNING
BBC feed has failed 4 consecutive fetches.
Last successful fetch: 42 minutes ago.
```

Critical alerts should be visually distinct but not neon.

---

# 62. Drill-Down Principle

Every major summary should allow deeper inspection.

Example:

```text
Stories Received
       ↓
Click
       ↓
News Intelligence
       ↓
Category
       ↓
Technology
       ↓
AI
       ↓
Source
       ↓
Individual ingestion records
```

The dashboard should support:

> **Overview → Explanation → Evidence**

---

# 63. Data Freshness

Every dashboard section that depends on live/periodic data should show:

```text
Updated 2 minutes ago
```

and provide:

```text
↻ Refresh
```

Do not make the user wonder whether a chart is current.

---

# 64. Privacy & Admin Security

This dashboard contains sensitive product analytics.

It must be:

- Admin-only
- Authenticated
- Authorization-checked server-side
- Protected from ordinary users
- Protected from direct URL access
- Auditable where appropriate

Do not rely only on hiding the navigation item.

The backend must verify admin permissions.

---

# 65. User Privacy

Admin analytics should prioritize aggregate information.

Avoid displaying unnecessary:

- Personal content
- Private message data
- Sensitive attributes
- Exact personal behaviour where aggregate data is sufficient

When user-level debugging is genuinely necessary, keep it restricted and purposeful.

---

# 66. Recommended Overview Above-the-Fold

At 1440px desktop:

```text
┌────────────────────────────────────────────────────────────┐
│ Overview                         Last 7 days   Refresh      │
├──────────┬──────────┬──────────┬──────────┬───────────────┤
│ DAU      │ Stories  │ Rec CTR  │ Saves    │ System Health │
├──────────┴──────────┴──────────┴──────────┴───────────────┤
│                                                            │
│                 NEWS INGESTION TREND                      │
│                                                            │
├─────────────────────────────┬──────────────────────────────┤
│ TOP TOPICS                  │ RECOMMENDATION QUALITY      │
│                             │                              │
├─────────────────────────────┼──────────────────────────────┤
│ USER ACTIVITY               │ CONTENT QUALITY             │
│                             │                              │
└─────────────────────────────┴──────────────────────────────┘
```

This gives the administrator the most important information without overwhelming the first viewport.

---

# 67. Admin Dashboard Navigation Summary

```text
OVERVIEW
    ├── KPIs
    ├── News
    ├── Users
    ├── Recommendations
    ├── Content Quality
    └── System Health

NEWS INTELLIGENCE
    ├── Volume
    ├── Sources
    ├── Categories
    ├── Languages
    ├── Freshness
    └── Duplicates

USERS
    ├── Growth
    ├── Activity
    ├── Retention
    ├── Topics
    └── Funnel

RECOMMENDATIONS
    ├── Performance
    ├── CTR
    ├── Personalization Lift
    ├── Diversity
    ├── Coverage
    ├── Exploration
    ├── Feedback
    └── Debug

CONTENT QUALITY
    ├── Completeness
    ├── Duplicates
    ├── Classification
    ├── Broken Links
    └── Freshness

AQUILA
    ├── Morning
    ├── Midday
    ├── Evening
    └── Edition Performance

SYSTEM
    ├── Ingestion
    ├── APIs
    ├── Database
    ├── Recommendation Jobs
    ├── Scheduler
    └── Errors

EXPERIMENTS
REPORTS
SETTINGS
```

---

# 68. Implementation Priority

Do not build every advanced metric immediately.

## Phase 1 — Essential Admin

Build:

- Admin authentication/authorization
- Overview
- News volume
- Sources
- Users
- Basic recommendation CTR
- System health
- Basic error monitoring

## Phase 2 — Evaluation

Add:

- Retention
- User funnel
- Topic interest
- Recommendation feedback
- Personalization lift
- Source/category performance
- Duplicate detection
- Freshness

## Phase 3 — Advanced Recommendation Evaluation

Add:

- Diversity
- Novelty
- Coverage
- Exploration vs exploitation
- Recommendation debugging
- Ranker score breakdown
- Experiments

## Phase 4 — Editorial Intelligence

Add:

- Aquila edition analytics
- Perspective coverage
- Content quality scoring
- Topic trend analysis
- Cross-source coverage

## Phase 5 — Advanced Reporting

Add:

- Automated daily reports
- Weekly reports
- Monthly reports
- Export
- Historical comparisons
- Long-term recommendation evaluation

---

# 69. Most Important Metrics

If implementation time is limited, prioritize these:

### News

1. Stories received
2. Unique stories
3. Duplicate rate
4. Source health
5. Freshness
6. Category distribution

### Users

7. DAU
8. WAU
9. MAU
10. Retention
11. Topic interest
12. Story engagement

### Recommendations

13. Recommendation CTR
14. Publisher CTR
15. Save rate
16. Feedback rate
17. Personalization lift
18. Diversity
19. Coverage
20. Exploration performance

### Operations

21. Ingestion success
22. API errors
23. Recommendation job health
24. Aquila publishing status
25. Page/system latency

These metrics provide a strong foundation for evaluating whether JustNews is actually improving.

---

# 70. The Admin Dashboard's Core Philosophy

The dashboard should not merely tell you:

> **"How many users do I have?"**

It should help answer:

> **"Is JustNews becoming better at helping people understand the news?"**

Therefore the dashboard should connect:

```text
NEWS
  ↓
QUALITY
  ↓
RECOMMENDATIONS
  ↓
USER BEHAVIOUR
  ↓
ENGAGEMENT
  ↓
RETENTION
  ↓
PRODUCT IMPROVEMENT
```

This relationship is the heart of the admin dashboard.

---

# 71. Final Design Principle

The public JustNews experience should say:

> **More than news. A wider perspective.**

The admin experience should say:

> **See what is happening beneath the surface.**

The administrator should be able to move from:

> **What happened?**

to:

> **Why did it happen?**

to:

> **Is the system working?**

to:

> **Are users finding value?**

to:

> **What should I improve next?**

That is the purpose of the JustNews Admin Intelligence Dashboard.


---

# 72. Deployment & Application Architecture

## Same Website / Same Project

The Admin Dashboard should be implemented **inside the same JustNews website/codebase**, not as a separate standalone website.

The public application and admin dashboard should share the same:

- Backend
- Database
- Authentication system
- News ingestion data
- Recommendation engine
- Analytics/event pipeline
- API layer
- Design tokens
- Core UI primitives

The admin area should simply be a **separate protected application area within JustNews**.

Recommended structure:

```text
JUSTNEWS
│
├── PUBLIC APPLICATION
│   ├── Home
│   ├── Aquila
│   ├── My Desk
│   ├── Search
│   └── Saved
│
└── ADMIN APPLICATION
    └── /admin
        ├── Overview
        ├── News Intelligence
        ├── Sources
        ├── Users
        ├── Recommendations
        ├── Content Quality
        ├── Aquila Editions
        ├── System Health
        ├── Experiments
        ├── Reports
        └── Settings
```

Conceptually:

```text
                     JUSTNEWS
                        │
             ┌──────────┴──────────┐
             │                     │
       PUBLIC APPLICATION      ADMIN APPLICATION
             │                     │
             │                     │
             └──────────┬──────────┘
                        │
                 Shared Backend
                        │
          ┌─────────────┼─────────────┐
          │             │             │
       Database      News Engine   Analytics
                        │             │
                  Recommendation      │
                     Engine           │
                                      │
                              Admin Intelligence
```

---

# 73. Admin URL / Routing

Use a dedicated route namespace:

```text
/admin
```

Recommended routes:

```text
/admin
/admin/news
/admin/sources
/admin/users
/admin/recommendations
/admin/content
/admin/aquila
/admin/system
/admin/experiments
/admin/reports
/admin/settings
```

The normal user should never see these routes in the public navigation.

---

# 74. Admin Authentication & Authorization

The admin dashboard must have **two separate security concepts**:

### Authentication

```text
Who is this user?
```

### Authorization

```text
Is this authenticated user allowed to access admin data?
```

The backend/server must enforce both.

Do NOT rely on:

```text
"Hide the Admin button from normal users"
```

That is not security.

A user manually navigating to:

```text
justnews.com/admin
```

must still be denied if they do not have admin privileges.

---

# 75. Admin Role

Use an explicit role/permission model.

For the initial version:

```text
role = admin
```

Later, this can expand to:

```text
owner
admin
editor
analyst
moderator
```

But do not over-engineer roles before they are needed.

---

# 76. Admin Session Security

The admin area should use the same trusted authentication infrastructure as the main application, while adding appropriate authorization checks.

Consider:

- Secure session handling
- Server-side authorization
- Session expiration
- Re-authentication for sensitive operations
- Protection against CSRF where applicable
- Rate limiting
- Audit logging for consequential admin actions

---

# 77. Public vs Admin Design Boundary

The two interfaces share the same visual DNA but have different purposes.

## Public JustNews

```text
Editorial
Calm
Readable
Immersive
Story-focused
```

## Admin JustNews

```text
Analytical
Dense
Precise
Operational
Data-focused
```

Do NOT make the admin dashboard look like a completely unrelated SaaS product.

Instead:

```text
Same brand
      +
Different information density
```

---

# 78. Shared Design Tokens

The admin dashboard should reuse the JustNews design tokens:

```text
Colors
Typography
Spacing
Borders
Radius
Iconography
Focus states
Accessibility rules
```

This creates brand consistency.

However, admin-specific components can have tighter spacing where information density requires it.

---

# 79. Shared Backend Data Flow

The architecture should allow analytics to be derived from the same events and records that power the product.

Example:

```text
User opens story
        ↓
Event recorded
        ↓
Analytics pipeline
        ↓
Aggregated metrics
        ↓
Admin dashboard
```

Similarly:

```text
News source
      ↓
Ingestion
      ↓
Normalization
      ↓
Deduplication
      ↓
Classification
      ↓
Recommendation engine
      ↓
User exposure
      ↓
Engagement
      ↓
Recommendation evaluation
```

This makes the admin dashboard useful for **actual product evaluation**, rather than being a collection of superficial counters.

---

# 80. Analytics Data Principle

Do not calculate expensive analytics directly from raw production tables on every dashboard page if the dataset becomes large.

Prefer an architecture where appropriate metrics are:

```text
Raw events
    ↓
Processing / aggregation
    ↓
Analytics tables or materialized views
    ↓
Admin API
    ↓
Dashboard
```

This keeps the admin interface fast as JustNews grows.

For the initial small-scale implementation, simpler database queries are acceptable, but the data layer should be structured so aggregation can be introduced later.

---

# 81. Admin API Boundary

The frontend admin pages should not directly expose privileged database credentials.

Use:

```text
Admin UI
   ↓
Authenticated admin API
   ↓
Server-side authorization
   ↓
Database / analytics layer
```

Never put service-role database credentials or equivalent privileged secrets into browser-side code.

---

# 82. Admin Dashboard as a Product Evaluation Tool

The admin dashboard is not merely an "analytics page."

It should eventually become the primary place where the owner evaluates:

```text
Is JustNews receiving good news?
          ↓
Is the news being processed correctly?
          ↓
Are recommendations good?
          ↓
Are users engaging with them?
          ↓
Are users returning?
          ↓
Is the product improving?
```

This should influence future product and recommendation decisions.

---

# 83. Recommended Architecture Decision

### FINAL DECISION

**Do not create a second standalone website for the admin dashboard at this stage.**

Use:

```text
Same repository
Same deployment
Same domain
Same authentication
Same backend
Same database
Separate /admin route
Separate admin layout
Strict admin authorization
```

This gives JustNews one coherent product while keeping the administrator experience completely separate from normal users.

---

# 84. Future Scaling Option

If JustNews becomes significantly larger, the admin application can eventually be separated into its own deployment.

For example:

```text
justnews.com
admin.justnews.com
```

But this should only happen if there is a concrete reason, such as:

- Independent deployment requirements
- Large administrative team
- Different infrastructure requirements
- Separate security boundary
- Large-scale analytics infrastructure
- Operational tooling becoming substantially different from the public product

Until then, a separate website adds complexity without providing enough benefit.

---

# 85. Admin Navigation Entry

The public application should generally **not display an Admin link** to ordinary users.

For an authorized administrator, an unobtrusive entry can exist in the account/settings area:

```text
Settings
Admin Dashboard
Sign out
```

Or the administrator can directly use:

```text
/admin
```

The admin navigation should have a clear:

```text
← Back to JustNews
```

action.

---

# 86. Admin Dashboard Success Criteria

The implementation is successful when:

- [ ] Admin is inside the same JustNews project
- [ ] `/admin` is a separate protected route
- [ ] Ordinary users cannot access admin data
- [ ] Admin authorization is enforced server-side
- [ ] Admin pages use a dedicated layout
- [ ] Public and admin interfaces share visual identity
- [ ] Admin data comes from the real JustNews analytics/data pipeline
- [ ] No privileged secrets are exposed to the browser
- [ ] Dashboard remains responsive
- [ ] Analytics can eventually scale through aggregated data
- [ ] Admin can return to the public JustNews application easily

---

# 87. Updated Architecture Summary

The complete JustNews product should therefore be thought of as:

```text
                         JUSTNEWS
                            │
             ┌──────────────┴──────────────┐
             │                             │
       PUBLIC EXPERIENCE              ADMIN INTELLIGENCE
             │                             │
       ┌─────┼─────┐              ┌────────┼─────────┐
       │     │     │              │        │         │
      Home Aquila My Desk       News     Users   Recommendations
       │                             │
       │                       Content Quality
       │                             │
       │                        System Health
       │                             │
       └──────────────┬──────────────┘
                      │
                Shared Platform
                      │
        ┌─────────────┼─────────────┐
        │             │             │
      News DB      User Data    Event Data
        │             │             │
        └─────────────┼─────────────┘
                      │
               Recommendation
                    Engine
```

This is the recommended architecture for the current stage of JustNews.
