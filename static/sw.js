// Bump esse número sempre que mudar algo em /static -- isso força os navegadores
// que já instalaram o service worker a descartar o cache antigo (ver "activate"
// abaixo). A estratégia stale-while-revalidate abaixo reduz a necessidade de
// lembrar disso pra próxima vez, mas o bump continua sendo o jeito garantido de
// forçar a atualização imediata pra quem já tem uma versão antiga instalada.
const CACHE_NAME = "termeeple-v4";

// Só os arquivos estáticos entram em cache (offline/velocidade): CSS/JS não mudam
// de um dia pro outro. A página "/" (e outros modos) e as chamadas de API NÃO
// podem ser cacheadas -- elas mudam todo dia (palavra/tamanho/tentativas), e
// servir a versão cacheada indefinidamente era o motivo da palavra "não trocar
// à meia-noite" pra quem já tinha aberto o app antes.
const STATIC_ASSETS = [
  "/static/style.css",
  "/static/game.js",
  "/static/stats.js",
  "/static/legacy.js",
];

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

  // stale-while-revalidate: responde com o cache na hora (rápido, funciona
  // offline), mas sempre busca uma versão nova em paralelo e atualiza o cache
  // pra próxima vez -- assim uma mudança em /static se propaga sozinha depois
  // de uma recarga, sem depender de lembrar de subir o CACHE_NAME toda vez que
  // um desses arquivos mudar (foi exatamente isso que causou o game.js ficar
  // preso numa versão antiga pra quem já tinha visitado antes).
  event.respondWith(
    caches.open(CACHE_NAME).then((cache) =>
      cache.match(event.request).then((cached) => {
        const buscaFresca = fetch(event.request)
          .then((resposta) => {
            cache.put(event.request, resposta.clone());
            return resposta;
          })
          .catch(() => cached);
        // Sem isso, o navegador pode encerrar o service worker assim que a
        // resposta cacheada for entregue, cancelando a atualização em segundo
        // plano antes dela terminar -- waitUntil mantém o worker vivo até ela
        // completar, mesmo já tendo respondido com o conteúdo antigo.
        event.waitUntil(buscaFresca);
        return cached || buscaFresca;
      })
    )
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
