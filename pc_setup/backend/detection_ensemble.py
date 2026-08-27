"""Run A/Run H 충치 앙상블과 단일 모델 추론을 한 인터페이스로 제공한다."""
import os
from pathlib import Path
from threading import Lock

from ultralytics import YOLO


MODE_ENSEMBLE = "ensemble"
MODE_RUN_H = "runH"
MODE_LEGACY = "legacy"
SUPPORTED_MODES = (MODE_ENSEMBLE, MODE_RUN_H, MODE_LEGACY)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


RUN_A_CAVITY_CONF = _env_float("CAVITY_CONF_RUN_A", 0.10)
RUN_H_CAVITY_CONF = _env_float("CAVITY_CONF_RUN_H", 0.15)
NORMAL_CONF = _env_float("NORMAL_CONF", 0.25)
ENSEMBLE_NMS_IOU = _env_float("CAVITY_ENSEMBLE_NMS_IOU", 0.50)


def _box_iou(left: dict, right: dict) -> float:
    x1 = max(left["x1"], right["x1"])
    y1 = max(left["y1"], right["y1"])
    x2 = min(left["x2"], right["x2"])
    y2 = min(left["y2"], right["y2"])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    left_area = max(0.0, left["x2"] - left["x1"]) * max(0.0, left["y2"] - left["y1"])
    right_area = max(0.0, right["x2"] - right["x1"]) * max(0.0, right["y2"] - right["y1"])
    union = left_area + right_area - intersection
    return intersection / union if union > 0 else 0.0


def _nms(detections: list[dict], iou_threshold: float) -> list[dict]:
    kept = []
    for detection in sorted(detections, key=lambda item: item["confidence"], reverse=True):
        if all(_box_iou(detection["box"], existing["box"]) < iou_threshold for existing in kept):
            kept.append(detection)
    return kept


def _detections_from_result(
    result,
    cavity_conf: float,
    include_normal: bool,
    source: str,
) -> tuple[list[dict], list[dict]]:
    cavity = []
    normal = []
    if result.boxes is None:
        return cavity, normal
    for box in result.boxes:
        class_id = int(box.cls[0])
        class_name = str(result.names[class_id])
        confidence = float(box.conf[0])
        x1, y1, x2, y2 = [float(value) for value in box.xyxy[0]]
        detection = {
            "class": class_name,
            "confidence": round(confidence, 4),
            "box": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            "source": source,
        }
        if class_name == "cavity" and confidence >= cavity_conf:
            cavity.append(detection)
        elif class_name == "normal" and include_normal and confidence >= NORMAL_CONF:
            normal.append(detection)
    return cavity, normal


class CavityDetector:
    def __init__(self, mode: str, models: dict[str, object]):
        if mode not in SUPPORTED_MODES:
            raise ValueError(f"지원하지 않는 추론 모드입니다: {mode}")
        self.mode = mode
        self.models = models
        self._lock = Lock()

    @property
    def model_names(self) -> list[str]:
        return list(self.models.keys())

    def predict(self, image) -> list[dict]:
        with self._lock:
            if self.mode == MODE_ENSEMBLE:
                result_a = self.models["runA"].predict(
                    image, conf=RUN_A_CAVITY_CONF, verbose=False
                )[0]
                result_h = self.models["runH"].predict(
                    image, conf=RUN_H_CAVITY_CONF, verbose=False
                )[0]
                cavity_a, normal = _detections_from_result(
                    result_a, RUN_A_CAVITY_CONF, True, "runA"
                )
                cavity_h, _ = _detections_from_result(
                    result_h, RUN_H_CAVITY_CONF, False, "runH"
                )
                cavity = _nms(cavity_a + cavity_h, ENSEMBLE_NMS_IOU)
                return cavity + normal

            model_name = "runH" if self.mode == MODE_RUN_H else "legacy"
            cavity_conf = RUN_H_CAVITY_CONF if self.mode == MODE_RUN_H else NORMAL_CONF
            result = self.models[model_name].predict(
                image, conf=min(cavity_conf, NORMAL_CONF), verbose=False
            )[0]
            cavity, normal = _detections_from_result(
                result, cavity_conf, True, model_name
            )
            return cavity + normal


def load_detector(model_dir: Path, mode: str | None = None) -> CavityDetector:
    selected_mode = (mode or os.getenv("CAVITY_INFERENCE_MODE", MODE_ENSEMBLE)).strip()
    required = {
        MODE_ENSEMBLE: ("runA", "runH"),
        MODE_RUN_H: ("runH",),
        MODE_LEGACY: ("legacy",),
    }.get(selected_mode)
    if required is None:
        raise ValueError(
            f"CAVITY_INFERENCE_MODE={selected_mode!r}는 지원하지 않습니다. "
            f"가능한 값: {', '.join(SUPPORTED_MODES)}"
        )
    paths = {
        "legacy": model_dir / "best.pt",
        "runA": model_dir / "best_runG_A.pt",
        "runH": model_dir / "best_runH.pt",
    }
    missing = [str(paths[name]) for name in required if not paths[name].is_file()]
    if missing:
        raise RuntimeError("모델 파일을 찾을 수 없습니다: " + ", ".join(missing))
    models = {name: YOLO(str(paths[name])) for name in required}
    return CavityDetector(selected_mode, models)
