# 충치 탐지 모델 학습 — 진행 상황 (2026-08-21 갱신)

새 컴퓨터/새 Claude Code 세션에서 이 프로젝트를 이어갈 때 이 파일부터 읽으면 맥락 파악이 됩니다.
아래 "지금 당장 이어서 할 일"이 최신이고, 그 아래 옛 기록 중 일부는 지금 시점에선 **참고용(더 이상 최선의 방법이 아님)**이니 헷갈리지 말 것 — 최신 결론은 항상 이 섹션 우선.

## 2026-08-21 세션 (집 컴퓨터로 이어감) — 진행사항

### 1) 새 컴퓨터 세팅
- 학교 컴퓨터에서 집 컴퓨터로 작업 이전. `origin`(`pthkbs123/matchpoint`) 클론 완료, `upstream`(`yuly0531/matchpoint`) 리모트도 추가함
- upstream에 팀원이 올린 새 커밋 2개(`83ea28e` 촬영 히스토리 이미지저장, `6a387a7` 시계열 기능)를 병합 → `.gitignore` 한 줄만 충돌(각자 다른 줄 추가라 안전하게 합침) → **origin에 push 완료** (`475273a`)
- 이 컴퓨터엔 `pc_setup/backend` 실행용 `venv`를 새로 만들고 `requirements.txt` 전체 설치함 (torch/ultralytics/opencv 포함) — 다음부턴 재설치 없이 바로 서버 실행 가능

### 2) runG 실험 A 결과 확인 — 21 epoch에서 중단, 개선 없음
- Kaggle `kaggle_train_runG_A.py`(runD best.pt → runG fine-tuning) 결과물 `best.pt`/`results.csv` 확인함
- **21 epoch에서 중단됨** (patience=30 조건 채우기 전 — 정상 조기종료 아니고 세션이 끊긴 것으로 추정)
- 로그상 **epoch 1이 best** (overall P=0.673 / R=0.670 / mAP50=0.690 / mAP50-95=0.469), 이후 20 epoch 동안 못 넘음
- **주의**: 사용자가 ChatGPT에 물어본 분석 결과(P=0.732/R=0.706/mAP50=0.744/mAP50-95=0.519 등, "30 epoch 갱신 못해 조기종료" 등)는 실제 `results.csv`와 전혀 일치하지 않음 — 실제 파일을 열람하지 않고 만들어낸(추정/환각) 수치로 판단됨. 패턴 설명(epoch1이 best)만 우연히 맞았고 구체적 숫자는 신뢰 불가
- 결론: 이 A실험 결과는 기존 배포 모델(`runD best.pt`, mAP50=0.698)보다 나은 게 없어 **교체 안 함**. 실험 기록으로만 유지

### 3) runG 실험 B 시작 — 진행 중
- `pc_setup/training/kaggle_train_runG_B.py`(공식 pretrained yolov8n.pt → runG 새로 학습, A와 조건 동일: epoch=80/imgsz=640/batch=64/patience=30/seed=42) 사용자가 Kaggle에서 **Save & Run All로 실행 시작함, 아직 결과 안 나옴**
- 완료되면 `best.pt` + `results.csv` 받아서 runD/A/B 셋을 **cavity Recall 중심으로** 비교 예정 (전체 mAP 상승만으로 판단 금지 — 이 프로젝트 핵심 문제가 "충치 놓침"이라서)
- 클래스별(cavity/normal) 세부 검증은 아직 못 함 — 이 컴퓨터에 `dataset_runG` valid/test 실물 데이터가 없음, Kaggle에서 검증 셀 추가하거나 로컬에 데이터 받아와야 함 (다음 세션 결정 필요)

