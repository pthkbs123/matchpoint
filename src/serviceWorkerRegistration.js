// CRA 공식 서비스 워커 등록 패턴을 단순화한 버전.
// 프로덕션 빌드에서만 등록하고, localhost에서는 등록하지 않음 (개발 중 캐시 혼선 방지).

export function register() {
  if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) {
    return;
  }

  window.addEventListener("load", () => {
    const swUrl = `${process.env.PUBLIC_URL}/service-worker.js`;
    navigator.serviceWorker.register(swUrl).catch((error) => {
      console.error("서비스 워커 등록 실패:", error);
    });
  });
}

export function unregister() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.ready.then((registration) => {
      registration.unregister();
    });
  }
}
