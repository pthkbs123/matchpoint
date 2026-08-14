"""
Run B: 기존 best.pt를 베이스로, dataset_runA 전체 + 데이터셋2(Caries_Dataset, 라벨 없어서
이미지 전체를 박스로 처리)까지 합본으로 이어서 학습.

사용법:
    python build_datasets.py   # 아직 안 돌렸으면 먼저 실행
    python train_runB.py
학습 끝나면 runs/detect/cavity_train_runB/weights/best.pt 생성.
"""
from pathlib import Path

from ultralytics import YOLO

PC_SETUP = Path(__file__).resolve().parent.parent  # pc_setup/ (이 파일은 pc_setup/training/ 안에 있음)


def main():
    model = YOLO(str(PC_SETUP / "backend" / "model" / "best.pt"))

    model.train(
        data=str(PC_SETUP / "dataset_runB" / "data.yaml"),
        epochs=100,
        imgsz=640,
        batch=8,
        patience=20,
        project=str(PC_SETUP / "runs" / "detect"),
        name="cavity_train_runB",
        device=0,
    )

    metrics = model.val()
    print(metrics)


if __name__ == "__main__":
    main()
