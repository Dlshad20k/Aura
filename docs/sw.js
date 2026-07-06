/* Aura Vision Service Worker – App-Shell offline verfügbar machen */
const CACHE = 'aura-vision-v2';
const SHELL = ['./', './index.html', './app.js', './labels.js', './manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ).then(()=>self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const url = e.request.url;
  // KI-Modell & CDN nicht cachen erzwingen – Netzwerk zuerst, dann Cache
  if (url.includes('tfjs') || url.includes('tensorflow') || url.includes('storage.googleapis')) return;
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request).then(resp => {
      if (e.request.method === 'GET' && resp.ok && url.startsWith(self.location.origin)){
        const copy = resp.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
      }
      return resp;
    }).catch(()=>r))
  );
});
