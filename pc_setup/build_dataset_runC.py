"""
Run C: dataset_runB 전체 + 데이터셋3(Dental.v1-dentalai, OBB 형식, 6418장)까지 합본.

데이터셋3은 회전 바운딩박스(OBB, 8개 좌표) 형식이라 축정렬 바운딩박스(x_center,y_center,w,h)로 변환.
클래스 재매핑: Caries(0), Cavity(1) -> cavity(0) / Tooth(3) -> normal(1) / Crack(2)는 충치 판별과 무관하므로 제외.
(한 이미지에서 Crack 박스만 있었다면 그 라인만 빠지고 나머지 박스는 유지, 전부 빠지면 빈 라벨 파일 = 배경 이미지로 처리)

사용법:
    python build_datasets.py       # runA/runB 아직 없으면 먼저 실행
    python build_dataset_runC.py
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent          # pc_setup/
BASE = ROOT.parent                                # matchpoint_tmp/
DOWNLOADS = BASE.parent                           # D:\pth

RUN_B = ROOT / "dataset_runB"
DS3 = DOWNLOADS / "Dental.v1-dentalai.yolov8-obb"

CLASSES = ["cavity", "normal"]  # 0=cavity, 1=normal (기존과 동일)

# Dental.v1-dentalai 클래스: 0=Caries,1=Cavity,2=Crack,3=Tooth
DS3_REMAP = {0: 0, 1: 0, 3: 1}  # Caries/Cavity -> cavity(0), Tooth -> normal(1), Crack(2)는 제외


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


def obb_to_aabb_line(parts):
    cls = int(parts[0])
    if cls not in DS3_REMAP:
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
    new_cls = DS3_REMAP[cls]
    return f"{new_cls} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}"


def add_ds3(src_root: Path, dst_root: Path):
    counts = {"train": 0, "valid": 0, "test": 0}
    for split in ("train", "valid", "test"):
        img_dir = src_root / split / "images"
        lbl_dir = src_root / split / "labels"
        if not img_dir.exists():
            continue
        for img in img_dir.glob("*"):
            dst_img = dst_root / split / "images" / f"ds3_{img.name}"
            shutil.copy2(img, dst_img)
            lbl_src = lbl_dir / (img.stem + ".txt")
            lbl_dst = dst_root / split / "labels" / (dst_img.stem + ".txt")
            lines_out = []
            if lbl_src.exists():
                for line in lbl_src.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    converted = obb_to_aabb_line(line.split())
                    if converted:
                        lines_out.append(converted)
            lbl_dst.write_text("\n".join(lines_out) + ("\n" if lines_out else ""), encoding="utf-8")
            counts[split] += 1
    return counts


def main():
    run_c = ROOT / "dataset_runC"
    if run_c.exists():
        shutil.rmtree(run_c)
    ensure_dirs(run_c)
    copy_as_is(RUN_B, run_c)
    ds3_counts = add_ds3(DS3, run_c)
    write_yaml(run_c)

    def count_split(root: Path):
        return {s: len(list((root / s / "images").glob("*"))) for s in ("train", "valid", "test")}

    print("Run C counts:", count_split(run_c))
    print("dataset3 added to Run C:", ds3_counts)


if __name__ == "__main__":
    main()