### 4) OpenCV 전처리 + 색상분석(황변지수/잇몸염증지수) — 구현 완료
- 목표: `analysis_records.yellowing_index`/`gum_inflammation_index` 컬럼과 리포트 그래프(`/api/report/summary`)는 이미 준비돼 있었는데 실제 계산 로직만 빠져있던 부분을 채움
- **모델 재학습 없이** 기존 YOLO cavity/normal 박스 좌표만으로 치아·잇몸 영역을 휴리스틱 추정하는 방식으로 결정 (시간 제약 때문에 새 잇몸 탐지 모델은 배제)
- 신규 `pc_setup/backend/color_analysis.py`:
  - `preprocess_bgr`: Gray-world 화이트밸런스 보정 + LAB L채널 CLAHE
  - `compute_yellowing_index`: `normal` 박스 내부만 사용(cavity 박스는 병변 어두움이라 제외), LAB b*채널 평균 → 0~100 지수(높을수록 건강, 기존 `score` 관례와 통일)
  - `compute_gum_inflammation_index`: 박스 바로 아래 30% 띠를 잇몸 후보로 잡고 HSV로 구강 점막색만 필터링(**Hue가 0 근처와 179 근처 양쪽에 걸치는 wraparound 버그를 단위 테스트로 발견해 수정함**) → LAB a*채널 평균 → 0~100 지수
  - `BASELINE_B/MAX_B/BASELINE_A/MAX_A` 등 보정 상수는 **임상 검증 안 된 휴리스틱 초깃값** — 실사용 데이터로 재보정 필요, 코드에도 주석으로 명시함
- `pc_setup/backend/main.py`의 `/analyze`에 연결 (실패해도 try/except로 감싸서 충치 탐지 응답 자체는 안 죽게 처리), `pc_setup/requirements.txt`에 `opencv-python-headless` 추가
- **엔드투엔드 테스트 완료**: 위키미디어 커먼즈 CC BY-SA 4.0 치아 사진(`Human_teeth.jpg`)으로 로컬 서버 띄워서 `/analyze` 호출 → YOLO가 치아 9개 정상 탐지, 두 지수 모두 null 아니고 실제 값(100.0/100.0) 계산됨 → 로그인 후 재호출해서 DB(`analysis_records`)/`/api/history` 조회까지 값 정상 저장·조회 확인
- **로컬 커밋 완료** (`246ba1b`), **origin push는 보류 중** (사용자가 나중에 하기로 함)
- **다음에 할 일**: 사용자가 실제 사진(본인 촬영 또는 팀 사진) 여러 장으로 PWA를 통해 직접 검증할 예정 — 그 결과 보고 보정 상수 튜닝 필요할 수 있음

## 지금 당장 이어서 할 일 (2026-08-20 세션 후반 갱신, 아래는 그 시점 기준 — runG 진행상황은 위 2026-08-21 섹션이 최신)
**Kaggle에서 `dataset_runG` + `kaggle_train_runG_A.py`로 학습 진행 중(새 노트북, 방금 시작함). 학교 컴퓨터라 재부팅 위험 있어 미리 기록.**

### 지금까지 일어난 일 순서대로 요약
1. cavity 성능이 실제로 나쁘다는 걸 검증함 (팀원 증언과 일치) → 원인 조사를 위해 데이터셋 감사(audit) 파이프라인을 만들어서 HIGH 우선순위 이미지 500장을 뽑아 ChatGPT 육안 검수용 contact sheet를 생성함 (`pc_setup/dataset_audit/`)
2. 감사 결과 **ICDAS 소스의 라벨링 기준이 문제**라는 걸 발견 (아래 상세) → 재매핑 수정한 `dataset_runF` 생성
3. GPT(사용자가 별도로 상담받은 AI)가 "**train-valid leakage(같은 원본 사진이 train/valid에 동시에 있는 문제) 먼저 확인하라**"고 지적 → 실제로 검사해보니 **valid의 84.5%가 train과 겹치는 심각한 leakage 발견**
4. leakage를 없앤 **원본 그룹 단위 재분할 `dataset_runG`**를 만들어서 지금 이 데이터로 재학습 진행 중

