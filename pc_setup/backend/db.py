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
    birthplace TEXT,
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
        _migrate(conn)


def _migrate(conn):
    """기존 DB를 삭제하지 않고 최신 스키마로 올린다."""
    user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    if "birthplace" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN birthplace TEXT")
    if "provider_user_id" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN provider_user_id TEXT")

    record_columns = {row["name"] for row in conn.execute("PRAGMA table_info(analysis_records)")}
    if "child_id" not in record_columns:
        conn.execute("ALTER TABLE analysis_records ADD COLUMN child_id INTEGER REFERENCES children(id)")

    child_columns = {row["name"] for row in conn.execute("PRAGMA table_info(children)")}
    if "birth_date" not in child_columns:
        conn.execute("ALTER TABLE children ADD COLUMN birth_date TEXT")

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_provider_identity
        ON users(provider, provider_user_id)
        WHERE provider_user_id IS NOT NULL
        """
    )
