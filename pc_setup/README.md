# MatchPoint - YOLOv8 충치 탐지 로컬 셋업 가이드

## 폴더 구조
```
pc_setup/
├── dataset_yolo_converted.zip   # 변환된 학습 데이터셋
├── requirements.txt
├── train.py                     # 모델 학습 스크립트
└── backend/
    ├── main.py                  # FastAPI 추론 서버
    └── model/                   # 배포용 Run A/Run H 가중치 위치
```

## 1단계. 파이썬 환경 준비
```bash
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```

## 2단계. 데이터셋 압축 풀기
`pc_setup` 폴더 안에서:
```bash
unzip dataset_yolo_converted.zip
```
`dataset_yolo/` 폴더가 생기고, `train.py`와 같은 위치에 있어야 합니다.

## 3단계. 학습 실행
```bash
python train.py
```
- 데이터가 작아서(총 418장) CPU로도 학습 가능하지만 시간이 좀 걸려요. GPU 있으면 `train.py`에서 `device=0` 주석 해제하세요.
- 학습 끝나면 `runs/detect/cavity_train/weights/best.pt` 생성됩니다.
- `runs/detect/cavity_train/` 폴더에 성능 그래프, confusion matrix 등도 같이 생성되니 확인해보세요.

## 4단계. 학습된 모델을 백엔드로 이동
기존 단일 모델을 `legacy` 모드로 사용할 때:

```bash
# Windows
copy runs\detect\cavity_train\weights\best.pt backend\model\best.pt
# Mac/Linux
cp runs/detect/cavity_train/weights/best.pt backend/model/best.pt
```

현재 기본 배포 모드는 cavity Recall을 우선한 Run A+Run H 앙상블입니다.

```text
backend/model/best_runG_A.pt
backend/model/best_runH.pt
```

환경변수 `CAVITY_INFERENCE_MODE`로 실행 모드를 바꿀 수 있습니다.

- `ensemble`(기본): Run A cavity conf 0.10 + Run H cavity conf 0.15, IoU 0.50 NMS, normal은 Run A conf 0.25
- `runH`: Run H 단일 모델
- `legacy`: 기존 `best.pt` 단일 모델(conf 0.25)

필요하면 `backend/.env`에서 각 임계값(`CAVITY_CONF_RUN_A`,
`CAVITY_CONF_RUN_H`, `NORMAL_CONF`, `CAVITY_ENSEMBLE_NMS_IOU`)을 조정할 수 있습니다.

## 5단계. 추론 서버 실행
```bash
cd backend
uvicorn main:app --reload --port 8000
```
- 정상 로드되면 `http://localhost:8000/health` 접속 시 `{"status":"ok","model_loaded":true}` 확인 가능
- 테스트: `http://localhost:8000/docs` 에서 Swagger UI로 이미지 업로드 테스트 가능

### 카카오·Google 로그인 설정

`backend/.env.example`을 `backend/.env`로 복사하고 서버용 키를 입력합니다.

```env
GOOGLE_CLIENT_ID=Google 웹 클라이언트 ID
KAKAO_REST_API_KEY=카카오 REST API 키
KAKAO_CLIENT_SECRET=카카오 클라이언트 시크릿
KAKAO_REDIRECT_URI=http://localhost:3000/
```

Google 클라이언트 ID와 Redirect URI는 프로젝트 루트 `.env` 값도 자동으로 사용합니다.
카카오 JavaScript 키와 REST API 키는 서로 다르므로 `KAKAO_REST_API_KEY`에는 반드시 REST API 키를 입력해야 합니다.

## 6단계. React 프론트와 연동 (다음 단계)
현재 React 앱(`localhost:3000`)의 `CapturePreviewPage` → `AnalyzingPage` 흐름에서
촬영한 이미지를 `http://localhost:8000/analyze` 로 POST 하도록 연결하면 됩니다.
CORS는 이미 `localhost:3000` 허용해뒀어요.

응답 예시:
```json
{
  "image_size": {"width": 640, "height": 480},
  "detections": [
    {"class": "cavity", "confidence": 0.87, "box": {"x1":120,"y1":80,"x2":180,"y2":140}}
  ],
  "summary": {"cavity_count": 1, "normal_count": 3, "total_detections": 4}
}
```

## 참고: 데이터셋 변환 정보
원본 캐글 데이터셋은 DOTA 형식 라벨(`labelTxt`, 4개 꼭짓점 좌표)이라 YOLOv8이 바로 못 읽어서,
표준 YOLO 형식(`class x_center y_center width height`, 정규화 값)으로 변환했습니다.
클래스: `0 = cavity`(충치), `1 = normal`(정상)
