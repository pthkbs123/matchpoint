import tempfile
import unittest
from pathlib import Path

import db
import main


class BaselineResetTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_path = db.DB_PATH
        db.DB_PATH = Path(self.temp_dir.name) / "test.db"
        db.init_db()
        with db.get_conn() as conn:
            user = conn.execute(
                """
                INSERT INTO users (email, password_hash, name, provider, created_at)
                VALUES ('reset@test.local', 'hash', '테스트', 'email', ?)
                """,
                (db.now_iso(),),
            )
            self.user_id = user.lastrowid
            child = conn.execute(
                """
                INSERT INTO children
                    (user_id, name, yellowing_baseline_b, yellowing_baseline_count,
                     gum_baseline_a, gum_baseline_count, created_at)
                VALUES (?, '자녀', 135.0, 3, 145.0, 3, ?)
                """,
                (self.user_id, db.now_iso()),
            )
            self.child_id = child.lastrowid
            conn.execute(
                """
                INSERT INTO analysis_records
                    (user_id, child_id, created_at, cavity_count, normal_count,
                     total_detections, score, detections_json)
                VALUES (?, ?, ?, 0, 1, 1, 100, '[]')
                """,
                (self.user_id, self.child_id, db.now_iso()),
            )

    def tearDown(self):
        db.DB_PATH = self.original_path
        self.temp_dir.cleanup()

    def test_reset_preserves_history_and_clears_only_child_baseline(self):
        result = main.reset_color_baseline(
            main.BaselineResetRequest(child_id=self.child_id),
            user={"id": self.user_id},
        )

        self.assertEqual(result["baseline"]["generation"], 2)
        self.assertEqual(result["baseline"]["yellowing"]["sample_count"], 0)
        self.assertEqual(result["baseline"]["gum_inflammation"]["sample_count"], 0)
        with db.get_conn() as conn:
            child = conn.execute("SELECT * FROM children WHERE id = ?", (self.child_id,)).fetchone()
            history_count = conn.execute(
                "SELECT COUNT(*) AS count FROM analysis_records WHERE child_id = ?",
                (self.child_id,),
            ).fetchone()["count"]
        self.assertIsNone(child["yellowing_baseline_b"])
        self.assertIsNone(child["gum_baseline_a"])
        self.assertEqual(history_count, 1)


if __name__ == "__main__":
    unittest.main()
