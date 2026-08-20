import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_leakage_free_split import detect_source

REPO_ROOT = Path(__file__).resolve().parents[3]
OLD_VALID = REPO_ROOT / "dataset/archive/dataset_runD/dataset_runD/valid"
OUT_DIR = REPO_ROOT / "pc_setup/dataset_audit/scratch_old_nonicdas"

if OUT_DIR.exists():
    shutil.rmtree(OUT_DIR)
(OUT_DIR / "valid/images").mkdir(parents=True, exist_ok=True)
(OUT_DIR / "valid/labels").mkdir(parents=True, exist_ok=True)

count = 0
for img_path in (OLD_VALID / "images").glob("*"):
    if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
        continue
    if detect_source(img_path.name) == "ICDAS_II":
        continue
    shutil.copy2(img_path, OUT_DIR / "valid/images" / img_path.name)
    lbl = OLD_VALID / "labels" / (img_path.stem + ".txt")
    if lbl.exists():
        shutil.copy2(lbl, OUT_DIR / "valid/labels" / lbl.name)
    count += 1

(OUT_DIR / "data.yaml").write_text(
    "train: valid/images\nval: valid/images\ntest: valid/images\n\nnc: 2\nnames: ['cavity', 'normal']\n",
    encoding="utf-8",
)
print(f"기존(leaky) valid, ICDAS 제외: {count}장")
