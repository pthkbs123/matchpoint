"""
train-valid 데이터 누수 검사.
방법 2가지를 같이 씀:
  1) 파일명 기반: Roboflow export는 "<원본이름>.rf.<증강해시>.jpg" 형식이라
     ".rf." 앞부분이 같으면 같은 원본에서 나온 augmentation임. 소스가 다르면 우연히
     이름이 겹칠 수 있어서 source까지 같이 묶어서 키로 씀.
  2) perceptual hash(average hash) 기반: 파일명이 달라도 이미지 내용이 사실상 같은
     경우(예: 파일명이 새로 생성된 ds_* 소스)를 잡기 위함. 정확히 같은 해시만 우선 비교
     (전수 pairwise Hamming 비교는 42,005장 규모에서 비용이 커서 1차는 exact hash만).

원본 파일은 읽기만 하고 수정/삭제하지 않음.
"""
import csv
from collections import defaultdict
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
DATASET_ROOT = REPO_ROOT / "dataset/archive/dataset_runD/dataset_runD"
OUT_CSV = REPO_ROOT / "pc_setup/dataset_audit/reports/leakage_report.csv"

ORIGINAL_YOLO_DIR = REPO_ROOT / "pc_setup/dataset_yolo/valid/images"
ICDAS_DIR = REPO_ROOT / "dataset/Caries Classification ICDAS II.v3i.yolov8/valid/images"
PREFIX_SOURCES = [
    ("ds3_", "Dental.v1-dentalai"), ("ds2_", "Caries_Dataset"),
    ("ds_datafix", "data_fix.v1i.yolov8"), ("ds_toothcaries", "ToothCariesAI.v1i.yolov8"),
    ("ds_mergessec", "caries_segmentation_merges_sec"),
]
HASH_SIZE = 8


def detect_source(name):
    for prefix, source in PREFIX_SOURCES:
        if name.startswith(prefix):
            return source
    if (ICDAS_DIR / name).exists():
        return "ICDAS_II"
    if (ORIGINAL_YOLO_DIR / name).exists():
        return "dataset_yolo_original"
    return "dentalv7_or_unknown"


def original_key(name):
    if ".rf." in name:
        return name.split(".rf.")[0]
    return Path(name).stem


def average_hash(path):
    try:
        small = Image.open(path).convert("L").resize((HASH_SIZE, HASH_SIZE))
        pixels = list(small.getdata())
        avg = sum(pixels) / len(pixels)
        bits = "".join("1" if p > avg else "0" for p in pixels)
        return int(bits, 2)
    except Exception:
        return None


def collect_split(split):
    img_dir = DATASET_ROOT / split / "images"
    return sorted(p.name for p in img_dir.glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png"))


def main():
    train_names = collect_split("train")
    valid_names = collect_split("valid")
    print(f"train {len(train_names)}장, valid {len(valid_names)}장 로드")

    train_by_key = defaultdict(list)
    for name in train_names:
        src = detect_source(name)
        train_by_key[(src, original_key(name))].append(name)

    rows = []
    filename_leak_valid_images = set()
    for name in valid_names:
        src = detect_source(name)
        key = (src, original_key(name))
        if key in train_by_key:
            for train_name in train_by_key[key]:
                rows.append({
                    "train_image": train_name, "valid_image": name,
                    "similarity": "same_original_filename", "source": src,
                    "possible_same_original": "yes",
                })
            filename_leak_valid_images.add(name)

    print(f"파일명 기반 검사 완료: valid {len(filename_leak_valid_images)}장이 train과 동일 원본 키 공유")

    print("perceptual hash 계산 중 (train)...")
    train_hash_index = defaultdict(list)
    for i, name in enumerate(train_names):
        h = average_hash(DATASET_ROOT / "train/images" / name)
        if h is not None:
            train_hash_index[h].append(name)
        if (i + 1) % 5000 == 0:
            print(f"  train {i + 1}/{len(train_names)}")

    print("perceptual hash 계산 중 (valid) + 비교...")
    hash_leak_valid_images = set()
    for i, name in enumerate(valid_names):
        h = average_hash(DATASET_ROOT / "valid/images" / name)
        if h is not None and h in train_hash_index:
            for train_name in train_hash_index[h]:
                if train_name == name:
                    continue
                rows.append({
                    "train_image": train_name, "valid_image": name,
                    "similarity": "identical_phash", "source": detect_source(name),
                    "possible_same_original": "yes",
                })
                hash_leak_valid_images.add(name)
        if (i + 1) % 2000 == 0:
            print(f"  valid {i + 1}/{len(valid_names)}")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["train_image", "valid_image", "similarity", "source", "possible_same_original"])
        writer.writeheader()
        writer.writerows(rows)

    all_leak_images = filename_leak_valid_images | hash_leak_valid_images
    print("\n=== 요약 ===")
    print(f"train-valid 완전 중복(동일 원본 파일명) 의심 valid 이미지: {len(filename_leak_valid_images)}장")
    print(f"train-valid 완전 동일(perceptual hash 일치) valid 이미지: {len(hash_leak_valid_images)}장")
    print(f"둘 중 하나라도 해당하는 valid 이미지(합집합): {len(all_leak_images)}장")
    print(f"valid 전체 대비 누수 의심 비율: {len(all_leak_images) / len(valid_names) * 100:.2f}%")
    print(f"저장: {OUT_CSV}")


if __name__ == "__main__":
    main()
