"""
Kaggle에서 받은 감사(audit) csv를 읽어서 ChatGPT 검수용 패키지를 만드는 로컬 스크립트.
원본 이미지/라벨/best.pt는 절대 수정하지 않음. GT는 로컬 label txt에서 다시 읽고,
예측 박스는 HIGH 우선순위로 뽑힌 이미지에 한해서만 로컬 GPU로 다시 추론해서 얻음
(6천 장 전체를 다시 추론하는 게 아니라 최대 500장만 대상이라 약한 GPU로도 충분히 빠름).

실행:
    python build_review_package.py                 # 기본: HIGH 상위 500장으로 batch_01 생성
    python build_review_package.py --max-images 20  # 빠른 동작 확인용 소량 테스트
"""

import argparse
import csv
import shutil
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[3]
AUDIT_CSV = REPO_ROOT / "pc_setup/dataset_audit/kaggle_output/dataset_audit_valid.csv"
LABEL_ISSUES_CSV = REPO_ROOT / "pc_setup/dataset_audit/kaggle_output/label_issues_valid.csv"
DATASET_ROOT = REPO_ROOT / "dataset/archive/dataset_runD/dataset_runD"
IMAGES_DIR = DATASET_ROOT / "valid/images"
LABELS_DIR = DATASET_ROOT / "valid/labels"
MODEL_PATH = REPO_ROOT / "pc_setup/backend/model/best_runD_backup.pt"
OUT_ROOT = REPO_ROOT / "pc_setup/dataset_audit"

SCORE_WEIGHTS = {
    "CAVITY_AS_NORMAL": 10,
    "CAVITY_MISSED": 8,
    "POSSIBLE_MISSING_CAVITY_LABEL": 8,
    "CLASS_CONFLICT": 8,
    "INVALID_BBOX_OUT_OF_RANGE": 7,
    "INVALID_BBOX_ZERO_SIZE": 7,
    "NORMAL_AS_CAVITY": 6,
    "LOW_IOU": 4,
    "DUPLICATE_LABEL": 4,
    "UNCERTAIN_SAMPLE": 2,
    "POSSIBLE_MISSING_NORMAL_LABEL": 3,
}
# 상위 ~10%가 HIGH, ~50%가 MEDIUM이 되도록 실제 점수 분포(top10%=46, top50%=10)를 보고 정한 기본값.
HIGH_THRESHOLD = 46
MEDIUM_THRESHOLD = 10

# 섹션10 우선순위: 이 순서로 먼저 정렬한 뒤, 같은 그룹 안에서는 review_score 내림차순
PRIORITY_ORDER = [
    "CAVITY_AS_NORMAL",
    "CAVITY_MISSED",
    "POSSIBLE_MISSING_CAVITY_LABEL",
    "CLASS_CONFLICT",
    "INVALID_BBOX_OUT_OF_RANGE",
    "INVALID_BBOX_ZERO_SIZE",
]

BATCH_SIZE = 500
SHEET_COLS, SHEET_ROWS = 5, 4  # 20장씩
CELL_SIZE = 380
HASH_SIZE = 8
DUP_HAMMING_THRESHOLD = 4  # 이 이하 해밍거리면 "거의 같은 이미지"로 취급
MAX_PER_DUP_CLUSTER = 3

CLASS_COLORS = {
    ("gt", "cavity"): (220, 30, 30),
    ("gt", "normal"): (30, 160, 60),
    ("pred", "cavity"): (255, 140, 0),
    ("pred", "normal"): (30, 120, 220),
}


