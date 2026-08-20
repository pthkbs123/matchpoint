"""
Kaggle Notebook 셀에 그대로 붙여넣어서 실행하는 데이터셋 감사(audit) 추론 스크립트.
valid set(6,059장)에 대해 best.pt로 추론 -> GT와 IoU 매칭 -> 오류/취약 샘플 후보를 csv로만 저장.
이미지는 다시 저장하지 않음 (로컬에 이미 원본이 있으므로 로컬 스크립트가 파일명 기준으로 불러와 contact sheet 생성).

사전 준비 (Kaggle 웹사이트에서):
  1) New Notebook 생성 -> Settings에서 Accelerator: GPU T4 x2 (코드에서 device=0만 사용)
  2) Add Input으로 hanium_dataset attach (dataset_runD, best.pt 포함)
  3) 아래 코드를 셀에 그대로 붙여넣고 실행 -> Save & Run All 권장 (창 닫아도 완주됨)
  4) 끝나면 Output의 dataset_audit_valid.csv, label_issues_valid.csv 다운로드해서 로컬로 가져오기

기본은 valid만 검사. train까지 검사하려면 SPLIT = "train"으로 바꿔서 한 번 더 실행.
"""

import subprocess
subprocess.run(["pip", "install", "-q", "ultralytics"], check=True)

import csv
from pathlib import Path
from ultralytics import YOLO

SPLIT = "valid"
DATASET_NAME = "dataset_runD"

MATCH_IOU_THRESHOLD = 0.5
LOW_IOU_GOOD_THRESHOLD = 0.7
HIGH_CONF_THRESHOLD = 0.75
MEDIUM_CONF_THRESHOLD = 0.45
DUPLICATE_IOU_THRESHOLD = 0.90
CLASS_CONFLICT_IOU_THRESHOLD = 0.5
PREDICT_CONF_FLOOR = 0.1

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
    x1 = (cx - w / 2) * img_w
    y1 = (cy - h / 2) * img_h
    x2 = (cx + w / 2) * img_w
    y2 = (cy + h / 2) * img_h
    return (x1, y1, x2, y2)


def read_gt_labels(label_path, img_w, img_h):
    boxes = []
    invalid = []
    if not label_path.exists():
        return boxes, invalid
    for line_no, line in enumerate(label_path.read_text(encoding="utf-8").splitlines(), start=1):
        parts = line.strip().split()
        if len(parts) != 5:
            continue
        cls, cx, cy, w, h = int(parts[0]), *map(float, parts[1:])
        reason = None
        if not (0 <= cx <= 1 and 0 <= cy <= 1 and 0 <= w <= 1 and 0 <= h <= 1):
            reason = "OUT_OF_RANGE"
        elif w <= 0 or h <= 0:
            reason = "ZERO_SIZE"
        if reason:
            invalid.append((line_no, reason, line.strip()))
            continue
        boxes.append({"cls": cls, "xyxy": yolo_to_xyxy(cx, cy, w, h, img_w, img_h)})
    return boxes, invalid


def find_label_issues(gt_boxes):
    issues = []
    for i in range(len(gt_boxes)):
        for j in range(i + 1, len(gt_boxes)):
            a, b = gt_boxes[i], gt_boxes[j]
            iou = iou_xyxy(a["xyxy"], b["xyxy"])
            if a["cls"] == b["cls"] and iou >= DUPLICATE_IOU_THRESHOLD:
                issues.append(("DUPLICATE_LABEL", a["cls"], b["cls"], iou))
            elif a["cls"] != b["cls"] and iou >= CLASS_CONFLICT_IOU_THRESHOLD:
                issues.append(("CLASS_CONFLICT", a["cls"], b["cls"], iou))
    return issues


def match_and_classify(gt_boxes, pred_boxes):
    issues = []
    matched_pred_idx = set()
    for gt in gt_boxes:
        best_iou, best_j = 0.0, -1
        for j, pred in enumerate(pred_boxes):
            if j in matched_pred_idx:
                continue
            iou = iou_xyxy(gt["xyxy"], pred["xyxy"])
            if iou > best_iou:
                best_iou, best_j = iou, j
        if best_j == -1 or best_iou < MATCH_IOU_THRESHOLD:
            if gt["cls"] == 0:
                issues.append({"type": "CAVITY_MISSED", "gt_cls": 0, "pred_cls": None, "conf": None, "iou": None})
            continue
        matched_pred_idx.add(best_j)
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
        if j in matched_pred_idx or pred["conf"] < HIGH_CONF_THRESHOLD:
            continue
        if pred["cls"] == 0:
            issues.append({"type": "POSSIBLE_MISSING_CAVITY_LABEL", "gt_cls": None, "pred_cls": 0, "conf": pred["conf"], "iou": None})
        else:
            issues.append({"type": "POSSIBLE_MISSING_NORMAL_LABEL", "gt_cls": None, "pred_cls": 1, "conf": pred["conf"], "iou": None})
    return issues


