"""
YOLO 박스(cavity/normal) 좌표만 이용한 휴리스틱 색상 분석.
잇몸을 별도로 탐지하는 모델이 없으므로, 치열 배치와 점막색을 함께 이용해
치아 박스 위·아래 중 잇몸 후보 영역을 추정한다.

주의: 아래 BASELINE_*/MAX_* 상수는 임상적으로 검증된 값이 아니라
일반적인 구강 사진 톤을 기준으로 잡은 휴리스틱 초깃값이다.
실사용 데이터가 쌓이면 재보정이 필요하다.
"""
import os

import cv2
import numpy as np

PREPROCESS_ORIGINAL = "original"
PREPROCESS_WB_CLAHE = "wb_clahe"
PREPROCESS_WB_BILATERAL_CLAHE = "wb_bilateral_clahe"
PREPROCESS_MODES = (
    PREPROCESS_ORIGINAL,
    PREPROCESS_WB_CLAHE,
    PREPROCESS_WB_BILATERAL_CLAHE,
)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default

# LAB b*채널(파랑-노랑 축) 기준: 이 값 이하는 황변 없음(0점), 이 값 이상은 심한 황변(100점)
BASELINE_B = _env_float("COLOR_YELLOW_LAB_B_GOOD", 132.0)
MAX_B = _env_float("COLOR_YELLOW_LAB_B_HIGH", 175.0)

# LAB a*채널(초록-빨강 축) 기준: 이 값 이하는 염증 없음(0점), 이 값 이상은 심한 염증(100점)
BASELINE_A = _env_float("COLOR_GUM_LAB_A_GOOD", 140.0)
MAX_A = _env_float("COLOR_GUM_LAB_A_HIGH", 185.0)
BASELINE_S = _env_float("COLOR_GUM_HSV_S_GOOD", 70.0)
MAX_S = _env_float("COLOR_GUM_HSV_S_HIGH", 180.0)

# 잇몸 후보 영역을 구강 점막 색으로 좁히기 위한 HSV(OpenCV 0-179/0-255/0-255) 범위
# 빨간색은 색상환에서 0 근처와 179 근처 양쪽에 걸쳐 나타나므로(wraparound) 두 구간을 모두 잡는다.
GUM_HUE_HIGH = 25
GUM_HUE_WRAP_LOW = 170
GUM_SAT_MIN = 40
GUM_VAL_MIN = 40

MIN_VALID_PIXELS = 200
GUM_BAND_RATIO = 0.15


def preprocess_bgr(
    image_bgr: np.ndarray,
    mode: str = PREPROCESS_WB_CLAHE,
) -> np.ndarray:
    """선택한 전처리를 적용한다. 실패 시 원본 복사본을 반환한다."""
    if mode not in PREPROCESS_MODES:
        raise ValueError(f"지원하지 않는 전처리 모드입니다: {mode}")
    if mode == PREPROCESS_ORIGINAL:
        return image_bgr.copy()

    try:
        result = image_bgr.astype(np.float32)
        mean_b, mean_g, mean_r = (result[:, :, i].mean() for i in range(3))
        gray_mean = (mean_b + mean_g + mean_r) / 3.0
        for i, channel_mean in enumerate((mean_b, mean_g, mean_r)):
            if channel_mean > 1e-3:
                result[:, :, i] *= gray_mean / channel_mean
        result = np.clip(result, 0, 255).astype(np.uint8)

        if mode == PREPROCESS_WB_BILATERAL_CLAHE:
            result = cv2.bilateralFilter(result, d=7, sigmaColor=40, sigmaSpace=40)

        lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_channel = clahe.apply(l_channel)
        lab = cv2.merge((l_channel, a_channel, b_channel))
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    except Exception:
        return image_bgr.copy()


