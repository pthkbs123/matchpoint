"""
Kaggle Notebook 셀에 그대로 붙여넣어서 실행하는 학습 스크립트.
로컬에서 화면이 멈추는 GPU 문제를 피하려고 Kaggle 클라우드 GPU에서 대신 학습합니다.

사전 준비 (Kaggle 웹사이트에서):
  1) kaggle.com -> Datasets -> New Dataset
     -> dataset_runC.zip 과 best.pt 를 같은 업로드 창에 함께 드래그해서 올리기
     (zip은 자동으로 풀리고 best.pt는 그 옆에 파일로 남음)
  2) New Notebook 생성 -> 오른쪽 Settings
     - Accelerator: GPU T4 x2 (또는 P100)
     - Add data: 위에서 만든 데이터셋 attach
  3) 아래 코드를 셀에 그대로 붙여넣고 실행
     (Kaggle이 데이터셋을 /kaggle/input 밑에 마운트할 때 폴더를 이중으로 감싸는 경우가 있어서
      경로를 하드코딩하지 않고 /kaggle/input 전체에서 data.yaml / best.pt를 자동으로 찾음)
"""

import subprocess
subprocess.run(["pip", "install", "-q", "ultralytics"], check=True)

from pathlib import Path
from ultralytics import YOLO

yaml_candidates = list(Path("/kaggle/input").rglob("dataset_runC/data.yaml"))
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
    batch=32,          # 클라우드 GPU는 VRAM 여유 있으니 배치 키워도 됨 (T4 16GB 기준)
    patience=20,
    project="/kaggle/working/runs/detect",
    name="cavity_train_runC",
    device=0,
)

metrics = model.val()
print(metrics)

# 학습 끝나면 아래 경로에서 best.pt 다운로드:
print("best.pt:", "/kaggle/working/runs/detect/cavity_train_runC/weights/best.pt")
