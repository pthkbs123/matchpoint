import unittest
from unittest.mock import patch

import numpy as np

from detection_ensemble import (
    CavityDetector,
    MODE_ENSEMBLE,
    MODE_LEGACY,
    MODE_RUN_H,
    load_detector,
)


class FakeBox:
    def __init__(self, class_id, confidence, coordinates):
        self.cls = np.array([class_id], dtype=np.float32)
        self.conf = np.array([confidence], dtype=np.float32)
        self.xyxy = np.array([coordinates], dtype=np.float32)


class FakeResult:
    names = {0: "cavity", 1: "normal"}

    def __init__(self, boxes):
        self.boxes = boxes


class FakeModel:
    def __init__(self, boxes):
        self.result = FakeResult(boxes)
        self.calls = []

    def predict(self, image, **kwargs):
        self.calls.append(kwargs)
        return [self.result]


class DetectionEnsembleTests(unittest.TestCase):
    def test_ensemble_merges_cavity_and_keeps_normal_only_from_run_a(self):
        run_a = FakeModel([
            FakeBox(0, 0.80, [10, 10, 50, 50]),
            FakeBox(0, 0.05, [80, 10, 110, 50]),
            FakeBox(1, 0.90, [10, 70, 50, 110]),
        ])
        run_h = FakeModel([
            FakeBox(0, 0.70, [11, 11, 51, 51]),
            FakeBox(0, 0.60, [80, 10, 110, 50]),
            FakeBox(1, 0.99, [80, 70, 110, 110]),
        ])
        detector = CavityDetector(MODE_ENSEMBLE, {"runA": run_a, "runH": run_h})

        detections = detector.predict(object())

        cavity = [item for item in detections if item["class"] == "cavity"]
        normal = [item for item in detections if item["class"] == "normal"]
        self.assertEqual(len(cavity), 2)
        self.assertEqual(len(normal), 1)
        self.assertEqual(normal[0]["source"], "runA")
        self.assertEqual({item["source"] for item in cavity}, {"runA", "runH"})
        self.assertEqual(run_a.calls[0]["conf"], 0.10)
        self.assertEqual(run_h.calls[0]["conf"], 0.15)

    def test_run_h_uses_separate_cavity_and_normal_thresholds(self):
        run_h = FakeModel([
            FakeBox(0, 0.16, [10, 10, 50, 50]),
            FakeBox(1, 0.20, [10, 70, 50, 110]),
            FakeBox(1, 0.30, [80, 70, 110, 110]),
        ])
        detector = CavityDetector(MODE_RUN_H, {"runH": run_h})

        detections = detector.predict(object())

        self.assertEqual([item["class"] for item in detections], ["cavity", "normal"])

    def test_legacy_mode_preserves_point_25_threshold(self):
        legacy = FakeModel([
            FakeBox(0, 0.24, [10, 10, 50, 50]),
            FakeBox(0, 0.30, [60, 10, 100, 50]),
        ])
        detector = CavityDetector(MODE_LEGACY, {"legacy": legacy})

        detections = detector.predict(object())

        self.assertEqual(len(detections), 1)
        self.assertEqual(detections[0]["source"], "legacy")

    def test_load_detector_rejects_unknown_mode(self):
        with self.assertRaises(ValueError):
            load_detector(object(), mode="unknown")

    def test_load_detector_checks_required_files(self):
        class MissingPath:
            def __truediv__(self, _name):
                return self

            def is_file(self):
                return False

            def __str__(self):
                return "missing.pt"

        with patch("detection_ensemble.YOLO"):
            with self.assertRaises(RuntimeError):
                load_detector(MissingPath(), mode=MODE_ENSEMBLE)


if __name__ == "__main__":
    unittest.main()
