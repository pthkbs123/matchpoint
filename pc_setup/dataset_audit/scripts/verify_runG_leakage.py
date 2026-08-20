import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_leakage_free_split import RUN_G, detect_source, original_key, average_hash

from itertools import combinations


def collect(split):
    img_dir = RUN_G / split / "images"
    return sorted(p.name for p in img_dir.glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png"))


def main():
    splits = {s: collect(s) for s in ("train", "valid", "test")}
    for s, names in splits.items():
        print(f"{s}: {len(names)}장")

    keys = {}
    hashes = {}
    for split, names in splits.items():
        for name in names:
            keys[(split, name)] = (detect_source(name), original_key(name))
            h = average_hash(RUN_G / split / "images" / name)
            if h is not None:
                hashes[(split, name)] = h

    key_sets = {s: set(keys[(s, n)] for n in names) for s, names in splits.items()}
    hash_sets = {s: set(hashes[(s, n)] for n in names if (s, n) in hashes) for s, names in splits.items()}

    print("\n=== 파일명 키(원본 ID) 기준 겹침 ===")
    for a, b in combinations(("train", "valid", "test"), 2):
        overlap = key_sets[a] & key_sets[b]
        print(f"{a}-{b}: {len(overlap)}개 그룹 겹침")

    print("\n=== perceptual hash 기준 겹침 ===")
    for a, b in combinations(("train", "valid", "test"), 2):
        overlap = hash_sets[a] & hash_sets[b]
        print(f"{a}-{b}: {len(overlap)}개 해시 겹침")


if __name__ == "__main__":
    main()
