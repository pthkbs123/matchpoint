import unittest

from color_baseline import REQUIRED_SAMPLES, advance_running_baseline


class ColorBaselineTests(unittest.TestCase):
    def test_first_three_valid_samples_become_average(self):
        average = None
        count = 0
        for sample in (130.0, 140.0, 150.0):
            average, count = advance_running_baseline(average, count, sample)

        self.assertEqual(count, REQUIRED_SAMPLES)
        self.assertEqual(average, 140.0)

    def test_fourth_sample_does_not_change_completed_baseline(self):
        average, count = advance_running_baseline(140.0, 3, 180.0)
        self.assertEqual((average, count), (140.0, 3))

    def test_invalid_sample_does_not_increase_count(self):
        average, count = advance_running_baseline(135.0, 1, None)
        self.assertEqual((average, count), (135.0, 1))


if __name__ == "__main__":
    unittest.main()