### 1) 데이터셋 감사(audit) — 완료
- `pc_setup/dataset_audit/scripts/kaggle_audit_infer.py`: Kaggle에서 `best_runD_backup.pt`로 valid 6,059장 전체 추론 → GT와 IoU 매칭 → CAVITY_MISSED/CAVITY_AS_NORMAL 등 이슈 자동 분류. 결과는 `pc_setup/dataset_audit/kaggle_output/`에 csv로 저장됨 (이미지 아니고 텍스트라 가벼움)
- `pc_setup/dataset_audit/scripts/build_review_package.py`: 그 csv로 review_score 계산 → HIGH 500장 뽑아서 GT/예측 박스 그린 contact sheet 25장(20장씩) + `chatgpt_review.csv` 생성 (`pc_setup/dataset_audit/chatgpt_review/`)
- 이슈 건수(valid 6,059장 기준): CAVITY_MISSED 5,783 > UNCERTAIN_SAMPLE 5,357 > LOW_IOU 3,586 > **CAVITY_AS_NORMAL 1,748** > POSSIBLE_MISSING_NORMAL_LABEL 408 > NORMAL_AS_CAVITY 256. 이슈 있는 이미지 4,947장/6,059장(82%)
- `pc_setup/dataset_audit/scripts/source_error_analysis.py`: 소스별로 **점유율 대비 정규화한 오류율** 계산 (GPT가 "HIGH 500장 중 비율만으로 판단하면 안 된다"고 지적해서 만듦). 결과는 `pc_setup/dataset_audit/reports/source_error_analysis.csv`

### 2) 소스별 정규화 오류율 핵심 결론
| source | 전체 점유율 | HIGH비율 | cavity_missed_rate | cavity_as_normal_rate |
|---|---|---|---|---|
| **ICDAS_II** | 6.6% | **46.2%** | 11.5% | **60.0%** |
| dataset_yolo_original | 1.5% | 26.9% | 11.5% | 42.8% |
| Dental.v1-dentalai | 4.2% | 13.4% | 58.9% | 2.1% |
| dentalv7_or_unknown | 9.5% | 7.3% | 50.5% | 0.1% |
| caries_segmentation_merges_sec | 38.0% | 6.0% | 45.2% | 1.8% |
| ToothCariesAI | 28.1% | 2.2% | 42.2% | 3.5% |
| data_fix | 8.8% | 1.9% | 28.0% | 1.0% |

- **ICDAS_II가 확실한 문제 소스** — 점유율 대비 7배 이상 과대표집. 원인: ICDAS 7단계(0=Sound~6=광범위충치) 중 기존 재매핑 규칙이 "0만 normal, 1~6 전부 cavity"였는데, 1(Faint)/2(Distinct) 단계는 육안으로 거의 안 보이는 초기 변화라 "사진은 정상처럼 보이는데 GT는 cavity"인 노이즈가 대량 발생했음
- **mergessec은 처음엔 의심했지만(HIGH 500장 중 32.2% 차지) 정규화하니 실제로는 평균 이하 — 문제 소스 아님으로 결론.** 전체의 38%나 차지하는 가장 큰 소스라서 절대 건수만 많아 보였던 것. OBB→AABB 변환 문제(박스가 커짐)는 여전히 존재할 수 있지만 지금은 **보류** (cavity_missed가 LOW_IOU/과도한 bbox와 강하게 연관된다는 증거 나오면 재검토)
- **`dataset_yolo_original`(최초 418장 베이스라인)도 새로 발견된 문제 소스** — 점유율 1.5%인데 HIGH 26.9%, cavity_as_normal 42.8%. 원인: 다른 소스와 **라벨링 단위(granularity) 자체가 다름** — 병변만이 아니라 **치아 전체를 하나의 cavity 박스**로 잡는 방식이라, 병변만 타이트하게 박스치도록 학습된 모델과 박스 크기가 안 맞아서 LOW_IOU/CAVITY_AS_NORMAL 대량 발생. 라벨 오류가 아니라 스키마 불일치. **아직 수정 안 함, 향후 정제 후보로 유지 중**

### 3) `dataset_runF` — ICDAS만 수정 (완료, 하지만 이후 runG로 대체되어 학습은 안 함)
`pc_setup/training/build_dataset_runF.py`: dataset_runE 전체를 베이스로 ICDAS 재매핑만 수정 (0/1/2→normal, 3~6→cavity). cavity 박스 8,917개→5,480개(-38.5%).
`pc_setup/training/kaggle_train_runF.py`도 만들어서(epoch=80, patience=30, GPU T4x2, dataset_runF가 runE보다 커서 100epoch면 9시간 넘을 위험 있어 80으로 낮춤) Kaggle에서 학습 시작했었으나, **leakage 발견 후 runG가 상위호환이라 판단되어 7~8epoch(약 49분)만에 취소함**. runF 자체는 폴더/zip으로 로컬에 남아있지만 이제 안 씀.

