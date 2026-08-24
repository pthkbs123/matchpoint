import unittest
from datetime import date

from monthly_report import build_monthly_report_notification


class MonthlyReportTests(unittest.TestCase):
    def test_previous_month_records_create_one_report(self):
        notification = build_monthly_report_notification(
            [
                {"date": date(2026, 7, 5), "score": 90},
                {"date": date(2026, 7, 12), "score": 100},
                {"date": date(2026, 6, 20), "score": 90},
            ],
            date(2026, 8, 24),
            "child-7",
        )

        self.assertEqual(notification["id"], "monthly-report:child-7:2026-07")
        self.assertEqual(notification["scan_count"], 2)
        self.assertEqual(notification["score"], 95)
        self.assertEqual(notification["score_change"], 5)

    def test_no_previous_month_records_returns_none(self):
        notification = build_monthly_report_notification(
            [{"date": date(2026, 8, 2), "score": 100}],
            date(2026, 8, 24),
            "child-7",
        )
        self.assertIsNone(notification)


if __name__ == "__main__":
    unittest.main()
