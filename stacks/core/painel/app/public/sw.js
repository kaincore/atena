// Service worker: guarda a casca do app para ele abrir mesmo sem conexão (e avisar).
// A API nunca vai para o cache: o estado do servidor tem que ser sempre o de agora.
const CACHE = "atena-painel-v1";
const CASCA = ["/", "/app.js", "/estilo.css", "/manifest.webmanifest", "/icone.svg", "/icone-192.png", "/icone-512.png"];

self.addEventListener("install", (evento) => {
  evento.waitUntil(caches.open(CACHE).then((c) => c.addAll(CASCA)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches.keys()
      .then((nomes) => Promise.all(nomes.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim()),
  );
});

// rede primeiro (versão nova sempre que houver conexão); o cache só serve offline
self.addEventListener("fetch", (evento) => {
  const url = new URL(evento.request.url);
  if (evento.request.method !== "GET" || url.origin !== location.origin || url.pathname.startsWith("/api/")) return;
  evento.respondWith(
    fetch(evento.request)
      .then((resposta) => {
        if (resposta.ok && CASCA.includes(url.pathname)) {
          const copia = resposta.clone();
          caches.open(CACHE).then((c) => c.put(evento.request, copia));
        }
        return resposta;
      })
      .catch(() => caches.match(evento.request).then((r) => r ?? caches.match("/"))),
  );
});
