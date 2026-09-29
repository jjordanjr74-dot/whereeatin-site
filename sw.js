/* Service worker for Where We Eatin' — what makes the site installable and usable on a phone with no signal.
 *
 * Deliberate choices:
 *   - Stripe and Google Fonts are NEVER cached or intercepted. A stale checkout page or a stale price is worse
 *     than no cache at all, and a payment surface must always be live.
 *   - .json is NETWORK-FIRST: the radar's venue data changes during the day, and a cached copy would show a
 *     closed kitchen as open. A food-truck tracker that lies about who is open is worse than one that says
 *     "offline".
 *   - HTML is network-first (so deployments appear immediately) with the cached shell as the offline fallback.
 *   - Static assets are cache-first, because they are content-hashed by name in practice and change rarely.
 */
const VERSION = 'wwe-v1';
const SHELL = [
  '/',
  '/index.html',
  '/assets/site.js',
  '/assets/favicon.svg',
  '/assets/icons/icon-192.png',
  '/assets/icons/icon-512.png',
  '/assets/icons/apple-touch-icon.png',
];

const NEVER_CACHE = [
  'checkout.stripe.com',
  'api.stripe.com',
  'js.stripe.com',
  'fonts.googleapis.com',
  'fonts.gstatic.com',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(VERSION).then((cache) =>
      // Individually, so one 404 cannot fail the whole install.
      Promise.all(SHELL.map((u) => cache.add(u).catch(() => null)))
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

const isStatic = (url) => /\.(?:css|js|png|jpe?g|webp|svg|ico|woff2?)$/i.test(url.pathname);

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;                       // never touch a write

  const url = new URL(req.url);
  if (NEVER_CACHE.some((h) => url.hostname.endsWith(h))) return;   // payments and fonts stay live
  if (url.origin !== self.location.origin) return;                // do not proxy third parties

  const json = /\.json$/i.test(url.pathname);

  if (req.mode === 'navigate' || json) {
    // network-first: freshness matters more than speed for the page and for venue data
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res && res.ok && !json) {
            const copy = res.clone();
            caches.open(VERSION).then((c) => c.put(req, copy)).catch(() => null);
          }
          return res;
        })
        .catch(() => caches.match(req).then((hit) => hit || caches.match('/index.html')))
    );
    return;
  }

  if (isStatic(url)) {
    event.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(VERSION).then((c) => c.put(req, copy)).catch(() => null);
        }
        return res;
      }))
    );
  }
});
