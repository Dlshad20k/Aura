const CACHE_NAME = 'myspotify-v1';
const ASSETS = [
  '/',
  '/manifest.json',
  'https://upload.wikimedia.org/wikipedia/commons/1/19/Spotify_logo_without_text.svg'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS))
  );
});

self.addEventListener('fetch', event => {
  if (event.request.url.includes('/stream/')) return; // Don't cache music streams
  event.respondWith(
    caches.match(event.request).then(response => response || fetch(event.request))
  );
});
