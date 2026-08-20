"""
소스별 오류율을 '전체 비율 대비'로 정규화해서 계산.
HIGH 500장 안에서 특정 소스가 많이 보였다는 것만으로는 그 소스가 진짜 문제인지
(전체 중 비중이 커서 그런 것 뿐인지) 구분이 안 되므로, valid set 전체를 기준으로
소스별 점유율과 오류율을 같이 계산해서 비교함.

모든 계산은 valid set(6,059장) 기준 — dataset_audit_valid.csv 자체가 valid만 대상으로 했기 때문에
비교 모집단을 맞추려면 total_images/total_ratio도 valid 기준이어야 함.

원본 파일은 읽기만 하고 수정하지 않음.
"""
import csv
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
AUDIT_CSV = REPO_ROOT / "pc_setup/dataset_audit/kaggle_output/dataset_audit_valid.csv"
DATASET_ROOT = REPO_ROOT / "dataset/archive/dataset_runD/dataset_runD"
IMAGES_DIR = DATASET_ROOT / "valid/images"
LABELS_DIR = DATASET_ROOT / "valid/labels"
OUT_CSV = REPO_ROOT / "pc_setup/dataset_audit/reports/source_error_analysis.csv"

ORIGINAL_YOLO_DIR = REPO_ROOT / "pc_setup/dataset_yolo/valid/images"
ICDAS_DIR = REPO_ROOT / "dataset/Caries Classification ICDAS II.v3i.yolov8/valid/images"

PREFIX_SOURCES = [
    ("ds3_", "Dental.v1-dentalai"),
    ("ds2_", "Caries_Dataset"),
    ("ds_datafix", "data_fix.v1i.yolov8"),
    ("ds_toothcaries", "ToothCariesAI.v1i.yolov8"),
    ("ds_mergessec", "caries_segmentation_merges_sec"),
]

HIGH_THRESHOLD = 46
SCORE_WEIGHTS = {
    "CAVITY_AS_NORMAL": 10, "CAVITY_MISSED": 8, "POSSIBLE_MISSING_CAVITY_LABEL": 8,
    "CLASS_CONFLICT": 8, "INVALID_BBOX_OUT_OF_RANGE": 7, "INVALID_BBOX_ZERO_SIZE": 7,
    "NORMAL_AS_CAVITY": 6, "LOW_IOU": 4, "DUPLICATE_LABEL": 4, "UNCERTAIN_SAMPLE": 2,
    "POSSIBLE_MISSING_NORMAL_LABEL": 3,
}


def detect_source(name):
    for prefix, source in PREFIX_SOURCES:
        if name.startswith(prefix):
            return source
    if (ICDAS_DIR / name).exists():
        return "ICDAS_II"
    if (ORIGINAL_YOLO_DIR / name).exists():
        return "dataset_yolo_original"
    return "dentalv7_or_unknown"


def gt_counts(name):
    label_path = LABELS_DIR / (Path(name).stem + ".txt")
    cavity, normal = 0, 0
    if label_path.exists():
        for line in label_path.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split()
            if not parts:
                continue
            if parts[0] == "0":
                cavity += 1
            elif parts[0] == "1":
                normal += 1
    return cavity, normal


def main():
    all_images = [p.name for p in IMAGES_DIR.glob("*.jpg")] + \
                 [p.name for p in IMAGES_DIR.glob("*.png")] + \
                 [p.name for p in IMAGES_DIR.glob("*.jpeg")]
    total_images = len(all_images)

    source_of = {name: detect_source(name) for name in all_images}

    per_image_issues = defaultdict(list)
    with open(AUDIT_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            per_image_issues[row["image"]].append(row["issue_type"])

    stats = defaultdict(lambda: {
        "total_images": 0, "cavity_gt": 0, "normal_gt": 0,
        "cavity_missed": 0, "cavity_as_normal": 0, "normal_as_cavity": 0,
        "high_priority_count": 0,
    })

    for name in all_images:
        src = source_of[name]
        s = stats[src]
        s["total_images"] += 1
        c, n = gt_counts(name)
        s["cavity_gt"] += c
        s["normal_gt"] += n

        issues = per_image_issues.get(name, [])
        s["cavity_missed"] += issues.count("CAVITY_MISSED")
        s["cavity_as_normal"] += issues.count("CAVITY_AS_NORMAL")
        s["normal_as_cavity"] += issues.count("NORMAL_AS_CAVITY")

        score = sum(SCORE_WEIGHTS.get(t, 1) for t in issues)
        if score >= HIGH_THRESHOLD:
            s["high_priority_count"] += 1

    rows = []
    for src, s in sorted(stats.items(), key=lambda x: -x[1]["total_images"]):
        total_ratio = s["total_images"] / total_images
        high_priority_rate = s["high_priority_count"] / s["total_images"] if s["total_images"] else 0
        cavity_missed_rate = s["cavity_missed"] / s["cavity_gt"] if s["cavity_gt"] else 0
        cavity_as_normal_rate = s["cavity_as_normal"] / s["cavity_gt"] if s["cavity_gt"] else 0
        normal_as_cavity_rate = s["normal_as_cavity"] / s["normal_gt"] if s["normal_gt"] else 0
        rows.append({
            "source": src,
            "total_images": s["total_images"],
            "total_ratio": round(total_ratio, 4),
            "cavity_gt": s["cavity_gt"],
            "normal_gt": s["normal_gt"],
            "cavity_missed": s["cavity_missed"],
            "cavity_missed_rate": round(cavity_missed_rate, 4),
            "cavity_as_normal": s["cavity_as_normal"],
            "cavity_as_normal_rate": round(cavity_as_normal_rate, 4),
            "normal_as_cavity": s["normal_as_cavity"],
            "normal_as_cavity_rate": round(normal_as_cavity_rate, 4),
            "high_priority_count": s["high_priority_count"],
            "high_priority_rate": round(high_priority_rate, 4),
        })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"valid 전체: {total_images}장")
    print(f"{'source':<28} {'점유율':>8} {'HIGH비율':>9} {'cavity놓침율':>12} {'cavity->normal율':>16}")
    for r in rows:
        print(f"{r['source']:<28} {r['total_ratio']*100:>7.1f}% {r['high_priority_rate']*100:>8.1f}% "
              f"{r['cavity_missed_rate']*100:>11.1f}% {r['cavity_as_normal_rate']*100:>15.1f}%")
    print(f"\n저장: {OUT_CSV}")


if __name__ == "__main__":
    main()