def _clip_box(x1, y1, x2, y2, width, height):
    x1 = max(0, min(int(x1), width - 1))
    x2 = max(0, min(int(x2), width))
    y1 = max(0, min(int(y1), height - 1))
    y2 = max(0, min(int(y2), height))
    return x1, y1, x2, y2


def compute_yellowing_details(preprocessed_bgr: np.ndarray, detections: list) -> dict:
    """황변 건강점수와 보정에 필요한 LAB b* 원시 통계를 반환한다."""
    height, width = preprocessed_bgr.shape[:2]
    lab = cv2.cvtColor(preprocessed_bgr, cv2.COLOR_BGR2LAB)

    b_values = []
    for d in detections:
        if d["class"] != "normal":
            continue
        x1, y1, x2, y2 = _clip_box(
            d["box"]["x1"], d["box"]["y1"], d["box"]["x2"], d["box"]["y2"], width, height
        )
        if x2 <= x1 or y2 <= y1:
            continue
        region = lab[y1:y2, x1:x2]
        l_region = region[:, :, 0].astype(np.float32)
        b_region = region[:, :, 2].astype(np.float32)
        # 과다노출(하이라이트)/그림자 픽셀 제외
        low, high = np.percentile(l_region, [15, 90])
        mask = (l_region >= low) & (l_region <= high)
        if mask.any():
            b_values.append(b_region[mask])

    if not b_values:
        return {"score": None, "mean_lab_b": None, "valid_pixels": 0}

    all_b = np.concatenate(b_values)
    if all_b.size < MIN_VALID_PIXELS:
        return {
            "score": None,
            "mean_lab_b": round(float(all_b.mean()), 3) if all_b.size else None,
            "valid_pixels": int(all_b.size),
        }

    mean_b = round(float(all_b.mean()), 3)
    return {
        "score": health_index_from_baseline(mean_b, BASELINE_B, MAX_B),
        "mean_lab_b": mean_b,
        "valid_pixels": int(all_b.size),
    }


def measure_yellowing_lab_b(preprocessed_bgr: np.ndarray, detections: list) -> float | None:
    """팀 기존 개인 Baseline 흐름과 호환되는 LAB b* 평균."""
    details = compute_yellowing_details(preprocessed_bgr, detections)
    return details["mean_lab_b"] if details["valid_pixels"] >= MIN_VALID_PIXELS else None


def _gum_color_mask(hsv_region: np.ndarray) -> np.ndarray:
    h_ch = hsv_region[:, :, 0]
    s_ch = hsv_region[:, :, 1]
    v_ch = hsv_region[:, :, 2]
    hue_mask = (h_ch <= GUM_HUE_HIGH) | (h_ch >= GUM_HUE_WRAP_LOW)
    return hue_mask & (s_ch >= GUM_SAT_MIN) & (v_ch >= GUM_VAL_MIN)


def _gum_band(box: dict, side: str, width: int, height: int) -> tuple[int, int, int, int]:
    box_h = box["y2"] - box["y1"]
    band_h = max(1.0, GUM_BAND_RATIO * box_h)
    if side == "above":
        band_y1, band_y2 = box["y1"] - band_h, box["y1"]
    else:
        band_y1, band_y2 = box["y2"], box["y2"] + band_h
    return _clip_box(box["x1"], band_y1, box["x2"], band_y2, width, height)


def _clear_two_row_split(boxes: list[dict]) -> tuple[set[int], set[int]] | None:
    """치아 중심 간 큰 공백이 확인될 때만 위·아래 치열을 분리한다."""
    if len(boxes) < 4:
        return None

    ordered = sorted(
        range(len(boxes)),
        key=lambda index: (boxes[index]["y1"] + boxes[index]["y2"]) / 2.0,
    )
    centers = np.array(
        [(boxes[index]["y1"] + boxes[index]["y2"]) / 2.0 for index in ordered],
        dtype=np.float32,
    )
    gaps = np.diff(centers)
    split_at = int(np.argmax(gaps))
    upper = ordered[: split_at + 1]
    lower = ordered[split_at + 1 :]
    if len(upper) < 2 or len(lower) < 2:
        return None

    heights = np.array([box["y2"] - box["y1"] for box in boxes], dtype=np.float32)
    within_gaps = np.delete(gaps, split_at)
    usual_gap = float(np.median(within_gaps)) if within_gaps.size else 0.0
    row_gap = float(gaps[split_at])
    minimum_gap = max(8.0, float(np.median(heights)) * 0.35, usual_gap * 1.8)
    if row_gap < minimum_gap:
        return None
    return set(upper), set(lower)


