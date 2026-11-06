// Service worker: app shell works offline; data is fetched fresh when online.
const VERSION = "v1";
const SHELL = `shell-${VERSION}`, DATA = `data-${VERSION}`, IMG = `img-${VERSION}`;
const SHELL_FILES = ["./", "index.html", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(SHELL_FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => ![SHELL, DATA, IMG].includes(k)).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

// Try the network first (so new deploys and new trades show up), fall back to cache offline.
async function networkFirst(req, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const res = await fetch(req);
    if (res.ok) cache.put(req, res.clone());
    return res;
  } catch (err) {
    return (await cache.match(req)) || Response.error();
  }
}

// Serve cached images instantly and refresh them in the background.
async function staleWhileRevalidate(req, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(req);
  const fresh = fetch(req).then(res => { if (res.ok || res.type === "opaque") cache.put(req, res.clone()); return res; }).catch(() => cached);
  return cached || fresh;
}

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin === location.origin) {
    if (url.pathname.endsWith("history.json")) return e.respondWith(networkFirst(req, DATA));
    if (req.mode === "navigate" || url.pathname.endsWith(".html")) return e.respondWith(networkFirst(req, SHELL));
    return e.respondWith(caches.match(req).then(hit => hit || networkFirst(req, SHELL)));
  }
  if (url.hostname.endsWith("sleepercdn.com")) e.respondWith(staleWhileRevalidate(req, IMG));
});
