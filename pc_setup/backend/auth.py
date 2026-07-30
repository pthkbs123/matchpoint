"""비밀번호 해싱, 세션 토큰 발급/검증, 비밀번호 재설정 토큰."""
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Header, HTTPException

from db import get_conn, now_iso

PBKDF2_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return secrets.compare_digest(digest.hex(), digest_hex)


def create_session(conn, user_id: int) -> str:
    token = secrets.token_hex(32)
    conn.execute(
        "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
        (token, user_id, now_iso()),
    )
    return token


def get_user_by_token(token: str):
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT users.* FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()
        return row


def _extract_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[len("Bearer "):].strip() or None


def require_user(authorization: str | None = Header(None)):
    token = _extract_token(authorization)
    user = get_user_by_token(token) if token else None
    if user is None:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    return user


def optional_user(authorization: str | None = Header(None)):
    token = _extract_token(authorization)
    return get_user_by_token(token) if token else None


def mask_email(email: str) -> str:
    """abcdef@gmail.com -> ab****@gmail.com 형태로 일부만 보여준다."""
    local, _, domain = email.partition("@")
    if not domain:
        return email
    visible = local[:2] if len(local) > 2 else local[:1]
    hidden_length = max(len(local) - len(visible), 2)
    return f"{visible}{'*' * hidden_length}@{domain}"


def create_password_reset_token(conn, user_id: int, ttl_minutes: int = 30) -> str:
    token = secrets.token_urlsafe(32)
    created = datetime.now(timezone.utc)
    expires = created + timedelta(minutes=ttl_minutes)
    conn.execute(
        "INSERT INTO password_resets (token, user_id, created_at, expires_at, used) VALUES (?, ?, ?, ?, 0)",
        (token, user_id, created.isoformat(), expires.isoformat()),
    )
    return token


def get_valid_password_reset(conn, token: str):
    row = conn.execute(
        "SELECT * FROM password_resets WHERE token = ? AND used = 0", (token,)
    ).fetchone()
    if row is None:
        return None
    if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
        return None
    return row


def mark_password_reset_used(conn, token: str):
    conn.execute("UPDATE password_resets SET used = 1 WHERE token = ?", (token,))
