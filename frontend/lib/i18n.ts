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
  "nav.language": "Language",
  "nav.home": "Home",
  "nav.home.subtitle": "What matters right now.",
  "nav.aquila": "Aquila",
  "nav.aquila.subtitle": "The world in context.",
  "nav.desk": "My Desk",
  "nav.desk.subtitle": "Your topics, in depth.",
  "nav.search": "Search",
  "nav.settings": "Settings",
  "nav.explore": "Explore",
  "nav.topics": "Topics",
  "nav.saved": "Saved",
  "nav.privacy": "Privacy",
  "nav.feedback": "Send feedback",

  "search.label": "Search headlines",
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

  "feed.heading": "Feed",
  "feed.degraded.personal":
    "Your feed is unavailable right now, so this page may be out of date. Everything else still works.",
  "feed.degraded.anonymous":
    "Live headlines are unavailable right now, so this page may be out of date. Everything else still works.",
  "feed.empty.title": "No headlines in your languages right now",
  "feed.empty.body":
    "We are still gathering today’s coverage. Explore is the same news without the personalisation, and it is worth a look in the meantime.",
  "feed.empty.action": "Go to Explore",

  "stats.articles": "articles",
  "stats.sources": "sources",
  "stats.languages": "languages",
  "stats.stories": "stories",

  "home.greeting.morning": "Good morning",
  "home.greeting.afternoon": "Good afternoon",
  "home.greeting.evening": "Good evening",
  "home.greeting.subtitle": "Here’s what matters today.",
  "home.glance.heading": "Today at a glance",
  "home.brief.heading": "The Daily Brief",
  "home.brief.cta": "Read today’s issue",
  "home.tabs.label": "Feed",
  "home.tabs.forYou": "For You",
  "home.tabs.trending": "Trending",
  "home.tabs.history": "Continue Reading",
  "home.tabs.saved": "Saved",

  "aquila.title": "The Aquila Tribune",
  "aquila.standfirst": "News · Ideas · People · Perspectives",
  "aquila.strap": "A clearer tomorrow, together",
  "aquila.volume": "Vol. {volume}  No. {number}",
  "aquila.edition.morning": "Morning Edition",
  "aquila.edition.midday": "Midday Edition",
  "aquila.edition.evening": "Evening Edition",
  "aquila.editions": "Today’s editions",
  "aquila.pages": "Pages",
  "aquila.frontPage": "Front page",
  "aquila.brief": "The brief",
  "aquila.footer": "Curated news for a more informed world",
  "aquila.sign": "Read deeper. See further.",
  "aquila.contents": "Contents",
  "aquila.pagination": "Pages",
  "aquila.previous": "Previous page",
  "aquila.next": "Next page",
  "aquila.pageOf": "{page} / {total}",
  "aquila.pageLabel": "Page {page}",
  "aquila.pageEmpty": "Nothing was set on this page.",
  "aquila.pageFailed": "That page would not load. Try again.",
  "aquila.backHome": "Back to the front page",
  "aquila.none.title": "No edition has been published yet",
  "aquila.none.body":
    "The Tribune is composed three times a day, at 6am, 2pm and 10pm. The next edition will appear here.",
  "aquila.none.action": "Go to Home",
  "explore.heading": "Aquila",
  "explore.intro":
    "The world in context — the latest across every source we follow, spread across topics and the same for every reader, whether or not you are signed in.",
  "explore.standfirst": "The Aquila Tribune",
  "explore.degraded": "Live headlines are unavailable right now, so this page may be out of date.",
  "explore.editions": "Editions",
  "explore.empty.title": "Nothing to explore in your languages yet",
  "explore.empty.body":
    "No sources we follow have published in these languages recently. Changing your languages in Settings will show you what is running elsewhere.",
  "explore.empty.action": "Browse topics",

  "trending.heading": "Most read",

  "blindspot.heading": "Not covered in your languages",
  "blindspot.note":
    "Being reported elsewhere right now, by outlets writing in a language you have not selected.",

  "coverage.label": "Languages covering this story",

  "article.notFound": "Not found",
  "article.readFull": "Read the full story at {source}",
  "article.otherLanguages.one": "Also covered in another language",
  "article.otherLanguages.other": "Also covered in {count} other languages",
  "article.otherSources.one": "Also reported by 1 other source",
  "article.otherSources.other": "Also reported by {count} other sources",
  "article.seeFullCoverage": "See full coverage",
  "article.backToFront": "Back to the front page",

  "story.coveredBy.one": "Covered by {count} source.",
  "story.coveredBy.other": "Covered by {count} sources.",
  "story.reportedIn": "Reported in {count} languages.",
  "story.reports.one": "{count} report",
  "story.reports.other": "{count} reports",
  "story.firstReported": "First reported {time}",
  "story.lastUpdated": "Last updated {time}",
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

  "topics.heading": "Topics",
  "topics.intro": "Browse headlines by subject, using the IPTC Media Topics taxonomy.",
  "topics.degraded": "Topics are unavailable right now.",
  "topics.allTopics": "All topics",
  "topics.empty.title": "Nothing tagged {topic} yet",
  "topics.empty.body":
    "Coverage of this topic in your languages is still thin. It fills in as sources publish through the day.",

  "search.heading": "Search",
  "search.titleWithQuery": "Search: {query}",
  "search.intro": "Full text search over headlines and summaries in your languages.",
  "search.degraded": "Search is unavailable right now.",
  "search.browseInstead": "Browse by topic instead",
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
  "site.tagline": "A clearer tomorrow",
  "site.sign": "Same world. More clarity.",
  "topics.fallbackTitle": "Topic",

  "desk.empty.title": "Your desk is empty",
  "desk.empty.body": "Choose a few topics to follow, and they’ll show up here.",
  "desk.addTopic": "+ Add Topic",
  "desk.addTopic.done": "Done",
  "desk.moveUp": "Move up",
  "desk.moveDown": "Move down",
  "desk.remove": "Remove",
  "desk.actionFailed": "That didn’t go through. Try again.",
  "desk.tabs.label": "Topic sections",
  "desk.tabs.latest": "Latest",
  "desk.tabs.timeline": "Timeline",
  "desk.tabs.keyDevelopments": "Key Developments",
  "desk.tabs.perspectives": "Perspectives",
  "desk.tabs.analysis": "Analysis",
  "desk.overview.heading": "Topic overview",
  "desk.related.heading": "Related topics",
  "desk.timeline.empty": "No story timeline yet for this topic.",
  "desk.timeline.coverage": "{sources} sources · {languages} languages",
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
  "desk.stub.analysis.title": "Analysis — coming soon",
  "desk.stub.analysis.body": "Deeper context and trend analysis for this topic.",

  "profile.languageMix.heading": "What you actually read",
  "profile.languageMix.body": "Based on your last {count} articles opened.",
  "profile.languageMix.empty": "Nothing to show yet — this fills in as you read.",
  "profile.languageMix.count": "{count} read",
  "profile.byLanguage": "By language",
  "profile.byTopic": "By topic",

  "card.why.followedTopic": "Because you follow {topic}",
  "card.why.followedSource": "Because you follow {source}",
  "card.why.trending": "Trending now",
  "card.why.exploration": "Something different, on purpose",
} as const;

