import unittest
from datetime import date

from main import _recommended_capture_schedule


class CaptureScheduleTests(unittest.TestCase):
    def test_missing_weekday_uses_current_weekday(self):
        interval, interval_label, schedule_label, schedule_type = _recommended_capture_schedule(
            None,
            date(2026, 8, 25),
            None,
        )

        self.assertEqual(interval, 7)
        self.assertEqual(interval_label, "주 1회")
        self.assertEqual(schedule_label, "매주 화요일")
        self.assertEqual(schedule_type, "weekly_1")


if __name__ == "__main__":
    unittest.main()
