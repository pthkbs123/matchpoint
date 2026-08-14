"""
dental.v7i.yolov8 (21클래스, 폴리곤 세그멘테이션 형식)을
cavity/normal 2클래스 bbox 형식으로 변환만 해두는 스크립트.
(runE 등 최종 병합에는 아직 안 넣음, 나중에 병합 지시하면 dataset_dentalv7_converted를 그대로 합치면 됨)

클래스 매핑:
  caries, caries cervical, caries de dentina, caries de esmalte,
  caries interproximal, caries profunda, caries radicular,
  caries rampante, cavity  -> cavity(0)   (충치 세부유형 전부 합침)
  tooth -> normal(1)
  나머지(absceso, bridge, crown, impaction, periapical lesion, pockets,
        root canal, root canal with prosthesis, root stump, sarro, ulcera) -> 제외
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent          # pc_setup/
DOWNLOADS = ROOT.parent.parent                    # D:\pth
SRC = DOWNLOADS / "dataset" / "dental.v7i.yolov8"
DST = ROOT / "dataset_dentalv7_converted"

CLASSES = ["cavity", "normal"]

# 원본 클래스 인덱스 (data.yaml 순서) -> 새 클래스 인덱스 (0=cavity, 1=normal). 없는 건 제외.
SRC_NAMES = [
    'absceso', 'bridge', 'caries', 'caries cervical', 'caries de dentina',
    'caries de esmalte', 'caries interproximal', 'caries profunda',
    'caries radicular', 'caries rampante', 'cavity', 'crown', 'impaction',
    'periapical lesion', 'pockets', 'root canal', 'root canal with prosthesis',
    'root stump', 'sarro', 'tooth', 'ulcera',
]
CAVITY_NAMES = {
    'caries', 'caries cervical', 'caries de dentina', 'caries de esmalte',
    'caries interproximal', 'caries profunda', 'caries radicular',
    'caries rampante', 'cavity',
}
NORMAL_NAMES = {'tooth'}

REMAP = {}
for i, name in enumerate(SRC_NAMES):
    if name in CAVITY_NAMES:
        REMAP[i] = 0
    elif name in NORMAL_NAMES:
        REMAP[i] = 1
    # 나머지는 REMAP에 없음 -> 제외


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


def polygon_to_aabb_line(parts):
    cls = int(parts[0])
    if cls not in REMAP:
        return None
    coords = list(map(float, parts[1:]))
    if len(coords) < 6 or len(coords) % 2 != 0:  # 폴리곤이면 점 3개(6개 값) 이상
        return None
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
    new_cls = REMAP[cls]
    return f"{new_cls} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}"


def main():
    if DST.exists():
        shutil.rmtree(DST)
    ensure_dirs(DST)
    write_yaml(DST)

    counts = {"train": 0, "valid": 0, "test": 0}
    dropped_empty = {"train": 0, "valid": 0, "test": 0}
    for split in ("train", "valid", "test"):
        img_dir = SRC / split / "images"
        lbl_dir = SRC / split / "labels"
        if not img_dir.exists():
            continue
        for img in img_dir.glob("*"):
            lbl_src = lbl_dir / (img.stem + ".txt")
            lines_out = []
            if lbl_src.exists():
                for line in lbl_src.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    converted = polygon_to_aabb_line(line.split())
                    if converted:
                        lines_out.append(converted)
            if not lines_out:
                # cavity/normal 어느 쪽도 아닌(전부 제외 대상 클래스) 이미지는 통째로 스킵
                dropped_empty[split] += 1
                continue
            dst_img = DST / split / "images" / img.name
            shutil.copy2(img, dst_img)
            (DST / split / "labels" / (img.stem + ".txt")).write_text(
                "\n".join(lines_out) + "\n", encoding="utf-8"
            )
            counts[split] += 1

    print("변환 완료:", counts)
    print("cavity/normal 라벨이 하나도 없어 제외된 이미지:", dropped_empty)


if __name__ == "__main__":
    main()
