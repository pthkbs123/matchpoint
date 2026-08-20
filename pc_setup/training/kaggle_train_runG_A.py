"""
Run G - 실험 A: runD의 best.pt를 이어받아 dataset_runG(leakage-free, ICDAS 수정 반영)로 fine-tuning.

실험 B(kaggle_train_runG_B.py, pretrained에서 새로 시작)와 최대한 동일한 조건으로 맞춤:
  imgsz, batch, epochs, patience, device 전부 동일.
  차이는 오직 "시작 가중치"뿐 (A=runD best.pt, B=공식 yolov8n.pt pretrained).

목적: runD가 이미 학습해버린 "잘못된 ICDAS 기준"의 영향이 fine-tuning으로도 남아있는지,
아니면 새로 처음부터 학습(B)하는 게 더 나은지 비교.

사전 준비 (Kaggle 웹사이트에서):
  1) hanium_dataset -> New Version -> dataset_runG.zip 업로드 (best.pt는 이미 runD 결과 있음)
  2) Accelerator: GPU T4 x2
  3) 이 코드 그대로 셀에 붙여넣고 실행 -> Save & Run All
"""

import subprocess
subprocess.run(["pip", "install", "-q", "ultralytics"], check=True)

from pathlib import Path
from ultralytics import YOLO

yaml_candidates = list(Path("/kaggle/input").rglob("dataset_runG/data.yaml"))
assert yaml_candidates, "data.yaml을 못 찾았어요. dataset_runG가 노트북에 Add Input 되어있는지 확인해주세요."
DATA_YAML = yaml_candidates[0]
print("사용할 data.yaml:", DATA_YAML)

pt_candidates = [p for p in Path("/kaggle/input").rglob("best.pt")]
assert pt_candidates, "runD의 best.pt를 못 찾았어요."
print("이어서 학습할 best.pt (runD):", pt_candidates[0])
model = YOLO(str(pt_candidates[0]))

model.train(
    data=str(DATA_YAML),
    epochs=80,
    imgsz=640,
    batch=64,
    patience=30,
    seed=42,
    project="/kaggle/working/runs/detect",
    name="cavity_train_runG_A_finetune",
    device=[0, 1],
)

metrics = model.val(split="test")
print(metrics)
print("best.pt:", "/kaggle/working/runs/detect/cavity_train_runG_A_finetune/weights/best.pt")
