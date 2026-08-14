"""
Run D (재정의): dataset_runC 전체 + runC 이후 찾은 데이터셋 전부를 한 번에 합본.

포함되는 것:
  - caries_segmentation_merges_sec.v1i.yolov8-obb (OBB, Caries/Cavity->cavity, Tooth->normal, Crack 제외)
  - data fix.v1i.yolov8 (클래스 0/1/2 중 2번=karies만 cavity로 사용, 나머지는 라인 제외.
    cavity 라벨이 하나도 안 남는 이미지는 통째로 제외 - normal 여부를 알 수 없으므로)
  - ToothCariesAI.v1i.yolov8 (단일 클래스 KARIES -> cavity)
  - dataset_dentalv7_converted (convert_dentalv7.py로 이미 cavity/normal 2클래스로 변환해둔 것, 그대로 복사)

사용법:
    python build_dataset_runC.py       # runC 아직 없으면 먼저
    python convert_dentalv7.py         # dataset_dentalv7_converted 아직 없으면 먼저
    python build_dataset_runD.py
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent          # pc_setup/
BASE = ROOT.parent                                # matchpoint_tmp/
DOWNLOADS = BASE.parent                           # D:\pth
DATASET_DIR = DOWNLOADS / "dataset"               # 사용자가 정리한 폴더

RUN_C = ROOT / "dataset_runC"
DS_MERGES_SEC = DATASET_DIR / "caries_segmentation_merges_sec.v1i.yolov8-obb"
DS_DATA_FIX = DATASET_DIR / "data fix.v1i.yolov8"
DS_TOOTHCARIES = DATASET_DIR / "ToothCariesAI.v1i.yolov8"
DS_DENTALV7 = ROOT / "dataset_dentalv7_converted"

CLASSES = ["cavity", "normal"]  # 0=cavity, 1=normal


def write_yaml(dst: Path):
    (dst / "data.yaml").write_text(
        "train: train/images\n"
        "val: valid/images\n"
        "test: test/images\n\n"
        f"nc: {len(CLASSES)}\n"
        f"names: {CLASSES}\n",
        encoding="utf-8",
    )


def ensure_dirs(dst: Path):
    for split in ("train", "valid", "test"):
        (dst / split / "images").mkdir(parents=True, exist_ok=True)
        (dst / split / "labels").mkdir(parents=True, exist_ok=True)


def copy_as_is(src_root: Path, dst_root: Path):
    for split in ("train", "valid", "test"):
        for img in (src_root / split / "images").glob("*"):
            shutil.copy2(img, dst_root / split / "images" / img.name)
        for lbl in (src_root / split / "labels").glob("*.txt"):
            shutil.copy2(lbl, dst_root / split / "labels" / lbl.name)


def obb_to_aabb_line(parts, remap):
    cls = int(parts[0])
    if cls not in remap:
        return None
    coords = list(map(float, parts[1:9]))
    xs = coords[0::2]
    ys = coords[1::2]
    xmin, xmax = max(0.0, min(xs)), min(1.0, max(xs))
    ymin, ymax = max(0.0, min(ys)), min(1.0, max(ys))
    w = xmax - xmin
    h = ymax - ymin
    if w <= 0 or h <= 0:
        return None
    xc = xmin + w / 2
    yc = ymin + h / 2
    return f"{remap[cls]} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}"


def add_obb_ds(src_root: Path, dst_root: Path, prefix: str, remap: dict):
    """OBB(8좌표) 형식 데이터셋을 클래스 재매핑하며 추가."""
    counts = {"train": 0, "valid": 0, "test": 0}
    for split in ("train", "valid", "test"):
        img_dir = src_root / split / "images"
        lbl_dir = src_root / split / "labels"
        if not img_dir.exists():
            continue
        for img in img_dir.glob("*"):
            dst_img = dst_root / split / "images" / f"{prefix}_{img.name}"
            shutil.copy2(img, dst_img)
            lbl_src = lbl_dir / (img.stem + ".txt")
            lines_out = []
            if lbl_src.exists():
                for line in lbl_src.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    converted = obb_to_aabb_line(line.split(), remap)
                    if converted:
                        lines_out.append(converted)
            (dst_root / split / "labels" / (dst_img.stem + ".txt")).write_text(
                "\n".join(lines_out) + ("\n" if lines_out else ""), encoding="utf-8"
            )
            counts[split] += 1
    return counts


def add_data_fix(src_root: Path, dst_root: Path, prefix: str = "ds_datafix"):
    """data fix v1: 클래스 2(karies)만 cavity로 사용. cavity 라벨이 없는 이미지는 통째로 제외."""
    counts = {"train": 0, "valid": 0, "test": 0}
    skipped = {"train": 0, "valid": 0, "test": 0}
    for split in ("train", "valid", "test"):
        img_dir = src_root / split / "images"
        lbl_dir = src_root / split / "labels"
        if not img_dir.exists():
            continue
        for img in img_dir.glob("*"):
            lbl_src = lbl_dir / (img.stem + ".txt")
            lines_out = []
            if lbl_src.exists():
                for line in lbl_src.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    parts = line.split()
                    if int(parts[0]) == 2:  # karies만
                        lines_out.append(" ".join(["0"] + parts[1:]))  # -> cavity(0)
            if not lines_out:
                skipped[split] += 1
                continue
            dst_img = dst_root / split / "images" / f"{prefix}_{img.name}"
            shutil.copy2(img, dst_img)
            (dst_root / split / "labels" / (dst_img.stem + ".txt")).write_text(
                "\n".join(lines_out) + "\n", encoding="utf-8"
            )
            counts[split] += 1
    return counts, skipped


def add_toothcaries(src_root: Path, dst_root: Path, prefix: str = "ds_toothcaries"):
    """ToothCariesAI: 단일 클래스(KARIES, index 0) -> cavity(0). 좌표 그대로, 클래스 인덱스만 확인."""
    counts = {"train": 0, "valid": 0, "test": 0}
    for split in ("train", "valid", "test"):
        img_dir = src_root / split / "images"
        lbl_dir = src_root / split / "labels"
        if not img_dir.exists():
            continue
        for img in img_dir.glob("*"):
            dst_img = dst_root / split / "images" / f"{prefix}_{img.name}"
            shutil.copy2(img, dst_img)
            lbl_src = lbl_dir / (img.stem + ".txt")
            lines_out = []
            if lbl_src.exists():
                for line in lbl_src.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    parts = line.split()
                    lines_out.append(" ".join(["0"] + parts[1:]))  # 유일한 클래스 -> cavity(0)
            (dst_root / split / "labels" / (dst_img.stem + ".txt")).write_text(
                "\n".join(lines_out) + ("\n" if lines_out else ""), encoding="utf-8"
            )
            counts[split] += 1
    return counts


def main():
    run_d = ROOT / "dataset_runD"
    if run_d.exists():
        shutil.rmtree(run_d)
    ensure_dirs(run_d)

    copy_as_is(RUN_C, run_d)

    merges_sec_remap = {0: 0, 1: 0, 3: 1}  # Caries/Cavity->cavity, Tooth->normal, Crack(2) 제외
    merges_sec_counts = add_obb_ds(DS_MERGES_SEC, run_d, "ds_mergessec", merges_sec_remap)

    data_fix_counts, data_fix_skipped = add_data_fix(DS_DATA_FIX, run_d)

    toothcaries_counts = add_toothcaries(DS_TOOTHCARIES, run_d)

    dentalv7_counts_before = {
        s: len(list((DS_DENTALV7 / s / "images").glob("*"))) for s in ("train", "valid", "test")
    }
    copy_as_is(DS_DENTALV7, run_d)

    write_yaml(run_d)

    def count_split(root: Path):
        return {s: len(list((root / s / "images").glob("*"))) for s in ("train", "valid", "test")}

    print("Run D (재정의) 최종 counts:", count_split(run_d))
    print("caries_segmentation_merges_sec 추가:", merges_sec_counts)
    print("data fix v1 추가(karies만):", data_fix_counts, "/ 제외된 이미지:", data_fix_skipped)
    print("ToothCariesAI 추가:", toothcaries_counts)
    print("dental.v7 변환본 추가:", dentalv7_counts_before)


if __name__ == "__main__":
    main()
