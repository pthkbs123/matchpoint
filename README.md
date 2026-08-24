# SmileGuard 백엔드/로그인 설정

프로젝트 루트에서 `.env.example`을 복사해 `.env`를 만들고 발급받은 공개 키를 입력합니다.

로그인/YOLO 분석/이력 조회는 전부 `pc_setup/backend`의 FastAPI 서버(포트 8000) 하나로 통합되어 있습니다. 실행 방법은 [pc_setup/README.md](pc_setup/README.md) 참고.

- 이메일 로그인: `POST /api/auth/email` — 계정이 없으면 최초 로그인 시 자동 가입되는 데모용 방식 (SQLite에 저장)
- Google / Kakao 로그인: `POST /api/auth/google`, `POST /api/auth/kakao` — 아직 실제 토큰 검증은 미구현 상태로, 실제 Client Secret / REST API 키가 준비되면 이어서 구현 예정 (현재는 501 응답)

로그인 응답은 `{ "accessToken": "...", "user": { "name": "...", "email": "...", "picture": "..." } }` 형식을 사용합니다. REST API 키와 Client Secret은 React 환경변수에 넣지 않고 FastAPI 서버에서만 관리합니다.

## 공모전 운영 구성

SmileGuard 공모전 버전은 별도의 클라우드 서버 없이 로컬 서버와 ngrok을 사용합니다.

```text
모바일·PC 브라우저
        ↓ HTTPS
      ngrok
        ↓
React 앱 + FastAPI 분석 서버 + SQLite
        ↓
YOLOv8 · OpenCV · 촬영 이미지 저장
```

- 외부 HTTPS 접속은 ngrok 개발 도메인을 사용합니다.
- 사용자·자녀·분석 기록은 로컬 FastAPI 서버의 SQLite에 저장합니다.
- 촬영 이미지도 `pc_setup/backend/uploads`에 로컬 저장합니다.
- 발표 중에는 React, FastAPI, ngrok 프로세스와 발표용 PC가 계속 실행되어야 합니다.
- 상시 서비스가 필요해지는 시점에만 클라우드 배포를 다시 검토합니다.
