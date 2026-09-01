import unittest

from capture_quality import assess_capture_quality


class CaptureQualityTests(unittest.TestCase):
    def test_rejects_cavity_only_false_positive(self):
        quality = assess_capture_quality([
            {"class": "cavity"},
            {"class": "cavity"},
        ])

        self.assertFalse(quality["valid"])
        self.assertEqual(quality["code"], "insufficient_tooth_regions")

    def test_accepts_capture_when_normal_tooth_region_exists(self):
        quality = assess_capture_quality([
            {"class": "cavity"},
            {"class": "normal"},
        ])

        self.assertTrue(quality["valid"])
        self.assertEqual(quality["code"], "accepted")


if __name__ == "__main__":
    unittest.main()