def load_issues():
    per_image = defaultdict(list)
    for fn, kind in [(AUDIT_CSV, "audit"), (LABEL_ISSUES_CSV, "label")]:
        with open(fn, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                per_image[row["image"]].append(row["issue_type"])
    return per_image


def primary_issue(issue_types):
    for t in PRIORITY_ORDER:
        if t in issue_types:
            return t
    counts = defaultdict(int)
    for t in issue_types:
        counts[t] += 1
    return max(counts, key=counts.get)


def average_hash(img):
    small = img.convert("L").resize((HASH_SIZE, HASH_SIZE))
    pixels = list(small.getdata())
    avg = sum(pixels) / len(pixels)
    bits = "".join("1" if p > avg else "0" for p in pixels)
    return int(bits, 2)


def hamming(a, b):
    return bin(a ^ b).count("1")


def dedupe_similar(ranked_images, images_dir):
    kept = []
    cluster_reps = []  # list of (hash, count)
    for name, score, primary in ranked_images:
        try:
            h = average_hash(Image.open(images_dir / name))
        except Exception:
            kept.append((name, score, primary))
            continue
        placed = False
        for i, (rep_hash, count) in enumerate(cluster_reps):
            if hamming(h, rep_hash) <= DUP_HAMMING_THRESHOLD:
                if count < MAX_PER_DUP_CLUSTER:
                    cluster_reps[i] = (rep_hash, count + 1)
                    kept.append((name, score, primary))
                placed = True
                break
        if not placed:
            cluster_reps.append((h, 1))
            kept.append((name, score, primary))
    return kept


def yolo_to_xyxy(cx, cy, w, h, img_w, img_h):
    x1 = (cx - w / 2) * img_w
    y1 = (cy - h / 2) * img_h
    x2 = (cx + w / 2) * img_w
    y2 = (cy + h / 2) * img_h
    return (x1, y1, x2, y2)


def read_gt_boxes(name, img_w, img_h):
    names = {0: "cavity", 1: "normal"}
    label_path = LABELS_DIR / (Path(name).stem + ".txt")
    boxes = []
    if not label_path.exists():
        return boxes
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) != 5:
            continue
        cls, cx, cy, w, h = int(parts[0]), *map(float, parts[1:])
        boxes.append({"cls": names.get(cls, str(cls)), "xyxy": yolo_to_xyxy(cx, cy, w, h, img_w, img_h)})
    return boxes


def run_local_predictions(image_names, max_images):
    from ultralytics import YOLO

    model = YOLO(str(MODEL_PATH))
    names = {0: "cavity", 1: "normal"}
    preds = {}
    for name in image_names[:max_images]:
        result = model.predict(str(IMAGES_DIR / name), conf=0.1, verbose=False)[0]
        boxes = []
        if result.boxes is not None:
            for box in result.boxes:
                boxes.append({
                    "cls": names.get(int(box.cls[0]), "?"),
                    "conf": float(box.conf[0]),
                    "xyxy": tuple(box.xyxy[0].tolist()),
                })
        preds[name] = boxes
    return preds


def draw_annotated(image_path, gt_boxes, pred_boxes, header_lines):
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font = ImageFont.load_default()

    for b in gt_boxes:
        draw.rectangle(b["xyxy"], outline=CLASS_COLORS[("gt", b["cls"])], width=3)
    for b in pred_boxes:
        x1, y1, x2, y2 = b["xyxy"]
        color = CLASS_COLORS[("pred", b["cls"])]
        draw.rectangle((x1, y1, x2, y2), outline=color, width=2)
        draw.text((x1, max(0, y1 - 16)), f"{b['cls']} {b['conf']:.2f}", fill=color, font=font)

    band_h = 16 * len(header_lines) + 8
    band = Image.new("RGB", (img.width, band_h), (0, 0, 0))
    band_draw = ImageDraw.Draw(band)
    for i, line in enumerate(header_lines):
        band_draw.text((4, 4 + i * 16), line, fill=(255, 255, 255), font=font)
    combined = Image.new("RGB", (img.width, img.height + band_h))
    combined.paste(band, (0, 0))
    combined.paste(img, (0, band_h))
    return combined