def _candidate_gum_density(
    hsv: np.ndarray,
    boxes: list[dict],
    side: str,
    width: int,
    height: int,
) -> float:
    valid_pixels = 0
    total_pixels = 0
    for box in boxes:
        x1, y1, x2, y2 = _gum_band(box, side, width, height)
        if x2 <= x1 or y2 <= y1:
            continue
        mask = _gum_color_mask(hsv[y1:y2, x1:x2])
        valid_pixels += int(mask.sum())
        total_pixels += int(mask.size)
    return valid_pixels / total_pixels if total_pixels else 0.0


def compute_gum_inflammation_details(preprocessed_bgr: np.ndarray, detections: list) -> dict:
    """치열 방향을 반영한 잇몸 LAB 건강점수와 HSV 보조점수를 반환한다."""
    height, width = preprocessed_bgr.shape[:2]
    hsv = cv2.cvtColor(preprocessed_bgr, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(preprocessed_bgr, cv2.COLOR_BGR2LAB)

    boxes = []
    for detection in detections:
        box = detection.get("box", {})
        if box.get("y2", 0) > box.get("y1", 0):
            boxes.append(box)

    row_split = _clear_two_row_split(boxes)
    if row_split:
        upper_indexes, lower_indexes = row_split
        sides = ["above" if index in upper_indexes else "below" for index in range(len(boxes))]
    else:
        above_density = _candidate_gum_density(hsv, boxes, "above", width, height)
        below_density = _candidate_gum_density(hsv, boxes, "below", width, height)
        selected_side = "above" if above_density > below_density else "below"
        sides = [selected_side] * len(boxes)

    a_values = []
    h_values = []
    s_values = []
    v_values = []
    used_sides = []
    for box, preferred_side in zip(boxes, sides):
        x1, y1, x2, y2 = _gum_band(box, preferred_side, width, height)
        if x2 <= x1 or y2 <= y1:
            continue

        hsv_region = hsv[y1:y2, x1:x2]
        lab_region = lab[y1:y2, x1:x2]
        mask = _gum_color_mask(hsv_region)
        used_side = preferred_side
        if not mask.any():
            opposite_side = "below" if preferred_side == "above" else "above"
            opposite = _gum_band(box, opposite_side, width, height)
            ox1, oy1, ox2, oy2 = opposite
            if ox2 > ox1 and oy2 > oy1:
                opposite_hsv = hsv[oy1:oy2, ox1:ox2]
                opposite_mask = _gum_color_mask(opposite_hsv)
                if opposite_mask.any():
                    x1, y1, x2, y2 = opposite
                    hsv_region = opposite_hsv
                    lab_region = lab[y1:y2, x1:x2]
                    mask = opposite_mask
                    used_side = opposite_side

        h_ch = hsv_region[:, :, 0]
        s_ch = hsv_region[:, :, 1]
        v_ch = hsv_region[:, :, 2]
        if mask.any():
            a_values.append(lab_region[:, :, 1][mask].astype(np.float32))
            h_values.append(h_ch[mask].astype(np.float32))
            s_values.append(s_ch[mask].astype(np.float32))
            v_values.append(v_ch[mask].astype(np.float32))
            used_sides.append(used_side)

    roi_details = {
        "roi_band_ratio": GUM_BAND_RATIO,
        "roi_above_count": used_sides.count("above"),
        "roi_below_count": used_sides.count("below"),
    }

    if not a_values:
        return {
            "score": None,
            "hsv_health_score": None,
            "lab_hsv_gap": None,
            "lab_hsv_agreement": None,
            "mean_lab_a": None,
            "mean_hsv_h": None,
            "mean_hsv_s": None,
            "mean_hsv_v": None,
            "valid_pixels": 0,
            **roi_details,
        }

    all_a = np.concatenate(a_values)
    all_h = np.concatenate(h_values)
    all_s = np.concatenate(s_values)
    all_v = np.concatenate(v_values)
    hue_radians = all_h * (2.0 * np.pi / 180.0)
    mean_hue_radians = np.arctan2(np.sin(hue_radians).mean(), np.cos(hue_radians).mean())
    mean_h = float((mean_hue_radians % (2.0 * np.pi)) * (180.0 / (2.0 * np.pi)))
    raw_values = {
        "mean_lab_a": round(float(all_a.mean()), 3),
        "mean_hsv_h": round(mean_h, 3),
        "mean_hsv_s": round(float(all_s.mean()), 3),
        "mean_hsv_v": round(float(all_v.mean()), 3),
        "valid_pixels": int(all_a.size),
        **roi_details,
    }
    if all_a.size < MIN_VALID_PIXELS:
        return {
            "score": None,
            "hsv_health_score": None,
            "lab_hsv_gap": None,
            "lab_hsv_agreement": None,
            **raw_values,
        }

    lab_health = health_index_from_baseline(raw_values["mean_lab_a"], BASELINE_A, MAX_A)
    hsv_health = health_index_from_baseline(raw_values["mean_hsv_s"], BASELINE_S, MAX_S)
    gap = round(abs(lab_health - hsv_health), 1)
    agreement = "high" if gap <= 10 else "medium" if gap <= 25 else "low"
    return {
        "score": lab_health,
        "hsv_health_score": hsv_health,
        "lab_hsv_gap": gap,
        "lab_hsv_agreement": agreement,
        **raw_values,
    }


def measure_gum_lab_a(preprocessed_bgr: np.ndarray, detections: list) -> float | None:
    """팀 기존 개인 Baseline 흐름과 호환되는 LAB a* 평균."""
    details = compute_gum_inflammation_details(preprocessed_bgr, detections)
    return details["mean_lab_a"] if details["valid_pixels"] >= MIN_VALID_PIXELS else None


def health_index_from_baseline(
    measured_value: float | None,
    baseline_value: float | None,
    maximum_reference: float,
) -> float | None:
    """개인 기준값보다 색상축 값이 증가한 정도를 100(유지)~0(주의) 건강 점수로 바꾼다."""
    if measured_value is None or baseline_value is None:
        return None
    scale = max(maximum_reference - baseline_value, 1.0)
    severity = np.clip((measured_value - baseline_value) / scale, 0.0, 1.0) * 100.0
    return round(100.0 - float(severity), 1)


def compute_yellowing_index(
    preprocessed_bgr: np.ndarray,
    detections: list,
    baseline_b: float = BASELINE_B,
) -> float | None:
    """LAB b* 평균을 지정한 기준값과 비교해 황변 건강 점수로 환산한다."""
    measured_b = measure_yellowing_lab_b(preprocessed_bgr, detections)
    return health_index_from_baseline(measured_b, baseline_b, MAX_B)


def compute_gum_inflammation_index(
    preprocessed_bgr: np.ndarray,
    detections: list,
    baseline_a: float = BASELINE_A,
) -> float | None:
    """LAB a* 평균을 지정한 기준값과 비교해 잇몸 건강 점수로 환산한다."""
    measured_a = measure_gum_lab_a(preprocessed_bgr, detections)
    return health_index_from_baseline(measured_a, baseline_a, MAX_A)
