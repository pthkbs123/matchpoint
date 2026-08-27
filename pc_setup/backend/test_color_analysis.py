import unittest

import cv2
import numpy as np

from color_analysis import (
    PREPROCESS_MODES,
    PREPROCESS_ORIGINAL,
    PREPROCESS_WB_BILATERAL_CLAHE,
    compute_gum_inflammation_details,
    compute_yellowing_details,
    preprocess_bgr,
)


class ColorAnalysisTest(unittest.TestCase):
    def setUp(self):
        self.image = np.full((120, 160, 3), (70, 90, 180), dtype=np.uint8)
        cv2.rectangle(self.image, (30, 75), (130, 110), (60, 70, 210), -1)
        self.detections = [
            {
                "class": "normal",
                "confidence": 0.9,
                "box": {"x1": 30, "y1": 20, "x2": 130, "y2": 80},
            }
        ]

    def test_all_preprocess_modes_preserve_shape_and_dtype(self):
        for mode in PREPROCESS_MODES:
            with self.subTest(mode=mode):
                result = preprocess_bgr(self.image, mode=mode)
                self.assertEqual(result.shape, self.image.shape)
                self.assertEqual(result.dtype, np.uint8)

    def test_original_mode_returns_independent_copy(self):
        result = preprocess_bgr(self.image, mode=PREPROCESS_ORIGINAL)
        self.assertTrue(np.array_equal(result, self.image))
        self.assertIsNot(result, self.image)

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            preprocess_bgr(self.image, mode="unknown")

    def test_color_details_include_raw_values_and_valid_pixel_counts(self):
        processed = preprocess_bgr(self.image, mode=PREPROCESS_WB_BILATERAL_CLAHE)
        yellowing = compute_yellowing_details(processed, self.detections)
        gum = compute_gum_inflammation_details(processed, self.detections)

        self.assertIsNotNone(yellowing["score"])
        self.assertIsNotNone(yellowing["mean_lab_b"])
        self.assertGreaterEqual(yellowing["valid_pixels"], 200)
        self.assertIsNotNone(gum["score"])
        self.assertIsNotNone(gum["mean_lab_a"])
        self.assertIsNotNone(gum["mean_hsv_h"])
        self.assertIsNotNone(gum["mean_hsv_s"])
        self.assertIsNotNone(gum["mean_hsv_v"])
        self.assertIsNotNone(gum["hsv_health_score"])
        self.assertIn(gum["lab_hsv_agreement"], {"high", "medium", "low"})
        self.assertAlmostEqual(
            gum["lab_hsv_gap"],
            abs(gum["score"] - gum["hsv_health_score"]),
            places=1,
        )
        self.assertGreaterEqual(gum["valid_pixels"], 200)
        self.assertEqual(gum["roi_band_ratio"], 0.15)
        self.assertEqual(gum["roi_below_count"], 1)

    def test_two_rows_use_above_for_upper_and_below_for_lower(self):
        image = np.full((220, 240, 3), (30, 30, 30), dtype=np.uint8)
        detections = []
        for x1 in (30, 90, 150):
            cv2.rectangle(image, (x1, 50), (x1 + 50, 90), (210, 210, 210), -1)
            cv2.rectangle(image, (x1, 43), (x1 + 50, 49), (60, 70, 210), -1)
            detections.append({
                "class": "normal",
                "confidence": 0.9,
                "box": {"x1": x1, "y1": 50, "x2": x1 + 50, "y2": 90},
            })
        for x1 in (30, 90, 150):
            cv2.rectangle(image, (x1, 130), (x1 + 50, 170), (210, 210, 210), -1)
            cv2.rectangle(image, (x1, 171), (x1 + 50, 177), (60, 70, 210), -1)
            detections.append({
                "class": "normal",
                "confidence": 0.9,
                "box": {"x1": x1, "y1": 130, "x2": x1 + 50, "y2": 170},
            })

        gum = compute_gum_inflammation_details(image, detections)

        self.assertEqual(gum["roi_above_count"], 3)
        self.assertEqual(gum["roi_below_count"], 3)
        self.assertGreaterEqual(gum["valid_pixels"], 200)

    def test_single_upper_row_can_select_gum_above_teeth(self):
        image = np.full((140, 180, 3), (30, 30, 30), dtype=np.uint8)
        cv2.rectangle(image, (30, 50), (150, 100), (210, 210, 210), -1)
        cv2.rectangle(image, (30, 42), (150, 49), (60, 70, 210), -1)
        detections = [{
            "class": "normal",
            "confidence": 0.9,
            "box": {"x1": 30, "y1": 50, "x2": 150, "y2": 100},
        }]

        gum = compute_gum_inflammation_details(image, detections)

        self.assertEqual(gum["roi_above_count"], 1)
        self.assertEqual(gum["roi_below_count"], 0)
        self.assertGreaterEqual(gum["valid_pixels"], 200)


if __name__ == "__main__":
    unittest.main()