def make_contact_sheets(individual_dir, out_dir, prefix):
    files = sorted(individual_dir.glob("*.jpg"))
    out_dir.mkdir(parents=True, exist_ok=True)
    per_sheet = SHEET_COLS * SHEET_ROWS
    sheet_paths = []
    for sheet_idx in range(0, len(files), per_sheet):
        chunk = files[sheet_idx:sheet_idx + per_sheet]
        sheet = Image.new("RGB", (SHEET_COLS * CELL_SIZE, SHEET_ROWS * CELL_SIZE), (30, 30, 30))
        for i, fp in enumerate(chunk):
            img = Image.open(fp)
            img.thumbnail((CELL_SIZE - 8, CELL_SIZE - 8))
            r, c = divmod(i, SHEET_COLS)
            x, y = c * CELL_SIZE + 4, r * CELL_SIZE + 4
            sheet.paste(img, (x, y))
        n = sheet_idx // per_sheet + 1
        sheet_path = out_dir / f"contact_sheet_{prefix}_{n:03d}.jpg"
        sheet.save(sheet_path, quality=85)
        sheet_paths.append(sheet_path)
    return sheet_paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-images", type=int, default=BATCH_SIZE)
    args = parser.parse_args()

    per_image_issues = load_issues()
    scored = []
    for name, issues in per_image_issues.items():
        score = sum(SCORE_WEIGHTS.get(t, 1) for t in issues)
        scored.append((name, score, primary_issue(issues), issues))

    def sort_key(item):
        _, score, primary, _ = item
        pr_rank = PRIORITY_ORDER.index(primary) if primary in PRIORITY_ORDER else len(PRIORITY_ORDER)
        return (pr_rank, -score)

    scored.sort(key=sort_key)

    def priority_of(score):
        if score >= HIGH_THRESHOLD:
            return "HIGH"
        if score >= MEDIUM_THRESHOLD:
            return "MEDIUM"
        return "LOW"

    high_ranked = [(n, s, p) for n, s, p, _ in scored if priority_of(s) == "HIGH"]
    deduped = dedupe_similar(high_ranked, IMAGES_DIR)
    batch = deduped[:args.max_images]
    print(f"HIGH 전체: {len(high_ranked)}장, 유사중복 제거 후: {len(deduped)}장, 이번 batch: {len(batch)}장")

    print("예측 재추론 중 (batch 대상만)...")
    preds_by_image = run_local_predictions([n for n, _, _ in batch], len(batch))

    individual_dir = OUT_ROOT / "chatgpt_review/individual"
    if individual_dir.exists():
        shutil.rmtree(individual_dir)
    individual_dir.mkdir(parents=True, exist_ok=True)

    issues_by_image = {name: issues for name, _, _, issues in scored}
    rows = []
    for i, (name, score, primary) in enumerate(batch, start=1):
        review_id = f"H{i:06d}"
        img = Image.open(IMAGES_DIR / name)
        img_w, img_h = img.size
        gt_boxes = read_gt_boxes(name, img_w, img_h)
        pred_boxes = preds_by_image.get(name, [])
        issue_types = issues_by_image[name]
        header = [
            f"ID: {review_id}  Issue: {primary}  Score: {score}",
            f"GT: {len(gt_boxes)}box  Pred: {len(pred_boxes)}box  AllIssues: {','.join(sorted(set(issue_types)))[:80]}",
        ]
        annotated = draw_annotated(IMAGES_DIR / name, gt_boxes, pred_boxes, header)
        annotated.save(individual_dir / f"{review_id}.jpg", quality=88)

        rows.append({
            "review_id": review_id,
            "image_path": str((IMAGES_DIR / name).relative_to(REPO_ROOT)),
            "label_path": str((LABELS_DIR / (Path(name).stem + ".txt")).relative_to(REPO_ROOT)),
            "preview_path": str((individual_dir / f"{review_id}.jpg").relative_to(REPO_ROOT)),
            "contact_sheet": "",
            "issue_type": primary,
            "gt_class": ";".join(sorted({b["cls"] for b in gt_boxes})),
            "pred_class": ";".join(sorted({b["cls"] for b in pred_boxes})),
            "confidence": ";".join(f"{b['conf']:.2f}" for b in pred_boxes),
            "iou": "",
            "review_score": score,
            "priority": "HIGH",
            "description": f"{primary} 외 {len(set(issue_types)) - 1}개 이슈" if len(set(issue_types)) > 1 else primary,
            "review_status": "",
            "review_comment": "",
        })

    high_dir = OUT_ROOT / "chatgpt_review/high"
    if high_dir.exists():
        shutil.rmtree(high_dir)
    sheet_paths = make_contact_sheets(individual_dir, high_dir, "high")

    per_sheet = SHEET_COLS * SHEET_ROWS
    for idx, row in enumerate(rows):
        sheet_n = idx // per_sheet + 1
        row["contact_sheet"] = f"chatgpt_review/high/contact_sheet_high_{sheet_n:03d}.jpg"

    review_csv = OUT_ROOT / "chatgpt_review/chatgpt_review.csv"
    with open(review_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    issue_type_counts = defaultdict(int)
    for _, issues in issues_by_image.items():
        for t in set(issues):
            issue_type_counts[t] += 1

    total_images = len(list(IMAGES_DIR.glob("*.jpg"))) + len(list(IMAGES_DIR.glob("*.png")))
    high_count = sum(1 for _, s, _, _ in scored if priority_of(s) == "HIGH")
    medium_count = sum(1 for _, s, _, _ in scored if priority_of(s) == "MEDIUM")

    readme = f"""이 폴더는 YOLO 충치 탐지 모델(cavity/normal 2클래스) 데이터셋 감사 결과입니다.
사람이 3만 장 이상을 직접 보지 않도록, 문제 가능성이 높은 이미지만 AI가 골라 정리했습니다.

## 데이터 규모
- valid set 전체: {total_images}장
- HIGH 우선순위: {high_count}장 (이번 batch: {len(batch)}장 처리, 나머지는 batch_02 이후로 이어서 처리 가능)
- MEDIUM 우선순위: {medium_count}장

## 이슈 유형별 이미지 수 (중복 포함, 한 이미지에 여러 유형이 있을 수 있음)
{chr(10).join(f'- {k}: {v}' for k, v in sorted(issue_type_counts.items(), key=lambda x: -x[1]))}

## Contact sheet 파일 목록
{chr(10).join(f'- {p.name}' for p in sheet_paths)}

## Review ID 규칙
- H000001, H000002, ... 형태. review_score 및 우선순위 규칙(섹션10)으로 정렬된 순번입니다.

## 박스 표시 방식
- GT cavity: 빨간 실선 / GT normal: 초록 실선
- Pred cavity: 주황 점선풍 실선 + confidence 텍스트 / Pred normal: 파랑 실선 + confidence 텍스트
- 이미지 상단 검은 띠에 ID, issue type, score, GT/Pred 박스 개수, 발견된 모든 이슈 유형 표시

## ChatGPT에게 검수 요청하는 방법
첨부된 contact sheet를 보고 각 ID를 검수해 주세요.

판정값:
LABEL_ERROR_LIKELY
MODEL_ERROR_LIKELY
BBOX_ERROR_LIKELY
AMBIGUOUS
OK
NEED_EXPERT_REVIEW

각 ID별로 판정과 짧은 이유를 작성해 주세요.
"""
    (OUT_ROOT / "chatgpt_review/README_FOR_CHATGPT.txt").write_text(readme, encoding="utf-8")

    print(f"완료: individual {len(rows)}장, contact sheet {len(sheet_paths)}장")
    print(f"CSV: {review_csv}")
    print(f"README: {OUT_ROOT / 'chatgpt_review/README_FOR_CHATGPT.txt'}")


if __name__ == "__main__":
    main()
