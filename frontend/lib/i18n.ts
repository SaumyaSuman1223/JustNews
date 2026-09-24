/**
 * Locale registry.
 *
 * i18n is structural here, not a later retrofit (ADR 0005). The two things
 * that must be right from the first component are the direction flag - which
 * drives `dir` on <html> and therefore every logical CSS property - and the
 * fact that a locale is part of the route, not a cookie. Retrofitting either
 * into a finished layout costs several times what building with them costs.
 *
 * Every locale here is currently `ltr`, and the `dir` flag is deliberately
 * kept anyway: the layout is still written entirely in logical properties, so
 * adding an RTL language back is an entry in this list rather than a
 * stylesheet fork. That is the whole point of paying the cost up front.
 *
 * This list must match `LAUNCH_LANGUAGES` in justnews_core.language. A language
 * we ingest but do not list here is content no reader can reach, and a locale
 * listed here with no source behind it is an empty page. A test on the Python
 * side reads this file and fails when the two drift apart.
 */

export const locales = [
  { code: "en", label: "English", dir: "ltr", htmlLang: "en" },
  { code: "es", label: "Español", dir: "ltr", htmlLang: "es" },
  { code: "hi", label: "हिन्दी", dir: "ltr", htmlLang: "hi" },
] as const;

export type Locale = (typeof locales)[number];
export type LocaleCode = Locale["code"];

export const defaultLocale: LocaleCode = "en";

export function isLocaleCode(value: string): value is LocaleCode {
  return locales.some((locale) => locale.code === value);
}

export function getLocale(code: string): Locale {
  return locales.find((locale) => locale.code === code) ?? locales[0];
}

/**
 * The city an edition is filed from, for the Aquila dateline - or `null`.
 *
 * A dateline is a factual claim: it says where this edition was put together.
 * JustNews publishes one worldwide edition per language, so for these locales
 * there is no such city, and the map is deliberately empty. Printing a
 * plausible capital would be a fabricated fact in the masthead, which is
 * exactly the kind of invented detail this product does not ship.
 *
 * The lookup exists rather than the call site simply omitting the city,
 * because regional editions are already a modelled concept (the `editions`
 * table) - when an edition genuinely is filed from one place, this is where
 * that becomes true, and the masthead already renders it.
 */
const DATELINE_CITIES: Partial<Record<LocaleCode, string>> = {};

export function datelineCity(locale: LocaleCode): string | null {
  return DATELINE_CITIES[locale] ?? null;
}

/**
 * The reader's content languages, as the comma-separated string every
 * `languages` query parameter takes (`en,es`).
 *
 * The active locale is the chrome's language, not the reader's answer to
 * "what do you want to read", and those are different questions - a Hindi
 * speaker reading the site in English still wants Hindi headlines. So a
 * signed-in reader's stored choice wins outright, and the locale is only the
 * anonymous fallback.
 *
 * Filtered to launch locales, because a language we do not ingest is an empty
 * page, and never widened past what the reader picked: no query may return
 * content in a language they did not ask for.
 */
export function readerLanguages(
  preferred: readonly string[] | null | undefined,
  active: LocaleCode,
): string {
  const chosen = (preferred ?? []).filter(isLocaleCode);
  return chosen.length > 0 ? chosen.join(",") : active;
}

/**
 * UI strings.
 *
 * A flat, explicit map per locale rather than a nested tree or a loader:
 * `messages.en` types the key set, and the other locales are declared as
 * `Record<MessageKey, string>`, so a missing translation is a `tsc` failure
 * in CI rather than an English word appearing on a Hindi page. That check is
 * the only thing that keeps this file honest as the string count grows.
 *
 * Article content is never routed through here - it arrives in whatever
 * language it was published in, and says so.
 */
