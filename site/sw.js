// Service worker: offline app shell, fresh content when online, cached Pyodide.
const SHELL_CACHE = "shell-v1";
const CONTENT_CACHE = "content-v1";
const PYODIDE_CACHE = "pyodide-v1";
const SHELL = [
  "./",
  "index.html",
  "manifest.webmanifest",
  "app/main.js",
  "app/views.js",
  "app/exercises.js",
  "app/checkers.js",
  "app/store.js",
  "app/ui.js",
  "app/config.js",
  "app/pyrunner.js",
  "app/pyworker.js",
  "app/styles.css",
  "app/highlight.css",
  "icons/icon-192.png",
  "icons/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  const keep = new Set([SHELL_CACHE, CONTENT_CACHE, PYODIDE_CACHE]);
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(names.filter((n) => !keep.has(n)).map((n) => caches.delete(n))))
      .then(() => self.clients.claim()),
  );
});

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch {
    const cached = await cache.match(request, { ignoreSearch: true });
    if (cached) return cached;
    throw new Error("offline and not cached");
  }
}

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) cache.put(request, response.clone());
  return response;
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request, { ignoreSearch: true });
  const update = fetch(request)
    .then((response) => {
      if (response.ok) cache.put(request, response.clone());
      return response;
    })
    .catch(() => cached);
  return cached ?? update;
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.hostname === "cdn.jsdelivr.net" && url.pathname.startsWith("/pyodide/")) {
    event.respondWith(cacheFirst(request, PYODIDE_CACHE));
    return;
  }
  if (url.origin !== self.location.origin) return;
  const path = url.pathname;
  if (path.includes("/content/") || path.includes("/downloads/") || path.includes("/py/")) {
    event.respondWith(networkFirst(request, CONTENT_CACHE));
    return;
  }
  event.respondWith(staleWhileRevalidate(request, SHELL_CACHE));
});
