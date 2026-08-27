# 충치 탐지 모델·앱 개발 — 진행 상황 (2026-08-27 갱신)

새 컴퓨터/새 Claude Code 세션에서 이 프로젝트를 이어갈 때 이 파일부터 읽으면 맥락 파악이 됩니다.
아래 "지금 당장 이어서 할 일"이 최신이고, 그 아래 옛 기록 중 일부는 지금 시점에선 **참고용(더 이상 최선의 방법이 아님)**이니 헷갈리지 말 것 — 최신 결론은 항상 이 섹션 우선.

## 2026-08-27 실제 내시경 카메라 검증 — 잇몸 ROI 개선 완료

### 촬영 및 계산 범위

- 실제 사용할 `HD Camera (0bda:0561)`를 브라우저에서 연결했고 실제 해상도는 `1280x1024`로 확인함.
- 같은 조건의 정면 사진 3장과 위·아래 잇몸 확인용 사진 2장, 총 5장을 로컬에서 분석함.
- 촬영 원본은 개인정보가 포함될 수 있으므로 Git에 넣지 않았고 로컬 검증 폴더에만 유지함.
- 앱 현재 모델과 최신 Run H 모델을 각각 원본/화이트밸런스+CLAHE/화이트밸런스+Bilateral+CLAHE 조건으로 비교함.

### 실제 카메라 품질 결론

- 정면 3장의 평균 밝기는 `142.343 / 142.911 / 148.621`로 범위가 `6.278`이어서 반복 촬영 조건은 충분히 일정했음.
- 흰색 완전 포화 비율은 정면 3장 모두 `0%`였으므로 LED 반사가 보이더라도 실제 픽셀 과다노출 문제는 아니었음.
- 카메라 특성상 정면 사진이 다소 부드럽고 노이즈가 있지만 현재 프로젝트의 실제 입력 환경으로 사용할 수 있음. 다른 카메라를 전제로 보정하지 않음.

### 잇몸 영역 계산 변경

- 기존 방식은 모든 치아 박스의 **아래 30% 띠**만 잇몸으로 간주해 위쪽 치열에서 치아·구강 내부를 잘못 포함할 수 있었음.
- 실제 사진 오버레이를 확인한 결과 다음 방식이 가장 타당했음.
  - 위쪽 치열: 치아 박스 **위 15%**
  - 아래쪽 치열: 치아 박스 **아래 15%**
  - 한쪽 치열만 검출되거나 배열이 불명확하면 HSV 점막색 픽셀이 더 많은 방향을 자동 선택
  - 선택한 방향에 유효 점막색이 없으면 반대 방향으로 안전하게 대체
- 정면 3회 Run H/원본 기준 LAB a* 값:
  - 새 방식: `140.289 / 139.735 / 141.523`, 범위 **`1.788`**
  - 기존 아래 30% 방식: 범위 약 **`7.595`**
  - 새 방식이 동일 조건 반복 측정에서 약 4배 안정적이었음.
- 실제 5장과 합성 위·아래 치열 케이스로 검증했고 백엔드 전체 단위 테스트 **13개 전부 통과**함.

### 전처리 및 모델 해석

- 잇몸색은 현재 실제 카메라 반복 안정성과 공개 잇몸 사진의 구분 방향을 함께 보면 **원본 색상 사용이 가장 유력**함.
- 황변 LAB b* 반복 안정성은 `WB+CLAHE`가 원본보다 좋았지만 황변 정도가 라벨된 사진이 없으므로 아직 기본 방식으로 확정하지 않음.
- Bilateral 포함 전처리는 정면 3장의 YOLO 검출 수 변동이 커져 현재 기본값으로 채택할 근거가 없음.
- 위·아래 잇몸 근접 사진에서 전처리에 따라 cavity 검출 수가 크게 변했지만 정답 라벨이 없으므로 정확도 향상으로 해석하면 안 됨. 충치 모델 비교는 정답 라벨이 있는 사진으로 별도 수행해야 함.
- 이 색상 결과는 진단값이 아니라 개인 3회 기준선 대비 변화 관찰용 보조 지표로만 사용함.

### GitHub/PR 반영

- 브랜치: `feature/color-analysis-completion`
- 커밋: `0519c70` (`실제 카메라 기준 잇몸 영역 추정 개선`)
- 커밋: `8b4c04c` (`실측 결과에 맞춰 색상 전처리 분리`)
- 운영 분석은 황변에 `WB+CLAHE`, 잇몸에 원본 색상을 각각 사용하며 YOLO 입력은 변경하지 않음.
- 개인 GitHub에 push 완료했으므로 기존 팀 Pull Request에도 자동 반영됨.

