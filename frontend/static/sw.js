// LibreFolio Service Worker — offline fallback only (no app caching)
const CACHE_NAME = 'offline-v1';
const OFFLINE_ASSETS = ['/offline.html', '/icons/icon-192.png'];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(OFFLINE_ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    if (event.request.mode !== 'navigate') return;
    event.respondWith(
        fetch(event.request).catch(() => caches.match('/offline.html'))
    );
});
