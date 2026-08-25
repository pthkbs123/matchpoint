"""
YOLO 박스(cavity/normal) 좌표만 이용한 휴리스틱 색상 분석.
잇몸을 별도로 탐지하는 모델이 없으므로, 치아 박스 바로 아래쪽 영역을 잇몸 후보로 추정한다.

주의: 아래 BASELINE_*/MAX_* 상수는 임상적으로 검증된 값이 아니라
일반적인 구강 사진 톤을 기준으로 잡은 휴리스틱 초깃값이다.
실사용 데이터가 쌓이면 재보정이 필요하다.
"""
import cv2
import numpy as np

# LAB b*채널(파랑-노랑 축) 기준: 이 값 이하는 황변 없음(0점), 이 값 이상은 심한 황변(100점)
BASELINE_B = 132.0
MAX_B = 175.0

# LAB a*채널(초록-빨강 축) 기준: 이 값 이하는 염증 없음(0점), 이 값 이상은 심한 염증(100점)
BASELINE_A = 140.0
MAX_A = 185.0

# 잇몸 후보 영역을 구강 점막 색으로 좁히기 위한 HSV(OpenCV 0-179/0-255/0-255) 범위
# 빨간색은 색상환에서 0 근처와 179 근처 양쪽에 걸쳐 나타나므로(wraparound) 두 구간을 모두 잡는다.
GUM_HUE_HIGH = 25
GUM_HUE_WRAP_LOW = 170
GUM_SAT_MIN = 40
GUM_VAL_MIN = 40

MIN_VALID_PIXELS = 200


def preprocess_bgr(image_bgr: np.ndarray) -> np.ndarray:
    """Gray-world 화이트밸런스 보정 + CLAHE 대비 정규화. 실패 시 원본 반환."""
    try:
        result = image_bgr.astype(np.float32)
        mean_b, mean_g, mean_r = (result[:, :, i].mean() for i in range(3))
        gray_mean = (mean_b + mean_g + mean_r) / 3.0
        for i, channel_mean in enumerate((mean_b, mean_g, mean_r)):
            if channel_mean > 1e-3:
                result[:, :, i] *= gray_mean / channel_mean
        result = np.clip(result, 0, 255).astype(np.uint8)

        lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_channel = clahe.apply(l_channel)
        lab = cv2.merge((l_channel, a_channel, b_channel))
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    except Exception:
        return image_bgr


def _clip_box(x1, y1, x2, y2, width, height):
    x1 = max(0, min(int(x1), width - 1))
    x2 = max(0, min(int(x2), width))
    y1 = max(0, min(int(y1), height - 1))
    y2 = max(0, min(int(y2), height))
    return x1, y1, x2, y2


def measure_yellowing_lab_b(preprocessed_bgr: np.ndarray, detections: list) -> float | None:
    """치아(normal) 박스의 유효 픽셀에서 개인 Baseline용 LAB b* 평균을 구한다."""
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
        return None

    all_b = np.concatenate(b_values)
    if all_b.size < MIN_VALID_PIXELS:
        return None

    return round(float(all_b.mean()), 3)


def measure_gum_lab_a(preprocessed_bgr: np.ndarray, detections: list) -> float | None:
    """HSV로 선별한 잇몸 후보 픽셀에서 개인 Baseline용 LAB a* 평균을 구한다."""
    height, width = preprocessed_bgr.shape[:2]
    hsv = cv2.cvtColor(preprocessed_bgr, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(preprocessed_bgr, cv2.COLOR_BGR2LAB)

    a_values = []
    for d in detections:
        box_h = d["box"]["y2"] - d["box"]["y1"]
        if box_h <= 0:
            continue
        band_y1 = d["box"]["y2"]
        band_y2 = d["box"]["y2"] + 0.3 * box_h
        x1, y1, x2, y2 = _clip_box(d["box"]["x1"], band_y1, d["box"]["x2"], band_y2, width, height)
        if x2 <= x1 or y2 <= y1:
            continue

        hsv_region = hsv[y1:y2, x1:x2]
        lab_region = lab[y1:y2, x1:x2]
        h_ch = hsv_region[:, :, 0]
        s_ch = hsv_region[:, :, 1]
        v_ch = hsv_region[:, :, 2]
        hue_mask = (h_ch <= GUM_HUE_HIGH) | (h_ch >= GUM_HUE_WRAP_LOW)
        mask = hue_mask & (s_ch >= GUM_SAT_MIN) & (v_ch >= GUM_VAL_MIN)
        if mask.any():
            a_values.append(lab_region[:, :, 1][mask].astype(np.float32))

    if not a_values:
        return None

    all_a = np.concatenate(a_values)
    if all_a.size < MIN_VALID_PIXELS:
        return None

    return round(float(all_a.mean()), 3)


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
