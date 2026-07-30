# SmileGuard 백엔드/로그인 설정

프로젝트 루트에서 `.env.example`을 복사해 `.env`를 만들고 발급받은 공개 키를 입력합니다.

로그인/YOLO 분석/이력 조회는 전부 `pc_setup/backend`의 FastAPI 서버(포트 8000) 하나로 통합되어 있습니다. 실행 방법은 [pc_setup/README.md](pc_setup/README.md) 참고.

- 이메일 로그인: `POST /api/auth/email` — 계정이 없으면 최초 로그인 시 자동 가입되는 데모용 방식 (SQLite에 저장)
- Google / Kakao 로그인: `POST /api/auth/google`, `POST /api/auth/kakao` — 아직 실제 토큰 검증은 미구현 상태로, 실제 Client Secret / REST API 키가 준비되면 이어서 구현 예정 (현재는 501 응답)

로그인 응답은 `{ "accessToken": "...", "user": { "name": "...", "email": "...", "picture": "..." } }` 형식을 사용합니다. REST API 키와 Client Secret은 React 환경변수에 넣지 않고 FastAPI 서버에서만 관리합니다.
