# 충치 탐지 모델 학습 — 진행 상황 (2026-08-20 갱신)

새 컴퓨터/새 Claude Code 세션에서 이 프로젝트를 이어갈 때 이 파일부터 읽으면 맥락 파악이 됩니다.

## 지금 당장 이어서 할 일 (2026-08-20 세션, 진행 중 — 미완료)
**작업 중 이 학교 컴퓨터가 멈춰서 재부팅할 위험이 있어 미리 기록해둠.**

1. **`dataset_runE` 학습이 조기종료로 실패한 걸 발견함** — 원인: `pc_setup/training/kaggle_train_runE.py`가 runD의 `best.pt`를 이어받아 학습하는데, 1 epoch째에 이미 mAP50-95=0.4686을 찍은 뒤 20 epoch 동안 그걸 못 넘어서 `patience=20` 때문에 **21 epoch만에 조기종료됨**. 저장된 "best"가 사실상 거의 학습 안 된, runD 가중치 그대로에 가까운 체크포인트였음 (runE 데이터가 나쁜 게 아니라 조기종료 설정 문제로 결론)
   - **조치 완료**: `pc_setup/training/kaggle_train_runE.py:41`의 `patience=20` → **`patience=50`으로 수정함** (이 파일 그대로 Kaggle에 다시 붙여넣으면 됨)
   - **Kaggle 쪽 `best.pt`는 이미 runD 버전 그대로 있음** (사용자가 runE 실행 이후로 갱신 안 함) — 그러니 Kaggle에 새로 업로드할 필요 없이, 고친 스크립트만 다시 실행하면 됨
   - 로컬 `pc_setup/backend/model/best.pt`는 한때 이 미완성 runE 결과로 교체했었으나 **다시 runD로 되돌려놓음** (`best_runD_backup.pt`가 원본 백업, mAP50=0.698). 지금 `best.pt` = runD 맞음.

2. **cavity 클래스 성능이 크게 낮다는 것을 검증 완료함** (팀원 증언 확인됨) — `best_runD_backup.pt`(=현재 `best.pt`)를 `dataset_runD` valid set(6,059장)으로 재검증한 결과:
   | 클래스 | Precision | Recall | mAP50 |
   |---|---|---|---|
   | cavity | 0.589 | **0.397** | 0.455 |
   | normal | 0.733 | 0.954 | 0.940 |

   전체 평균 mAP50=0.698이 normal의 높은 성능(0.94)에 가려져서 cavity 문제(mAP50=0.455, recall 0.40)를 숨기고 있었음. 실제 서비스에서 충치를 잘 못 잡는다는 사용자 팀원 피드백과 정확히 일치.
   - 추정 원인(미확정): valid 기준 cavity 인스턴스(15,397개)가 normal(26,046개)보다 1.7배 적어서 학습이 normal 쪽에 유리했을 가능성 + cavity 병변 자체가 형태 다양성이 커서 본질적으로 더 어려운 태스크일 가능성 + 서비스 코드의 `conf=0.25` 임계값이 실제 recall을 더 깎을 가능성. **어느 게 진짜 원인인지는 아래 3번 데이터셋 감사로 확인할 계획.**

3. **다음 작업: YOLO 데이터셋 감사(audit) 파이프라인 구축 — 사용자가 다른 AI에게 받은 스펙 검토 완료, 이대로 진행하기로 합의함.** 목적: 3만 장 이상 데이터를 사람이 직접 다 안 봐도 되게, 라벨 오류/모델 취약 샘플 후보를 자동 선별해서 ChatGPT가 육안 1차 검수할 수 있는 contact sheet + CSV로 정리.
   - **핵심 설계 결정 (사용자와 합의됨)**:
     - **1차는 train(28,898장) 전체가 아니라 valid(6,059장)만 우선 감사** — best.pt가 train으로 학습됐으니 train 추론은 신호가 흐림. valid 결과 보고 필요하면 train으로 확장.
     - **추론은 Kaggle(T4 x2)에서, 결과 정리/시각화는 이 로컬 컴퓨터(CPU)에서** — 이 컴퓨터 GPU는 **GTX 1060 3GB**(PROGRESS.md에 예전에 GTX 1660으로 잘못 적혀있었음, 2026-08-20에 `torch.cuda.get_device_name()`으로 실측 정정함)라 VRAM이 작아서 몇만 장 추론에 부적합. Kaggle에서는 예측+GT 매칭 결과를 **가벼운 csv/json으로만** 추출해서 다운로드하고, contact sheet 그리기(이미지에 박스 그리는 것)는 로컬 CPU로 충분함.
   - **아직 스크립트 작성 시작 전** — 다음 세션에서 이어가려면: (1) Kaggle용 추론+매칭 스크립트(`pc_setup/training/`에 만들 예정, 아직 없음) 먼저 작성 → (2) 로컬용 contact sheet/CSV 생성 스크립트(`pc_setup/dataset_audit/scripts/`) 작성. 사용자가 준 원본 스펙(오류 타입 A~I 분류, review_score, HIGH/MEDIUM/LOW, batch당 500장, contact sheet 16~25장 등)은 대부분 그대로 따르기로 함.
   - 원칙(사용자가 강조함, 반드시 지킬 것): 원본 이미지/라벨/`best.pt` 절대 수정 금지, AI가 GT 자동 수정 금지, 결과는 전부 별도 폴더(`pc_setup/dataset_audit/`)에 저장.

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