export type MessageKey = keyof typeof en;

const messages: Record<LocaleCode, Record<MessageKey, string>> = {
  en,
  es: {
    "skip.toContent": "Saltar al contenido",

    "nav.primary": "Principal",
    "nav.language": "Idioma",
    "nav.home": "Inicio",
    "nav.home.subtitle": "Lo que importa ahora mismo.",
    "nav.aquila": "Aquila",
    "nav.aquila.subtitle": "El mundo en contexto.",
    "nav.desk": "Mi Escritorio",
    "nav.desk.subtitle": "Tus temas, a fondo.",
    "nav.search": "Buscar",
    "nav.settings": "Ajustes",
    "nav.explore": "Explorar",
    "nav.topics": "Temas",
    "nav.saved": "Guardados",
    "nav.privacy": "Privacidad",
    "nav.feedback": "Enviar comentarios",

    "search.label": "Buscar titulares",
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

    "feed.heading": "Portada",
    "feed.degraded.personal":
      "Tu feed no está disponible ahora mismo, así que esta página puede estar desactualizada. Todo lo demás sigue funcionando.",
    "feed.degraded.anonymous":
      "Los titulares en directo no están disponibles ahora mismo, así que esta página puede estar desactualizada. Todo lo demás sigue funcionando.",
    "feed.empty.title": "Ahora mismo no hay titulares en tus idiomas",
    "feed.empty.body":
      "Todavía estamos reuniendo la cobertura de hoy. Explorar son las mismas noticias sin la personalización, y merece la pena echarle un vistazo mientras tanto.",
    "feed.empty.action": "Ir a Explorar",

    "stats.articles": "artículos",
    "stats.sources": "fuentes",
    "stats.languages": "idiomas",
    "stats.stories": "historias",

    "home.greeting.morning": "Buenos días",
    "home.greeting.afternoon": "Buenas tardes",
    "home.greeting.evening": "Buenas noches",
    "home.greeting.subtitle": "Esto es lo que importa hoy.",
    "home.glance.heading": "Hoy de un vistazo",
    "home.brief.heading": "El resumen diario",
    "home.brief.cta": "Leer la edición de hoy",
    "home.tabs.label": "Feed",
    "home.tabs.forYou": "Para ti",
    "home.tabs.trending": "Tendencias",
    "home.tabs.history": "Sigue leyendo",
    "home.tabs.saved": "Guardados",

    "aquila.title": "The Aquila Tribune",
    "aquila.standfirst": "Noticias · Ideas · Personas · Perspectivas",
    "aquila.strap": "Un mañana más claro, juntos",
    "aquila.volume": "Vol. {volume}  N.º {number}",
    "aquila.edition.morning": "Edición de la mañana",
    "aquila.edition.midday": "Edición del mediodía",
    "aquila.edition.evening": "Edición de la noche",
    "aquila.editions": "Ediciones de hoy",
    "aquila.pages": "Páginas",
    "aquila.frontPage": "Portada",
    "aquila.brief": "En breve",
    "aquila.footer": "Noticias seleccionadas para un mundo mejor informado",
    "aquila.sign": "Lee más a fondo. Mira más lejos.",
    "aquila.contents": "Índice",
    "aquila.pagination": "Páginas",
    "aquila.previous": "Página anterior",
    "aquila.next": "Página siguiente",
    "aquila.pageOf": "{page} / {total}",
    "aquila.pageLabel": "Página {page}",
    "aquila.pageEmpty": "No se compuso nada en esta página.",
    "aquila.pageFailed": "Esa página no se ha cargado. Inténtalo de nuevo.",
    "aquila.backHome": "Volver a la portada",
    "aquila.none.title": "Aún no se ha publicado ninguna edición",
    "aquila.none.body":
      "El Tribune se compone tres veces al día: a las 6:00, las 14:00 y las 22:00. La próxima edición aparecerá aquí.",
    "aquila.none.action": "Ir a Inicio",
    "explore.heading": "Aquila",
    "explore.intro":
      "El mundo en contexto: lo último de todas las fuentes que seguimos, repartido entre temas e igual para cada lector, hayas iniciado sesión o no.",
    "explore.standfirst": "The Aquila Tribune",
    "explore.degraded":
      "Los titulares en directo no están disponibles ahora mismo, así que esta página puede estar desactualizada.",
    "explore.editions": "Ediciones",
    "explore.empty.title": "Todavía no hay nada que explorar en tus idiomas",
    "explore.empty.body":
      "Ninguna de las fuentes que seguimos ha publicado en estos idiomas recientemente. Si cambias tus idiomas en Ajustes verás lo que está pasando en otros sitios.",
    "explore.empty.action": "Explorar temas",

    "trending.heading": "Lo más leído",

    "blindspot.heading": "Sin cobertura en tus idiomas",
    "blindspot.note":
      "Se está informando de esto ahora mismo, por medios que escriben en un idioma que no has seleccionado.",

    "coverage.label": "Idiomas que cubren esta historia",

    "article.notFound": "No encontrado",
    "article.readFull": "Leer la noticia completa en {source}",
    "article.otherLanguages.one": "También cubierto en otro idioma",
    "article.otherLanguages.other": "También cubierto en otros {count} idiomas",
    "article.otherSources.one": "También informado por 1 fuente más",
    "article.otherSources.other": "También informado por otras {count} fuentes",
    "article.seeFullCoverage": "Ver la cobertura completa",
    "article.backToFront": "Volver a la portada",

    "story.coveredBy.one": "Cubierto por {count} fuente.",
    "story.coveredBy.other": "Cubierto por {count} fuentes.",
    "story.reportedIn": "Informado en {count} idiomas.",
    "story.reports.one": "{count} información",
    "story.reports.other": "{count} informaciones",
    "story.firstReported": "Primer informe {time}",
    "story.lastUpdated": "Última actualización {time}",
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

    "topics.heading": "Temas",
    "topics.intro": "Explora titulares por materia, con la taxonomía IPTC Media Topics.",
    "topics.degraded": "Los temas no están disponibles ahora mismo.",
    "topics.allTopics": "Todos los temas",
    "topics.empty.title": "Todavía no hay nada etiquetado como {topic}",
    "topics.empty.body":
      "La cobertura de este tema en tus idiomas todavía es escasa. Se va llenando a medida que las fuentes publican durante el día.",

    "search.heading": "Buscar",
    "search.titleWithQuery": "Buscar: {query}",
    "search.intro": "Búsqueda de texto completo en titulares y resúmenes en tus idiomas.",
    "search.degraded": "La búsqueda no está disponible ahora mismo.",
    "search.browseInstead": "Explorar por tema en su lugar",
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
    "site.tagline": "Un mañana más claro",
    "site.sign": "El mismo mundo. Más claridad.",
    "topics.fallbackTitle": "Tema",

    "desk.empty.title": "Tu escritorio está vacío",
    "desk.empty.body": "Elige algunos temas para seguir y aparecerán aquí.",
    "desk.addTopic": "+ Añadir tema",
    "desk.addTopic.done": "Listo",
    "desk.moveUp": "Subir",
    "desk.moveDown": "Bajar",
    "desk.remove": "Quitar",
    "desk.actionFailed": "Eso no funcionó. Inténtalo de nuevo.",
    "desk.tabs.label": "Secciones del tema",
    "desk.tabs.latest": "Lo último",
    "desk.tabs.timeline": "Cronología",
    "desk.tabs.keyDevelopments": "Desarrollos clave",
    "desk.tabs.perspectives": "Perspectivas",
    "desk.tabs.analysis": "Análisis",
    "desk.overview.heading": "Resumen del tema",
    "desk.related.heading": "Temas relacionados",
    "desk.timeline.empty": "Todavía no hay cronología para este tema.",
    "desk.timeline.coverage": "{sources} fuentes · {languages} idiomas",
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
    "desk.stub.analysis.title": "Análisis — próximamente",
    "desk.stub.analysis.body": "Contexto más profundo y análisis de tendencias para este tema.",

    "profile.languageMix.heading": "Lo que realmente lees",
    "profile.languageMix.body": "Según tus últimos {count} artículos abiertos.",
    "profile.languageMix.empty": "Todavía no hay nada que mostrar — esto se llena a medida que lees.",
    "profile.languageMix.count": "{count} leídos",
    "profile.byLanguage": "Por idioma",
    "profile.byTopic": "Por tema",

    "card.why.followedTopic": "Porque sigues {topic}",
    "card.why.followedSource": "Porque sigues {source}",
    "card.why.trending": "Tendencia ahora",
    "card.why.exploration": "Algo distinto, a propósito",
  },
  hi: {
    "skip.toContent": "सामग्री पर जाएँ",

    "nav.primary": "मुख्य",
    "nav.language": "भाषा",
    "nav.home": "होम",
    "nav.home.subtitle": "अभी जो मायने रखता है।",
    "nav.aquila": "अक्विला",
    "nav.aquila.subtitle": "दुनिया, सन्दर्भ के साथ।",
    "nav.desk": "मेरा डेस्क",
    "nav.desk.subtitle": "आपके विषय, गहराई से।",
    "nav.search": "खोजें",
    "nav.settings": "सेटिंग्स",
    "nav.explore": "एक्सप्लोर",
    "nav.topics": "विषय",
    "nav.saved": "सहेजे गए",
    "nav.privacy": "निजता",
    "nav.feedback": "प्रतिक्रिया भेजें",

    "search.label": "सुर्ख़ियाँ खोजें",
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

    "feed.heading": "मुख्य पृष्ठ",
    "feed.degraded.personal":
      "आपकी फ़ीड अभी उपलब्ध नहीं है, इसलिए यह पेज पुराना हो सकता है। बाकी सब कुछ काम कर रहा है।",
    "feed.degraded.anonymous":
      "ताज़ा सुर्ख़ियाँ अभी उपलब्ध नहीं हैं, इसलिए यह पेज पुराना हो सकता है। बाकी सब कुछ काम कर रहा है।",
    "feed.empty.title": "अभी आपकी भाषाओं में कोई सुर्ख़ी नहीं है",
    "feed.empty.body":
      "हम आज की कवरेज अब भी जुटा रहे हैं। एक्सप्लोर पर वही ख़बरें बिना वैयक्तिकरण के मिलती हैं, और तब तक देखने लायक है।",
    "feed.empty.action": "एक्सप्लोर पर जाएँ",

    "stats.articles": "लेख",
    "stats.sources": "स्रोत",
    "stats.languages": "भाषाएँ",
    "stats.stories": "कहानियाँ",

    "home.greeting.morning": "सुप्रभात",
    "home.greeting.afternoon": "नमस्कार",
    "home.greeting.evening": "शुभ संध्या",
    "home.greeting.subtitle": "आज जो मायने रखता है।",
    "home.glance.heading": "आज एक नज़र में",
    "home.brief.heading": "दैनिक सार",
    "home.brief.cta": "आज का अंक पढ़ें",
    "home.tabs.label": "फ़ीड",
    "home.tabs.forYou": "आपके लिए",
    "home.tabs.trending": "ट्रेंडिंग",
    "home.tabs.history": "पढ़ना जारी रखें",
    "home.tabs.saved": "सहेजे गए",

    "aquila.title": "The Aquila Tribune",
    "aquila.standfirst": "ख़बरें · विचार · लोग · दृष्टिकोण",
    "aquila.strap": "एक स्पष्ट कल, साथ मिलकर",
    "aquila.volume": "खंड {volume}  अंक {number}",
    "aquila.edition.morning": "प्रातः संस्करण",
    "aquila.edition.midday": "मध्याह्न संस्करण",
    "aquila.edition.evening": "सायं संस्करण",
    "aquila.editions": "आज के संस्करण",
    "aquila.pages": "पृष्ठ",
    "aquila.frontPage": "मुखपृष्ठ",
    "aquila.brief": "संक्षेप में",
    "aquila.footer": "बेहतर जानकारी वाली दुनिया के लिए चुनी हुई ख़बरें",
    "aquila.sign": "गहराई से पढ़ें। दूर तक देखें।",
    "aquila.contents": "अनुक्रम",
    "aquila.pagination": "पृष्ठ",
    "aquila.previous": "पिछला पृष्ठ",
    "aquila.next": "अगला पृष्ठ",
    "aquila.pageOf": "{page} / {total}",
    "aquila.pageLabel": "पृष्ठ {page}",
    "aquila.pageEmpty": "इस पृष्ठ पर कुछ नहीं रखा गया।",
    "aquila.pageFailed": "वह पृष्ठ लोड नहीं हुआ। फिर कोशिश करें।",
    "aquila.backHome": "मुखपृष्ठ पर वापस",
    "aquila.none.title": "अभी कोई संस्करण प्रकाशित नहीं हुआ",
    "aquila.none.body":
      "ट्रिब्यून दिन में तीन बार तैयार होता है — सुबह 6, दोपहर 2 और रात 10 बजे। अगला संस्करण यहाँ दिखेगा।",
    "aquila.none.action": "होम पर जाएँ",
    "explore.heading": "अक्विला",
    "explore.intro":
      "दुनिया, सन्दर्भ के साथ — हमारे स्रोतों की ताज़ा ख़बरें, विषयों में फैलाकर और हर पाठक के लिए एक जैसी, चाहे आप साइन इन हों या नहीं।",
    "explore.standfirst": "The Aquila Tribune",
    "explore.degraded":
      "ताज़ा सुर्ख़ियाँ अभी उपलब्ध नहीं हैं, इसलिए यह पेज पुराना हो सकता है।",
    "explore.editions": "संस्करण",
    "explore.empty.title": "आपकी भाषाओं में एक्सप्लोर करने के लिए अभी कुछ नहीं है",
    "explore.empty.body":
      "हम जिन स्रोतों को फ़ॉलो करते हैं, उनमें से किसी ने हाल में इन भाषाओं में कुछ नहीं छापा। सेटिंग्स में अपनी भाषाएँ बदलकर देखिए और कहाँ क्या चल रहा है।",
    "explore.empty.action": "विषय देखें",

    "trending.heading": "सबसे ज़्यादा पढ़े गए",

    "blindspot.heading": "आपकी भाषाओं में कवर नहीं हुआ",
    "blindspot.note":
      "यह अभी कहीं और छप रहा है, ऐसे संस्थानों में जो उस भाषा में लिखते हैं जो आपने नहीं चुनी।",

    "coverage.label": "इस कहानी को कवर करने वाली भाषाएँ",

    "article.notFound": "नहीं मिला",
    "article.readFull": "पूरी ख़बर {source} पर पढ़ें",
    "article.otherLanguages.one": "एक और भाषा में भी कवर किया गया",
    "article.otherLanguages.other": "{count} और भाषाओं में भी कवर किया गया",
    "article.otherSources.one": "1 और स्रोत ने भी यह ख़बर दी",
    "article.otherSources.other": "{count} और स्रोतों ने भी यह ख़बर दी",
    "article.seeFullCoverage": "पूरी कवरेज देखें",
    "article.backToFront": "मुख्य पृष्ठ पर लौटें",

    "story.coveredBy.one": "{count} स्रोत ने कवर किया।",
    "story.coveredBy.other": "{count} स्रोतों ने कवर किया।",
    "story.reportedIn": "{count} भाषाओं में ख़बर दी गई।",
    "story.reports.one": "{count} रिपोर्ट",
    "story.reports.other": "{count} रिपोर्ट",
    "story.firstReported": "पहली बार रिपोर्ट {time}",
    "story.lastUpdated": "आख़िरी अपडेट {time}",
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

    "topics.heading": "विषय",
    "topics.intro": "IPTC मीडिया टॉपिक्स वर्गीकरण की मदद से विषय के हिसाब से सुर्ख़ियाँ देखें।",
    "topics.degraded": "विषय अभी उपलब्ध नहीं हैं।",
    "topics.allTopics": "सभी विषय",
    "topics.empty.title": "{topic} के साथ अभी कुछ नहीं है",
    "topics.empty.body":
      "आपकी भाषाओं में इस विषय की कवरेज अभी कम है। दिन भर में जैसे-जैसे स्रोत छापेंगे, यह भरता जाएगा।",

    "search.heading": "खोज",
    "search.titleWithQuery": "खोज: {query}",
    "search.intro": "आपकी भाषाओं में सुर्ख़ियों और सारांशों में पूरा-पाठ खोज।",
    "search.degraded": "खोज अभी उपलब्ध नहीं है।",
    "search.browseInstead": "इसके बजाय विषय के हिसाब से देखें",
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
    "site.tagline": "एक स्पष्ट कल",
    "site.sign": "वही दुनिया। ज़्यादा स्पष्टता।",
    "topics.fallbackTitle": "विषय",

    "desk.empty.title": "आपका डेस्क खाली है",
    "desk.empty.body": "कुछ विषय फ़ॉलो करें, वे यहाँ दिखने लगेंगे।",
    "desk.addTopic": "+ विषय जोड़ें",
    "desk.addTopic.done": "हो गया",
    "desk.moveUp": "ऊपर ले जाएँ",
    "desk.moveDown": "नीचे ले जाएँ",
    "desk.remove": "हटाएँ",
    "desk.actionFailed": "यह पूरा नहीं हुआ। फिर कोशिश करें।",
    "desk.tabs.label": "विषय अनुभाग",
    "desk.tabs.latest": "ताज़ा",
    "desk.tabs.timeline": "समयरेखा",
    "desk.tabs.keyDevelopments": "मुख्य घटनाक्रम",
    "desk.tabs.perspectives": "दृष्टिकोण",
    "desk.tabs.analysis": "विश्लेषण",
    "desk.overview.heading": "विषय अवलोकन",
    "desk.related.heading": "संबंधित विषय",
    "desk.timeline.empty": "इस विषय के लिए अभी कोई समयरेखा नहीं है।",
    "desk.timeline.coverage": "{sources} स्रोत · {languages} भाषाएँ",
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
    "desk.stub.analysis.title": "विश्लेषण — जल्द आ रहा है",
    "desk.stub.analysis.body": "इस विषय के लिए गहन संदर्भ और रुझान विश्लेषण।",

    "profile.languageMix.heading": "आप असल में क्या पढ़ते हैं",
    "profile.languageMix.body": "आपके पिछले {count} खोले गए लेखों के आधार पर।",
    "profile.languageMix.empty": "अभी दिखाने को कुछ नहीं — जैसे-जैसे आप पढ़ेंगे, यह भरता जाएगा।",
    "profile.languageMix.count": "{count} पढ़े गए",
    "profile.byLanguage": "भाषा के अनुसार",
    "profile.byTopic": "विषय के अनुसार",

    "card.why.followedTopic": "क्योंकि आप {topic} को फ़ॉलो करते हैं",
    "card.why.followedSource": "क्योंकि आप {source} को फ़ॉलो करते हैं",
    "card.why.trending": "अभी ट्रेंड में",
    "card.why.exploration": "जान-बूझकर कुछ अलग",
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
  | "article.otherLanguages"
  | "article.otherSources"
  | "story.coveredBy"
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
