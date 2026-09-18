// Service worker do PWA — só cuida do "shell" da aplicação (HTML/CSS/JS/ícones)
// para abrir rápido e sobreviver a uma rede instável. Nunca guarda respostas
// de /api/: dado clínico (fila, agenda, prontuário) tem que vir sempre da rede.
const CACHE = "vida-clinica-v1";
const APP_SHELL = [
  "/",
  "/portal",
  "/manifest.json",
  "/portal-manifest.json",
  "/assets/styles.css",
  "/assets/js/core.js",
  "/assets/js/prontuario.js",
  "/assets/js/gestao.js",
  "/assets/js/expansao.js",
  "/assets/js/boot.js",
  "/assets/js/portal.js",
  "/assets/icons/icon-192.png",
  "/assets/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((chaves) => Promise.all(chaves.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.pathname.startsWith("/api/")) return; // dado clínico: sempre rede, nunca cache

  // shell da aplicação: tenta a rede primeiro (conteúdo sempre atualizado
  // quando há conexão) e cai no cache só se a rede falhar (offline/instável).
  event.respondWith(
    fetch(request)
      .then((resp) => {
        const copia = resp.clone();
        caches.open(CACHE).then((cache) => cache.put(request, copia));
        return resp;
      })
      .catch(() => caches.match(request).then((achado) => achado || caches.match("/")))
  );
});