yaml_candidates = list(Path("/kaggle/input").rglob(f"{DATASET_NAME}/data.yaml"))
assert yaml_candidates, "data.yaml을 못 찾았어요. hanium_dataset이 Input에 추가되어있는지 확인해주세요."
DATA_YAML = yaml_candidates[0]
DATASET_ROOT = DATA_YAML.parent
print("사용할 data.yaml:", DATA_YAML)

pt_candidates = list(Path("/kaggle/input").rglob("best.pt"))
assert pt_candidates, "best.pt를 못 찾았어요."
MODEL_PATH = pt_candidates[0]
print("사용할 best.pt:", MODEL_PATH)

model = YOLO(str(MODEL_PATH))

images_dir = DATASET_ROOT / SPLIT / "images"
labels_dir = DATASET_ROOT / SPLIT / "labels"
image_paths = sorted(list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpeg")))
print(f"{SPLIT} 이미지 수: {len(image_paths)}")

out_dir = Path("/kaggle/working")
audit_rows = []
label_issue_rows = []
error_count = 0

for idx, img_path in enumerate(image_paths):
    try:
        result = model.predict(str(img_path), conf=PREDICT_CONF_FLOOR, verbose=False, device=0)[0]
        img_h, img_w = result.orig_shape

        gt_boxes, invalid_labels = read_gt_labels(labels_dir / (img_path.stem + ".txt"), img_w, img_h)
        for line_no, reason, raw in invalid_labels:
            label_issue_rows.append({
                "image": img_path.name, "issue_type": f"INVALID_BBOX_{reason}",
                "line_no": line_no, "raw_line": raw, "cls_a": "", "cls_b": "", "iou": "",
            })
        for issue_type, cls_a, cls_b, iou in find_label_issues(gt_boxes):
            label_issue_rows.append({
                "image": img_path.name, "issue_type": issue_type,
                "line_no": "", "raw_line": "", "cls_a": CLASS_NAMES.get(cls_a, cls_a),
                "cls_b": CLASS_NAMES.get(cls_b, cls_b), "iou": round(iou, 4),
            })

        pred_boxes = []
        if result.boxes is not None:
            for box in result.boxes:
                xyxy = tuple(box.xyxy[0].tolist())
                pred_boxes.append({"cls": int(box.cls[0]), "conf": float(box.conf[0]), "xyxy": xyxy})

        for issue in match_and_classify(gt_boxes, pred_boxes):
            audit_rows.append({
                "image": img_path.name,
                "issue_type": issue["type"],
                "gt_class": CLASS_NAMES.get(issue["gt_cls"], ""),
                "pred_class": CLASS_NAMES.get(issue["pred_cls"], ""),
                "confidence": round(issue["conf"], 4) if issue["conf"] is not None else "",
                "iou": round(issue["iou"], 4) if issue["iou"] is not None else "",
            })
    except Exception as e:
        error_count += 1
        audit_rows.append({
            "image": img_path.name, "issue_type": "PROCESSING_ERROR",
            "gt_class": "", "pred_class": "", "confidence": "", "iou": str(e)[:200],
        })

    if (idx + 1) % 500 == 0:
        print(f"{idx + 1}/{len(image_paths)} 처리, 지금까지 오류 {error_count}건")

audit_csv = out_dir / f"dataset_audit_{SPLIT}.csv"
with open(audit_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["image", "issue_type", "gt_class", "pred_class", "confidence", "iou"])
    writer.writeheader()
    writer.writerows(audit_rows)

label_csv = out_dir / f"label_issues_{SPLIT}.csv"
with open(label_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["image", "issue_type", "line_no", "raw_line", "cls_a", "cls_b", "iou"])
    writer.writeheader()
    writer.writerows(label_issue_rows)

print(f"완료: {len(image_paths)}장 처리, 처리 실패 {error_count}건")
print(f"모델 예측 vs GT 이슈: {len(audit_rows)}건 -> {audit_csv}")
print(f"라벨 자체 이슈(중복/충돌/무효): {len(label_issue_rows)}건 -> {label_csv}")

from collections import Counter
print("이슈 유형별 개수 (audit):", Counter(r["issue_type"] for r in audit_rows))
print("이슈 유형별 개수 (label):", Counter(r["issue_type"] for r in label_issue_rows))
