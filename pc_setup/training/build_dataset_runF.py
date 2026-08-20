"""
Run F: dataset_runE 전체를 베이스로, ICDAS 소스의 2클래스 재매핑 기준만 다시 잡음.

배경 (dataset_audit로 확인된 문제):
  기존 규칙(build_datasets.py): ICDAS 0=Sound만 normal, 1~6 전부 cavity로 재매핑.
  근데 ICDAS 1(Faint Visual Change)/2(Distinct Visual Change)는 육안으로 거의 안 보이는
  초기 탈회 단계라 "충치"라 부르기 애매함. HIGH 우선순위로 뽑힌 ICDAS 소스 이미지의 원본 라벨
  2,525개 중 30.6%가 이 1~2단계였고, 이게 "사진은 정상처럼 보이는데 GT는 cavity"인 노이즈의
  큰 원인으로 추정됨 (dataset_audit/chatgpt_review 참고).

새 규칙: 0(Sound), 1(Faint), 2(Distinct) -> normal / 3(국소붕괴), 4(상아질음영), 5(뚜렷cavity), 6(광범위) -> cavity
  즉 "육안으로 실제 구조적 손상이 보이는 단계"만 cavity로 남김.

사용법:
    python build_dataset_runF.py              # 전체 실행
    python build_dataset_runF.py --max-images 50   # 소량 테스트
"""
import argparse
import shutil
from pathlib import Path

PC_SETUP = Path(__file__).resolve().parent.parent
BASE = PC_SETUP.parent
DATASET_DIR = BASE / "dataset"

RUN_E = PC_SETUP / "dataset_runE" / "dataset_runE"
if not RUN_E.exists():
    RUN_E = DATASET_DIR / "archive" / "dataset_runE" / "dataset_runE"

ICDAS_SRC = DATASET_DIR / "Caries Classification ICDAS II.v3i.yolov8"

CLASSES = ["cavity", "normal"]
OLD_REMAP = {0: 1, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}   # 기존에 실제 적용됐던 규칙 (검증용)
NEW_REMAP = {0: 1, 1: 1, 2: 1, 3: 0, 4: 0, 5: 0, 6: 0}   # 이번에 새로 적용할 규칙


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


def copy_as_is(src_root: Path, dst_root: Path, max_images: int | None):
    counts = {"train": 0, "valid": 0, "test": 0}
    for split in ("train", "valid", "test"):
        imgs = sorted((src_root / split / "images").glob("*"))
        if max_images is not None:
            imgs = imgs[:max_images]
        for img in imgs:
            shutil.copy2(img, dst_root / split / "images" / img.name)
            lbl = src_root / split / "labels" / (img.stem + ".txt")
            if lbl.exists():
                shutil.copy2(lbl, dst_root / split / "labels" / lbl.name)
            counts[split] += 1
    return counts


def remap_icdas_line(line: str, remap: dict):
    parts = line.strip().split()
    if len(parts) != 5:
        return None
    cls = int(parts[0])
    if cls not in remap:
        return None
    parts[0] = str(remap[cls])
    return " ".join(parts)


def fix_icdas_labels(dst_root: Path):
    icdas_images = {p.name: p for p in ICDAS_SRC.rglob("images/*") if p.is_file()}
    fixed_count, before_cavity, after_cavity = 0, 0, 0
    for split in ("train", "valid", "test"):
        for img in (dst_root / split / "images").glob("*"):
            if img.name not in icdas_images:
                continue
            src_img = icdas_images[img.name]
            src_label = src_img.parent.parent / "labels" / (src_img.stem + ".txt")
            if not src_label.exists():
                continue
            dst_label = dst_root / split / "labels" / (img.stem + ".txt")
            old_lines = dst_label.read_text(encoding="utf-8").splitlines() if dst_label.exists() else []
            before_cavity += sum(1 for l in old_lines if l.strip().startswith("0 "))

            new_lines = []
            for raw_line in src_label.read_text(encoding="utf-8").splitlines():
                converted = remap_icdas_line(raw_line, NEW_REMAP)
                if converted:
                    new_lines.append(converted)
            dst_label.write_text("\n".join(new_lines) + ("\n" if new_lines else ""), encoding="utf-8")
            after_cavity += sum(1 for l in new_lines if l.startswith("0 "))
            fixed_count += 1
    return fixed_count, before_cavity, after_cavity


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-images", type=int, default=None)
    args = parser.parse_args()

    run_f = PC_SETUP / "dataset_runF"
    if run_f.exists():
        shutil.rmtree(run_f)
    ensure_dirs(run_f)

    counts = copy_as_is(RUN_E, run_f, args.max_images)
    write_yaml(run_f)
    fixed_count, before_cavity, after_cavity = fix_icdas_labels(run_f)

    print("Run F counts (runE 그대로 복사):", counts)
    print(f"ICDAS 라벨 재매핑 적용된 이미지: {fixed_count}장")
    print(f"cavity 박스 수: 기존규칙 {before_cavity}개 -> 새규칙 {after_cavity}개 "
          f"({after_cavity - before_cavity:+d}, {(after_cavity - before_cavity) / before_cavity * 100:+.1f}%)"
          if before_cavity else "")


if __name__ == "__main__":
    main()
