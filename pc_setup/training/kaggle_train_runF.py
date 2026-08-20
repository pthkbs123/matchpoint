"""
Kaggle Notebook 셀에 그대로 붙여넣어서 실행하는 학습 스크립트 (Run F).
runD 학습이 끝나 나온 best.pt를 베이스로, dataset_runF(runE와 이미지 구성은 동일, ICDAS 라벨만 재매핑)로 이어서 학습.

runE 대비 바뀐 것: 이미지/분할은 동일, ICDAS 소스(2,000장)의 클래스 재매핑 기준만 수정
  - 기존: ICDAS 0(Sound)만 normal, 1~6 전부 cavity
  - 변경: 0(Sound)/1(Faint)/2(Distinct) -> normal, 3(국소붕괴)/4(상아질음영)/5(뚜렷cavity)/6(광범위) -> cavity
  - 근거: dataset_audit로 HIGH 우선순위 이미지 중 ICDAS 소스가 36.6%를 차지했고, 그 원본 라벨의 30.6%가
    1~2단계(육안으로 거의 안 보이는 초기 변화)였음. 이게 cavity로 뭉뚱그려지면서
    "사진은 정상처럼 보이는데 GT는 cavity"인 노이즈가 대량 발생 -> cavity recall 저하의 유력한 원인으로 추정.
  - 결과: cavity 박스 8,917개 -> 5,480개 (-38.5%)

**주의 (9시간 세션 제한)**: dataset_runF는 runD보다 train 이미지가 23% 많아서(35,690장),
100epoch 그대로 돌리면 약 10.8시간 예상되어 Kaggle 무료 세션 제한(약 9시간)을 넘길 위험이 있음.
그래서 epochs=80으로 낮춤 (약 8.7시간 예상, 살짝 넘길 수도 있지만 크게 넘기진 않을 것으로 판단하고 진행하기로 함).

사전 준비 (Kaggle 웹사이트에서):
  1) kaggle.com -> Datasets -> hanium_dataset -> New Version
     -> dataset_runF.zip 을 새로 올리기 (best.pt는 이미 runD 결과가 올라가 있으니 새로 안 올려도 됨)
  2) 노트북 Settings에서 Accelerator: GPU T4 x2 확인 (멀티 GPU 씀)
  3) 아래 코드를 셀에 그대로 붙여넣고 실행 -> Save & Run All 권장 (창 닫아도 완주됨)
"""

import subprocess
subprocess.run(["pip", "install", "-q", "ultralytics"], check=True)

from pathlib import Path
from ultralytics import YOLO

yaml_candidates = list(Path("/kaggle/input").rglob("dataset_runF/data.yaml"))
assert yaml_candidates, "data.yaml을 못 찾았어요. dataset_runF가 노트북에 Add Input 되어있는지 확인해주세요."
DATA_YAML = yaml_candidates[0]
print("사용할 data.yaml:", DATA_YAML)

pt_candidates = list(Path("/kaggle/input").rglob("best.pt"))
if pt_candidates:
    print("이어서 학습할 best.pt:", pt_candidates[0])
    model = YOLO(str(pt_candidates[0]))
else:
    print("best.pt 없음 -> yolov8n.pt로 처음부터 학습")
    model = YOLO("yolov8n.pt")

model.train(
    data=str(DATA_YAML),
    epochs=80,
    imgsz=640,
    batch=64,
    patience=30,
    project="/kaggle/working/runs/detect",
    name="cavity_train_runF",
    device=[0, 1],
)

metrics = model.val()
print(metrics)
print("best.pt:", "/kaggle/working/runs/detect/cavity_train_runF/weights/best.pt")
