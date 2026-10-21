// Service worker: guarda a casca do app para ele abrir mesmo sem conexão (e avisar).
// A API nunca vai para o cache: o estado do servidor tem que ser sempre o de agora.
const CACHE = "atena-painel-v3";
const CASCA = ["/", "/app.js", "/comum.js", "/zonas.js", "/pictos.js", "/visor.js", "/paleta.js", "/estilo.css",
  "/fontes/archivo.woff2", "/fontes/martian-mono.woff2", "/manifest.webmanifest", "/icone.svg", "/icone-192.png",
  "/icone-512.png",
  // uma tela por arquivo
  "/telas/agenda.js", "/telas/ajustes.js", "/telas/aprovacoes.js", "/telas/arquivos.js", "/telas/atividade.js",
  "/telas/historico.js", "/telas/inicio.js", "/telas/lab.js", "/telas/pc.js", "/telas/servicos.js", "/telas/sistema.js"];

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