### 4) train-valid leakage 발견 — 이번 세션에서 제일 중요한 발견
GPT 요청으로 `pc_setup/dataset_audit/scripts/leakage_check.py`(파일명 `.rf.` 이전 원본ID + perceptual hash 두 방식) 실행 결과:
- **valid 6,059장 중 5,121장(84.5%)이 train과 같은 원본 사진에서 나온 augmentation copy였음** — Roboflow가 증강 후 분할해서 train/valid에 같은 원본이 흩어져 들어간 전형적인 버그. 실제 이미지 쌍 하나를 열어서 육안으로도 확인함 (같은 사람 혀 무늬/치아 배열, 각도만 다름)
- **leakage의 실제 성능 영향(직접 비교, runD valid 내부에서 leaked vs not_leaked로만 비교)**:
  | | leaked(5,121장) | not_leaked(938장) |
  |---|---|---|
  | cavity_missed_rate | 38.1% | 34.8% |
  | cavity_as_normal_rate | **9.5%** | **21.4%** |
  → leakage는 "완전히 놓치는" recall 문제에는 영향이 제한적이고(오히려 leaked 쪽이 근소하게 더 나쁨), **"cavity를 normal로 확신 있게 잘못 부르는" 고신뢰 오분류에는 유의미한 영향을 줌**(leaked면 그 실수가 절반 이하로 줄어듦). "leakage가 성능을 부풀렸다"는 예상과는 다른, 더 구체적인 결론임.

### 5) `dataset_runG` — leakage-free 그룹 단위 재분할 (완료, 지금 이걸로 학습 중)
`pc_setup/dataset_audit/scripts/build_leakage_free_split.py`: dataset_runF(이미지 구성 동일, ICDAS 라벨 수정 반영)를 원본으로, Union-Find로 그룹을 묶어서(같은 source+파일명키, 완전동일 perceptual hash, 해밍거리<=4인 근접 hash 전부 병합) train/valid/test가 원본 그룹을 절대 안 넘도록 재분할.
- 결과: train 36,433장(그룹 8,152개) / valid 4,553장(그룹 1,109개) / test 4,558장(그룹 1,082개), 목표 80/10/10에 근접. cavity 비율도 32.0/33.5/33.1%로 균등
- `pc_setup/dataset_audit/scripts/verify_runG_leakage.py`로 재검증: **train-valid/train-test/valid-test 전부 0건 겹침 확인 (파일명+hash 둘 다)**
- 소스별 비율도 train/valid/test 간 1~2%p 이내로 균등 유지됨 (`pc_setup/dataset_audit/reports/runG_split_stats.csv`)
- **runG를 앞으로의 기준 split으로 삼기로 함.** 기존 leaky split(runD/E/F)은 참고용으로만 남김
- `pc_setup/dataset_runG.zip`(1.71GB)로 압축 완료, Kaggle `hanium_dataset`에 New Version으로 업로드함
- `pc_setup/dataset_audit/scripts/local_audit_runG.py`로 runG valid+test에 대해서도 로컬 감사 추론 완료 (`dataset_audit_runG_valid.csv`, `dataset_audit_runG_test.csv`) — **이 결과로 source별 재분석은 아직 안 함, 다음 세션에서 이어서 할 일**

### 6) 지금 Kaggle에서 도는 것: runG 실험 A
`pc_setup/training/kaggle_train_runG_A.py` — runD의 best.pt를 이어받아 dataset_runG로 fine-tuning (epoch=80, patience=30, seed=42, GPU T4x2). **사용자가 방금 새 Kaggle 노트북에서 Save & Run All로 시작함.**
- 비교용 대조군 `pc_setup/training/kaggle_train_runG_B.py`(공식 pretrained yolov8n.pt에서 새로 학습, 조건 동일)도 만들어뒀지만 **아직 실행 안 함** — A 결과 먼저 보고 B 필요성 판단하기로 함 (쿼터 아끼려고)
- 목적: runD가 이미 학습해버린 "잘못된 ICDAS 기준"의 영향이 fine-tuning(A)에도 남아있는지, 새로 학습(B)이 더 나은지 비교하기 위함

