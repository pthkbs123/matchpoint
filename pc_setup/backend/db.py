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

CREATE TABLE IF NOT EXISTS analysis_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    cavity_count INTEGER NOT NULL,
    normal_count INTEGER NOT NULL,
    total_detections INTEGER NOT NULL,
    score INTEGER NOT NULL,
    detections_json TEXT NOT NULL
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

        # 기존 smileguard.db도 삭제 없이 소셜 로그인 스키마로 올린다.
        user_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        if "provider_user_id" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN provider_user_id TEXT")

        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_provider_identity
            ON users(provider, provider_user_id)
            WHERE provider_user_id IS NOT NULL
            """
        )
