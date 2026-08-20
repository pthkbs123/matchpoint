"""
Run G - 실험 B: 공식 pretrained YOLOv8n 가중치에서 dataset_runG(leakage-free, ICDAS 수정 반영)로 새로 학습.

실험 A(kaggle_train_runG_A.py, runD best.pt에서 이어학습)와 조건 동일 (imgsz/batch/epochs/patience/seed/device).
차이는 시작 가중치만: A=runD best.pt, B=공식 yolov8n.pt.

목적: runD가 학습해버린 "잘못된 ICDAS 기준"의 영향이 fine-tuning(A)에도 남아있는지 확인하기 위한 대조군.

사전 준비: kaggle_train_runG_A.py와 동일 (같은 노트북에서 이어서 실행해도 되고, 새 노트북이어도 됨).
"""

import subprocess
subprocess.run(["pip", "install", "-q", "ultralytics"], check=True)

from pathlib import Path
from ultralytics import YOLO

yaml_candidates = list(Path("/kaggle/input").rglob("dataset_runG/data.yaml"))
assert yaml_candidates, "data.yaml을 못 찾았어요. dataset_runG가 노트북에 Add Input 되어있는지 확인해주세요."
DATA_YAML = yaml_candidates[0]
print("사용할 data.yaml:", DATA_YAML)

print("공식 pretrained yolov8n.pt로 처음부터 학습")
model = YOLO("yolov8n.pt")

model.train(
    data=str(DATA_YAML),
    epochs=80,
    imgsz=640,
    batch=64,
    patience=30,
    seed=42,
    project="/kaggle/working/runs/detect",
    name="cavity_train_runG_B_fresh",
    device=[0, 1],
)

metrics = model.val(split="test")
print(metrics)
print("best.pt:", "/kaggle/working/runs/detect/cavity_train_runG_B_fresh/weights/best.pt")
