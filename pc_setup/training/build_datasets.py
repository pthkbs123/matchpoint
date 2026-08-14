"""
두 개의 학습용 데이터셋을 만든다.

Run A (dataset_runA): 기존 dataset_yolo(418장, cavity/normal) + 새 데이터셋1(ICDAS 7단계, 2000장)
  - 데이터셋1의 7단계 라벨을 2클래스로 재매핑: 0(Sound)->normal, 1~6->cavity

Run B (dataset_runB): Run A 전체 + 새 데이터셋2(Caries_Dataset, 2001장, 분류용 폴더 구조)
  - 바운딩박스 라벨이 없으므로 이미지 전체를 하나의 박스로 취급해서 라벨 생성
  - 폴더명 기준: NoEnamel_Caries->normal, AdvanceEnamel_Caries/EarlyStageEnamel_Caries->cavity

최종 클래스 순서는 기존과 동일하게 유지: 0=cavity, 1=normal
"""
import random
import shutil
from pathlib import Path

random.seed(42)

PC_SETUP = Path(__file__).resolve().parent.parent  # pc_setup/ (이 파일은 pc_setup/training/ 안에 있음)
BASE = PC_SETUP.parent                              # matchpoint_tmp/
DOWNLOADS = BASE.parent                             # D:\pth
DATASET_DIR = DOWNLOADS / "dataset"                 # D:\pth\dataset (사용자가 원본 데이터셋들을 정리해둔 폴더)

ORIG = PC_SETUP / "dataset_yolo"
DS1 = DATASET_DIR / "Caries Classification ICDAS II.v3i.yolov8"
DS2 = DATASET_DIR / "Caries_Dataset"

CLASSES = ["cavity", "normal"]  # 0=cavity, 1=normal (기존과 동일)


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
    """이미 cavity/normal 2클래스인 dataset_yolo를 그대로 복사."""
    for split in ("train", "valid", "test"):
        for img in (src_root / split / "images").glob("*"):
            shutil.copy2(img, dst_root / split / "images" / img.name)
        for lbl in (src_root / split / "labels").glob("*.txt"):
            shutil.copy2(lbl, dst_root / split / "labels" / lbl.name)


def copy_remap_ds1(src_root: Path, dst_root: Path):
    """ICDAS 7단계 -> 2클래스로 재매핑하며 복사. 0=Sound->normal(1), 1~6->cavity(0)."""
    for split in ("train", "valid", "test"):
        img_dir = src_root / split / "images"
        lbl_dir = src_root / split / "labels"
        if not img_dir.exists():
            continue
        for img in img_dir.glob("*"):
            shutil.copy2(img, dst_root / split / "images" / img.name)
            lbl_src = lbl_dir / (img.stem + ".txt")
            lbl_dst = dst_root / split / "labels" / (img.stem + ".txt")
            if not lbl_src.exists():
                lbl_dst.write_text("", encoding="utf-8")
                continue
            lines_out = []
            for line in lbl_src.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                parts = line.split()
                cls = int(parts[0])
                new_cls = 1 if cls == 0 else 0  # 0=Sound->normal, 1~6->cavity
                lines_out.append(" ".join([str(new_cls)] + parts[1:]))
            lbl_dst.write_text("\n".join(lines_out) + ("\n" if lines_out else ""), encoding="utf-8")


def add_ds2_whole_image_boxes(src_root: Path, dst_root: Path, split_ratio=(0.8, 0.1, 0.1)):
    """라벨 없는 분류용 이미지 -> 전체 이미지를 박스로 하는 라벨 생성 후 train/valid/test 분배."""
    folder_to_class = {
        "NoEnamel_Caries": 1,          # normal
        "AdvanceEnamel_Caries": 0,     # cavity
        "EarlyStageEnamel_Caries": 0,  # cavity
    }
    counts = {"train": 0, "valid": 0, "test": 0}
    for folder, cls in folder_to_class.items():
        imgs = sorted(p for p in (src_root / folder).glob("*") if p.is_file())
        random.shuffle(imgs)
        n = len(imgs)
        n_train = int(n * split_ratio[0])
        n_valid = int(n * split_ratio[1])
        split_assign = (
            ["train"] * n_train
            + ["valid"] * n_valid
            + ["test"] * (n - n_train - n_valid)
        )
        for img, split in zip(imgs, split_assign):
            dst_img = dst_root / split / "images" / f"ds2_{folder}_{img.name}"
            shutil.copy2(img, dst_img)
            lbl_path = dst_root / split / "labels" / (dst_img.stem + ".txt")
            # 이미지 전체를 박스로 사용 (가장자리 여유 살짝 둠)
            lbl_path.write_text(f"{cls} 0.5 0.5 0.98 0.98\n", encoding="utf-8")
            counts[split] += 1
    return counts


def main():
    # ---- Run A: dataset_yolo + dataset1(remap) ----
    run_a = PC_SETUP / "dataset_runA"
    if run_a.exists():
        shutil.rmtree(run_a)
    ensure_dirs(run_a)
    copy_as_is(ORIG, run_a)
    copy_remap_ds1(DS1, run_a)
    write_yaml(run_a)

    # ---- Run B: Run A 전체 복사 + dataset2(whole-image box) 추가 ----
    run_b = PC_SETUP / "dataset_runB"
    if run_b.exists():
        shutil.rmtree(run_b)
    shutil.copytree(run_a, run_b)
    ds2_counts = add_ds2_whole_image_boxes(DS2, run_b)
    write_yaml(run_b)

    def count_split(root: Path):
        return {s: len(list((root / s / "images").glob("*"))) for s in ("train", "valid", "test")}

    print("Run A counts:", count_split(run_a))
    print("Run B counts:", count_split(run_b))
    print("dataset2 added to Run B:", ds2_counts)


if __name__ == "__main__":
    main()
