// Service worker: fresh files whenever the network answers, the cached copy when it does not.
// Every app file is network-first, revalidated past the browser's HTTP cache, so a deploy shows
// on the next launch. A slow network falls back to the cache after NETWORK_WAIT_MS.
const SHELL_CACHE = "shell-v7";
const CONTENT_CACHE = "content-v1";
const PYODIDE_CACHE = "pyodide-v1";
const NETWORK_WAIT_MS = 4000;
const SHELL = [
  "./",
  "index.html",
  "manifest.webmanifest",
  "app/main.js",
  "app/views.js",
  "app/pathways.js",
  "app/interview.js",
  "app/interview-view.js",
  "app/placement.js",
  "app/placement-view.js",
  "app/notes.js",
  "app/month-view.js",
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
  // cache: "reload" skips the HTTP cache, so a new worker never stores files from the last deploy.
  const requests = SHELL.map((url) => new Request(url, { cache: "reload" }));
  event.waitUntil(caches.open(SHELL_CACHE).then((cache) => cache.addAll(requests)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  const keep = new Set([SHELL_CACHE, CONTENT_CACHE, PYODIDE_CACHE]);
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(names.filter((n) => !keep.has(n)).map((n) => caches.delete(n))))
      .then(() => self.clients.claim()),
  );
});

// Asks the server (no-cache revalidates with the ETag, so an unchanged file costs a 304),
// stores the answer, and falls back to the cache when offline or slow.
function networkFirst(event, cacheName) {
  const { request } = event;
  const network = fetch(request.url, { cache: "no-cache", credentials: "same-origin" }).then((response) => {
    if (response.ok) {
      const copy = response.clone();
      event.waitUntil(caches.open(cacheName).then((cache) => cache.put(request, copy)));
    }
    return response;
  });
  event.waitUntil(network.then(() => undefined, () => undefined));
  return caches.open(cacheName)
    .then((cache) => cache.match(request, { ignoreSearch: true }))
    .then((cached) => {
      if (!cached) return network;
      const slow = new Promise((resolve) => setTimeout(() => resolve(cached), NETWORK_WAIT_MS));
      return Promise.race([network.catch(() => cached), slow]);
    });
}

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) cache.put(request, response.clone());
  return response;
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
  const content = path.includes("/content/") || path.includes("/downloads/") || path.includes("/py/");
  event.respondWith(networkFirst(event, content ? CONTENT_CACHE : SHELL_CACHE));
});