const en = {
  "skip.toContent": "Skip to content",

  "nav.primary": "Primary",
  "error.rateLimited": "Too many requests. Try again in a minute.",
  "nav.language": "Language",
  "nav.aquila": "Aquila",
  "nav.desk": "My Desk",
  "nav.search": "Search",
  "nav.settings": "Settings",
  "nav.saved": "Saved",
  "nav.privacy": "Privacy",
  "nav.feedback": "Send feedback",

  "search.placeholder": "Search headlines",
  "search.submit": "Search",

  "account.signIn": "Sign in",
  "account.signOut": "Sign out",
  "account.saved": "Saved",
  "account.history": "History",
  "account.settings": "Settings",
  "account.chooseTopics": "Choose topics",
  "account.enterInvite": "Enter invite code",
  "account.feedback": "Send feedback",

  "beta.notice":
    "JustNews is in private beta. You’re signed in, but you’ll need an invite code to unlock your personalised feed, saves and history.",
  "beta.enterCode": "Enter your code",

  "signIn.title": "Sign in to see this",
  "signIn.body":
    "This page shows things tied to your account, so it needs you signed in first.",

  "signIn.saved.body":
    "Save a story from any card with the heart, and it waits here on every device you sign in on.",
  "signIn.following.body":
    "Follow a story and this page counts the new reports each time you come back.",
  "signIn.history.body":
    "Stories you open while signed in are listed here, so you can find one again.",

  "feed.degraded.personal":
    "Your feed is unavailable right now, so this page may be out of date. Everything else still works.",
  "feed.degraded.anonymous":
    "Live headlines are unavailable right now, so this page may be out of date. Everything else still works.",
  "feed.empty.action": "Go to Explore",

  "stats.articles.one": "article",
  "stats.articles.other": "articles",
  "stats.sources.one": "source",
  "stats.sources.other": "sources",
  "stats.stories.one": "story",
  "stats.stories.other": "stories",

  "home.lead.context.show": "More about this story",
  "home.lead.context.hide": "Less",
  "home.lead.context.published": "Published {time}",
  "home.lead.context.coverage": "See full coverage",

  "aquila.title": "Aquila Tribune",
  "aquila.strap": "The world in context",
  "aquila.volume": "Vol. {volume}  No. {number}",
  "aquila.dateline": "{city}, {date}",
  "aquila.editionTime": "{time}",
  "aquila.edition.morning": "Morning Edition",
  "aquila.edition.midday": "Midday Edition",
  "aquila.edition.evening": "Evening Edition",
  "aquila.moreSections.one": "+ {count} more section",
  "aquila.moreSections.other": "+ {count} more sections",
  "aquila.editions": "Today’s editions",
  "aquila.frontPage": "Front page",
  "aquila.motto": "Better information builds a better tomorrow.",
  "aquila.mottoAttribution": "JustNews",
  "aquila.moreNews": "Also today",
  "aquila.inFocus": "In focus",
  "aquila.highlights": "Today’s highlights",
  "aquila.pageRef": "Page {page}",
  "aquila.pageRef.label": "More {section} coverage, page {page}",
  "aquila.pageRef.labelPlain": "Page {page}",
  "aquila.footer": "Curated news for a more informed world",
  "aquila.sign": "Read deeper. See further.",
  "aquila.contents": "Contents",
  "aquila.pagination": "Pages",
  "aquila.previous": "Previous page",
  "aquila.next": "Next page",
  "aquila.fullscreen": "Full screen",
  "aquila.exitFullscreen": "Exit full screen",
  "aquila.pageOf": "{page} / {total}",
  "aquila.pageLabel": "Page {page}",
  "aquila.pageEmpty": "Nothing was set on this page.",
  "aquila.pageFailed": "That page would not load. Try again.",
  "aquila.backHome": "Back to the front page",
  "aquila.none.title": "No edition has been published yet",
  "aquila.none.body":
    "The Tribune is composed three times a day, at 6am, 2pm and 10pm. The next edition will appear here.",
  "aquila.none.action": "Go to Home",

  "coverage.label": "Languages covering this story",

  "article.notFound": "Not found",
  "article.readFull": "Read the full story at {source}",
  "article.otherLanguages.one": "Also covered in another language",
  "article.otherLanguages.other": "Also covered in {count} other languages",
  "article.otherSources.one": "Also reported by 1 other source",
  "article.otherSources.other": "Also reported by {count} other sources",
  "article.seeFullCoverage": "See full coverage",
  "article.backToFront": "Back to the front page",
  "article.filedUnder": "Filed under",
  "article.moreIn": "More in {topic}",
  "article.moreFrom": "More from {source}",
  "source.eyebrow": "Publisher",
  "source.notFound": "Publisher not found",
  "source.visit": "Visit {source}",
  "source.latest": "Latest reporting",
  "source.empty.title": "Nothing from {source} yet",
  "source.empty.body": "Their reporting appears here as soon as it is published.",
  "source.articleCount.one": "{count} article on JustNews",
  "source.articleCount.other": "{count} articles on JustNews",
  "story.reports.one": "{count} report",
  "story.reports.other": "{count} reports",
  "story.firstReported": "First reported {time}",
  "story.lastUpdated": "Last updated {time}",
  "story.sources.label": "Sources covering this story",
  "story.perspectives.heading": "What differs between them?",
  "story.related.heading": "Related stories",

  "settings.heading": "Settings",
  "settings.signedInAs": "Signed in as {email}.",
  "settings.languages.label": "Languages for your feed",
  "settings.languages.note":
    "Choose at least one. Your feed only ever shows languages you pick here.",
  "settings.save": "Save",
  "settings.yourData": "Your data",
  "settings.privacyPolicy": "Read what this applies to in the privacy policy",
  "settings.download": "Download your data",

  "account.delete": "Delete my account",
  "account.delete.warning":
    "This removes your saves, follows and profile permanently. Your reading history is kept but no longer linked to you. This cannot be undone.",
  "account.delete.confirm": "Yes, delete everything",
  "account.delete.pending": "Deleting…",
  "account.delete.cancel": "Cancel",

  "onboarding.heading": "Get set up",
  "onboarding.intro": "Two quick choices — both changeable later from Settings.",
  "onboarding.languages.note": "Choose at least one.",
  "onboarding.deck.heading": "What are you interested in?",
  "onboarding.deck.intro": "Tap what catches your eye, skip what doesn't — no checkboxes.",
  "onboarding.deck.empty": "Nothing to sample right now — you can always shape this later from Settings.",
  "onboarding.categories.label": "Or pick categories directly",
  "onboarding.categories.note": "Optional — tap any that interest you.",
  "onboarding.continue": "Continue",
  "onboarding.skip": "Skip for now",
  "onboarding.shapesFeed": "All three already shape your feed — not just saved for later.",
  "onboarding.sources.label": "Sources you already trust",
  "onboarding.sources.note": "Optional — pick any you already read.",

  "login.title": "Sign in",
  "login.createHeading": "Create an account",
  "login.createSubmit": "Create account",
  "login.intro": "Welcome back. Sign in to save articles and shape your feed.",
  "login.google": "Continue with Google",
  "login.or": "or",
  "login.newHere": "New here?",
  "login.alreadyHaveOne": "Already have one?",
  "login.email": "Email",
  "login.password": "Password",
  "login.pending": "Please wait…",
  "login.unavailable":
    "Accounts are not set up in this environment yet. Browsing, search and exploration all work without one — saved articles, history and a personalised feed need sign-in.",
  "login.minPassword": "Choose a password of at least {count} characters.",
  "login.checkEmail": "Check your email to confirm your account, then sign in.",
  "login.error.generic": "Something went wrong. Try again.",
  "login.error.credentials":
    "That email and password don’t match an account. Check both, or create an account.",
  "login.error.unconfirmed":
    "Confirm your email first — check your inbox for the link we sent when you signed up.",
  "login.error.registered": "There is already an account with that email. Sign in instead.",
  "login.error.rateLimit": "Too many attempts just now. Wait a minute and try again.",
  "login.error.network": "We could not reach the sign-in service. Check your connection and try again.",

  "invite.title": "Redeem your invite",
  "invite.heading": "You’re invited",
  "invite.intro":
    "JustNews is in private beta. Enter your invite code to unlock your personalised feed.",
  "invite.codeLabel": "Invite code",
  "invite.pending": "Checking…",
  "invite.submit": "Unlock",
  "invite.failed": "That code did not work.",

  "common.backToFeed": "Back to the feed",
  "common.browseTopics": "Browse topics",

  "saved.heading": "Saved",
  "saved.degraded": "Saved articles are unavailable right now.",
  "saved.empty.title": "Nothing saved yet",
  "saved.empty.body":
    "Every headline has a Save button. Saved stories stay here, and they keep working after the article scrolls off the feed.",

  "history.heading": "History",
  "history.intro": "Articles you have opened, most recent first.",
  "history.degraded": "History is unavailable right now.",
  "history.empty.title": "No reading history yet",
  "history.empty.body": "Articles you open appear here, most recent first. Only you can see this.",
  "history.viewed": "Viewed {time}",

  "topics.empty.title": "Nothing tagged {topic} yet",
  "topics.empty.body":
    "Coverage of this topic in your languages is still thin. It fills in as sources publish through the day.",

  "search.heading": "Search",
  "search.titleWithQuery": "Search: {query}",
  "search.intro": "What are you trying to understand?",
  "search.results": "Results",
  "search.resultCount.one": "{count} result",
  "search.resultCount.other": "{count} results",
  "search.degraded": "Search is unavailable right now.",
  "search.browseInstead": "Browse by topic instead",
  "search.filter.topic": "Topic",
  "search.filter.anyTopic": "Any topic",
  "search.filter.language": "Language",
  "search.filter.anyLanguage": "Any language you read",
  "search.filter.source": "Source",
  "search.filter.anySource": "Any source",
  "search.filter.date": "Date",
  "search.filter.anyDate": "Any time",
  "search.filter.date.day": "Past day",
  "search.filter.date.week": "Past week",
  "search.filter.date.month": "Past month",
  "search.group.topics": "Topics",
  "search.group.sources": "Sources",
  "search.group.stories": "Stories",
  "search.suggest.label": "Go straight to",
  "search.suggest.topic": "Topic",
  "search.suggest.source": "Publisher",
  "search.moreReports.one": "+ {count} more report on this story",
  "search.moreReports.other": "+ {count} more reports on this story",
  "search.recent": "Recent searches",
  "search.recent.clear": "Clear",
  "search.tooShort": "Type at least two characters to search.",
  "search.empty.title": "No headlines match “{query}”",
  "search.empty.body":
    "Try a shorter phrase, or a different language — the same story is often filed under quite different words.",

  "edition.intro": "Reported by newsrooms in {name}, in {language}.",
  "edition.degraded": "This edition is unavailable right now, so the page may be out of date.",
  "edition.empty.title": "No headlines from this edition yet",
  "edition.empty.body":
    "This edition draws on publishers based in one country. It fills in as they publish.",

  "notFound.heading": "That page does not exist",
  "notFound.action": "Go to the front page",

  "consent.label": "Cookie choice",
  "consent.body":
    "We'd like to remember your visit so we can measure whether the feed actually works and, later, personalise it. Nothing you save or mark isn't affected either way.",
  "consent.accept": "Accept",
  "consent.decline": "Decline",
  "consent.settings.label": "Analytics",
  "consent.settings.currentlyOn": "On — we remember your visits to measure how the site is used.",
  "consent.settings.currentlyOff": "Off — your visits aren't logged.",
  "consent.settings.turnOn": "Turn on",
  "consent.settings.turnOff": "Turn off",

  "feedback.heading": "Send feedback",
  "feedback.body": "Tell us what's working, what isn't, or what you wish JustNews did.",
  "feedback.placeholder": "What's on your mind?",
  "feedback.submit": "Send",
  "feedback.thanks": "Thanks — we read every one of these.",
  "feedback.signInRequired": "Sign in to send feedback.",

  "privacy.englishOnly":
    "This policy is currently available in English only. Machine-translating legal text risks getting your rights wrong, which is worse than not translating it at all — we'd rather say so plainly than guess.",

  "pagination.label": "More headlines",
  "pagination.next": "More headlines",
  "pagination.latest": "Back to the latest",

  "actions.save": "Save",
  "actions.saved": "Saved",
  "actions.save.failed": "Could not save that. Try again.",
  "actions.notInterested": "Not interested",
  "actions.notInterested.done": "Hidden from your feed",
  "actions.notInterested.failed": "Could not hide that. Try again.",
  "actions.undo": "Undo",
  "actions.undo.failed": "Could not undo. Try again.",
  "actions.share": "Share",
  "actions.share.done": "Shared",
  "actions.share.failed": "Could not share that. Try again.",
  "actions.follow": "Follow {source}",
  "actions.following": "Following {source}",
  "actions.follow.failed": "Could not change that. Try again.",

  "account.menu": "Account",

  "site.description": "Personalised, multilingual news.",
  "topics.fallbackTitle": "Topic",

  "desk.tabs.label": "Topic sections",
  "desk.tabs.latest": "Latest",
  "desk.tabs.perspectives": "Perspectives",
  "desk.overview.heading": "Topic overview",
  "desk.related.heading": "Related topics",
  "desk.timeline.empty": "No story timeline yet for this topic.",
  "desk.coverage.sources.one": "{count} source",
  "desk.coverage.sources.other": "{count} sources",
  "desk.coverage.languages.one": "{count} language",
  "desk.coverage.languages.other": "{count} languages",
  // Audit §21's diversity line - "7 sources / 4 countries / 2 languages".
  // A fresh set rather than reusing desk.coverage.* above: that pair is
  // My Desk's topic-coverage line (Chunk 8), and this is a different
  // feature - an article's own story-cluster coverage - that only happens
  // to want the same shape of sentence.
  "coverage.sources.one": "{count} source",
  "coverage.sources.other": "{count} sources",
  "coverage.countries.one": "{count} country",
  "coverage.countries.other": "{count} countries",
  "coverage.languages.one": "{count} language",
  "coverage.languages.other": "{count} languages",
  "desk.keyDevelopments.empty": "No major developments yet.",
  "desk.perspectives.empty":
    "Not enough named-source coverage yet to show perspectives for this topic.",
  "desk.perspectives.sourceCount": "{count} sources",
  "desk.perspectives.role.industry": "Industry press",
  "desk.perspectives.role.government": "Government sources",
  "desk.perspectives.role.academic": "Academic sources",
  "desk.perspectives.role.investor": "Investor press",
  "desk.perspectives.role.consumer": "Consumer press",
  "desk.perspectives.role.public": "Public sources",
  "desk.tabs.understand": "Understand",
  "desk.understand.heading": "Understand {topic}",
  "desk.understand.happening": "What\u2019s happening",
  "desk.understand.happening.note": "The developments the most publishers are covering.",
  "desk.understand.happening.fallbackNote":
    "No story has been picked up by more than one outlet yet. The latest reporting:",
  "desk.understand.saying": "Who is saying what",
  "desk.understand.saying.note": "Which kinds of publisher are reporting this, and who they are.",
  "desk.understand.saying.fallbackNote": "The outlets reporting on this most recently.",
  "desk.understand.changing": "What\u2019s changing",
  "desk.understand.changing.note": "How the coverage developed, newest first.",

  "profile.languageMix.heading": "What you actually read",
  "profile.languageMix.body": "Based on your last {count} articles opened.",
  "profile.languageMix.empty": "Nothing to show yet — this fills in as you read.",
  "profile.languageMix.count": "{count} read",
  "profile.byLanguage": "By language",
  "profile.byTopic": "By topic",

  "card.why.followedTopic": "Because you follow {topic}",
  "card.why.trending": "Trending now",
  "card.why.exploration": "Something different, on purpose",
  "card.timeline.developing": "Developing since {time}",
  "card.new": "New",
  "display.heading": "Display",
  "display.intro": "How JustNews looks on this device.",
  "display.theme": "Theme",
  "display.theme.system": "Match my device",
  "display.theme.light": "Light",
  "display.theme.dark": "Dark",
  "display.textSize": "Text size",
  "display.textSize.standard": "Standard",
  "display.textSize.large": "Larger",
  "display.save": "Save",
  "nav.display": "Display",
  "nav.howItWorks": "How it works",
  "how.heading": "How JustNews works",
  "how.intro": "A news reader built around one idea: the same event, reported by many newsrooms in many languages, is one story.",
  "how.stories.title": "Stories, not duplicates",
  "how.stories.body": "Every headline is compared with what has already arrived. When several outlets report the same event, their articles are grouped into one story, so you see it once - with how many outlets, countries and languages are carrying it.",
  "how.languages.title": "Across languages",
  "how.languages.body": "The grouping works across languages: a story reported in English, Spanish and Hindi is one story. When coverage exists in languages other than the one you are reading, the story says so and shows you where.",
  "how.perspectives.title": "Perspectives",
  "how.perspectives.body": "Perspectives group coverage by who published it - industry press, government sources, academic sources and others. It is a fact about the publisher, not a guess about what an article thinks, and every source listed is a link you can check.",
  "how.aquila.title": "The Aquila Tribune",
  "how.aquila.body": "Aquila is a newspaper published three times a day - morning, midday and evening. Each edition is composed once and then fixed, so an old edition reads exactly as it did on the day.",
  "how.ranking.title": "How your feed is ordered",
  "how.ranking.body": "When you are signed in, your feed weighs how recent a story is, the topics you follow, what other readers are reading, the source, and your languages - and keeps a small share of slots for something outside your usual interests. Where a card says why it is there, that is the reason the ranker actually used.",
  "how.data.title": "What we keep",
  "how.data.body": "JustNews stores a headline, a short snippet, an image link, the source and the link to the original - never the full article. Reading always happens on the publisher's own site. You can export or delete your account data at any time from Settings.",
  "shortcuts.heading": "Keyboard shortcuts",
  "shortcuts.next": "Next story",
  "shortcuts.previous": "Previous story",
  "shortcuts.open": "Open the story",
  "shortcuts.save": "Save it (signed in)",
  "shortcuts.search": "Search",
  "shortcuts.help": "Show this list",
  "shortcuts.close": "Close",
  "login.reset.link": "Forgot your password?",
  "login.reset.heading": "Reset your password",
  "login.reset.intro": "We will email you a link to choose a new one.",
  "login.reset.submit": "Send a reset link",
  "login.reset.sent": "If an account uses that address, a reset link is on its way. Check your inbox.",
  "login.reset.back": "Back to sign in",
  "login.reset.newHeading": "Choose a new password",
  "login.reset.newPassword": "New password",
  "login.reset.save": "Save password",
  "login.reset.done": "Your password is changed.",
  "story.follow": "Follow this story",
  "story.following": "Following this story",
  "following.heading": "Stories you follow",
  "following.note": "New reports since you last opened each one.",
  "following.new.one": "{count} new report",
  "following.new.other": "{count} new reports",
  "following.upToDate": "Up to date",
  "nav.discover": "Discover",
  "nav.history": "History",
  "nav.following": "Following",
  "following.empty.title": "You are not following any stories",
  "following.empty.body": "Follow a story from its page and it appears here, with a count of the new reports each time you come back.",
  "sidebar.label": "Main menu",
  "sidebar.collapse": "Collapse sidebar",
  "sidebar.expand": "Expand sidebar",
  "sidebar.open": "Open menu",
  "sidebar.close": "Close menu",
  "sidebar.search": "Search news",
  "discover.title": "Discover",
  "discover.tabs": "Discover views",
  "discover.tab.forYou": "For You",
  "discover.tab.top": "Top",
  "discover.tab.topics": "Topics",
  "discover.forYouIsTop": "For You shows Top stories until you choose some interests.",
  "discover.chooseInterests": "Choose interests",
  "discover.published": "Published {time}",
  "discover.save": "Save",
  "discover.unsave": "Remove from saved",
  "discover.signInToSave": "Sign in to save stories",
  "discover.more": "More options",
  "discover.share": "Share",
  "discover.copied": "Link copied",
  "discover.openOriginal": "Read at {source}",
  "discover.allSources": "See every source",
  "discover.notInterested": "Not interested",
  "discover.hidden": "Hidden. You'll see less like this.",
  "discover.undo": "Undo",
  "discover.loadingMore": "Loading more stories",
  "discover.end": "You're all caught up.",
  "discover.error": "Couldn't load stories.",
  "discover.retry": "Try again",
  "discover.empty": "Nothing here yet. Try another topic.",
  "discover.actionFailed": "That didn't work. Try again.",
  "rail.label": "Your Discover rail",
  "rail.customize": "Customize",
  "rail.customize.title": "Customize your rail",
  "rail.customize.up": "Move {widget} up",
  "rail.customize.down": "Move {widget} down",
  "rail.customize.done": "Done",
  "interests.title": "Make it yours",
  "interests.body": "Select topics and interests to customize your Discover experience.",
  "interests.save": "Save interests",
  "interests.saving": "Saving…",
  "interests.close": "Not now",
  "interests.failed": "Couldn't save. Try again.",
  "weather.title": "Weather",
  "weather.setCity": "Show the weather for your city",
  "weather.search": "Search for a city",
  "weather.noResults": "No places found",
  "weather.change": "Change city",
  "weather.useLocation": "Use my location",
  "weather.myLocation": "My location",
  "weather.highLow": "H: {high}° L: {low}°",
  "weather.unit": "Show in °{unit}",
  "weather.error": "Weather is unavailable right now.",
  "weather.attribution": "Weather data by Open-Meteo",
  "weather.code.clear": "Clear",
  "weather.code.partlyCloudy": "Partly cloudy",
  "weather.code.cloudy": "Cloudy",
  "weather.code.fog": "Fog",
  "weather.code.drizzle": "Drizzle",
  "weather.code.rain": "Rain",
  "weather.code.snow": "Snow",
  "weather.code.showers": "Showers",
  "weather.code.thunder": "Thunderstorm",
  "markets.title": "Market Outlook",
  "markets.note": "Index-tracking ETFs, and Bitcoin. Prices may be delayed.",
  "markets.empty": "Market data isn't available yet.",
  "markets.tile": "{label}: {price}, {change} today",
  "companies.title": "Trending Companies",
  "companies.subtitle": "Most named in the last day's news",
  "companies.stories.one": "{count} story today",
  "companies.stories.other": "{count} stories today",
  "companies.empty": "No company stands out in today's news yet.",
  "discover.sharePage": "Share",
} as const;

