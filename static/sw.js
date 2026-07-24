// Bump esse número sempre que mudar algo em /static -- isso força os navegadores
// que já instalaram o service worker a descartar o cache antigo (ver "activate" abaixo).
const CACHE_NAME = "termeeple-v2";

// Só os arquivos estáticos entram no cache-first: CSS/JS não mudam de um dia pro
// outro. A página "/" (e outros modos) e as chamadas de API NÃO podem ser
// cache-first -- elas mudam todo dia (palavra/tamanho/tentativas), e servir a
// versão cacheada indefinidamente era o motivo da palavra "não trocar à meia-noite"
// pra quem já tinha aberto o app antes.
const STATIC_ASSETS = ["/static/style.css", "/static/game.js", "/static/stats.js"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  if (!url.pathname.startsWith("/static/")) {
    // Rede primeiro; cache só como fallback pra funcionar offline.
    event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => {
      return cached || fetch(event.request);
    })
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.filter((name) => name !== CACHE_NAME).map((name) => caches.delete(name))
        );
      })
      .then(() => self.clients.claim())
  );
});
