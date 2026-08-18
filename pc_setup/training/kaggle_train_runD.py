"""
Kaggle Notebook 셀에 그대로 붙여넣어서 실행하는 학습 스크립트 (Run D).
runC 학습이 끝나 나온 best.pt를 베이스로, dataset_runD(runC 전체 + 새 데이터셋4)로 이어서 학습.

사전 준비 (Kaggle 웹사이트에서):
  1) kaggle.com -> Datasets -> New Dataset
     -> dataset_runD.zip 과, runC 학습 결과로 받은 best.pt를 같은 업로드 창에 함께 올리기
  2) New Notebook 생성 -> Settings에서 Accelerator: GPU T4 x2, Add Input으로 데이터셋 attach
  3) 아래 코드를 셀에 그대로 붙여넣고 실행
"""

import subprocess
subprocess.run(["pip", "install", "-q", "ultralytics"], check=True)

from pathlib import Path
from ultralytics import YOLO

yaml_candidates = list(Path("/kaggle/input").rglob("dataset_runD/data.yaml"))
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
    epochs=100,
    imgsz=640,
    batch=64,
    patience=20,
    project="/kaggle/working/runs/detect",
    name="cavity_train_runD",
    device=[0, 1],
)

metrics = model.val()
print(metrics)
print("best.pt:", "/kaggle/working/runs/detect/cavity_train_runD/weights/best.pt")
