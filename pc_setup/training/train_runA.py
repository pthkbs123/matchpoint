"""
Run A: 기존 best.pt를 베이스로, dataset_yolo(418) + 데이터셋1(ICDAS 7단계->2클래스 재매핑, 2000장) 합본으로 이어서 학습.
데이터셋2(Caries_Dataset)는 포함하지 않음.

사용법:
    python build_datasets.py   # 아직 안 돌렸으면 먼저 실행 (dataset_runA/, dataset_runB/ 생성)
    python train_runA.py
학습 끝나면 runs/detect/cavity_train_runA/weights/best.pt 생성.
"""
from pathlib import Path

from ultralytics import YOLO

PC_SETUP = Path(__file__).resolve().parent.parent  # pc_setup/ (이 파일은 pc_setup/training/ 안에 있음)


def main():
    model = YOLO(str(PC_SETUP / "backend" / "model" / "best.pt"))  # 처음부터가 아니라 기존 학습 결과에서 이어서

    model.train(
        data=str(PC_SETUP / "dataset_runA" / "data.yaml"),
        epochs=100,
        imgsz=640,
        batch=8,
        patience=20,
        project=str(PC_SETUP / "runs" / "detect"),
        name="cavity_train_runA",
        device=0,
    )

    metrics = model.val()
    print(metrics)


if __name__ == "__main__":
    main()