### 다음 세션에서 이어서 할 일 (우선순위)
1. **runG 실험 A 학습 결과 확인** — Kaggle Output에서 `cavity_train_runG_A_finetune/weights/best.pt` 받아서 로컬 `best.pt`와 비교 (cavity P/R/mAP50/mAP50-95, normal 동일 지표)
2. A 결과 보고 실험 B(pretrained에서 새로 학습) 진행 여부 결정
3. `dataset_audit_runG_valid.csv`/`dataset_audit_runG_test.csv`로 **source별 cavity_missed_rate를 runG 기준으로 재계산** (`source_error_analysis.py`를 runG용으로 변형해서 돌리면 됨) — GPT가 요청한 CAVITY_MISSED 대표 실패유형 분류(30~50장씩, source별)도 이어서 할 것
4. `dataset_yolo_original`의 runG 기준 실제 영향도 계산 (아직 자동수정/삭제 금지, 정제 후보로만 유지)
5. mergessec은 계속 보류, cavity_missed가 LOW_IOU/과도한 bbox와 강하게 연관된다는 증거 나오면 그때 OBB/segmentation 처리 방식 재검토
6. **쿼터 주의**: runD(8.8h) + runE 조기종료(2.3h 낭비) + runF 취소분(49분) 이미 소모함. runG A(예상 8.9h)+B(예상 8.9h)까지 하면 주간 30시간 빠듯할 수 있음, Kaggle "Your Kaggle Quota" 패널로 실제 잔여량 확인 필요

## PWA 구현 (2026-08-18, 로컬 커밋만 완료 — origin에 아직 push 안 함)
- **커밋**: `ae301fe` "PWA 지원 추가: 매니페스트, 서비스 워커, 설치 가능성" (로컬 main 브랜치, origin/main엔 미반영)
- **왜 아직 안 올렸나**: 사용자가 좀 더 확인해볼 게 있어서 일부러 push 보류함. 새 세션에서 이어갈 때 이 커밋이 origin에 없다는 점 주의 — 다른 컴퓨터에서 작업 이어가려면 이 로컬 저장소(`D:\pth\matchpoint_tmp`)의 커밋을 가져와야 함
- **변경 내용**:
  - `public/manifest.json`: 앱 이름 "SmileGuard - 충치 탐지", 테마색 `#0f172a`, 아이콘에 `purpose: any` 추가, `scope`/`orientation` 추가
  - `public/index.html`: title/description/theme-color meta 반영
  - `public/service-worker.js` (신규): 앱 셸 캐싱(cache-first), `/api/`·`/analyze` 요청은 캐싱 제외(백엔드는 항상 최신 응답)
  - `src/serviceWorkerRegistration.js` (신규): **프로덕션 빌드에서만** 서비스 워커 등록 (localhost 개발 중엔 캐시 혼선 방지 위해 미등록)
  - `src/index.js`: `serviceWorkerRegistration.register()` 호출 연결
  - `start-dev.cmd` (신규): Node.js PATH 잡고 `npm start` 실행하는 배치 파일
- **Node.js 설치 확인**: `v24.19.0`, npm `11.17.0` 정상 설치됨 (학교 컴퓨터 재부팅 후에도 유지됨 — 재부팅해도 초기화 안 되는 걸 보니 시스템 전역 설치였던 듯)
- **테스트 완료**: `npm run build` 정상 컴파일 → `npx serve -s build`로 정적 서빙 → 실제 Edge 브라우저(일반 창)에서 서비스 워커 `activated and is running` 확인, 설치 프롬프트("SmileGuard - 충치 탐지 앱 설치") 정상 노출 확인
- **알아둘 것**: Claude Code 인앱 프리뷰(Browser pane, 샌드박스 환경)에서는 서비스 워커 `register()`가 "unknown error occurred when fetching the script"로 실패함 — 파일 자체나 서버 문제 아니고 프리뷰 샌드박스 제약으로 추정됨. PWA 관련 테스트는 실제 브라우저(Edge/Chrome)에서 해야 신뢰 가능
- **다음에 할 일**: 사용자가 추가로 확인할 부분 남음 (구체적으로 뭘 더 볼 건지는 미정 — 다음 세션에서 사용자에게 확인). 확인 끝나면 origin에 push