export type MessageKey = keyof typeof en;

const messages: Record<LocaleCode, Record<MessageKey, string>> = {
  en,
  es: {
    "skip.toContent": "Saltar al contenido",

    "nav.primary": "Principal",
    "error.rateLimited": "Demasiadas solicitudes. Inténtalo de nuevo en un minuto.",
    "nav.language": "Idioma",
    "nav.aquila": "Aquila",
    "nav.desk": "Mi Escritorio",
    "nav.search": "Buscar",
    "nav.settings": "Ajustes",
    "nav.saved": "Guardados",
    "nav.privacy": "Privacidad",
    "nav.feedback": "Enviar comentarios",

    "search.placeholder": "Buscar titulares",
    "search.submit": "Buscar",

    "account.signIn": "Iniciar sesión",
    "account.signOut": "Cerrar sesión",
    "account.saved": "Guardados",
    "account.history": "Historial",
    "account.settings": "Ajustes",
    "account.chooseTopics": "Elegir temas",
    "account.enterInvite": "Introducir código de invitación",
    "account.feedback": "Enviar comentarios",

    "beta.notice":
      "JustNews está en beta privada. Has iniciado sesión, pero necesitas un código de invitación para desbloquear tu feed personalizado, tus guardados y tu historial.",
    "beta.enterCode": "Introduce tu código",

    "signIn.title": "Inicia sesión para ver esto",
    "signIn.body":
      "Esta página muestra cosas vinculadas a tu cuenta, así que primero tienes que iniciar sesión.",

    "signIn.saved.body":
      "Guarda una historia desde cualquier tarjeta con el corazón y te esperará aquí en todos los dispositivos donde inicies sesión.",
    "signIn.following.body":
      "Sigue una historia y esta página contará las informaciones nuevas cada vez que vuelvas.",
    "signIn.history.body":
      "Las historias que abras con la sesión iniciada aparecen aquí para que puedas volver a encontrarlas.",

    "feed.degraded.personal":
      "Tu feed no está disponible ahora mismo, así que esta página puede estar desactualizada. Todo lo demás sigue funcionando.",
    "feed.degraded.anonymous":
      "Los titulares en directo no están disponibles ahora mismo, así que esta página puede estar desactualizada. Todo lo demás sigue funcionando.",
    "feed.empty.action": "Ir a Explorar",

    "stats.articles.one": "artículo",
    "stats.articles.other": "artículos",
    "stats.sources.one": "fuente",
    "stats.sources.other": "fuentes",
    "stats.stories.one": "historia",
    "stats.stories.other": "historias",

    "home.lead.context.show": "Más sobre esta historia",
    "home.lead.context.hide": "Menos",
    "home.lead.context.published": "Publicado {time}",
    "home.lead.context.coverage": "Ver cobertura completa",

    "aquila.title": "Aquila Tribune",
    "aquila.strap": "El mundo en contexto",
    "aquila.volume": "Vol. {volume}  N.º {number}",
    "aquila.dateline": "{city}, {date}",
    "aquila.editionTime": "{time}",
    "aquila.edition.morning": "Edición de la mañana",
    "aquila.edition.midday": "Edición del mediodía",
    "aquila.edition.evening": "Edición de la noche",
    "aquila.moreSections.one": "+ {count} sección más",
    "aquila.moreSections.other": "+ {count} secciones más",
    "aquila.editions": "Ediciones de hoy",
    "aquila.frontPage": "Portada",
    "aquila.motto": "Mejor información construye un mañana mejor.",
    "aquila.mottoAttribution": "JustNews",
    "aquila.moreNews": "También hoy",
    "aquila.inFocus": "En foco",
    "aquila.highlights": "Destacados de hoy",
    "aquila.pageRef": "Página {page}",
    "aquila.pageRef.label": "Más cobertura de {section}, página {page}",
    "aquila.pageRef.labelPlain": "Página {page}",
    "aquila.footer": "Noticias seleccionadas para un mundo mejor informado",
    "aquila.sign": "Lee más a fondo. Mira más lejos.",
    "aquila.contents": "Índice",
    "aquila.pagination": "Páginas",
    "aquila.previous": "Página anterior",
    "aquila.next": "Página siguiente",
    "aquila.fullscreen": "Pantalla completa",
    "aquila.exitFullscreen": "Salir de pantalla completa",
    "aquila.pageOf": "{page} / {total}",
    "aquila.pageLabel": "Página {page}",
    "aquila.pageEmpty": "No se compuso nada en esta página.",
    "aquila.pageFailed": "Esa página no se ha cargado. Inténtalo de nuevo.",
    "aquila.backHome": "Volver a la portada",
    "aquila.none.title": "Aún no se ha publicado ninguna edición",
    "aquila.none.body":
      "El Tribune se compone tres veces al día: a las 6:00, las 14:00 y las 22:00. La próxima edición aparecerá aquí.",
    "aquila.none.action": "Ir a Inicio",

    "coverage.label": "Idiomas que cubren esta historia",

    "article.notFound": "No encontrado",
    "article.readFull": "Leer la noticia completa en {source}",
    "article.otherLanguages.one": "También cubierto en otro idioma",
    "article.otherLanguages.other": "También cubierto en otros {count} idiomas",
    "article.otherSources.one": "También informado por 1 fuente más",
    "article.otherSources.other": "También informado por otras {count} fuentes",
    "article.seeFullCoverage": "Ver la cobertura completa",
    "article.backToFront": "Volver a la portada",
    "article.filedUnder": "Archivado en",
    "article.moreIn": "Más en {topic}",
    "article.moreFrom": "Más de {source}",
    "source.eyebrow": "Medio",
    "source.notFound": "Medio no encontrado",
    "source.visit": "Visitar {source}",
    "source.latest": "Lo más reciente",
    "source.empty.title": "Todavía nada de {source}",
    "source.empty.body": "Sus informaciones aparecen aquí en cuanto se publican.",
    "source.articleCount.one": "{count} artículo en JustNews",
    "source.articleCount.other": "{count} artículos en JustNews",
    "story.reports.one": "{count} información",
    "story.reports.other": "{count} informaciones",
    "story.firstReported": "Primer informe {time}",
    "story.lastUpdated": "Última actualización {time}",
    "story.sources.label": "Fuentes que cubren esta historia",
    "story.perspectives.heading": "¿En qué se diferencian?",
    "story.related.heading": "Historias relacionadas",

    "settings.heading": "Ajustes",
    "settings.signedInAs": "Sesión iniciada como {email}.",
    "settings.languages.label": "Idiomas de tu feed",
    "settings.languages.note":
      "Elige al menos uno. Tu feed solo muestra los idiomas que elijas aquí.",
    "settings.save": "Guardar",
    "settings.yourData": "Tus datos",
    "settings.privacyPolicy": "Consulta a qué se aplica esto en la política de privacidad",
    "settings.download": "Descargar tus datos",

    "account.delete": "Eliminar mi cuenta",
    "account.delete.warning":
      "Esto elimina permanentemente tus guardados, tus seguimientos y tu perfil. Tu historial de lectura se conserva, pero deja de estar vinculado a ti. Esto no se puede deshacer.",
    "account.delete.confirm": "Sí, eliminarlo todo",
    "account.delete.pending": "Eliminando…",
    "account.delete.cancel": "Cancelar",

    "onboarding.heading": "Vamos a configurarlo",
    "onboarding.intro": "Dos decisiones rápidas — ambas se pueden cambiar luego en Ajustes.",
    "onboarding.languages.note": "Elige al menos uno.",
    "onboarding.deck.heading": "¿Qué te interesa?",
    "onboarding.deck.intro": "Toca lo que te llame la atención, omite lo demás — sin casillas.",
    "onboarding.deck.empty": "Nada que probar ahora mismo — siempre puedes ajustarlo luego en Ajustes.",
    "onboarding.categories.label": "O elige categorías directamente",
    "onboarding.categories.note": "Opcional — toca las que te interesen.",
    "onboarding.continue": "Continuar",
    "onboarding.skip": "Ahora no",
    "onboarding.shapesFeed": "Los tres ya dan forma a tu feed — no es solo para más tarde.",
    "onboarding.sources.label": "Medios en los que ya confías",
    "onboarding.sources.note": "Opcional — elige los que ya lees.",

    "login.title": "Iniciar sesión",
    "login.createHeading": "Crear una cuenta",
    "login.createSubmit": "Crear cuenta",
    "login.intro": "Bienvenido de nuevo. Inicia sesión para guardar artículos y ajustar tu feed.",
    "login.google": "Continuar con Google",
    "login.or": "o",
    "login.newHere": "¿Eres nuevo por aquí?",
    "login.alreadyHaveOne": "¿Ya tienes una?",
    "login.email": "Correo electrónico",
    "login.password": "Contraseña",
    "login.pending": "Un momento…",
    "login.unavailable":
      "Las cuentas todavía no están configuradas en este entorno. Navegar, buscar y explorar funcionan sin una — los artículos guardados, el historial y el feed personalizado necesitan iniciar sesión.",
    "login.minPassword": "Elige una contraseña de al menos {count} caracteres.",
    "login.checkEmail": "Revisa tu correo para confirmar la cuenta y luego inicia sesión.",
    "login.error.generic": "Algo ha salido mal. Inténtalo de nuevo.",
    "login.error.credentials":
      "Ese correo y esa contraseña no coinciden con ninguna cuenta. Compruébalos o crea una cuenta.",
    "login.error.unconfirmed":
      "Confirma tu correo primero — busca en tu bandeja el enlace que te enviamos al registrarte.",
    "login.error.registered": "Ya existe una cuenta con ese correo. Inicia sesión en su lugar.",
    "login.error.rateLimit": "Demasiados intentos ahora mismo. Espera un minuto y vuelve a probar.",
    "login.error.network":
      "No hemos podido conectar con el servicio de inicio de sesión. Comprueba tu conexión y vuelve a intentarlo.",

    "invite.title": "Canjear tu invitación",
    "invite.heading": "Tienes una invitación",
    "invite.intro":
      "JustNews está en beta privada. Introduce tu código de invitación para desbloquear tu feed personalizado.",
    "invite.codeLabel": "Código de invitación",
    "invite.pending": "Comprobando…",
    "invite.submit": "Desbloquear",
    "invite.failed": "Ese código no ha funcionado.",

    "common.backToFeed": "Volver al feed",
    "common.browseTopics": "Explorar temas",

    "saved.heading": "Guardados",
    "saved.degraded": "Los artículos guardados no están disponibles ahora mismo.",
    "saved.empty.title": "Todavía no has guardado nada",
    "saved.empty.body":
      "Cada titular tiene un botón de Guardar. Las historias guardadas se quedan aquí y siguen funcionando cuando el artículo ya no está en el feed.",

    "history.heading": "Historial",
    "history.intro": "Artículos que has abierto, del más reciente al más antiguo.",
    "history.degraded": "El historial no está disponible ahora mismo.",
    "history.empty.title": "Todavía no hay historial de lectura",
    "history.empty.body":
      "Los artículos que abras aparecen aquí, del más reciente al más antiguo. Solo tú puedes ver esto.",
    "history.viewed": "Visto {time}",

    "topics.empty.title": "Todavía no hay nada etiquetado como {topic}",
    "topics.empty.body":
      "La cobertura de este tema en tus idiomas todavía es escasa. Se va llenando a medida que las fuentes publican durante el día.",

    "search.heading": "Buscar",
    "search.titleWithQuery": "Buscar: {query}",
    "search.intro": "¿Qué estás tratando de entender?",
    "search.results": "Resultados",
    "search.resultCount.one": "{count} resultado",
    "search.resultCount.other": "{count} resultados",
    "search.degraded": "La búsqueda no está disponible ahora mismo.",
    "search.browseInstead": "Explorar por tema en su lugar",
    "search.filter.topic": "Tema",
    "search.filter.anyTopic": "Cualquier tema",
    "search.filter.language": "Idioma",
    "search.filter.anyLanguage": "Cualquier idioma que leas",
    "search.filter.source": "Fuente",
    "search.filter.anySource": "Cualquier fuente",
    "search.filter.date": "Fecha",
    "search.filter.anyDate": "Cualquier momento",
    "search.filter.date.day": "Último día",
    "search.filter.date.week": "Última semana",
    "search.filter.date.month": "Último mes",
    "search.group.topics": "Temas",
    "search.group.sources": "Fuentes",
    "search.group.stories": "Historias",
    "search.suggest.label": "Ir directamente a",
    "search.suggest.topic": "Tema",
    "search.suggest.source": "Medio",
    "search.moreReports.one": "+ {count} información más sobre esta historia",
    "search.moreReports.other": "+ {count} informaciones más sobre esta historia",
    "search.recent": "Búsquedas recientes",
    "search.recent.clear": "Borrar",
    "search.tooShort": "Escribe al menos dos caracteres para buscar.",
    "search.empty.title": "Ningún titular coincide con «{query}»",
    "search.empty.body":
      "Prueba con una frase más corta, o con otro idioma: la misma historia suele archivarse con palabras muy distintas.",

    "edition.intro": "Informado por redacciones de {name}, en {language}.",
    "edition.degraded":
      "Esta edición no está disponible ahora mismo, así que la página puede estar desactualizada.",
    "edition.empty.title": "Todavía no hay titulares de esta edición",
    "edition.empty.body":
      "Esta edición se nutre de medios con sede en un país. Se va llenando a medida que publican.",

    "notFound.heading": "Esa página no existe",
    "notFound.action": "Ir a la portada",

    "consent.label": "Elección de cookies",
    "consent.body":
      "Nos gustaría recordar tu visita para poder medir si el feed realmente funciona y, más adelante, personalizarlo. Nada que guardes o marques se ve afectado en ningún caso.",
    "consent.accept": "Aceptar",
    "consent.decline": "Rechazar",
    "consent.settings.label": "Analítica",
    "consent.settings.currentlyOn":
      "Activada — recordamos tus visitas para medir cómo se usa el sitio.",
    "consent.settings.currentlyOff": "Desactivada — tus visitas no se registran.",
    "consent.settings.turnOn": "Activar",
    "consent.settings.turnOff": "Desactivar",

    "feedback.heading": "Enviar comentarios",
    "feedback.body": "Cuéntanos qué funciona, qué no, o qué te gustaría que JustNews hiciera.",
    "feedback.placeholder": "¿Qué tienes en mente?",
    "feedback.submit": "Enviar",
    "feedback.thanks": "Gracias — leemos todos los comentarios.",
    "feedback.signInRequired": "Inicia sesión para enviar comentarios.",

    "privacy.englishOnly":
      "Esta política solo está disponible en inglés por ahora. Traducir texto legal automáticamente puede tergiversar tus derechos, lo cual es peor que no traducirlo — preferimos decirlo claramente antes que arriesgarnos.",

    "pagination.label": "Más titulares",
    "pagination.next": "Más titulares",
    "pagination.latest": "Volver a lo más reciente",

    "actions.save": "Guardar",
    "actions.saved": "Guardado",
    "actions.save.failed": "No se ha podido guardar. Inténtalo de nuevo.",
    "actions.notInterested": "No me interesa",
    "actions.notInterested.done": "Oculto de tu feed",
    "actions.notInterested.failed": "No se ha podido ocultar. Inténtalo de nuevo.",
    "actions.undo": "Deshacer",
    "actions.undo.failed": "No se ha podido deshacer. Inténtalo de nuevo.",
    "actions.share": "Compartir",
    "actions.share.done": "Compartido",
    "actions.share.failed": "No se ha podido compartir. Inténtalo de nuevo.",
    "actions.follow": "Seguir a {source}",
    "actions.following": "Siguiendo a {source}",
    "actions.follow.failed": "No se ha podido cambiar. Inténtalo de nuevo.",

    "account.menu": "Cuenta",

    "site.description": "Noticias personalizadas y multilingües.",
    "topics.fallbackTitle": "Tema",

    "desk.tabs.label": "Secciones del tema",
    "desk.tabs.latest": "Lo último",
    "desk.tabs.perspectives": "Perspectivas",
    "desk.overview.heading": "Resumen del tema",
    "desk.related.heading": "Temas relacionados",
    "desk.timeline.empty": "Todavía no hay cronología para este tema.",
    "desk.coverage.sources.one": "{count} fuente",
    "desk.coverage.sources.other": "{count} fuentes",
    "desk.coverage.languages.one": "{count} idioma",
    "desk.coverage.languages.other": "{count} idiomas",
    "coverage.sources.one": "{count} fuente",
    "coverage.sources.other": "{count} fuentes",
    "coverage.countries.one": "{count} país",
    "coverage.countries.other": "{count} países",
    "coverage.languages.one": "{count} idioma",
    "coverage.languages.other": "{count} idiomas",
    "desk.keyDevelopments.empty": "Todavía no hay desarrollos importantes.",
    "desk.perspectives.empty":
      "Todavía no hay suficiente cobertura de fuentes identificadas para mostrar perspectivas de este tema.",
    "desk.perspectives.sourceCount": "{count} fuentes",
    "desk.perspectives.role.industry": "Prensa especializada",
    "desk.perspectives.role.government": "Fuentes gubernamentales",
    "desk.perspectives.role.academic": "Fuentes académicas",
    "desk.perspectives.role.investor": "Prensa de inversión",
    "desk.perspectives.role.consumer": "Prensa de consumo",
    "desk.perspectives.role.public": "Fuentes públicas",
    "desk.tabs.understand": "Entender",
    "desk.understand.heading": "Entender {topic}",
    "desk.understand.happening": "Qué está pasando",
    "desk.understand.happening.note": "Los desarrollos que más medios están cubriendo.",
    "desk.understand.happening.fallbackNote":
      "Ninguna historia ha sido recogida todavía por más de un medio. Lo más reciente:",
    "desk.understand.saying": "Quién dice qué",
    "desk.understand.saying.note": "Qué tipos de medio lo están cubriendo, y cuáles son.",
    "desk.understand.saying.fallbackNote": "Los medios que han informado sobre esto más recientemente.",
    "desk.understand.changing": "Qué está cambiando",
    "desk.understand.changing.note": "Cómo se ha desarrollado la cobertura, lo más nuevo primero.",

    "profile.languageMix.heading": "Lo que realmente lees",
    "profile.languageMix.body": "Según tus últimos {count} artículos abiertos.",
    "profile.languageMix.empty": "Todavía no hay nada que mostrar — esto se llena a medida que lees.",
    "profile.languageMix.count": "{count} leídos",
    "profile.byLanguage": "Por idioma",
    "profile.byTopic": "Por tema",

    "card.why.followedTopic": "Porque sigues {topic}",
    "card.why.trending": "Tendencia ahora",
    "card.why.exploration": "Algo distinto, a propósito",
    "card.timeline.developing": "En desarrollo desde {time}",
    "card.new": "Nuevo",
    "display.heading": "Pantalla",
    "display.intro": "Cómo se ve JustNews en este dispositivo.",
    "display.theme": "Tema",
    "display.theme.system": "Como mi dispositivo",
    "display.theme.light": "Claro",
    "display.theme.dark": "Oscuro",
    "display.textSize": "Tamaño del texto",
    "display.textSize.standard": "Normal",
    "display.textSize.large": "Más grande",
    "display.save": "Guardar",
    "nav.display": "Pantalla",
    "nav.howItWorks": "Cómo funciona",
    "how.heading": "Cómo funciona JustNews",
    "how.intro": "Un lector de noticias construido sobre una idea: el mismo acontecimiento, contado por muchas redacciones en muchos idiomas, es una sola historia.",
    "how.stories.title": "Historias, no duplicados",
    "how.stories.body": "Cada titular se compara con lo que ya ha llegado. Cuando varios medios informan del mismo hecho, sus artículos se agrupan en una historia, así que la ves una vez, junto con cuántos medios, países e idiomas la cubren.",
    "how.languages.title": "Entre idiomas",
    "how.languages.body": "La agrupación funciona entre idiomas: una historia publicada en inglés, español e hindi es una sola. Cuando hay cobertura en otros idiomas además del que lees, la historia lo indica y te muestra dónde.",
    "how.perspectives.title": "Perspectivas",
    "how.perspectives.body": "Las perspectivas agrupan la cobertura según quién la publica: prensa especializada, fuentes gubernamentales, fuentes académicas y otras. Es un dato sobre el medio, no una suposición sobre lo que opina un artículo, y cada fuente es un enlace que puedes comprobar.",
    "how.aquila.title": "The Aquila Tribune",
    "how.aquila.body": "Aquila es un periódico que se publica tres veces al día: mañana, mediodía y noche. Cada edición se compone una vez y queda fija, así que una edición antigua se lee exactamente como aquel día.",
    "how.ranking.title": "Cómo se ordena tu portada",
    "how.ranking.body": "Con la sesión iniciada, tu portada tiene en cuenta lo reciente que es una historia, los temas que sigues, lo que leen otros lectores, la fuente y tus idiomas, y reserva unos pocos espacios para algo fuera de tus intereses habituales. Cuando una tarjeta dice por qué está ahí, es la razón que el sistema usó de verdad.",
    "how.data.title": "Qué guardamos",
    "how.data.body": "JustNews guarda un titular, un fragmento breve, un enlace a la imagen, la fuente y el enlace al original, nunca el artículo completo. La lectura siempre ocurre en la web del medio. Puedes exportar o borrar los datos de tu cuenta cuando quieras desde Ajustes.",
    "shortcuts.heading": "Atajos de teclado",
    "shortcuts.next": "Siguiente historia",
    "shortcuts.previous": "Historia anterior",
    "shortcuts.open": "Abrir la historia",
    "shortcuts.save": "Guardarla (con sesión iniciada)",
    "shortcuts.search": "Buscar",
    "shortcuts.help": "Mostrar esta lista",
    "shortcuts.close": "Cerrar",
    "login.reset.link": "¿Olvidaste tu contraseña?",
    "login.reset.heading": "Restablece tu contraseña",
    "login.reset.intro": "Te enviaremos un enlace para elegir una nueva.",
    "login.reset.submit": "Enviar un enlace",
    "login.reset.sent": "Si hay una cuenta con esa dirección, te llegará un enlace. Revisa tu correo.",
    "login.reset.back": "Volver a iniciar sesión",
    "login.reset.newHeading": "Elige una contraseña nueva",
    "login.reset.newPassword": "Contraseña nueva",
    "login.reset.save": "Guardar contraseña",
    "login.reset.done": "Tu contraseña ha cambiado.",
    "story.follow": "Seguir esta historia",
    "story.following": "Siguiendo esta historia",
    "following.heading": "Historias que sigues",
    "following.note": "Informaciones nuevas desde la última vez que abriste cada una.",
    "following.new.one": "{count} información nueva",
    "following.new.other": "{count} informaciones nuevas",
    "following.upToDate": "Al día",
    "nav.discover": "Descubrir",
    "nav.history": "Historial",
    "nav.following": "Siguiendo",
    "following.empty.title": "No sigues ninguna historia",
    "following.empty.body": "Sigue una historia desde su página y aparecerá aquí, con el número de informaciones nuevas cada vez que vuelvas.",
    "sidebar.label": "Menú principal",
    "sidebar.collapse": "Contraer barra lateral",
    "sidebar.expand": "Expandir barra lateral",
    "sidebar.open": "Abrir menú",
    "sidebar.close": "Cerrar menú",
    "sidebar.search": "Buscar noticias",
    "discover.title": "Descubrir",
    "discover.tabs": "Vistas de Descubrir",
    "discover.tab.forYou": "Para ti",
    "discover.tab.top": "Destacadas",
    "discover.tab.topics": "Temas",
    "discover.forYouIsTop": "Para ti muestra las destacadas hasta que elijas algunos intereses.",
    "discover.chooseInterests": "Elegir intereses",
    "discover.published": "Publicado {time}",
    "discover.save": "Guardar",
    "discover.unsave": "Quitar de guardados",
    "discover.signInToSave": "Inicia sesión para guardar historias",
    "discover.more": "Más opciones",
    "discover.share": "Compartir",
    "discover.copied": "Enlace copiado",
    "discover.openOriginal": "Leer en {source}",
    "discover.allSources": "Ver todas las fuentes",
    "discover.notInterested": "No me interesa",
    "discover.hidden": "Oculto. Verás menos como esto.",
    "discover.undo": "Deshacer",
    "discover.loadingMore": "Cargando más historias",
    "discover.end": "Estás al día.",
    "discover.error": "No se pudieron cargar las historias.",
    "discover.retry": "Reintentar",
    "discover.empty": "Aún no hay nada. Prueba otro tema.",
    "discover.actionFailed": "No funcionó. Inténtalo de nuevo.",
    "rail.label": "Tu panel de Descubrir",
    "rail.customize": "Personalizar",
    "rail.customize.title": "Personaliza tu panel",
    "rail.customize.up": "Subir {widget}",
    "rail.customize.down": "Bajar {widget}",
    "rail.customize.done": "Listo",
    "interests.title": "Hazlo tuyo",
    "interests.body": "Elige temas e intereses para personalizar Descubrir.",
    "interests.save": "Guardar intereses",
    "interests.saving": "Guardando…",
    "interests.close": "Ahora no",
    "interests.failed": "No se pudo guardar. Inténtalo de nuevo.",
    "weather.title": "El tiempo",
    "weather.setCity": "Muestra el tiempo de tu ciudad",
    "weather.search": "Busca una ciudad",
    "weather.noResults": "No se encontraron lugares",
    "weather.change": "Cambiar ciudad",
    "weather.useLocation": "Usar mi ubicación",
    "weather.myLocation": "Mi ubicación",
    "weather.highLow": "Máx: {high}° Mín: {low}°",
    "weather.unit": "Mostrar en °{unit}",
    "weather.error": "El tiempo no está disponible ahora.",
    "weather.attribution": "Datos del tiempo de Open-Meteo",
    "weather.code.clear": "Despejado",
    "weather.code.partlyCloudy": "Parcialmente nublado",
    "weather.code.cloudy": "Nublado",
    "weather.code.fog": "Niebla",
    "weather.code.drizzle": "Llovizna",
    "weather.code.rain": "Lluvia",
    "weather.code.snow": "Nieve",
    "weather.code.showers": "Chubascos",
    "weather.code.thunder": "Tormenta",
    "markets.title": "Panorama del mercado",
    "markets.note": "ETF que siguen índices, y bitcóin. Los precios pueden ir con retraso.",
    "markets.empty": "Aún no hay datos del mercado.",
    "markets.tile": "{label}: {price}, {change} hoy",
    "companies.title": "Empresas en tendencia",
    "companies.subtitle": "Las más citadas en las noticias del último día",
    "companies.stories.one": "{count} noticia hoy",
    "companies.stories.other": "{count} noticias hoy",
    "companies.empty": "Ninguna empresa destaca aún en las noticias de hoy.",
    "discover.sharePage": "Compartir",
  },
  hi: {
    "skip.toContent": "सामग्री पर जाएँ",

    "nav.primary": "मुख्य",
    "error.rateLimited": "बहुत ज़्यादा अनुरोध। एक मिनट बाद फिर कोशिश करें।",
    "nav.language": "भाषा",
    "nav.aquila": "अक्विला",
    "nav.desk": "मेरा डेस्क",
    "nav.search": "खोजें",
    "nav.settings": "सेटिंग्स",
    "nav.saved": "सहेजे गए",
    "nav.privacy": "निजता",
    "nav.feedback": "प्रतिक्रिया भेजें",

    "search.placeholder": "सुर्ख़ियाँ खोजें",
    "search.submit": "खोजें",

    "account.signIn": "साइन इन",
    "account.signOut": "साइन आउट",
    "account.saved": "सहेजे गए",
    "account.history": "इतिहास",
    "account.settings": "सेटिंग्स",
    "account.chooseTopics": "विषय चुनें",
    "account.enterInvite": "आमंत्रण कोड डालें",
    "account.feedback": "प्रतिक्रिया भेजें",

    "beta.notice":
      "JustNews निजी बीटा में है। आप साइन इन हैं, लेकिन अपनी वैयक्तिकृत फ़ीड, सहेजे गए लेख और इतिहास खोलने के लिए आपको एक आमंत्रण कोड चाहिए।",
    "beta.enterCode": "अपना कोड डालें",

    "signIn.title": "इसे देखने के लिए साइन इन करें",
    "signIn.body":
      "यह पेज आपके खाते से जुड़ी चीज़ें दिखाता है, इसलिए पहले साइन इन करना ज़रूरी है।",

    "signIn.saved.body":
      "किसी भी कार्ड के दिल से ख़बर सहेजें, और वह हर उस डिवाइस पर यहाँ मिलेगी जहाँ आप साइन इन करते हैं।",
    "signIn.following.body":
      "कोई ख़बर फ़ॉलो करें, और हर बार लौटने पर यह पेज नई रिपोर्टें गिनेगा।",
    "signIn.history.body":
      "साइन इन रहते हुए खोली गई ख़बरें यहाँ दिखती हैं, ताकि आप उन्हें फिर ढूँढ सकें।",

    "feed.degraded.personal":
      "आपकी फ़ीड अभी उपलब्ध नहीं है, इसलिए यह पेज पुराना हो सकता है। बाकी सब कुछ काम कर रहा है।",
    "feed.degraded.anonymous":
      "ताज़ा सुर्ख़ियाँ अभी उपलब्ध नहीं हैं, इसलिए यह पेज पुराना हो सकता है। बाकी सब कुछ काम कर रहा है।",
    "feed.empty.action": "एक्सप्लोर पर जाएँ",

    "stats.articles.one": "लेख",
    "stats.articles.other": "लेख",
    "stats.sources.one": "स्रोत",
    "stats.sources.other": "स्रोत",
    "stats.stories.one": "कहानी",
    "stats.stories.other": "कहानियाँ",

    "home.lead.context.show": "इस कहानी के बारे में और",
    "home.lead.context.hide": "कम करें",
    "home.lead.context.published": "प्रकाशित {time}",
    "home.lead.context.coverage": "पूरी कवरेज देखें",

    "aquila.title": "Aquila Tribune",
    "aquila.strap": "दुनिया, सन्दर्भ के साथ",
    "aquila.volume": "खंड {volume}  अंक {number}",
    "aquila.dateline": "{city}, {date}",
    "aquila.editionTime": "{time}",
    "aquila.edition.morning": "प्रातः संस्करण",
    "aquila.edition.midday": "मध्याह्न संस्करण",
    "aquila.edition.evening": "सायं संस्करण",
    "aquila.moreSections.one": "+ {count} और खंड",
    "aquila.moreSections.other": "+ {count} और खंड",
    "aquila.editions": "आज के संस्करण",
    "aquila.frontPage": "मुखपृष्ठ",
    "aquila.motto": "बेहतर जानकारी बेहतर कल बनाती है।",
    "aquila.mottoAttribution": "JustNews",
    "aquila.moreNews": "आज और भी",
    "aquila.inFocus": "विशेष",
    "aquila.highlights": "आज की मुख्य बातें",
    "aquila.pageRef": "पृष्ठ {page}",
    "aquila.pageRef.label": "{section} पर और कवरेज, पृष्ठ {page}",
    "aquila.pageRef.labelPlain": "पृष्ठ {page}",
    "aquila.footer": "बेहतर जानकारी वाली दुनिया के लिए चुनी हुई ख़बरें",
    "aquila.sign": "गहराई से पढ़ें। दूर तक देखें।",
    "aquila.contents": "अनुक्रम",
    "aquila.pagination": "पृष्ठ",
    "aquila.previous": "पिछला पृष्ठ",
    "aquila.next": "अगला पृष्ठ",
    "aquila.fullscreen": "पूर्ण स्क्रीन",
    "aquila.exitFullscreen": "पूर्ण स्क्रीन से बाहर निकलें",
    "aquila.pageOf": "{page} / {total}",
    "aquila.pageLabel": "पृष्ठ {page}",
    "aquila.pageEmpty": "इस पृष्ठ पर कुछ नहीं रखा गया।",
    "aquila.pageFailed": "वह पृष्ठ लोड नहीं हुआ। फिर कोशिश करें।",
    "aquila.backHome": "मुखपृष्ठ पर वापस",
    "aquila.none.title": "अभी कोई संस्करण प्रकाशित नहीं हुआ",
    "aquila.none.body":
      "ट्रिब्यून दिन में तीन बार तैयार होता है — सुबह 6, दोपहर 2 और रात 10 बजे। अगला संस्करण यहाँ दिखेगा।",
    "aquila.none.action": "होम पर जाएँ",

    "coverage.label": "इस कहानी को कवर करने वाली भाषाएँ",

    "article.notFound": "नहीं मिला",
    "article.readFull": "पूरी ख़बर {source} पर पढ़ें",
    "article.otherLanguages.one": "एक और भाषा में भी कवर किया गया",
    "article.otherLanguages.other": "{count} और भाषाओं में भी कवर किया गया",
    "article.otherSources.one": "1 और स्रोत ने भी यह ख़बर दी",
    "article.otherSources.other": "{count} और स्रोतों ने भी यह ख़बर दी",
    "article.seeFullCoverage": "पूरी कवरेज देखें",
    "article.backToFront": "मुख्य पृष्ठ पर लौटें",
    "article.filedUnder": "इस विषय में",
    "article.moreIn": "{topic} में और",
    "article.moreFrom": "{source} से और",
    "source.eyebrow": "प्रकाशक",
    "source.notFound": "प्रकाशक नहीं मिला",
    "source.visit": "{source} पर जाएँ",
    "source.latest": "ताज़ा रिपोर्टिंग",
    "source.empty.title": "{source} से अभी कुछ नहीं",
    "source.empty.body": "इनकी रिपोर्टिंग प्रकाशित होते ही यहाँ दिखेगी।",
    "source.articleCount.one": "JustNews पर {count} लेख",
    "source.articleCount.other": "JustNews पर {count} लेख",
    "story.reports.one": "{count} रिपोर्ट",
    "story.reports.other": "{count} रिपोर्ट",
    "story.firstReported": "पहली बार रिपोर्ट {time}",
    "story.lastUpdated": "आख़िरी अपडेट {time}",
    "story.sources.label": "इस कहानी को कवर करने वाले स्रोत",
    "story.perspectives.heading": "इनमें क्या फ़र्क़ है?",
    "story.related.heading": "संबंधित कहानियाँ",

    "settings.heading": "सेटिंग्स",
    "settings.signedInAs": "{email} के रूप में साइन इन हैं।",
    "settings.languages.label": "आपकी फ़ीड की भाषाएँ",
    "settings.languages.note":
      "कम से कम एक चुनें। आपकी फ़ीड सिर्फ़ वही भाषाएँ दिखाती है जो आप यहाँ चुनते हैं।",
    "settings.save": "सहेजें",
    "settings.yourData": "आपका डेटा",
    "settings.privacyPolicy": "यह किस पर लागू होता है, यह निजता नीति में पढ़ें",
    "settings.download": "अपना डेटा डाउनलोड करें",

    "account.delete": "मेरा खाता हटाएँ",
    "account.delete.warning":
      "इससे आपके सहेजे गए लेख, फ़ॉलो और प्रोफ़ाइल हमेशा के लिए हट जाते हैं। आपका पढ़ने का इतिहास रखा जाता है, पर उसका आपसे कोई नाता नहीं रहता। यह वापस नहीं किया जा सकता।",
    "account.delete.confirm": "हाँ, सब कुछ हटाएँ",
    "account.delete.pending": "हटाया जा रहा है…",
    "account.delete.cancel": "रहने दें",

    "onboarding.heading": "शुरू करते हैं",
    "onboarding.intro": "दो छोटे फ़ैसले — दोनों बाद में सेटिंग्स से बदले जा सकते हैं।",
    "onboarding.languages.note": "कम से कम एक चुनें।",
    "onboarding.deck.heading": "आपकी दिलचस्पी किसमें है?",
    "onboarding.deck.intro": "जो पसंद आए उसे चुनें, बाक़ी छोड़ दें — कोई चेकबॉक्स नहीं।",
    "onboarding.deck.empty": "अभी आज़माने को कुछ नहीं — बाद में सेटिंग्स से इसे बदला जा सकता है।",
    "onboarding.categories.label": "या सीधे श्रेणियाँ चुनें",
    "onboarding.categories.note": "वैकल्पिक — जो दिलचस्प लगे उन्हें चुनें।",
    "onboarding.continue": "आगे बढ़ें",
    "onboarding.skip": "अभी नहीं",
    "onboarding.shapesFeed": "तीनों अभी से आपकी सुर्ख़ियों को आकार देते हैं — सिर्फ़ बाद के लिए सहेजे नहीं गए।",
    "onboarding.sources.label": "जिन स्रोतों पर आप पहले से भरोसा करते हैं",
    "onboarding.sources.note": "वैकल्पिक — जो पहले से पढ़ते हैं उन्हें चुनें।",

    "login.title": "साइन इन",
    "login.createHeading": "खाता बनाएँ",
    "login.createSubmit": "खाता बनाएँ",
    "login.intro": "वापसी पर स्वागत है। लेख सहेजने और अपनी फ़ीड को अपने अनुसार ढालने के लिए साइन इन करें।",
    "login.google": "Google से जारी रखें",
    "login.or": "या",
    "login.newHere": "यहाँ नए हैं?",
    "login.alreadyHaveOne": "पहले से खाता है?",
    "login.email": "ईमेल",
    "login.password": "पासवर्ड",
    "login.pending": "एक पल…",
    "login.unavailable":
      "इस माहौल में खाते अभी सेट नहीं हुए हैं। पढ़ना, खोजना और एक्सप्लोर करना बिना खाते के भी चलता है — सहेजे गए लेख, इतिहास और वैयक्तिकृत फ़ीड के लिए साइन इन चाहिए।",
    "login.minPassword": "कम से कम {count} अक्षरों का पासवर्ड चुनें।",
    "login.checkEmail": "अपना खाता पक्का करने के लिए ईमेल देखें, फिर साइन इन करें।",
    "login.error.generic": "कुछ गड़बड़ हो गई। फिर कोशिश करें।",
    "login.error.credentials":
      "यह ईमेल और पासवर्ड किसी खाते से मेल नहीं खाते। दोनों जाँचें, या नया खाता बनाएँ।",
    "login.error.unconfirmed":
      "पहले अपना ईमेल पक्का करें — साइन अप के समय भेजा गया लिंक अपने इनबॉक्स में देखें।",
    "login.error.registered": "इस ईमेल से पहले से एक खाता है। इसके बजाय साइन इन करें।",
    "login.error.rateLimit": "अभी बहुत ज़्यादा कोशिशें हो गईं। एक मिनट रुककर फिर कोशिश करें।",
    "login.error.network":
      "हम साइन-इन सेवा तक नहीं पहुँच सके। अपना कनेक्शन जाँचें और फिर कोशिश करें।",

    "invite.title": "अपना आमंत्रण भुनाएँ",
    "invite.heading": "आप आमंत्रित हैं",
    "invite.intro":
      "JustNews निजी बीटा में है। अपनी वैयक्तिकृत फ़ीड खोलने के लिए अपना आमंत्रण कोड डालें।",
    "invite.codeLabel": "आमंत्रण कोड",
    "invite.pending": "जाँच रहे हैं…",
    "invite.submit": "खोलें",
    "invite.failed": "यह कोड काम नहीं आया।",

    "common.backToFeed": "फ़ीड पर लौटें",
    "common.browseTopics": "विषय देखें",

    "saved.heading": "सहेजे गए",
    "saved.degraded": "सहेजे गए लेख अभी उपलब्ध नहीं हैं।",
    "saved.empty.title": "अभी तक कुछ सहेजा नहीं गया",
    "saved.empty.body":
      "हर सुर्ख़ी के साथ सहेजने का बटन है। सहेजी गई कहानियाँ यहीं रहती हैं, और लेख के फ़ीड से हट जाने के बाद भी काम करती रहती हैं।",

    "history.heading": "इतिहास",
    "history.intro": "आपके खोले हुए लेख, सबसे नए पहले।",
    "history.degraded": "इतिहास अभी उपलब्ध नहीं है।",
    "history.empty.title": "अभी पढ़ने का कोई इतिहास नहीं",
    "history.empty.body":
      "आप जो लेख खोलते हैं वे यहाँ दिखते हैं, सबसे नए पहले। यह सिर्फ़ आपको दिखता है।",
    "history.viewed": "{time} देखा",

    "topics.empty.title": "{topic} के साथ अभी कुछ नहीं है",
    "topics.empty.body":
      "आपकी भाषाओं में इस विषय की कवरेज अभी कम है। दिन भर में जैसे-जैसे स्रोत छापेंगे, यह भरता जाएगा।",

    "search.heading": "खोज",
    "search.titleWithQuery": "खोज: {query}",
    "search.intro": "आप क्या समझना चाहते हैं?",
    "search.results": "परिणाम",
    "search.resultCount.one": "{count} परिणाम",
    "search.resultCount.other": "{count} परिणाम",
    "search.degraded": "खोज अभी उपलब्ध नहीं है।",
    "search.browseInstead": "इसके बजाय विषय के हिसाब से देखें",
    "search.filter.topic": "विषय",
    "search.filter.anyTopic": "कोई भी विषय",
    "search.filter.language": "भाषा",
    "search.filter.anyLanguage": "आपकी पढ़ी जाने वाली कोई भी भाषा",
    "search.filter.source": "स्रोत",
    "search.filter.anySource": "कोई भी स्रोत",
    "search.filter.date": "तारीख़",
    "search.filter.anyDate": "कभी भी",
    "search.filter.date.day": "पिछला दिन",
    "search.filter.date.week": "पिछला सप्ताह",
    "search.filter.date.month": "पिछला महीना",
    "search.group.topics": "विषय",
    "search.group.sources": "स्रोत",
    "search.group.stories": "ख़बरें",
    "search.suggest.label": "सीधे जाएँ",
    "search.suggest.topic": "विषय",
    "search.suggest.source": "प्रकाशक",
    "search.moreReports.one": "इस ख़बर पर {count} और रिपोर्ट",
    "search.moreReports.other": "इस ख़बर पर {count} और रिपोर्ट",
    "search.recent": "हाल की खोजें",
    "search.recent.clear": "साफ़ करें",
    "search.tooShort": "खोजने के लिए कम से कम दो अक्षर लिखें।",
    "search.empty.title": "“{query}” से कोई सुर्ख़ी मेल नहीं खाती",
    "search.empty.body":
      "छोटा वाक्यांश आज़माएँ, या कोई दूसरी भाषा — वही ख़बर अक्सर बिल्कुल अलग शब्दों में दर्ज होती है।",

    "edition.intro": "{name} की संपादकीय टीमों की ख़बरें, {language} में।",
    "edition.degraded": "यह संस्करण अभी उपलब्ध नहीं है, इसलिए पेज पुराना हो सकता है।",
    "edition.empty.title": "इस संस्करण से अभी कोई सुर्ख़ी नहीं",
    "edition.empty.body":
      "यह संस्करण एक देश के प्रकाशकों पर टिका है। जैसे-जैसे वे छापेंगे, यह भरता जाएगा।",

    "notFound.heading": "यह पेज मौजूद नहीं है",
    "notFound.action": "मुख्य पृष्ठ पर जाएँ",

    "consent.label": "कुकी विकल्प",
    "consent.body":
      "हम आपकी विज़िट याद रखना चाहते हैं ताकि यह माप सकें कि फ़ीड वाकई काम करती है या नहीं, और आगे चलकर इसे वैयक्तिकृत कर सकें। आप जो कुछ सहेजते या चिह्नित करते हैं, वह दोनों ही स्थिति में प्रभावित नहीं होता।",
    "consent.accept": "स्वीकार करें",
    "consent.decline": "अस्वीकार करें",
    "consent.settings.label": "एनालिटिक्स",
    "consent.settings.currentlyOn": "चालू — हम साइट के इस्तेमाल को मापने के लिए आपकी विज़िट याद रखते हैं।",
    "consent.settings.currentlyOff": "बंद — आपकी विज़िट दर्ज नहीं की जातीं।",
    "consent.settings.turnOn": "चालू करें",
    "consent.settings.turnOff": "बंद करें",

    "feedback.heading": "प्रतिक्रिया भेजें",
    "feedback.body": "बताएं कि क्या ठीक काम कर रहा है, क्या नहीं, या JustNews में आप क्या चाहते हैं।",
    "feedback.placeholder": "आपके मन में क्या है?",
    "feedback.submit": "भेजें",
    "feedback.thanks": "धन्यवाद — हम हर प्रतिक्रिया पढ़ते हैं।",
    "feedback.signInRequired": "प्रतिक्रिया भेजने के लिए साइन इन करें।",

    "privacy.englishOnly":
      "यह नीति अभी सिर्फ़ अंग्रेज़ी में उपलब्ध है। कानूनी पाठ का मशीनी अनुवाद आपके अधिकारों को ग़लत बता सकता है, जो बिना अनुवाद के छोड़ने से भी बुरा है — हम अंदाज़ा लगाने के बजाय साफ़-साफ़ यह बता देना बेहतर समझते हैं।",

    "pagination.label": "और सुर्ख़ियाँ",
    "pagination.next": "और सुर्ख़ियाँ",
    "pagination.latest": "ताज़ा ख़बरों पर लौटें",

    "actions.save": "सहेजें",
    "actions.saved": "सहेजा गया",
    "actions.save.failed": "सहेजा नहीं जा सका। फिर कोशिश करें।",
    "actions.notInterested": "दिलचस्पी नहीं",
    "actions.notInterested.done": "आपकी फ़ीड से हटाया गया",
    "actions.notInterested.failed": "हटाया नहीं जा सका। फिर कोशिश करें।",
    "actions.undo": "पूर्ववत करें",
    "actions.undo.failed": "पूर्ववत नहीं किया जा सका। फिर कोशिश करें।",
    "actions.share": "साझा करें",
    "actions.share.done": "साझा किया गया",
    "actions.share.failed": "साझा नहीं किया जा सका। फिर कोशिश करें।",
    "actions.follow": "{source} को फ़ॉलो करें",
    "actions.following": "{source} को फ़ॉलो कर रहे हैं",
    "actions.follow.failed": "बदला नहीं जा सका। फिर कोशिश करें।",

    "account.menu": "खाता",

    "site.description": "वैयक्तिकृत, बहुभाषी ख़बरें।",
    "topics.fallbackTitle": "विषय",

    "desk.tabs.label": "विषय अनुभाग",
    "desk.tabs.latest": "ताज़ा",
    "desk.tabs.perspectives": "दृष्टिकोण",
    "desk.overview.heading": "विषय अवलोकन",
    "desk.related.heading": "संबंधित विषय",
    "desk.timeline.empty": "इस विषय के लिए अभी कोई समयरेखा नहीं है।",
    "desk.coverage.sources.one": "{count} स्रोत",
    "desk.coverage.sources.other": "{count} स्रोत",
    "desk.coverage.languages.one": "{count} भाषा",
    "desk.coverage.languages.other": "{count} भाषाएँ",
    "coverage.sources.one": "{count} स्रोत",
    "coverage.sources.other": "{count} स्रोत",
    "coverage.countries.one": "{count} देश",
    "coverage.countries.other": "{count} देश",
    "coverage.languages.one": "{count} भाषा",
    "coverage.languages.other": "{count} भाषाएँ",
    "desk.keyDevelopments.empty": "अभी कोई बड़ा घटनाक्रम नहीं है।",
    "desk.perspectives.empty":
      "इस विषय के लिए दृष्टिकोण दिखाने के लिए अभी पर्याप्त पहचाने गए स्रोतों की कवरेज नहीं है।",
    "desk.perspectives.sourceCount": "{count} स्रोत",
    "desk.perspectives.role.industry": "उद्योग प्रेस",
    "desk.perspectives.role.government": "सरकारी स्रोत",
    "desk.perspectives.role.academic": "शैक्षणिक स्रोत",
    "desk.perspectives.role.investor": "निवेशक प्रेस",
    "desk.perspectives.role.consumer": "उपभोक्ता प्रेस",
    "desk.perspectives.role.public": "सार्वजनिक स्रोत",
    "desk.tabs.understand": "समझें",
    "desk.understand.heading": "{topic} को समझें",
    "desk.understand.happening": "क्या हो रहा है",
    "desk.understand.happening.note": "वे घटनाक्रम जिन्हें सबसे ज़्यादा प्रकाशक कवर कर रहे हैं।",
    "desk.understand.happening.fallbackNote":
      "अभी तक किसी ख़बर को एक से ज़्यादा प्रकाशक ने नहीं उठाया है। सबसे ताज़ा रिपोर्टिंग:",
    "desk.understand.saying": "कौन क्या कह रहा है",
    "desk.understand.saying.note": "किस तरह के प्रकाशक इसे कवर कर रहे हैं, और वे कौन हैं।",
    "desk.understand.saying.fallbackNote": "वे प्रकाशक जिन्होंने हाल में इस पर रिपोर्ट किया है।",
    "desk.understand.changing": "क्या बदल रहा है",
    "desk.understand.changing.note": "कवरेज कैसे आगे बढ़ा, सबसे नया पहले।",

    "profile.languageMix.heading": "आप असल में क्या पढ़ते हैं",
    "profile.languageMix.body": "आपके पिछले {count} खोले गए लेखों के आधार पर।",
    "profile.languageMix.empty": "अभी दिखाने को कुछ नहीं — जैसे-जैसे आप पढ़ेंगे, यह भरता जाएगा।",
    "profile.languageMix.count": "{count} पढ़े गए",
    "profile.byLanguage": "भाषा के अनुसार",
    "profile.byTopic": "विषय के अनुसार",

    "card.why.followedTopic": "क्योंकि आप {topic} को फ़ॉलो करते हैं",
    "card.why.trending": "अभी ट्रेंड में",
    "card.why.exploration": "जान-बूझकर कुछ अलग",
    "card.timeline.developing": "{time} से विकसित हो रही है",
    "card.new": "नया",
    "display.heading": "डिस्प्ले",
    "display.intro": "इस डिवाइस पर JustNews कैसा दिखे।",
    "display.theme": "थीम",
    "display.theme.system": "डिवाइस जैसा",
    "display.theme.light": "हल्का",
    "display.theme.dark": "गहरा",
    "display.textSize": "टेक्स्ट का आकार",
    "display.textSize.standard": "सामान्य",
    "display.textSize.large": "बड़ा",
    "display.save": "सहेजें",
    "nav.display": "डिस्प्ले",
    "nav.howItWorks": "यह कैसे काम करता है",
    "how.heading": "JustNews कैसे काम करता है",
    "how.intro": "एक समाचार रीडर जो एक विचार पर बना है: एक ही घटना, जिसे कई भाषाओं में कई न्यूज़रूम रिपोर्ट करते हैं, एक ही ख़बर है।",
    "how.stories.title": "ख़बरें, दोहराव नहीं",
    "how.stories.body": "हर सुर्ख़ी की तुलना पहले आई ख़बरों से की जाती है। जब कई प्रकाशक एक ही घटना की रिपोर्ट करते हैं, तो उनके लेख एक ख़बर में जुड़ जाते हैं - आप उसे एक बार देखते हैं, साथ में यह भी कि कितने प्रकाशक, देश और भाषाएँ उसे कवर कर रहे हैं।",
    "how.languages.title": "भाषाओं के पार",
    "how.languages.body": "यह जोड़ना भाषाओं के पार काम करता है: अंग्रेज़ी, स्पैनिश और हिंदी में रिपोर्ट की गई ख़बर एक ही ख़बर है। जब आपकी पढ़ी जा रही भाषा के अलावा दूसरी भाषाओं में कवरेज हो, तो ख़बर यह बताती है और दिखाती है कहाँ।",
    "how.perspectives.title": "दृष्टिकोण",
    "how.perspectives.body": "दृष्टिकोण कवरेज को इस आधार पर समूहित करते हैं कि उसे किसने प्रकाशित किया - उद्योग प्रेस, सरकारी स्रोत, शैक्षणिक स्रोत और अन्य। यह प्रकाशक के बारे में एक तथ्य है, किसी लेख की राय का अनुमान नहीं, और हर स्रोत एक लिंक है जिसे आप जाँच सकते हैं।",
    "how.aquila.title": "The Aquila Tribune",
    "how.aquila.body": "Aquila एक अख़बार है जो दिन में तीन बार छपता है - सुबह, दोपहर और शाम। हर संस्करण एक बार तैयार होकर तय हो जाता है, इसलिए पुराना संस्करण ठीक वैसा ही पढ़ा जाता है जैसा उस दिन था।",
    "how.ranking.title": "आपकी फ़ीड का क्रम कैसे तय होता है",
    "how.ranking.body": "साइन इन होने पर आपकी फ़ीड देखती है कि ख़बर कितनी ताज़ा है, आप कौन-से विषय फ़ॉलो करते हैं, दूसरे पाठक क्या पढ़ रहे हैं, स्रोत कौन है और आपकी भाषाएँ क्या हैं - और कुछ जगहें आपकी सामान्य रुचियों से बाहर की चीज़ों के लिए रखती है। जहाँ कार्ड बताता है कि वह वहाँ क्यों है, वही असली कारण है।",
    "how.data.title": "हम क्या रखते हैं",
    "how.data.body": "JustNews एक सुर्ख़ी, छोटा अंश, तस्वीर का लिंक, स्रोत और मूल लेख का लिंक रखता है - पूरा लेख कभी नहीं। पढ़ना हमेशा प्रकाशक की अपनी साइट पर होता है। आप कभी भी सेटिंग्स से अपने खाते का डेटा निर्यात या हटा सकते हैं।",
    "shortcuts.heading": "कीबोर्ड शॉर्टकट",
    "shortcuts.next": "अगली ख़बर",
    "shortcuts.previous": "पिछली ख़बर",
    "shortcuts.open": "ख़बर खोलें",
    "shortcuts.save": "सहेजें (साइन इन होने पर)",
    "shortcuts.search": "खोजें",
    "shortcuts.help": "यह सूची दिखाएँ",
    "shortcuts.close": "बंद करें",
    "login.reset.link": "पासवर्ड भूल गए?",
    "login.reset.heading": "पासवर्ड रीसेट करें",
    "login.reset.intro": "हम आपको नया पासवर्ड चुनने का लिंक ईमेल करेंगे।",
    "login.reset.submit": "रीसेट लिंक भेजें",
    "login.reset.sent": "अगर इस पते से कोई खाता है, तो रीसेट लिंक आ रहा है। अपना इनबॉक्स देखें।",
    "login.reset.back": "साइन इन पर लौटें",
    "login.reset.newHeading": "नया पासवर्ड चुनें",
    "login.reset.newPassword": "नया पासवर्ड",
    "login.reset.save": "पासवर्ड सहेजें",
    "login.reset.done": "आपका पासवर्ड बदल गया है।",
    "story.follow": "यह ख़बर फ़ॉलो करें",
    "story.following": "यह ख़बर फ़ॉलो कर रहे हैं",
    "following.heading": "आपकी फ़ॉलो की हुई ख़बरें",
    "following.note": "पिछली बार खोलने के बाद आई नई रिपोर्ट।",
    "following.new.one": "{count} नई रिपोर्ट",
    "following.new.other": "{count} नई रिपोर्ट",
    "following.upToDate": "कुछ नया नहीं",
    "nav.discover": "डिस्कवर",
    "nav.history": "इतिहास",
    "nav.following": "फ़ॉलो की हुई",
    "following.empty.title": "आप कोई ख़बर फ़ॉलो नहीं कर रहे",
    "following.empty.body": "किसी ख़बर को उसके पेज से फ़ॉलो करें। हर बार लौटने पर वह यहाँ नई रिपोर्टों की गिनती के साथ दिखेगी।",
    "sidebar.label": "मुख्य मेनू",
    "sidebar.collapse": "साइडबार छोटा करें",
    "sidebar.expand": "साइडबार बड़ा करें",
    "sidebar.open": "मेनू खोलें",
    "sidebar.close": "मेनू बंद करें",
    "sidebar.search": "समाचार खोजें",
    "discover.title": "डिस्कवर",
    "discover.tabs": "डिस्कवर दृश्य",
    "discover.tab.forYou": "आपके लिए",
    "discover.tab.top": "शीर्ष",
    "discover.tab.topics": "विषय",
    "discover.forYouIsTop": "जब तक आप कुछ रुचियाँ नहीं चुनते, आपके लिए में प्रमुख ख़बरें दिखती हैं।",
    "discover.chooseInterests": "रुचियाँ चुनें",
    "discover.published": "प्रकाशित {time}",
    "discover.save": "सहेजें",
    "discover.unsave": "सहेजे गए से हटाएँ",
    "discover.signInToSave": "खबरें सहेजने के लिए साइन इन करें",
    "discover.more": "और विकल्प",
    "discover.share": "साझा करें",
    "discover.copied": "लिंक कॉपी हो गया",
    "discover.openOriginal": "{source} पर पढ़ें",
    "discover.allSources": "सभी स्रोत देखें",
    "discover.notInterested": "रुचि नहीं",
    "discover.hidden": "छिपा दिया गया। ऐसी खबरें कम दिखेंगी।",
    "discover.undo": "पूर्ववत करें",
    "discover.loadingMore": "और खबरें लोड हो रही हैं",
    "discover.end": "आप पूरी तरह अपडेट हैं।",
    "discover.error": "खबरें लोड नहीं हो सकीं।",
    "discover.retry": "फिर कोशिश करें",
    "discover.empty": "अभी यहाँ कुछ नहीं है। कोई और विषय आज़माएँ।",
    "discover.actionFailed": "यह नहीं हुआ। फिर कोशिश करें।",
    "rail.label": "आपका डिस्कवर पैनल",
    "rail.customize": "अनुकूलित करें",
    "rail.customize.title": "अपना पैनल अनुकूलित करें",
    "rail.customize.up": "{widget} ऊपर ले जाएँ",
    "rail.customize.down": "{widget} नीचे ले जाएँ",
    "rail.customize.done": "हो गया",
    "interests.title": "इसे अपना बनाएँ",
    "interests.body": "डिस्कवर को अपने हिसाब से बनाने के लिए विषय और रुचियाँ चुनें।",
    "interests.save": "रुचियाँ सहेजें",
    "interests.saving": "सहेजा जा रहा है…",
    "interests.close": "अभी नहीं",
    "interests.failed": "सहेजा नहीं जा सका। फिर कोशिश करें।",
    "weather.title": "मौसम",
    "weather.setCity": "अपने शहर का मौसम दिखाएँ",
    "weather.search": "शहर खोजें",
    "weather.noResults": "कोई जगह नहीं मिली",
    "weather.change": "शहर बदलें",
    "weather.useLocation": "मेरी लोकेशन इस्तेमाल करें",
    "weather.myLocation": "मेरी लोकेशन",
    "weather.highLow": "अधि: {high}° न्यू: {low}°",
    "weather.unit": "°{unit} में दिखाएँ",
    "weather.error": "मौसम अभी उपलब्ध नहीं है।",
    "weather.attribution": "मौसम डेटा: Open-Meteo",
    "weather.code.clear": "साफ़",
    "weather.code.partlyCloudy": "आंशिक बादल",
    "weather.code.cloudy": "बादल",
    "weather.code.fog": "कोहरा",
    "weather.code.drizzle": "बूंदाबांदी",
    "weather.code.rain": "बारिश",
    "weather.code.snow": "बर्फ़",
    "weather.code.showers": "बौछारें",
    "weather.code.thunder": "आंधी-तूफ़ान",
    "markets.title": "बाज़ार का हाल",
    "markets.note": "सूचकांक ट्रैक करने वाले ETF और बिटकॉइन। कीमतें देर से हो सकती हैं।",
    "markets.empty": "बाज़ार का डेटा अभी उपलब्ध नहीं है।",
    "markets.tile": "{label}: {price}, आज {change}",
    "companies.title": "चर्चा में कंपनियाँ",
    "companies.subtitle": "पिछले दिन की खबरों में सबसे ज़्यादा ज़िक्र",
    "companies.stories.one": "आज {count} खबर",
    "companies.stories.other": "आज {count} खबरें",
    "companies.empty": "आज की खबरों में अभी कोई कंपनी खास नहीं है।",
    "discover.sharePage": "साझा करें",
  },
};

