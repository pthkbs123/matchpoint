"""
Run E: dataset_runD 전체 + 새로 찾은 데이터셋 중 실제 쓸 수 있는 것만 병합.

포함되는 것:
  - DentalCaries.v2i.yolov8 (axis-aligned, 4663장, Caries/Cavity->cavity, Tooth->normal, Crack 제외)
    클래스 인덱스는 이미지에 박스 그려서 직접 확인한 값: 0=Caries, 1=Cavity, 2=Tooth, 3=Crack
  - caries detection.v1i.yolov8 (중복 제거 후 499장만 남은 버전 사용, DentalCaries.v2i와 80% 겹쳐서 중복 제거해둠)
    클래스 인덱스: 0=Caries, 1=Cavity, 2=Crack, 3=Tooth (역시 시각 확인한 값)
  - Benchmarking Dataset (Zenodo, 6266장 중 실제 충치 라벨이 있는 2164장만 사용)
    라벨 없는 이미지(약 4039장)는 "정상"인지 "라벨 누락"인지 알 수 없어서 통째로 제외.
    클래스 0(유치 충치)/1(영구치 충치) 둘 다 -> cavity. normal 기여는 없음(이 소스는 충치 박스만 있어서).

사용법:
    python build_dataset_runE.py    # dataset_runD가 pc_setup/ 아래 이미 있어야 함
"""
import json
import shutil
from pathlib import Path

PC_SETUP = Path(__file__).resolve().parent.parent  # pc_setup/ (이 파일은 pc_setup/training/ 안에 있음)
BASE = PC_SETUP.parent                              # matchpoint_tmp/
DOWNLOADS = BASE.parent                             # D:\pth
DATASET_DIR = DOWNLOADS / "dataset"                 # 사용자가 정리한 원본 데이터셋 폴더

RUN_D = PC_SETUP / "dataset_runD"
DS_DENTALCARIES_V2 = DATASET_DIR / "DentalCaries.v2i.yolov8"
DS_CARIES_DETECTION = DATASET_DIR / "caries detection.v1i.yolov8"  # 중복 제거된 버전
DS_BENCHMARK = DATASET_DIR / "Benchmarking Dataset" / "Benchmarking Dataset"

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


def add_yolo_ds(src_root: Path, dst_root: Path, prefix: str, remap: dict):
    """axis-aligned YOLO 라벨(class cx cy w h) 데이터셋을 클래스 재매핑하며 추가.
    remap에 없는 클래스(Crack 등)는 해당 라인만 제외하고, 이미지 자체는 유지
    (Tooth->normal 매핑이 있어서 대부분 이미지에 normal 라벨은 남기 때문)."""
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
                    cls = int(parts[0])
                    if cls not in remap:
                        continue
                    lines_out.append(" ".join([str(remap[cls])] + parts[1:]))
            (dst_root / split / "labels" / (dst_img.stem + ".txt")).write_text(
                "\n".join(lines_out) + ("\n" if lines_out else ""), encoding="utf-8"
            )
            counts[split] += 1
    return counts


def add_benchmark(src_root: Path, dst_root: Path, prefix: str = "ds_zenodo"):
    """Zenodo Benchmarking Dataset: yolo/ 라벨이 있고 내용이 비어있지 않은 이미지만 사용.
    class 0/1(유치/영구치 충치) 둘 다 -> cavity(0). 라벨 없는 이미지는 통째로 제외
    (정상인지 라벨 누락인지 알 수 없어서 normal로 쓸 수 없음)."""
    counts = {"train": 0, "valid": 0, "test": 0}
    skipped = {"train": 0, "valid": 0, "test": 0}
    for split in ("train", "valid", "test"):
        img_dir = src_root / split / "images"
        lbl_dir = src_root / split / "yolo"
        if not img_dir.exists():
            continue
        for img in img_dir.glob("*"):
            lbl_src = lbl_dir / (img.stem + ".txt")
            if not lbl_src.exists():
                skipped[split] += 1
                continue
            lines_in = [l for l in lbl_src.read_text(encoding="utf-8").splitlines() if l.strip()]
            if not lines_in:
                skipped[split] += 1
                continue
            lines_out = []
            for line in lines_in:
                parts = line.split()
                lines_out.append(" ".join(["0"] + parts[1:]))  # 0/1 둘 다 -> cavity(0)
            dst_img = dst_root / split / "images" / f"{prefix}_{img.name}"
            shutil.copy2(img, dst_img)
            (dst_root / split / "labels" / (dst_img.stem + ".txt")).write_text(
                "\n".join(lines_out) + "\n", encoding="utf-8"
            )
            counts[split] += 1
    return counts, skipped


def main():
    run_e = PC_SETUP / "dataset_runE"
    if run_e.exists():
        shutil.rmtree(run_e)
    ensure_dirs(run_e)

    copy_as_is(RUN_D, run_e)

    dentalcaries_v2_remap = {0: 0, 1: 0, 2: 1}  # Caries/Cavity->cavity, Tooth->normal, Crack(3) 제외
    dentalcaries_v2_counts = add_yolo_ds(DS_DENTALCARIES_V2, run_e, "ds_dentalcariesv2", dentalcaries_v2_remap)

    caries_detection_remap = {0: 0, 1: 0, 3: 1}  # Caries/Cavity->cavity, Tooth->normal, Crack(2) 제외
    caries_detection_counts = add_yolo_ds(DS_CARIES_DETECTION, run_e, "ds_cariesdetection", caries_detection_remap)

    benchmark_counts, benchmark_skipped = add_benchmark(DS_BENCHMARK, run_e)

    write_yaml(run_e)

    def count_split(root: Path):
        return {s: len(list((root / s / "images").glob("*"))) for s in ("train", "valid", "test")}

    print("Run E 최종 counts:", count_split(run_e))
    print("DentalCaries.v2i 추가:", dentalcaries_v2_counts)
    print("caries detection.v1i(중복제거) 추가:", caries_detection_counts)
    print("Zenodo Benchmarking(라벨있는 것만) 추가:", benchmark_counts, "/ 제외:", benchmark_skipped)


if __name__ == "__main__":
    main()
