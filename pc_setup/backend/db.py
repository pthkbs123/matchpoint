"""SQLite 저장소: 사용자, 로그인 세션, 분석 이력."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "smileguard.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    name TEXT NOT NULL,
    phone TEXT,
    picture TEXT,
    provider TEXT NOT NULL DEFAULT 'email',
    provider_user_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS password_resets (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS children (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    birth_date TEXT,
    reminder_weekday INTEGER,
    yellowing_baseline_b REAL,
    yellowing_baseline_count INTEGER NOT NULL DEFAULT 0,
    gum_baseline_a REAL,
    gum_baseline_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    child_id INTEGER REFERENCES children(id),
    created_at TEXT NOT NULL,
    cavity_count INTEGER NOT NULL,
    normal_count INTEGER NOT NULL,
    total_detections INTEGER NOT NULL,
    score INTEGER NOT NULL,
    yellowing_index REAL,
    gum_inflammation_index REAL,
    lab_b_mean REAL,
    lab_a_mean REAL,
    yellowing_baseline_b REAL,
    gum_baseline_a REAL,
    yellowing_delta REAL,
    gum_inflammation_delta REAL,
    color_baseline_source TEXT,
    detections_json TEXT NOT NULL,
    image_path TEXT
);
"""


def now_iso():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)


def _migrate(conn):
    """기존 DB를 삭제하지 않고 최신 스키마로 올린다."""
    user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    if "phone" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    if "provider_user_id" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN provider_user_id TEXT")

    record_columns = {row["name"] for row in conn.execute("PRAGMA table_info(analysis_records)")}
    if "child_id" not in record_columns:
        conn.execute("ALTER TABLE analysis_records ADD COLUMN child_id INTEGER REFERENCES children(id)")
    if "image_path" not in record_columns:
        conn.execute("ALTER TABLE analysis_records ADD COLUMN image_path TEXT")
    if "yellowing_index" not in record_columns:
        conn.execute("ALTER TABLE analysis_records ADD COLUMN yellowing_index REAL")
    if "gum_inflammation_index" not in record_columns:
        conn.execute("ALTER TABLE analysis_records ADD COLUMN gum_inflammation_index REAL")
    if "lab_b_mean" not in record_columns:
        conn.execute("ALTER TABLE analysis_records ADD COLUMN lab_b_mean REAL")
    if "lab_a_mean" not in record_columns:
        conn.execute("ALTER TABLE analysis_records ADD COLUMN lab_a_mean REAL")
    if "yellowing_baseline_b" not in record_columns:
        conn.execute("ALTER TABLE analysis_records ADD COLUMN yellowing_baseline_b REAL")
    if "gum_baseline_a" not in record_columns:
        conn.execute("ALTER TABLE analysis_records ADD COLUMN gum_baseline_a REAL")
    if "yellowing_delta" not in record_columns:
        conn.execute("ALTER TABLE analysis_records ADD COLUMN yellowing_delta REAL")
    if "gum_inflammation_delta" not in record_columns:
        conn.execute("ALTER TABLE analysis_records ADD COLUMN gum_inflammation_delta REAL")
    if "color_baseline_source" not in record_columns:
        conn.execute("ALTER TABLE analysis_records ADD COLUMN color_baseline_source TEXT")

    child_columns = {row["name"] for row in conn.execute("PRAGMA table_info(children)")}
    if "birth_date" not in child_columns:
        conn.execute("ALTER TABLE children ADD COLUMN birth_date TEXT")
    if "reminder_weekday" not in child_columns:
        conn.execute("ALTER TABLE children ADD COLUMN reminder_weekday INTEGER")
    if "yellowing_baseline_b" not in child_columns:
        conn.execute("ALTER TABLE children ADD COLUMN yellowing_baseline_b REAL")
    if "yellowing_baseline_count" not in child_columns:
        conn.execute("ALTER TABLE children ADD COLUMN yellowing_baseline_count INTEGER NOT NULL DEFAULT 0")
    if "gum_baseline_a" not in child_columns:
        conn.execute("ALTER TABLE children ADD COLUMN gum_baseline_a REAL")
    if "gum_baseline_count" not in child_columns:
        conn.execute("ALTER TABLE children ADD COLUMN gum_baseline_count INTEGER NOT NULL DEFAULT 0")

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_provider_identity
        ON users(provider, provider_user_id)
        WHERE provider_user_id IS NOT NULL
        """
    )
