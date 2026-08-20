"""
kaggle_audit_infer.py와 동일한 로직을 로컬에서 runG valid+test에 대해 실행.
(runG는 이미지 수가 관리 가능한 범위라 로컬 GPU로도 충분함, Kaggle 안 씀)
"""
import csv
from pathlib import Path

from ultralytics import YOLO

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_G = REPO_ROOT / "pc_setup/dataset_runG"
MODEL_PATH = REPO_ROOT / "pc_setup/backend/model/best_runD_backup.pt"
OUT_DIR = REPO_ROOT / "pc_setup/dataset_audit/kaggle_output"

MATCH_IOU_THRESHOLD = 0.5
LOW_IOU_GOOD_THRESHOLD = 0.7
HIGH_CONF_THRESHOLD = 0.75
MEDIUM_CONF_THRESHOLD = 0.45
CLASS_NAMES = {0: "cavity", 1: "normal"}


def iou_xyxy(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def yolo_to_xyxy(cx, cy, w, h, img_w, img_h):
    return ((cx - w / 2) * img_w, (cy - h / 2) * img_h, (cx + w / 2) * img_w, (cy + h / 2) * img_h)


def read_gt_boxes(label_path, img_w, img_h):
    boxes = []
    if not label_path.exists():
        return boxes
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) != 5:
            continue
        cls, cx, cy, w, h = int(parts[0]), *map(float, parts[1:])
        boxes.append({"cls": cls, "xyxy": yolo_to_xyxy(cx, cy, w, h, img_w, img_h)})
    return boxes


def match_and_classify(gt_boxes, pred_boxes):
    issues = []
    matched = set()
    for gt in gt_boxes:
        best_iou, best_j = 0.0, -1
        for j, pred in enumerate(pred_boxes):
            if j in matched:
                continue
            iou = iou_xyxy(gt["xyxy"], pred["xyxy"])
            if iou > best_iou:
                best_iou, best_j = iou, j
        if best_j == -1 or best_iou < MATCH_IOU_THRESHOLD:
            if gt["cls"] == 0:
                issues.append({"type": "CAVITY_MISSED", "gt_cls": 0, "pred_cls": None, "conf": None, "iou": None})
            continue
        matched.add(best_j)
        pred = pred_boxes[best_j]
        if pred["cls"] == gt["cls"]:
            if best_iou < LOW_IOU_GOOD_THRESHOLD:
                issues.append({"type": "LOW_IOU", "gt_cls": gt["cls"], "pred_cls": pred["cls"], "conf": pred["conf"], "iou": best_iou})
            elif pred["conf"] < MEDIUM_CONF_THRESHOLD:
                issues.append({"type": "UNCERTAIN_SAMPLE", "gt_cls": gt["cls"], "pred_cls": pred["cls"], "conf": pred["conf"], "iou": best_iou})
        elif gt["cls"] == 0 and pred["cls"] == 1:
            issues.append({"type": "CAVITY_AS_NORMAL", "gt_cls": 0, "pred_cls": 1, "conf": pred["conf"], "iou": best_iou})
        elif gt["cls"] == 1 and pred["cls"] == 0:
            issues.append({"type": "NORMAL_AS_CAVITY", "gt_cls": 1, "pred_cls": 0, "conf": pred["conf"], "iou": best_iou})
    for j, pred in enumerate(pred_boxes):
        if j in matched or pred["conf"] < HIGH_CONF_THRESHOLD:
            continue
        issues.append({"type": "POSSIBLE_MISSING_CAVITY_LABEL" if pred["cls"] == 0 else "POSSIBLE_MISSING_NORMAL_LABEL",
                        "gt_cls": None, "pred_cls": pred["cls"], "conf": pred["conf"], "iou": None})
    return issues


def run_split(model, split):
    images_dir = RUN_G / split / "images"
    labels_dir = RUN_G / split / "labels"
    image_paths = sorted(list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png")))
    rows = []
    for i, img_path in enumerate(image_paths):
        try:
            result = model.predict(str(img_path), conf=0.1, verbose=False)[0]
            img_h, img_w = result.orig_shape
            gt_boxes = read_gt_boxes(labels_dir / (img_path.stem + ".txt"), img_w, img_h)
            pred_boxes = []
            if result.boxes is not None:
                for box in result.boxes:
                    pred_boxes.append({"cls": int(box.cls[0]), "conf": float(box.conf[0]), "xyxy": tuple(box.xyxy[0].tolist())})
            for issue in match_and_classify(gt_boxes, pred_boxes):
                rows.append({
                    "image": img_path.name, "issue_type": issue["type"],
                    "gt_class": CLASS_NAMES.get(issue["gt_cls"], ""),
                    "pred_class": CLASS_NAMES.get(issue["pred_cls"], ""),
                    "confidence": round(issue["conf"], 4) if issue["conf"] is not None else "",
                    "iou": round(issue["iou"], 4) if issue["iou"] is not None else "",
                })
        except Exception as e:
            rows.append({"image": img_path.name, "issue_type": "PROCESSING_ERROR", "gt_class": "", "pred_class": "", "confidence": "", "iou": str(e)[:200]})
        if (i + 1) % 1000 == 0:
            print(f"  {split} {i + 1}/{len(image_paths)}")
    return rows


def main():
    model = YOLO(str(MODEL_PATH))
    for split in ("valid", "test"):
        print(f"=== runG {split} 추론 시작 ===")
        rows = run_split(model, split)
        out_csv = OUT_DIR / f"dataset_audit_runG_{split}.csv"
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["image", "issue_type", "gt_class", "pred_class", "confidence", "iou"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"완료: {out_csv} ({len(rows)}건)")


if __name__ == "__main__":
    main()
