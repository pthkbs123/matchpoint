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


if __name__ == "__main__":
    unittest.main()

