"""
dataset_runF(이미지 구성은 runE와 동일 + ICDAS 라벨만 수정됨)을 원본으로,
"같은 원본 사진에서 나온 여러 장"이 train/valid/test에 흩어지지 않도록
원본 그룹 단위로 다시 split해서 dataset_runG를 만든다.

그룹 판정 기준 (Union-Find로 합침):
  1) 같은 source 안에서 ".rf." 이전 파일명이 같으면 같은 원본
  2) perceptual hash(average hash)가 완전히 같으면 같은 원본
  3) perceptual hash가 거의 같으면(해밍 거리 <= NEAR_DUP_HAMMING) 같은 원본으로 취급
     (전수 비교는 비용이 커서, 해시 상위 비트를 버킷 키로 써서 같은 버킷 안에서만 비교)

split은 그룹 단위로 배정하되, source 분포와 cavity/normal 비율이 심하게 안 무너지도록
그리디 방식으로 80/10/10에 최대한 맞춤.

기존 dataset_runD/runE/runF는 전혀 건드리지 않고, 새 폴더(dataset_runG)만 생성.
"""
import csv
import random
import shutil
from collections import defaultdict
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_F = REPO_ROOT / "pc_setup/dataset_runF"
RUN_G = REPO_ROOT / "pc_setup/dataset_runG"
REPORT_DIR = REPO_ROOT / "pc_setup/dataset_audit/reports"

ORIGINAL_YOLO_DIR = REPO_ROOT / "pc_setup/dataset_yolo"
ICDAS_DIR = REPO_ROOT / "dataset/Caries Classification ICDAS II.v3i.yolov8"
PREFIX_SOURCES = [
    ("ds3_", "Dental.v1-dentalai"), ("ds2_", "Caries_Dataset"),
    ("ds_datafix", "data_fix.v1i.yolov8"), ("ds_toothcaries", "ToothCariesAI.v1i.yolov8"),
    ("ds_mergessec", "caries_segmentation_merges_sec"),
]
_yolo_names = None
_icdas_names = None


def _load_name_sets():
    global _yolo_names, _icdas_names
    if _yolo_names is None:
        _yolo_names = set()
        for split in ("train", "valid", "test"):
            _yolo_names |= {p.name for p in (ORIGINAL_YOLO_DIR / split / "images").glob("*")}
    if _icdas_names is None:
        _icdas_names = set()
        for split in ("train", "valid", "test"):
            _icdas_names |= {p.name for p in (ICDAS_DIR / split / "images").glob("*")}


def detect_source(name):
    _load_name_sets()
    for prefix, source in PREFIX_SOURCES:
        if name.startswith(prefix):
            return source
    if name in _icdas_names:
        return "ICDAS_II"
    if name in _yolo_names:
        return "dataset_yolo_original"
    return "dentalv7_or_unknown"


def original_key(name):
    if ".rf." in name:
        return name.split(".rf.")[0]
    return Path(name).stem


HASH_SIZE = 8
NEAR_DUP_HAMMING = 4
BUCKET_BITS = 16  # 상위 16비트를 버킷 키로 사용


def average_hash(path):
    try:
        small = Image.open(path).convert("L").resize((HASH_SIZE, HASH_SIZE))
        pixels = list(small.getdata())
        avg = sum(pixels) / len(pixels)
        bits = "".join("1" if p > avg else "0" for p in pixels)
        return int(bits, 2)
    except Exception:
        return None


def hamming(a, b):
    return bin(a ^ b).count("1")


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def collect_all_images():
    items = []  # (split, name, source, path)
    for split in ("train", "valid", "test"):
        img_dir = RUN_F / split / "images"
        for p in sorted(img_dir.glob("*")):
            if p.suffix.lower() in (".jpg", ".jpeg", ".png"):
                items.append((split, p.name, detect_source(p.name), p))
    return items