## 다음에 할 일 (우선순위 순)
1. **데이터셋 감사(audit) 파이프라인 만들기** — 맨 위 "지금 당장 이어서 할 일" 3번 참고. 아직 스크립트 작성 시작 전.
2. **`dataset_runE` 재학습** — `kaggle_train_runE.py`는 이미 `patience=50`으로 고쳐놨음. Kaggle 쪽 Input(`best.pt`=runD, `dataset_runE`)은 그대로 재사용 가능, 새로 업로드할 필요 없음. 학습 끝나면 runD(mAP50=0.698) 대비 비교하고 `pc_setup/backend/model/best.pt` 교체할지 판단
3. (테스트 이슈, 미해결) 사용자가 노트북 웹캠으로 입 사진 찍어서 테스트했더니 충치 탐지가 "놓침" 현상 있었음. `pc_setup/backend/main.py:411`의 `model.predict(image, conf=0.25, ...)` — confidence threshold 때문에 화질/조명 다른 웹캠 사진에서 낮은 확률로 탐지된 게 걸러졌을 가능성이 있음. **2026-08-20 검증 결과 cavity recall이 valid set 기준으로도 0.397밖에 안 나와서, conf 임계값 문제라기보다 모델 자체의 cavity 탐지력 문제일 가능성이 높아짐** — 데이터셋 감사로 원인(라벨 누락 vs 모델 학습 부족) 구분 예정
4. (로드맵, 아직 미착수) 사용자가 로컬 PC 의존도를 더 줄이고 싶어함 — 지금은 "로컬에서 병합 스크립트 실행 → zip → Kaggle 업로드" 흐름인데, 이걸 Kaggle 노트북 안에서 직접 병합까지 하도록 바꾸면 로컬 PC는 "새 원본 데이터셋 다운받아서 Kaggle에 업로드"만 하면 되므로 어느 컴퓨터에서 작업하든 상관없어짐. 사용자가 원하면 이 방식으로 전환 가능
5. 사용자가 집 컴퓨터(GPU 사양 미확인, iGPU 여부도 미확인)로 로컬 학습을 시도해볼 수도 있음 — 로컬 학습 스크립트가 아직 없어서(지금까지 전부 Kaggle 전용) 필요하면 새로 작성해야 함. iGPU 없으면 학교 PC와 같은 화면 멈춤 위험 있다고 미리 안내해둠

## 알아둘 것 (함정 주의)
- 학습 파이프라인 스크립트는 전부 `pc_setup/training/`으로 옮겨져 있음 (원래 `pc_setup/` 바로 아래 있었는데, upstream에 나중에 push할 때 앱 코드랑 안 섞이게 분리함). 스크립트 안 경로 계산도 이 위치 기준으로 다 맞춰놨으니 새로 옮기거나 실행 위치 바꾸지 말 것
- `D:\pth\dataset\` 로 원본 데이터셋들을 사용자가 정리해서 옮겨놨고, 스크립트들은 전부 이 경로(`DATASET_DIR`)를 정확히 참조하도록 되어 있음 (원래 `build_datasets.py`/`build_dataset_runC.py`가 옛 경로를 참조하던 문제 있었는데 분리하면서 같이 고쳐둠)
- `dataset_runA`, `dataset_runB`, `dataset_runC`, `dataset_runD`, `dataset_dentalv7_converted` 폴더와 그 zip 파일들은 용량이 커서 **git에 커밋 안 함** (`.gitignore`에 추가해둠). 새 PC에서 이어가려면 이 스크립트들을 다시 돌려서 로컬에 재생성하거나, Kaggle에 이미 업로드된 버전을 그대로 활용하면 됨 (Kaggle 쪽은 클라우드라 이미 다 있음)
- `pc_setup/backend/model/best.pt`는 2026-08-18부로 `dataset_runD` 학습 결과로 교체됨 (mAP50=0.698)
- Kaggle Output에서 파일 받을 때 **파일명 조심**: 노트북이 참조하던 베이스 사전학습 가중치(`yolo26n...` 등 다른 이름)를 실수로 받을 수 있음. 진짜 결과물은 `runs/detect/cavity_train_runD/weights/best.pt` 경로에 있는 파일이어야 하고, 로드해서 `model.names`가 `{0: 'cavity', 1: 'normal'}`인지 확인하면 됨