/** Placeholders are `{name}`, filled from `vars`. */
function interpolate(template: string, vars?: Record<string, string | number>): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (whole, name: string) =>
    name in vars ? String(vars[name]) : whole,
  );
}

/**
 * Look up a UI string. Falls back to English rather than rendering the key,
 * because a reader seeing an English word has lost less than a reader seeing
 * `nav.explore`, and `tsc` is what stops it happening in the first place.
 */
export function t(
  locale: LocaleCode,
  key: MessageKey,
  vars?: Record<string, string | number>,
): string {
  return interpolate(messages[locale]?.[key] ?? en[key], vars);
}

/**
 * A message whose wording depends on a count.
 *
 * Listed explicitly rather than derived from the key names: every base here
 * must have a `.one` and a `.other` in `en`, which makes them ordinary
 * MessageKeys, which is what forces every other locale to translate them.
 */
type PluralBase =
  | "aquila.moreSections"
  | "article.otherLanguages"
  | "article.otherSources"
  | "coverage.countries"
  | "coverage.languages"
  | "coverage.sources"
  | "companies.stories"
  | "desk.coverage.languages"
  | "desk.coverage.sources"
  | "search.moreReports"
  | "search.resultCount"
  | "source.articleCount"
  | "following.new"
  | "stats.articles"
  | "stats.sources"
  | "stats.stories"
  | "story.reports";

