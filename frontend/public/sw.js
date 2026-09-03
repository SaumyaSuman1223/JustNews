// Deliberately narrow. This exists for one thing: the saved-articles page
// still rendering when a reader opens it offline. It does not try to be a
// general offline cache - see docs/decisions (Stage 3's PWA requirement) for
// what "offline-readable saved articles" is actually scoped to.
//
// No build-time precache list: Next's static asset filenames are
// content-hashed and change on every deploy, so a hand-maintained precache
// manifest would go stale the moment it shipped. Everything here is
// runtime, cache-as-you-go instead.

const CACHE_NAME = "justnews-v1";
const SAVED_PAGE_PATTERN = /^\/[a-z]{2}\/saved\/?$/;

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === "navigate" && SAVED_PAGE_PATTERN.test(url.pathname)) {
    event.respondWith(networkFirst(request));
    return;
  }

  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(cacheFirst(request));
  }
});

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) return cached;
    throw error;
  }
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) {
    const cache = await caches.open(CACHE_NAME);
    cache.put(request, response.clone());
  }
  return response;
}
