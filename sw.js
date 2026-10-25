// Guarda la interfaz para que abra sin conexión, pero SIEMPRE pide la versión
// más reciente a la red (sin caché HTTP), así los cambios llegan al momento.
// Los audios NO pasan por aquí: Safari necesita servirlos por rangos
// y eso solo funciona bien directamente desde la red/caché HTTP.
const CACHE = "lluvia-v7";
const APP = [
  "./",
  "index.html",
  "manifest.json",
  "iconos/apple-touch-icon.png",
  "iconos/icon-192.png",
  "iconos/icon-512.png"
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => c.addAll(APP.map((u) => new Request(u, { cache: "no-store" }))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.includes("/sonidos/")) return; // audio: directo a la red

  // Red primero y sin caché HTTP; la copia guardada solo se usa sin conexión
  e.respondWith(
    fetch(e.request, { cache: "no-store" })
      .then((res) => {
        if (res.ok) {
          const copia = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copia));
        }
        return res;
      })
      .catch(() => caches.match(e.request).then((r) => r || caches.match("./")))
  );
});
