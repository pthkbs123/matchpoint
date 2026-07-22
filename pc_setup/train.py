"""
YOLOv8 충치(cavity) 탐지 모델 학습 스크립트
사용법:
    1) pip install -r requirements.txt
    2) dataset_yolo_converted.zip 압축을 이 파일과 같은 위치에 풀기 (dataset_yolo/ 폴더 생성됨)
    3) python train.py
학습이 끝나면 runs/detect/train/weights/best.pt 가 생성됩니다.
이 best.pt 를 backend/model/best.pt 로 복사해서 서버에서 사용하세요.
"""
from ultralytics import YOLO

def main():
    # yolov8n(nano) = 가장 가볍고 빠름. 정확도 더 필요하면 yolov8s.pt 로 변경 가능
    model = YOLO("yolov8n.pt")

    model.train(
        data="dataset_yolo/data.yaml",
        epochs=100,
        imgsz=640,
        batch=8,           # GTX 1060 3GB라 VRAM 부족 방지 위해 16→8로 축소
        patience=20,       # 20 epoch 동안 개선 없으면 조기 종료
        project="runs/detect",
        name="cavity_train",
        device=0,          # GPU(0번, GTX 1060) 사용
    )

    # 학습 완료 후 valid셋으로 성능 확인
    metrics = model.val()
    print(metrics)

if __name__ == "__main__":
    main()