## 프로젝트 개요
- **SmileGuard / MatchPoint**: 스마트폰으로 치아 촬영 → YOLOv8로 충치(cavity) 탐지 → 결과/리포트를 보여주는 앱
- 프론트: React (`src/`), 백엔드: FastAPI (`pc_setup/backend/`, 포트 8000, 로그인+YOLO 추론+이력조회 통합)
- 모델: YOLOv8n, **2클래스만 사용 (`0=cavity`, `1=normal`)** — 충치 있음/없음만 판별하면 되는 프로젝트라 세부 단계 분류는 안 함
- GitHub: origin=`pthkbs123/matchpoint`, upstream=`yuly0531/matchpoint`

## 왜 로컬이 아니라 Kaggle 클라우드에서 학습하나
- 이 PC(학교 컴퓨터)는 GPU가 GTX 1060 3GB 하나뿐이고(2026-08-20 실측 정정 — 예전 기록엔 GTX 1660으로 잘못 적혀있었음) 내장그래픽(iGPU)이 없어서, 화면 출력과 학습 연산을 같은 GPU가 담당함
- 로컬에서 학습 돌리면 WDDM/TDR 충돌로 화면이 완전히 멈추는 문제 발생 (2시간 방치해도 안 풀림 → 강제 재부팅 필요했음)
- 학교 컴퓨터라 재부팅하면 상태가 초기화돼서 WSL2 같은 재부팅 필요한 해결책도 못 씀
- → **Kaggle Notebook의 무료 GPU(T4 x2)에서 학습하는 방식으로 전환**. 로컬 PC는 "데이터셋 가공 + Kaggle 업로드"만 담당

## Kaggle 계정/리소스
- Kaggle 데이터셋: `hanium_dataset` (소유자: pthkbs) — 여러 버전(New Version)으로 계속 갱신 중
- Kaggle 노트북: `hanium yolov8 notebook`
- 무료 플랜 GPU 쿼터: 주 30시간, 롤링(rolling) 방식으로 매일 조금씩 복구됨. `Your Kaggle Quota` 패널에서 확인 가능
- **주의**: `Save & Run All`(커밋)은 노트북을 처음부터 다시 통째로 실행하는 방식이라 비효율적이지만, 브라우저/컴퓨터를 꺼도 안전하게 백그라운드로 도는 유일한 방법이라 이걸 씀. Draft(인터랙티브) 세션은 브라우저 닫으면 끊길 위험 있음