const pluralRules = new Map<LocaleCode, Intl.PluralRules>();

/**
 * Plural-aware lookup. `count` is passed to the template as `{count}`.
 *
 * Intl decides the category rather than a `count === 1` check, because that
 * check is an assumption about English that happens to survive Spanish and
 * Hindi and will not survive Arabic - which the roadmap plans to add, and
 * which has six. Categories we do not carry a string for fall back to
 * `other`, so adding a locale is a translation job, not a code change.
 */
export function tPlural(
  locale: LocaleCode,
  base: PluralBase,
  count: number,
  vars?: Record<string, string | number>,
): string {
  let rules = pluralRules.get(locale);
  if (!rules) {
    rules = new Intl.PluralRules(locale);
    pluralRules.set(locale, rules);
  }
  const category = rules.select(count);
  const table = messages[locale] ?? en;
  // The cast is the one place the key set is assembled at runtime; `base` is
  // constrained above and `.other` is guaranteed to exist for each of them.
  const exact = table[`${base}.${category}` as MessageKey];
  const template = exact ?? table[`${base}.other` as MessageKey];
  return interpolate(template, { count, ...vars });
}

/**
 * "5 sources · 2 languages", with both halves pluralised.
 *
 * It was one template with two numbers substituted into it, which produced
 * "1 languages" wherever a story had only been reported in one - and it now
 * appears in four places rather than one, so the seam shows. Two plural
 * lookups joined here is the smallest honest fix: a single template cannot
 * carry two independent plural categories in any language.
 */