def gt_counts(label_path):
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
    print("이미지 목록 수집 중...")
    items = collect_all_images()
    print(f"총 {len(items)}장 (train/valid/test 합계)")

    print("perceptual hash 계산 중...")
    hashes = {}
    for i, (split, name, source, path) in enumerate(items):
        h = average_hash(path)
        if h is not None:
            hashes[(split, name)] = h
        if (i + 1) % 5000 == 0:
            print(f"  {i + 1}/{len(items)}")

    print("그룹(Union-Find) 구성 중...")
    uf = UnionFind()
    key_to_items = defaultdict(list)
    for split, name, source, path in items:
        uf.find((split, name))
        key_to_items[(source, original_key(name))].append((split, name))

    for group_items in key_to_items.values():
        for i in range(1, len(group_items)):
            uf.union(group_items[0], group_items[i])

    exact_hash_groups = defaultdict(list)
    for (split, name), h in hashes.items():
        exact_hash_groups[h].append((split, name))
    for group_items in exact_hash_groups.values():
        for i in range(1, len(group_items)):
            uf.union(group_items[0], group_items[i])

    bucket_groups = defaultdict(list)
    shift = 64 - BUCKET_BITS
    for (split, name), h in hashes.items():
        bucket_groups[h >> shift].append((split, name, h))
    near_dup_unions = 0
    for bucket_items in bucket_groups.values():
        if len(bucket_items) > 400:
            continue  # 버킷이 지나치게 크면(자주 나오는 패턴) 비용 폭발 방지 위해 스킵
        for i in range(len(bucket_items)):
            for j in range(i + 1, len(bucket_items)):
                if hamming(bucket_items[i][2], bucket_items[j][2]) <= NEAR_DUP_HAMMING:
                    uf.union(bucket_items[i][:2], bucket_items[j][:2])
                    near_dup_unions += 1
    print(f"근접중복(해밍<= {NEAR_DUP_HAMMING}) 추가 병합: {near_dup_unions}건")

    groups = defaultdict(list)
    for split, name, source, path in items:
        root = uf.find((split, name))
        groups[root].append((split, name, source, path))
    print(f"고유 원본 그룹 수: {len(groups)}")

    group_list = list(groups.values())
    random.Random(42).shuffle(group_list)

    target_ratio = {"train": 0.8, "valid": 0.1, "test": 0.1}
    running = {"train": 0, "valid": 0, "test": 0}
    assignment = {}
    for group in group_list:
        total_so_far = sum(running.values()) or 1
        deficits = {s: target_ratio[s] - running[s] / total_so_far for s in target_ratio}
        best_split = max(deficits, key=deficits.get)
        assignment[id(group)] = best_split
        running[best_split] += len(group)

    if RUN_G.exists():
        shutil.rmtree(RUN_G)
    for split in ("train", "valid", "test"):
        (RUN_G / split / "images").mkdir(parents=True, exist_ok=True)
        (RUN_G / split / "labels").mkdir(parents=True, exist_ok=True)
    (RUN_G / "data.yaml").write_text(
        "train: train/images\nval: valid/images\ntest: test/images\n\nnc: 2\nnames: ['cavity', 'normal']\n",
        encoding="utf-8",
    )

    split_stats = {s: {"images": 0, "cavity_gt": 0, "normal_gt": 0, "groups": 0,
                        "by_source": defaultdict(int)} for s in ("train", "valid", "test")}

    for group in group_list:
        dst_split = assignment[id(group)]
        split_stats[dst_split]["groups"] += 1
        for orig_split, name, source, img_path in group:
            dst_img = RUN_G / dst_split / "images" / name
            shutil.copy2(img_path, dst_img)
            src_label = RUN_F / orig_split / "labels" / (img_path.stem + ".txt")
            dst_label = RUN_G / dst_split / "labels" / (img_path.stem + ".txt")
            if src_label.exists():
                shutil.copy2(src_label, dst_label)
                c, n = gt_counts(src_label)
            else:
                c, n = 0, 0
            split_stats[dst_split]["images"] += 1
            split_stats[dst_split]["cavity_gt"] += c
            split_stats[dst_split]["normal_gt"] += n
            split_stats[dst_split]["by_source"][source] += 1

    report_path = REPORT_DIR / "runG_split_stats.csv"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    all_sources = sorted({src for s in split_stats.values() for src in s["by_source"]})
    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["split", "images", "unique_groups", "cavity_gt", "normal_gt",
                          "cavity_ratio"] + [f"source_{s}" for s in all_sources] +
                         [f"source_{s}_ratio" for s in all_sources])
        for split in ("train", "valid", "test"):
            st = split_stats[split]
            cavity_ratio = st["cavity_gt"] / (st["cavity_gt"] + st["normal_gt"]) if (st["cavity_gt"] + st["normal_gt"]) else 0
            row = [split, st["images"], st["groups"], st["cavity_gt"], st["normal_gt"], round(cavity_ratio, 4)]
            row += [st["by_source"].get(s, 0) for s in all_sources]
            row += [round(st["by_source"].get(s, 0) / st["images"], 4) if st["images"] else 0 for s in all_sources]
            writer.writerow(row)

    print("\n=== dataset_runG split 결과 ===")
    for split in ("train", "valid", "test"):
        st = split_stats[split]
        total = st["cavity_gt"] + st["normal_gt"]
        print(f"{split}: {st['images']}장 (그룹 {st['groups']}개), "
              f"cavity {st['cavity_gt']} / normal {st['normal_gt']} "
              f"(cavity비율 {st['cavity_gt']/total*100:.1f}%)" if total else f"{split}: {st['images']}장")
    print(f"\n저장: {report_path}")
    print(f"새 데이터셋 위치: {RUN_G}")


if __name__ == "__main__":
    main()
