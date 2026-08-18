# 충치 탐지 모델 학습 — 진행 상황 (2026-08-14 기준)

새 컴퓨터/새 Claude Code 세션에서 이 프로젝트를 이어갈 때 이 파일부터 읽으면 맥락 파악이 됩니다.

## 프로젝트 개요
- **SmileGuard / MatchPoint**: 스마트폰으로 치아 촬영 → YOLOv8로 충치(cavity) 탐지 → 결과/리포트를 보여주는 앱
- 프론트: React (`src/`), 백엔드: FastAPI (`pc_setup/backend/`, 포트 8000, 로그인+YOLO 추론+이력조회 통합)
- 모델: YOLOv8n, **2클래스만 사용 (`0=cavity`, `1=normal`)** — 충치 있음/없음만 판별하면 되는 프로젝트라 세부 단계 분류는 안 함
- GitHub: origin=`pthkbs123/matchpoint`, upstream=`yuly0531/matchpoint`

## 왜 로컬이 아니라 Kaggle 클라우드에서 학습하나
- 이 PC(학교 컴퓨터)는 GPU가 GTX 1660 하나뿐이고 내장그래픽(iGPU)이 없어서, 화면 출력과 학습 연산을 같은 GPU가 담당함
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

## Kaggle 노트북 학습 스크립트 방식
- `pc_setup/training/kaggle_train_runC.py`, `pc_setup/training/kaggle_train_runD.py` — Kaggle 노트북 셀에 붙여넣는 스크립트
- **경로를 하드코딩하지 않고 `/kaggle/input` 전체에서 `rglob`으로 `data.yaml`/`best.pt` 자동 탐색** (Kaggle이 데이터셋 마운트할 때 폴더를 이중으로 감싸는 경우가 있어서 하드코딩하면 자꾸 에러 났음, 자동탐색으로 해결)
- **매 라운드마다 직전 라운드의 `best.pt`를 이어받아 `model.train()` 다시 호출하는 방식** — 진짜 resume(중단 지점부터 재개)이 아니라 그 가중치로 처음부터 다시 학습하는 것이므로 매번 실제 GPU 시간을 다 씀 (주의)

## 다음에 할 일 (우선순위 순)
1. (선택) 새 `best.pt`를 Kaggle `hanium_dataset`에 `+ New Version`으로 교체 업로드 — 아직 안 함
2. 사용자가 데이터셋을 계속 찾아오는 중 — **병합(runE 등)은 사용자가 명시적으로 "만들어"라고 지시할 때만 진행할 것** (토큰 절약을 위해 확인만 먼저 하고 대기하기로 합의됨)
3. (로드맵, 아직 미착수) 사용자가 로컬 PC 의존도를 더 줄이고 싶어함 — 지금은 "로컬에서 병합 스크립트 실행 → zip → Kaggle 업로드" 흐름인데, 이걸 Kaggle 노트북 안에서 직접 병합까지 하도록 바꾸면 로컬 PC는 "새 원본 데이터셋 다운받아서 Kaggle에 업로드"만 하면 되므로 어느 컴퓨터에서 작업하든 상관없어짐. 사용자가 원하면 이 방식으로 전환 가능
4. runD가 조기종료 없이 100 epoch 끝까지 개선 추세였으므로, 여유 되면 epoch을 늘려서(`patience` 유지, `epochs` 상향) 추가 학습해보는 것도 고려해볼 만함

## 알아둘 것 (함정 주의)
- 학습 파이프라인 스크립트는 전부 `pc_setup/training/`으로 옮겨져 있음 (원래 `pc_setup/` 바로 아래 있었는데, upstream에 나중에 push할 때 앱 코드랑 안 섞이게 분리함). 스크립트 안 경로 계산도 이 위치 기준으로 다 맞춰놨으니 새로 옮기거나 실행 위치 바꾸지 말 것
- `D:\pth\dataset\` 로 원본 데이터셋들을 사용자가 정리해서 옮겨놨고, 스크립트들은 전부 이 경로(`DATASET_DIR`)를 정확히 참조하도록 되어 있음 (원래 `build_datasets.py`/`build_dataset_runC.py`가 옛 경로를 참조하던 문제 있었는데 분리하면서 같이 고쳐둠)
- `dataset_runA`, `dataset_runB`, `dataset_runC`, `dataset_runD`, `dataset_dentalv7_converted` 폴더와 그 zip 파일들은 용량이 커서 **git에 커밋 안 함** (`.gitignore`에 추가해둠). 새 PC에서 이어가려면 이 스크립트들을 다시 돌려서 로컬에 재생성하거나, Kaggle에 이미 업로드된 버전을 그대로 활용하면 됨 (Kaggle 쪽은 클라우드라 이미 다 있음)
- `pc_setup/backend/model/best.pt`는 2026-08-18부로 `dataset_runD` 학습 결과로 교체됨 (mAP50=0.698)
- Kaggle Output에서 파일 받을 때 **파일명 조심**: 노트북이 참조하던 베이스 사전학습 가중치(`yolo26n...` 등 다른 이름)를 실수로 받을 수 있음. 진짜 결과물은 `runs/detect/cavity_train_runD/weights/best.pt` 경로에 있는 파일이어야 하고, 로드해서 `model.names`가 `{0: 'cavity', 1: 'normal'}`인지 확인하면 됨
