"""
Kaggle Notebook 셀에 그대로 붙여넣어서 실행하는 학습 스크립트 (Run E).
runD 학습이 끝나 나온 best.pt를 베이스로, dataset_runE(runD 전체 + 새 데이터셋3)로 이어서 학습.

runD 대비 추가된 것:
  - DentalCaries.v2i.yolov8 (4,663장, train에만 전부 포함 - 원본 zip에 valid/test 분할이 없었음)
  - caries detection.v1i.yolov8 (중복 제거 후 499장 - DentalCaries.v2i와 80% 겹쳐서 중복 제거함)
  - Zenodo Benchmarking Dataset (라벨 있는 2,164장만 - 나머지 4,102장은 라벨 없어서 제외)

사전 준비 (Kaggle 웹사이트에서):
  1) kaggle.com -> Datasets -> hanium_dataset -> New Version
     -> dataset_runE.zip 과, runD 학습 결과로 받은 best.pt를 함께 올리기
  2) 노트북 Settings에서 Accelerator: GPU T4 x2 확인 (멀티 GPU 씀)
  3) 아래 코드를 셀에 그대로 붙여넣고 실행
"""

import subprocess
subprocess.run(["pip", "install", "-q", "ultralytics"], check=True)

from pathlib import Path
from ultralytics import YOLO

yaml_candidates = list(Path("/kaggle/input").rglob("dataset_runE/data.yaml"))
assert yaml_candidates, "data.yaml을 못 찾았어요. 데이터셋이 노트북에 Add Input 되어있는지 확인해주세요."
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
    epochs=120,
    imgsz=640,
    batch=64,
    patience=50,
    project="/kaggle/working/runs/detect",
    name="cavity_train_runE",
    device=[0, 1],
)

metrics = model.val()
print(metrics)
print("best.pt:", "/kaggle/working/runs/detect/cavity_train_runE/weights/best.pt")
