/* eslint-disable no-restricted-globals */
const CACHE_NAME = "smileguard-cache-v1";
const APP_SHELL = ["/", "/index.html", "/manifest.json", "/Gom.ico"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
        )
      )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // GET 요청만 다루고, 백엔드 API(/api/, /analyze)는 항상 네트워크에서 최신으로 받아옴
  if (request.method !== "GET" || request.url.includes("/api/") || request.url.includes("/analyze")) {
    return;
  }

  // 정적 자산: 캐시 우선, 없으면 네트워크에서 받아와 캐시에 저장 (앱 셸 오프라인/설치 지원용)
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request)
        .then((response) => {
          if (response && response.status === 200 && response.type === "basic") {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, responseClone));
          }
          return response;
        })
        .catch(() => cached);
    })
  );
});
