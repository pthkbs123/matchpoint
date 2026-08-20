"""
leakage 제거 효과와 ICDAS 재매핑 효과를 분리해서 보기 위해,
runG valid/test에서 ICDAS 소스를 제외한 나머지만 따로 평가.
(ICDAS를 빼면 라벨 기준 변경의 영향이 없는 상태에서 순수하게
"leakage 있는 옛 valid" vs "leakage 없는 새 valid" 비교가 됨,
단 split 구성 자체가 달라졌다는 점은 여전히 남는 한계.)

원본 파일은 전혀 수정하지 않고, 임시 평가용 서브셋만 별도 폴더에 복사해서 사용.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_leakage_free_split import RUN_G, detect_source

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "pc_setup/dataset_audit/scratch_nonicdas"


def build_subset(split):
    img_dir = RUN_G / split / "images"
    lbl_dir = RUN_G / split / "labels"
    dst_img = OUT_DIR / split / "images"
    dst_lbl = OUT_DIR / split / "labels"
    dst_img.mkdir(parents=True, exist_ok=True)
    dst_lbl.mkdir(parents=True, exist_ok=True)
    count = 0
    for img_path in img_dir.glob("*"):
        if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        if detect_source(img_path.name) == "ICDAS_II":
            continue
        shutil.copy2(img_path, dst_img / img_path.name)
        lbl_path = lbl_dir / (img_path.stem + ".txt")
        if lbl_path.exists():
            shutil.copy2(lbl_path, dst_lbl / lbl_path.name)
        count += 1
    return count


def main():
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    for split in ("valid", "test"):
        n = build_subset(split)
        print(f"{split} (ICDAS 제외): {n}장")
    (OUT_DIR / "data.yaml").write_text(
        "train: valid/images\nval: valid/images\ntest: test/images\n\nnc: 2\nnames: ['cavity', 'normal']\n",
        encoding="utf-8",
    )
    print(f"저장 위치: {OUT_DIR}")


if __name__ == "__main__":
    main()