## 데이터 파이프라인 (로컬, `pc_setup/training/`)
원본 공개 데이터셋(Roboflow 등)을 받아서 `D:\pth\dataset\` 폴더에 모아두고, 로컬 파이썬 스크립트로 **cavity/normal 2클래스 YOLO bbox 형식**으로 변환·병합 → zip → Kaggle 업로드.
학습 파이프라인 스크립트는 전부 `pc_setup/training/` 폴더에 모아둠 (앱 실행에 필요한 코드가 아니라 "모델을 어떻게 만들었는지" 기록용이라, 나중에 upstream(원본 저장소)에 PR 보낼 때 안 섞이도록 따로 분리함). 생성되는 데이터셋 폴더(`dataset_runX`)와 `best.pt`는 지금까지처럼 `pc_setup/` 바로 아래에 만들어짐 (스크립트가 `pc_setup/training/`에 있어도 출력 위치는 그대로 `pc_setup/`).

### 완료된 병합: `dataset_runC`
`pc_setup/training/build_dataset_runC.py` (구버전 `pc_setup/training/build_datasets.py`가 runA/runB 만든 걸 이어받음)
- 원본 `dataset_yolo` (418장, 이미 cavity/normal)
- Caries Classification ICDAS II v3 (7단계 → 0=Sound만 normal, 나머지 cavity로 재매핑)
- Caries_Dataset (분류 폴더 구조, bbox 없어서 이미지 전체를 박스로 사용)
- Dental.v1-dentalai (OBB 형식, Caries/Cavity→cavity, Tooth→normal, Crack 제외)
- **결과: train 9,203 / valid 945 / test 688장**
- **Kaggle 학습 완료**: 34 epoch에서 조기종료(patience=20), best는 14 epoch, mAP50=0.598, mAP50-95=0.404

### 완료된 병합: `dataset_runD` (재정의된 버전, 처음 만든 runD는 삭제하고 다시 만듦)
`pc_setup/training/build_dataset_runD.py`
- `dataset_runC` 전체
- `caries_segmentation_merges_sec.v1i.yolov8-obb` (OBB, Dental.v1-dentalai와 같은 클래스체계: Caries/Cavity→cavity, Tooth→normal, Crack 제외)
- `data fix.v1i.yolov8` (클래스명이 그냥 '0','1','2'라 의미 불명확했음 → 샘플 이미지 시각화해서 사용자가 직접 판별: **파란색(class 2)=karies=cavity만 사용**, 나머지(치석/잇몸염 추정)는 제외, cavity 라벨이 없는 이미지는 통째로 제외)
- `ToothCariesAI.v1i.yolov8` (단일 클래스 `KARIES` → 그대로 cavity, 깔끔함)
- `dataset_dentalv7_converted` (`convert_dentalv7.py`로 별도 변환해둔 것) ← `dental.v7i.yolov8` 원본은 21클래스 스페인어+폴리곤 세그멘테이션 형식. 충치 세부유형 9개(caries, caries cervical 등)→cavity, `tooth`→normal, 나머지 11개(bridge/crown/root canal 등 무관한 소견)는 제외. cavity/normal 라벨이 하나도 없는 이미지는 통째로 제외 (11,658장 중 4,729장만 사용 가능했음)
- **결과: train 28,898 / valid 6,059 / test 3,261장**
- **Kaggle 학습 완료** (2026-08-14~18, `cavity_train_runD`): patience=20 조기종료 없이 100 epoch 전부 완주, 100 epoch째가 곧 최고 성능(계속 개선 중이었다는 뜻 — 더 돌리면 성능 더 오를 여지 있음)
- **결과: mAP50=0.698, mAP50-95=0.476, precision=0.660, recall=0.676** (runC 대비 mAP50 +0.100, mAP50-95 +0.072 — 데이터 4배 확장의 효과 확인됨)
- **로컬 반영 완료**: `pc_setup/backend/model/best.pt`를 이 runD 결과로 교체함 (2026-08-18)

### 완료된 병합: `dataset_runE`
`pc_setup/training/build_dataset_runE.py`
- `dataset_runD` 전체
- `DentalCaries.v2i.yolov8` (Roboflow, 4,663장, axis-aligned, 클래스 0=Caries/1=Cavity→cavity, 2=Tooth→normal, 3=Crack 제외 — `data.yaml`의 names 필드가 깨져 나와서 이미지에 박스 그려서 직접 확인한 값. **원본 zip에 train만 있고 valid/test가 없어서 전부 train으로 들어감**)
- `caries detection.v1i.yolov8` (Roboflow, 원래 2,495장인데 `DentalCaries.v2i`와 md5 기준 1,996장(80%)이 완전히 동일한 이미지라 **중복 제거하고 499장만 사용**. 클래스 0=Caries/1=Cavity→cavity, 3=Tooth→normal, 2=Crack 제외)
- Zenodo `Benchmarking Dataset` (6,266장 중 **yolo 라벨 파일이 있고 내용도 있는 2,164장만 사용**. 나머지 4,102장은 라벨 파일 자체가 없어서 정상인지 라벨 누락인지 알 수 없어 제외. 클래스 0/1(유치/영구치 충치) 모두 → cavity. **이 소스는 normal 기여가 전혀 없음**, 충치 있는 사진만 있어서)
- **결과: train 35,690 / valid 6,315 / test 3,539장**
- **Kaggle 학습 1차 시도함 (2026-08-18~20) — 실패(조기종료), 원인 파악 완료, 재시도 대기 중.** 자세한 내용은 파일 맨 위 "지금 당장 이어서 할 일" 참고. 1차 결과(참고용, 실제 쓰면 안 됨): mAP50=0.690, mAP50-95=0.469 — `patience=20` 조기종료로 1 epoch째 수준에서 거의 안 움직인 값이라 의미 없음. `patience=50`으로 고쳐서 재학습 예정.

## Kaggle 노트북 학습 스크립트 방식
- `pc_setup/training/kaggle_train_runC.py`, `pc_setup/training/kaggle_train_runD.py` — Kaggle 노트북 셀에 붙여넣는 스크립트
- **경로를 하드코딩하지 않고 `/kaggle/input` 전체에서 `rglob`으로 `data.yaml`/`best.pt` 자동 탐색** (Kaggle이 데이터셋 마운트할 때 폴더를 이중으로 감싸는 경우가 있어서 하드코딩하면 자꾸 에러 났음, 자동탐색으로 해결)
- **매 라운드마다 직전 라운드의 `best.pt`를 이어받아 `model.train()` 다시 호출하는 방식** — 진짜 resume(중단 지점부터 재개)이 아니라 그 가중치로 처음부터 다시 학습하는 것이므로 매번 실제 GPU 시간을 다 씀 (주의)

## 옛 "다음에 할 일" (2026-08-20 세션 초반 기준 — 대부분 완료/대체됨, 최신은 맨 위 섹션 참고)
1. ~~데이터셋 감사 파이프라인 만들기~~ → 완료, 맨 위 섹션 참고
2. ~~`dataset_runE` 재학습~~ → runE는 조기종료 문제 확인 후 ICDAS 수정한 runF로, 다시 leakage 발견 후 runG로 대체됨. runE/runF 둘 다 실제 학습은 안 함(또는 중도 취소)
3. (테스트 이슈, 아직 미해결) 웹캠 촬영 시 cavity "놓침" — cavity recall 자체가 낮다는 게 확인됐으니 conf 임계값 문제라기보다 모델 성능 문제. runG 재학습 결과 나오면 재점검
4. (로드맵, 아직 미착수) Kaggle 노트북 안에서 직접 데이터 병합까지 하도록 전환하는 방안 — 사용자가 원하면 진행
5. (로드맵, 아직 미착수) 로컬 학습 스크립트 작성 — 필요시 진행

## 알아둘 것 (함정 주의)
- 학습 파이프라인 스크립트는 전부 `pc_setup/training/`으로 옮겨져 있음 (원래 `pc_setup/` 바로 아래 있었는데, upstream에 나중에 push할 때 앱 코드랑 안 섞이게 분리함). 스크립트 안 경로 계산도 이 위치 기준으로 다 맞춰놨으니 새로 옮기거나 실행 위치 바꾸지 말 것
- `D:\pth\dataset\` 로 원본 데이터셋들을 사용자가 정리해서 옮겨놨고, 스크립트들은 전부 이 경로(`DATASET_DIR`)를 정확히 참조하도록 되어 있음 (원래 `build_datasets.py`/`build_dataset_runC.py`가 옛 경로를 참조하던 문제 있었는데 분리하면서 같이 고쳐둠)
- `dataset_runA`, `dataset_runB`, `dataset_runC`, `dataset_runD`, `dataset_dentalv7_converted` 폴더와 그 zip 파일들은 용량이 커서 **git에 커밋 안 함** (`.gitignore`에 추가해둠). 새 PC에서 이어가려면 이 스크립트들을 다시 돌려서 로컬에 재생성하거나, Kaggle에 이미 업로드된 버전을 그대로 활용하면 됨 (Kaggle 쪽은 클라우드라 이미 다 있음)
- `pc_setup/backend/model/best.pt`는 2026-08-18부로 `dataset_runD` 학습 결과로 교체됨 (mAP50=0.698)
- Kaggle Output에서 파일 받을 때 **파일명 조심**: 노트북이 참조하던 베이스 사전학습 가중치(`yolo26n...` 등 다른 이름)를 실수로 받을 수 있음. 진짜 결과물은 `runs/detect/cavity_train_runD/weights/best.pt` 경로에 있는 파일이어야 하고, 로드해서 `model.names`가 `{0: 'cavity', 1: 'normal'}`인지 확인하면 됨