### 다음 실제 촬영/검증

1. 이번 정면 3장은 임시 카메라 확인 페이지에서만 저장되어 앱의 개인 기준선에는 아직 반영되지 않았다. 기존 정면 3장을 실제 앱의 로그인 사용자/선택 자녀로 분석해 기준선을 만들거나 앱에서 3장을 다시 촬영한 뒤, **새 정면 사진 1장을 4번째로 분석**해 변화량과 SQLite 저장·이력 표시까지 확인한다.
2. 정면에서 일부러 약간 기울인 사진 1장을 찍어 촬영환경 임계값과 재촬영 안내가 필요한 실패 범위를 확인한다.
3. 황변·잇몸 임계값 확정에는 같은 사람의 사진을 더 찍는 것보다 상태 라벨이 있는 정상/황변 및 정상/치은염 사진이 필요하다. 충치 Recall 검증도 치과 판독 또는 정답 박스가 있는 사진으로 진행한다.

### 전문가 라벨 공개 사진으로 잇몸 색상 외부 검증

- 사용자가 직접 만들 수 없는 임상 정답 사진은 공개 자료에서 확보하기로 함.
- [MIO 공개 임상 자료](https://zenodo.org/records/21140854)(DOI `10.5281/zenodo.21140854`)에서 치과 전문가가 분류한 건강 잇몸 30장과 치은염 30장을 ZIP 전체 순서에 걸쳐 균등 표본 추출함.
- 임상 사진은 Git에 올리지 않고 로컬에만 보관했으며 표본의 ZIP 내부 원본 경로를 manifest로 기록함.
- 현재 앱 모델의 원본 YOLO 박스와 PR의 적응형 15% ROI 코드로 세 전처리를 동일 비교함.
- 각 그룹 앞 15장으로 후보 임계값을 정하고 뒤 15장을 holdout으로 확인함.

| 입력/지표 | 건강 평균 | 치은염 평균 | 전체 AUC | holdout 민감도 | holdout 특이도 | 균형정확도 |
|---|---:|---:|---:|---:|---:|---:|
| 원본 LAB a* | 153.959 | 155.393 | 0.5867 | 0.8000 | 0.3333 | 0.5667 |
| 원본 HSV S | 119.356 | 128.574 | **0.6356** | 0.7333 | 0.3333 | 0.5333 |
| WB+CLAHE LAB a* | 138.798 | 138.734 | 0.4711 | 0.8000 | 0.0667 | 0.4333 |
| WB+CLAHE HSV S | 79.796 | 83.628 | 0.5356 | 0.6000 | 0.2000 | 0.4000 |
| Bilateral 포함 LAB a* | 138.736 | 138.720 | 0.4733 | 0.8000 | 0.0667 | 0.4333 |
| Bilateral 포함 HSV S | 79.934 | 83.376 | 0.5311 | 0.5333 | 0.2000 | 0.3667 |

- **원본 색상이 세 조건 중 가장 낫다는 기존 결정은 유지**한다. 반면 화이트밸런스/CLAHE는 건강과 치은염의 차이까지 약화했다.
- 하지만 가장 나은 원본 HSV도 holdout 특이도가 0.3333뿐이라 정상 잇몸을 너무 많이 경고한다. LAB/HSV 평균만으로 절대 치은염 판정 임계값을 적용하지 않는다.
- ROI 문제라기보다 치은염에 필요한 붓기·치은 변연 형태·국소 발적·출혈 등의 형태 정보가 현재 평균 색상식에 없다는 것이 핵심 한계다.
- 현재 기능은 **개인 3회 기준선 대비 잇몸 색상 변화 보조지표**로 유지하고 의료 진단값으로 표현하지 않는다.
- 절대 치은염 분류가 필요하면 MIO 전체 또는 MGI 단계/ROI 라벨 1,096장이 있는 Mendeley 자료로 별도 분류·세그멘테이션 모델을 학습해야 한다.
- 세부 보고서와 CSV/JSON은 로컬 `public_validation` 폴더에 생성함.

---

## 2026-08-26 Kaggle 최신 작업 복구 — 교수님 모델 vs Run A+H

학교 PC에서 작업했으나 로컬 MD에 적지 못한 내용을 Kaggle 로그인 후 최신 노트북과 입력 데이터셋에서 직접 확인함.

### 확인한 Kaggle 항목

- 최신 노트북: `hanium yolov8 v3`
  - https://www.kaggle.com/code/pthkbs/hanium-yolov8-v3
  - 최신 실행본: **Version 8 of 8**, run ID `345049773`
  - 실행 시간: **24분 1초**, GPU **T4 x2**
- 사용자 데이터셋: `hanium_dataset` Version 12, 약 **7.66GB / 399k files**
  - `dataset_runE`, `dataset_runF`, `dataset_runG`, `dataset_runH`
  - `best.pt`, `best_runG.pt`, `best_runG_A.pt`, `best_runH.pt`
- 교수님 입력: `hanuim_dataset_professor_best_pt` Version 1
  - 실제 포함 파일은 **`professor_best.pt` 1개(40.73MB)**뿐임
  - 원본 학습 이미지, 라벨, `data.yaml`, `results.csv`, 학습 설정은 포함되지 않음

### 비교의 정확한 의미

이 작업은 교수님 **학습 데이터셋과** 사용자 학습 데이터셋을 직접 비교한 것이 아니다.
교수님이 주신 YOLOv12m `best.pt`와 사용자의 Run A+H 앙상블을 사용자의 원본
`dataset_runG` leakage-free valid/test에서 동일한 규칙으로 외부 평가한 **모델 비교**다.

- 평가 데이터: 수정하지 않은 `dataset_runG` valid 4,553장 / test 4,558장
- 이미지 크기: `768`
- GT 매칭 IoU: `0.50`
- cavity 목표 Recall: `0.60`
- threshold는 valid에서만 선택하고 고정한 뒤 test를 한 번 평가
- normal confidence: `0.25`
- 교수님 모델 클래스 이름은 `{0: cavity, 1: normal}`로 확인되어 단순 클래스 순서 반전은 아님
- 이 노트북은 mAP를 계산하지 않고 threshold별 **Precision / Recall / F2 / TP / FP / FN**을 계산함

### 사용자 Run A+H 결과

Run A와 Run H의 cavity 예측을 합친 뒤 NMS로 중복 제거하며, normal은 Run A만 사용한다.

| 구분 | threshold | Precision | Recall | F2 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| VALID cavity A+H | A=0.10, H=0.15 | 0.3872 | 0.6538 | 0.5747 | 7,310 | 11,568 | 3,871 |
| TEST cavity A+H | VALID에서 고정 | 0.4065 | **0.6729** | 0.5950 | 7,514 | 10,970 | 3,652 |
| TEST normal Run A | 0.25 | 0.7639 | **0.9442** | 0.9017 | 21,343 | 6,595 | 1,261 |

참고로 단일 모델 test cavity 결과는 Run A `P=0.3329, R=0.6683`, Run H
`P=0.3593, R=0.6428`이었다. A+H는 두 단일 모델보다 test cavity Recall과 Precision이 모두 높았다.

### 교수님 YOLOv12m 결과

교수님 모델은 valid에서 목표 Recall 0.60을 어느 threshold에서도 달성하지 못했다.
코드 규칙에 따라 F2가 가장 높은 threshold `0.40`이 선택되었다.

| 구분 | threshold | Precision | Recall | F2 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| VALID cavity 교수님 모델 | 0.40 | 0.0449 | 0.1131 | 0.0867 | 1,265 | 26,923 | 9,916 |
| TEST cavity 교수님 모델 | VALID에서 고정 | 0.0397 | **0.1084** | 0.0805 | 1,210 | 29,303 | 9,956 |
| TEST normal 교수님 모델 | 0.25 | 0.1919 | **0.1209** | 0.1305 | 2,732 | 11,504 | 19,872 |

- 교수님 모델은 threshold `0.001`에서도 VALID cavity Recall이 약 `0.2223`에 불과했고 Precision은 약 `0.0058`이었다.
- 추론 속도는 T4 한 장, batch 16에서 valid 약 `66.51ms/image`, test 약 `65.59ms/image`였다.

### 현재 결론

- **현재 프로젝트의 `dataset_runG` 기준에서는 Run A+H가 압도적으로 우수하다.** 가장 중요한 test cavity Recall은 `0.6729 vs 0.1084`다.
- 따라서 현재 수치만 보면 교수님 모델로 프로젝트 모델을 교체하면 안 된다.
- 다만 이 결과만으로 교수님 모델 자체가 나쁘다고 확정하면 안 된다. 교수님 모델이 학습한 원본 데이터와 `dataset_runG` 사이의 촬영 환경·박스 기준·라벨 기준 차이가 클 가능성이 높다.
- A+H는 2개 모델 앙상블이고 교수님 모델은 1개 모델이므로 모델 용량·추론 비용까지 동일한 완전한 조건 비교는 아니다. 하지만 현재 프로젝트 데이터에 대한 배포 적합성 비교로는 의미가 있다.
- Precision이 A+H도 `0.4065`로 낮아 오탐은 여전히 많다. Recall 목표를 달성했다는 이유만으로 최종 모델이라고 확정하지 않는다.

### Kaggle 출력 파일

- `runAH_ensemble_metrics.json`
- `runAH_valid_threshold_sweep.csv`
- `professor_vs_runAH_metrics.json`
- `professor_valid_threshold_sweep.csv`

### 다음에 반드시 할 일

1. 교수님께 원본 학습 데이터의 `data.yaml`, train/valid/test 이미지·라벨, 학습 설정, `results.csv`를 받아야 실제 **데이터셋 비교**가 가능하다.
2. 교수님 모델과 A+H가 서로 다르게 예측한 `dataset_runG` valid/test 이미지 30~50장을 박스 오버레이로 뽑아 라벨 기준·도메인 차이를 육안 확인한다.
3. 동일 테스트셋에서 Ultralytics 표준 클래스별 mAP50/mAP50-95도 별도로 계산한다. 현재 노트북 수치는 P/R/F2만 있으므로 기존 실험 mAP와 직접 섞어 비교하지 않는다.
4. A+H 앙상블의 실제 배포 속도와 메모리 사용량을 측정한다. 라즈베리파이 또는 서버에서 너무 무거우면 Run A 단독과 Recall/속도 절충안을 비교한다.
5. 교수님 원본 데이터가 확보되기 전에는 두 데이터셋의 우열이나 leakage 여부를 단정하지 않는다.

---

## 2026-08-25 인수인계 기록

### GitHub와 PR 상태

- 개인 저장소: `origin = https://github.com/pthkbs123/matchpoint.git`
- 팀 저장소: `upstream = https://github.com/yuly0531/matchpoint.git`
- 팀 최신 `main`을 개인 `main`에 병합하고 개인 GitHub에 push 완료
  - 개인 `main` 병합 커밋: `5c7ba0c`
- 팀 `main`을 기준으로 PR 전용 브랜치를 새로 생성함
  - 브랜치: `feature/color-analysis-completion`
  - 커밋: `5ca10d0` (`색상 기준 재설정과 실데이터 보정 기능 추가`)
  - 개인 GitHub에 push 완료
  - 사용자가 팀 저장소를 대상으로 Pull Request 생성 완료
- 이 PR 브랜치는 팀 `main` 이후 기능 커밋 1개만 포함하도록 만들었음. 개인 `PROGRESS.md` 기록이나 모델 학습용 개인 커밋은 PR에 섞이지 않음.

### 팀 main에 이미 있던 기능 — 반드시 유지

- 자녀별 최초 3회 색상 측정값의 누적 평균을 개인 기준으로 저장
- LAB b* 치아 황변 측정, LAB a* 잇몸 측정, 개인 기준 대비 변화량 계산
- 결과 화면의 개인 기준 수집 진행률 표시
- 날짜별·월별·연간 추이와 월간 리포트
- 알림 화면과 월간 리포트 연결

팀 구현을 우선으로 삼았으며, 위 기능은 새 PR에서도 삭제하거나 다른 방식으로 교체하지 않았음.

### PR에서 추가한 색상 분석 보완 기능

- OpenCV 전처리 3종 비교
  - `original`
  - `wb_clahe`
  - `wb_bilateral_clahe`
- 자녀별 `기준 다시 만들기`
  - 기존 촬영 이력은 삭제하지 않음
  - 자녀 테이블의 색상 기준값/수집 횟수만 초기화
  - 기준 세대를 1 증가시키고 새 측정 3회부터 다시 수집
- 잇몸 HSV 보조 분석
  - HSV H/S/V 원시값
  - HSV 채도 기반 보조 건강점수
  - LAB 점수와 HSV 보조점수의 차이 및 `high/medium/low` 일치도
- `마이페이지 → 색상 분석 테스트` 화면
  - 같은 사진을 전처리 3종으로 비교
  - 촬영 조건(같은 조명/밝음/어두움/각도 변경) 기록
  - 참고 상태(정상/황변/잇몸 붉음/둘 다) 기록
  - 전처리별 반복 측정 변동 폭 표시
  - 결과 브라우저 로컬 저장 및 CSV 내보내기
- 실제 라벨 데이터 기반 보정 후보
  - 기본 운영 전처리인 `WB + CLAHE` 결과 사용
  - 정상 사진 3장과 변화 사진 3장 이상이 모이면 LAB b/a, HSV S의 GOOD/HIGH 후보 계산
  - 후보값은 자동 적용하지 않고 화면에 `.env` 형식으로 제시
- 색상 보정 상수를 `pc_setup/backend/.env`로 조정할 수 있도록 분리

### 검증 완료

- 백엔드 전체 테스트: **11개 통과**
- 프런트엔드 전체 테스트: **39개 통과**
- React 운영 빌드: **성공**
- 팀의 월간 리포트·알림·기존 3회 기준 테스트를 모두 포함한 결과임

### 아직 완료로 판단하면 안 되는 부분

- 기능 구현은 끝났지만 LAB/HSV 숫자는 아직 임상적으로 확정된 값이 아님
- 실제 사진으로 전처리 안정성, 잇몸 ROI, 정상/변화 분리도를 확인해야 함
- 당시 잇몸 후보 영역은 치아 박스 바로 아래 30% 띠였으나, 2026-08-27 실제 사진 검증 후 위·아래 치열 방향을 반영한 15% 방식으로 교체 완료함.
- 공개 전문 카메라 사진만으로 프로젝트 카메라의 최종 색상 임계값을 확정하면 안 됨
- 최종 단계에서는 프로젝트 카메라·LED로 촬영한 동일 대상 사진이 최소 3~6장 필요함

### 실제 사진으로 검증해야 하는 항목 — 코드 확인 결과

아래 항목은 자동 테스트 통과만으로는 확인할 수 없다. 공개 구강 사진으로 1차 확인할 수 있는 것과
프로젝트 카메라·조명으로 직접 촬영해야 확인되는 것을 구분한다.

#### 1. YOLO 박스가 실제 촬영 환경에서도 맞는지

- 서버는 confidence `0.25`로 `cavity`와 `normal`을 탐지한다.
- 실제 카메라 사진에서 충치 누락, 정상을 충치로 잘못 잡는 경우, 한 치아를 여러 번 잡는 경우를 눈으로 확인한다.
- **충치 Recall이 최우선**이므로 알려진 충치 사진에서 놓친 충치 수를 반드시 기록한다. 자가 판단 사진은 임상 정답으로 간주하지 말고, 가능하면 치과 확인 또는 라벨이 있는 공개 사진을 사용한다.
- 황변 계산은 `normal` 박스만 사용하므로 정상 박스를 하나도 찾지 못하면 황변값이 `null`이 될 수 있다.
- 전처리 3종마다 YOLO를 다시 실행하므로 전처리에 따라 충치·정상 개수가 크게 달라지는지도 확인한다.

#### 2. 전처리 3종 중 무엇이 촬영 변화에 가장 안정적인지

- 비교 대상: `original`, `WB + CLAHE`, `WB + Bilateral + CLAHE`.
- 같은 파일을 반복 분석하면 코드의 반복성만 확인된다. **카메라로 연속 3회 따로 촬영한 사진**이 있어야 흔들림·자동노출·화이트밸런스 변화를 검증할 수 있다.
- 동일 대상·동일 조명·동일 거리로 3회 촬영하고 황변 점수, 잇몸 LAB 점수, HSV 보조점수, LAB b/a, HSV S의 범위를 비교한다.
- 밝은 조명, 어두운 조명, 각도 변경 사진도 각각 추가하여 점수와 탐지 개수가 얼마나 흔들리는지 확인한다.
- 우선 선택 기준은 `null` 발생이 없고 YOLO 탐지가 유지되면서 세 색상 점수의 변동 폭이 가장 작은 전처리다. 현재 기본값은 `WB + CLAHE`지만 실제 결과로 확정해야 한다.
- 초기 공학적 목표값은 동일 조건 3회에서 건강점수 범위 5점 이내로 잡되, 실제 분포를 본 뒤 조정한다. 이는 임상 기준이 아니다.

#### 3. 치아 황변 측정이 실제 색 차이를 반영하는지

- `normal` 박스 안의 LAB b* 평균을 사용하며, 너무 밝거나 어두운 픽셀은 제외한다.
- 정상 치아와 육안상 황변된 치아에서 `LAB b*`가 실제로 분리되는지 확인한다.
- 기대 방향은 **황변 사진의 LAB b* 증가, 황변 건강점수 감소**다. 방향이 반대이거나 두 그룹이 겹치면 임계값을 적용하지 않는다.
- 반사광, 침, 그림자, 치아 외 잇몸이 박스에 섞일 때 값이 급변하는지 확인한다.
- 유효 픽셀이 200개 미만이면 점수는 `null`이므로 작은 박스·심한 크롭 사진에서 `황변유효픽셀`도 함께 확인한다.

#### 4. 잇몸 ROI가 실제 잇몸을 잡는지 — 2026-08-27 검증·수정 완료

- 아래 내용은 검증 전 계획 기록이다. 실제 사진 5장과 오버레이로 검증했으며 현재 코드는 위쪽 치열의 위 15%, 아래쪽 치열의 아래 15%를 사용한다. 자세한 결과는 파일 맨 위 2026-08-27 섹션을 우선한다.
- 아랫니에는 맞을 수 있지만 윗니 잇몸은 치아 위쪽에 있으므로, 윗니 사진에서 입술·혀·구강 안쪽을 잘못 측정할 가능성이 있다.
- 윗니 정면, 아랫니 정면, 위·아래 치아가 함께 나온 사진을 따로 확인해야 한다.
- 실제 사진 위에 치아 박스와 선택된 잇몸 영역을 그린 **디버그 오버레이**로 ROI를 눈으로 확인해야 한다. 현재 테스트 화면은 숫자만 보여주므로 이 시각화는 다음 검증 전에 추가하거나 별도 스크립트로 생성한다.
- 30%와 요구사항 후보인 10%, 15%를 비교해 어느 범위가 실제 잇몸을 가장 적게 벗어나는지 결정한다.
- 정상 잇몸과 붉은 잇몸에서 기대 방향은 **LAB a*와 HSV S 증가, 두 건강점수 감소**다.
- `LAB/HSV 일치도`가 반복해서 `low`이면 ROI 오류, 조명 영향 또는 임계값 오류로 보고 원본과 오버레이를 다시 확인한다.
- 잇몸 유효 픽셀도 200개 미만이면 점수가 `null`이므로 `잇몸유효픽셀`을 함께 기록한다.

#### 5. 개인 3회 Baseline 흐름이 실제 촬영에서도 맞는지

- 같은 자녀를 선택하고 건강 상태가 변하지 않은 조건에서 **서로 다른 사진 3장**을 순서대로 분석한다. 같은 파일 3회 재사용은 실제 Baseline 검증으로 인정하지 않는다.
- 1회와 2회 후에는 수집 진행률만 표시되고, 3회 후 `맞춤 기준 완료`, 4번째 촬영부터 기준 대비 점수와 변화량이 나오는지 확인한다.
- 첫 3장 사이의 LAB b/a 편차가 너무 크면 그 평균을 기준으로 확정하지 말고 촬영 조건부터 고정한다.
- 자녀를 두 명 등록했을 때 Baseline이 서로 섞이지 않는지 확인한다.
- `기준 다시 만들기` 실행 후 수집 횟수가 0/3, 기준 세대가 증가하고 기존 촬영 이력·이미지는 그대로 남는지 확인한다.
- 황변 또는 잇몸 측정이 `null`이면 두 Baseline 수집 횟수가 서로 다를 수 있으므로 양쪽 진행률을 모두 확인한다.

#### 6. 저장·결과·그래프까지 전체 흐름 확인

- 로그인하고 자녀를 선택한 상태에서 촬영해야 SQLite에 자녀별 기록, 원본 이미지, LAB 원시값, 기준값, 변화량이 저장되는지 검증할 수 있다.
- 촬영 직후 결과 화면의 탐지 수·색상 점수·Baseline 상태와 히스토리에서 다시 연 기록이 같은지 확인한다.
- 날짜별·월별·연간 그래프는 개인 Baseline이 준비된 기록을 올바르게 사용하는지 확인한다.
- 색상 분석 테스트 기록은 서버 DB가 아니라 **현재 브라우저 로컬 저장소**에만 남는다. 학교 PC로 옮기거나 브라우저 데이터를 지우기 전 반드시 CSV를 내려받는다.

#### 7. 반드시 포함할 촬영 실패 조건

- 초점이 흐린 사진, 과도한 플래시 반사, 너무 어두운 사진, 치아 일부만 나온 사진
- 촬영 거리 변화, 좌우/상하 각도 변화, 입을 덜 벌린 사진
- 침·혀·입술이 많이 보이는 사진, 교정기·보철·충전재가 있는 사진
- 이 조건에서 잘못된 높은 점수를 그대로 보여주는지, `null` 또는 재촬영 안내가 필요한지 판단한다. 현재는 별도 화질 거절 기준이 없으므로 결과에 따라 촬영환경 임계값을 추가한다.

### 실제 사진 최소 수집안

#### A. 기능·안정성 확인용 — 프로젝트 카메라로 최소 7장

1. 같은 대상·같은 조명·정면 사진 3장: 독립 촬영 반복성 및 Baseline 1~3회 확인
2. 같은 조건의 4번째 사진 1장: 개인 기준 대비 점수·변화량 확인
3. 밝은 조명 1장, 어두운 조명 1장, 각도 변경 1장: 전처리 안정성 확인

가능하면 윗니와 아랫니가 모두 포함되게 추가 촬영한다. 이 7장은 기능 검증용이며 정상/황변/염증 판별 임계값을 확정하기에는 부족하다.

#### B. 색상 임계값 후보 확인용

- 화면에서 후보값을 계산하는 최소 조건은 `정상 3장 + 해당 변화 3장`이다.
- 황변과 잇몸을 모두 보려면 최소 `정상 3장 + 황변 3장 + 잇몸 붉음 3장`이 필요하다. `둘 다` 사진은 두 변화 그룹에 함께 포함된다.
- 3장씩으로 나온 값은 기능 확인용 후보일 뿐이다. 최종값은 가능하면 각 그룹 10장 이상, 여러 사람과 여러 촬영일을 포함하고 라벨 근거를 확인한 뒤 정한다.
- 공개 사진은 정상/변화 방향과 ROI 코드의 1차 검증에 사용하고, 프로젝트 카메라의 최종 임계값과 촬영 안정성은 직접 촬영 사진으로 결정한다.

### 실제 사진 검증 결과 기록 형식

각 사진마다 `대상 ID(익명) / 촬영일 / 카메라 / LED 단계 / 거리 / 각도 / 윗니·아랫니 / 참고 상태 / 육안 YOLO 오류 / null 여부 / 메모`를 남긴다.
색상 테스트 화면에서 CSV를 내려받고, ROI 디버그 이미지는 원본 파일명과 연결되게 보관한다. 얼굴·이름 등 개인정보가 포함된 사진은 공개 GitHub에 올리지 않는다.

### 공개 사진 검증 계획

사용자가 직접 촬영하기 전에 공개 데이터로 초기 검증 가능함.

1. 우선 후보: MIO 공개 데이터셋
   - 건강한 잇몸, 치은염, 치주염으로 분류된 전문가 검증 구강 사진 765장
   - https://zenodo.org/records/21140854
   - 정상(`SANO.zip`) 약 433.8MB + 치은염(`GINGIVITIS.zip`) 약 441.6MB
2. 보조 후보: Gingivitis Image Captioning Dataset
   - MGI 0~4 단계가 표시된 고해상도 구강 사진 1,096장
   - https://data.mendeley.com/datasets/3253gj88rr/1
3. 정상 3장·치은염 3장 이상을 먼저 뽑아 전처리 3종, LAB·HSV, 잇몸 ROI를 비교
4. 공개 데이터로 코드와 초기 범위를 검증한 뒤 프로젝트 카메라 사진으로 최종 보정

### 2026-08-26 MIO 공개 사진 1차 검증 완료

- Kaggle 비공개 노트북: `pthkbs/mio-color-preprocessing-validation` Version 1
- 자료: MIO의 전문가 촬영 정상 잇몸 12장 + 치은염 12장, 총 24장
- 모델: `best_runG_A.pt`, confidence `0.25`
- 비교 전처리: `original`, `WB + CLAHE`, `WB + Bilateral + CLAHE`
- 비교 ROI: 치아 박스 위/아래 각각 `10%`, `15%`, `30%`
- 생성 파일: `mio_color_metrics.csv`, `mio_roi_comparison.csv`, `mio_roi_contact_sheet.jpg`, `mio_validation_summary.json`

#### 수치 결과

정상 대비 치은염에서 `LAB a*`와 `HSV S`가 함께 증가하는지를 1차 방향성 기준으로 확인했다.

| 전처리 | ROI | 치은염-정상 LAB a* | 치은염-정상 HSV S | 기대 방향 |
|---|---:|---:|---:|---|
| original | above 10% | +3.428 | +8.198 | 충족 |
| original | above 15% | +3.074 | +8.212 | 충족 |
| original | above 30% | +2.297 | +8.681 | 충족 |
| original | below 10% | +0.177 | +16.184 | 충족 |
| original | below 15% | +0.327 | +13.293 | 충족 |
| original | below 30% | -0.054 | +9.269 | 불충족 |
| WB + CLAHE | 모든 ROI | LAB a* 감소, HSV S도 대부분 감소 |  | 불충족 |
| WB + Bilateral + CLAHE | 모든 ROI | LAB a*가 대부분 감소, HSV S도 대부분 감소 |  | 불충족 |

- 24장 표본에서는 모든 조합의 잇몸 유효 픽셀 확보율이 `100%`였다.
- 원본의 사진당 YOLO 탐지 중앙값은 정상 `21.5`, 치은염 `20.5`였다.
- `WB + CLAHE`는 정상 `19.0`, 치은염 `21.5`, `WB + Bilateral + CLAHE`는 정상 `20.0`, 치은염 `20.5`였다.
- 이 표본에서는 색상 보정 전처리가 정상/치은염 사이의 원래 색 차이를 약화하거나 뒤집었다. 따라서 **잇몸 염증 색상 계산의 기본 입력을 WB + CLAHE로 확정하면 안 되며, 현재 1순위 후보는 original**이다.
- 서로 다른 대상의 사진을 비교한 결과이므로 같은 대상을 연속 촬영했을 때의 전처리 안정성은 아직 검증되지 않았다.

#### ROI 오버레이 육안 확인

- 윗니 박스에서는 위쪽 띠가 실제 잇몸과 맞고, 아랫니 박스에서는 아래쪽 띠가 실제 잇몸과 맞았다.
- 모든 치아에 `below 30%`를 고정하는 현재 방식은 윗니에서 잘못된 조직을 포함할 위험이 실제로 확인됐다.
- 30%는 주변 조직 포함 범위가 커지므로, 다음 구현 후보는 **15%를 기본 폭으로 하고 위/아래 후보 중 잇몸색 유효 픽셀과 위치 조건이 더 적절한 쪽을 자동 선택**하는 방식이다.
- 공개 사진 24장만으로 임상 임계값을 확정하지 않는다. MIO에는 황변 정답 라벨이 없으므로 이번 결과로 황변 분리 성능도 판단할 수 없다.

#### 이번 검증으로 바뀐 다음 작업

1. 잇몸 ROI를 `below 30%` 고정 방식에서 `above/below 15%` 적응형 선택으로 수정
2. 잇몸 염증용 색상 입력은 `original`과 보정 영상 결과를 분리하고, 공개 사진에서는 original을 우선 사용
3. 같은 사람을 프로젝트 카메라·LED로 3회 촬영해 탐지 수와 LAB/HSV 변동 폭을 비교
4. 프로젝트 카메라 사진에서 15% 적응형 ROI 오버레이를 다시 육안 검증
5. 정상/치은염 라벨 수를 늘린 뒤 보정 상수와 임계값 후보를 다시 계산

### 학교 PC에서 이어가는 순서

PR이 아직 병합되지 않았다면:

```bash
git clone https://github.com/pthkbs123/matchpoint.git
cd matchpoint
git remote add upstream https://github.com/yuly0531/matchpoint.git
git fetch --all --prune
git switch feature/color-analysis-completion
```

이미 저장소가 있다면:

```bash
git fetch --all --prune
git switch feature/color-analysis-completion
git pull origin feature/color-analysis-completion
```

PR이 팀 `main`에 병합된 뒤라면 개인 기능 브랜치 대신 팀 `main`을 사용:

```bash
git fetch upstream
git switch main
git pull upstream main
```

프런트엔드와 백엔드 실행 전 의존성 설치:

```bash
npm install
cd pc_setup/backend
python -m venv venv
venv\Scripts\activate
pip install -r ../requirements.txt
```

### 학교 PC에서 반드시 다시 만들어야 하는 로컬 설정

`.env`는 보안상 Git에서 제외되므로 클론해도 따라오지 않음. 카카오 로그인에서
`카카오 JavaScript 키가 설정되지 않았습니다`가 나오면 코드 오류가 아니라 `.env` 누락임.

- 프로젝트 루트 `.env`: `.env.example`을 복사하고 `REACT_APP_KAKAO_JAVASCRIPT_KEY` 등 공개 키 입력
- `pc_setup/backend/.env`: `.env.example`을 복사하고 `KAKAO_REST_API_KEY` 등 서버 키 입력
- `.env` 작성 후 React와 FastAPI 서버를 모두 재시작
- 실제 키나 Client Secret을 Git에 커밋하지 말 것

### 다음 작업 우선순위

1. 생성한 PR의 팀 리뷰·병합 여부 확인
2. ~~공개 정상/치은염 사진 표본 선정과 전처리 3종 비교~~ — MIO 24장으로 1차 완료
3. ~~LAB/HSV 방향성과 10/15/30% ROI 비교~~ — original과 적응형 15% 후보 도출
4. 잇몸 ROI를 위/아래 15% 적응형 선택 방식으로 구현하고 테스트 추가
5. 프로젝트 카메라·LED로 같은 대상 3회 이상 촬영해 반복 안정성 검증
6. 실제 촬영 결과로 최종 임계값과 보정 상수 결정

---

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
  - `compute_gum_inflammation_index`: 이 시점의 초기 구현은 박스 아래 30% 띠였으나 2026-08-27 위·아래 치열 방향을 반영한 15% 방식으로 교체됨. HSV 점막색 필터와 Hue wraparound 처리는 그대로 유지함.
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
