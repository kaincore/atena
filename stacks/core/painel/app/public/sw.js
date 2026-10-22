// Service worker: guarda a casca do app e abre com ela na hora, mesmo sem conexão.
// A API nunca vai para o cache: o estado do servidor tem que ser sempre o de agora.
// O servidor do painel (servidor.ts) troca as duas linhas abaixo ao servir: a versão é um resumo de
// todos os arquivos da interface, então qualquer mudança neles instala um cache novo, inteiro.
const VERSAO = "dev";
const CASCA = ["/"];
const CACHE = `atena-painel-${VERSAO}`;

self.addEventListener("install", (evento) => {
  // cache: "reload" pula o cache HTTP: a casca nova vem toda do servidor, nunca meio a meio
  evento.waitUntil(caches.open(CACHE)
    .then((c) => c.addAll(CASCA.map((caminho) => new Request(caminho, { cache: "reload" }))))
    .then(() => self.skipWaiting()));
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches.keys()
      .then((nomes) => Promise.all(nomes.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim()),
  );
});

// cache primeiro: a casca é a desta versão e só muda quando o sw.js muda (o app recarrega sozinho)
self.addEventListener("fetch", (evento) => {
  const url = new URL(evento.request.url);
  if (evento.request.method !== "GET" || url.origin !== location.origin || url.pathname.startsWith("/api/")) return;
  evento.respondWith(
    caches.open(CACHE)
      .then((c) => c.match(evento.request.mode === "navigate" ? "/" : evento.request))
      .then((guardada) => guardada ?? fetch(evento.request))
      .catch(() => caches.match("/")),
  );
});