export function formatCoverage(
  locale: LocaleCode,
  sources: number,
  languages: number,
): string {
  return [
    tPlural(locale, "desk.coverage.sources", sources),
    tPlural(locale, "desk.coverage.languages", languages),
  ].join(" · ");
}

/**
 * Audit §21's diversity line - "7 sources / 4 countries / 2 languages" - for
 * an article's own story-cluster coverage. Countries is omitted entirely
 * rather than printed as "0 countries" when no source in the cluster has a
 * recorded country: a real zero and an unknown value are different facts,
 * and this line only ever states the first one.
 */
export function formatArticleCoverage(
  locale: LocaleCode,
  coverage: { sources: number; countries: number; languages: number },
): string {
  const parts = [tPlural(locale, "coverage.sources", coverage.sources)];
  if (coverage.countries > 0) {
    parts.push(tPlural(locale, "coverage.countries", coverage.countries));
  }
  parts.push(tPlural(locale, "coverage.languages", coverage.languages));
  return parts.join(" · ");
}

/** Locale-aware absolute time, e.g. "September 6, 2026 at 2:45 PM" - the
 * exact instant a reader reaches for once "yesterday" isn't precise enough
 * (Home's lead expansion, audit §35). */
export function formatAbsoluteTime(iso: string, locale: LocaleCode): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: "long", timeStyle: "short" }).format(
    new Date(iso),
  );
}

/** Locale-aware relative time, e.g. "3 hours ago" / "منذ ٣ ساعات". */
export function formatRelativeTime(iso: string, locale: LocaleCode): string {
  const seconds = Math.round((Date.parse(iso) - Date.now()) / 1000);
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 31_536_000],
    ["month", 2_592_000],
    ["day", 86_400],
    ["hour", 3_600],
    ["minute", 60],
  ];
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) return formatter.format(Math.round(seconds / size), unit);
  }
  return formatter.format(Math.round(seconds), "second");
}
