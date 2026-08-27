import tempfile
import unittest
from pathlib import Path

import db


class DatabaseSchemaTests(unittest.TestCase):
    def test_color_baseline_and_measurement_columns_are_created(self):
        original_path = db.DB_PATH
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                db.DB_PATH = Path(temp_dir) / "test-smileguard.db"
                db.init_db()
                with db.get_conn() as conn:
                    user_columns = {
                        row["name"] for row in conn.execute("PRAGMA table_info(users)")
                    }
                    child_columns = {
                        row["name"] for row in conn.execute("PRAGMA table_info(children)")
                    }
                    record_columns = {
                        row["name"] for row in conn.execute("PRAGMA table_info(analysis_records)")
                    }

                self.assertIn("phone", user_columns)
                self.assertTrue({
                    "yellowing_baseline_b",
                    "yellowing_baseline_count",
                    "gum_baseline_a",
                    "gum_baseline_count",
                    "color_baseline_generation",
                    "color_baseline_reset_at",
                }.issubset(child_columns))
                self.assertTrue({
                    "lab_b_mean",
                    "lab_a_mean",
                    "yellowing_baseline_b",
                    "gum_baseline_a",
                    "yellowing_delta",
                    "gum_inflammation_delta",
                    "color_baseline_source",
                }.issubset(record_columns))
        finally:
            db.DB_PATH = original_path


if __name__ == "__main__":
    unittest.main()
