"""
로컬 YOLOv8 추론 + 로그인/이력 백엔드 서버
사용법:
    1) 학습 완료 후 best.pt 를 backend/model/best.pt 위치에 복사
    2) uvicorn main:app --reload --port 8000   (이 파일이 있는 backend/ 폴더에서 실행)
    3) React 프론트(개발서버 localhost:3000)에서 http://localhost:8000 으로 요청
"""
import io
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from PIL import Image, ImageOps
from pydantic import BaseModel
from ultralytics import YOLO

BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env", override=True)

from auth import (
    create_password_reset_token,
    create_session,
    get_valid_password_reset,
    hash_password,
    mark_password_reset_used,
    mask_email,
    optional_user,
    require_user,
    verify_password,
)
from db import get_conn, init_db, now_iso
from mailer import send_reset_password_email

MODEL_PATH = BACKEND_DIR / "model" / "best.pt"
CAPTURE_DIR = BACKEND_DIR / "uploads"
_backend_google_client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
_frontend_google_client_id = os.getenv("REACT_APP_GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_ID = (
    _frontend_google_client_id
    if not _backend_google_client_id
    or _backend_google_client_id.lower().startswith("your-")
    else _backend_google_client_id
)
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "").strip()
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET", "").strip()
KAKAO_REDIRECT_URI = (
    os.getenv("KAKAO_REDIRECT_URI")
    or os.getenv("REACT_APP_KAKAO_REDIRECT_URI")
    or "http://localhost:3000/"
).strip()
FRONTEND_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

app = FastAPI(title="MatchPoint API")

# React 개발 서버(localhost:3000)에서의 요청 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = None


@app.on_event("startup")
def startup():
    global model
    init_db()

    if not MODEL_PATH.exists():
        raise RuntimeError(
            f"모델 파일을 찾을 수 없습니다: {MODEL_PATH}\n"
            "train.py로 학습 후 생성된 best.pt를 backend/model/ 폴더에 넣어주세요."
        )
    model = YOLO(str(MODEL_PATH))
    print(f"모델 로드 완료: {MODEL_PATH}")


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model is not None}


# ---------------------------------------------------------------------------
# 인증
# ---------------------------------------------------------------------------
class EmailAuthRequest(BaseModel):
    email: str
    password: str
    name: str | None = None
    birthplace: str | None = None


class KakaoAuthRequest(BaseModel):
    code: str
    redirectUri: str


class GoogleAuthRequest(BaseModel):
    credential: str


def _user_json(user_row, email_override: str | None = None) -> dict:
    return {
        "name": user_row["name"],
        "email": email_override or user_row["email"],
        "picture": user_row["picture"] or "/profile-avatar.svg",
        "memberSince": user_row["created_at"],
    }


def _social_login_response(
    provider: str,
    provider_user_id: str,
    email: str | None,
    name: str,
    picture: str | None,
) -> dict:
    """소셜 사용자를 찾거나 만든 뒤 SmileGuard 세션을 발급한다."""
    normalized_email = (email or "").strip().lower()
    fallback_email = f"{provider}_{provider_user_id}@oauth.smileguard.local"

    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE provider = ? AND provider_user_id = ?",
            (provider, provider_user_id),
        ).fetchone()

        if row is None:
            # 같은 이메일의 기존 계정을 자동 연결하면 계정 탈취 위험이 있으므로
            # 충돌할 때는 공급자 고유 ID 기반 내부 이메일을 사용한다.
            stored_email = normalized_email or fallback_email
            email_owner = conn.execute(
                "SELECT id FROM users WHERE email = ?", (stored_email,)
            ).fetchone()
            if email_owner is not None:
                stored_email = fallback_email

            cur = conn.execute(
                """
                INSERT INTO users
                    (email, password_hash, name, picture, provider, provider_user_id, created_at)
                VALUES (?, NULL, ?, ?, ?, ?, ?)
                """,
                (stored_email, name, picture, provider, provider_user_id, now_iso()),
            )
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
        else:
            stored_email = row["email"]
            if normalized_email and normalized_email != stored_email:
                email_owner = conn.execute(
                    "SELECT id FROM users WHERE email = ?", (normalized_email,)
                ).fetchone()
                if email_owner is None or email_owner["id"] == row["id"]:
                    stored_email = normalized_email

            conn.execute(
                "UPDATE users SET email = ?, name = ?, picture = ? WHERE id = ?",
                (stored_email, name, picture, row["id"]),
            )
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (row["id"],)
            ).fetchone()

        token = create_session(conn, row["id"])

    # 동일 이메일의 일반 계정이 이미 있어 DB에는 내부 식별용 주소를
    # 유지하더라도, 공급자가 검증해 전달한 이메일은 화면에 표시한다.
    return {
        "accessToken": token,
        "user": _user_json(row, email_override=normalized_email or None),
    }


@app.post("/api/auth/email")
def auth_email(payload: EmailAuthRequest):
    email = payload.email.strip().lower()
    if not email or not payload.password:
        raise HTTPException(status_code=400, detail="이메일과 비밀번호를 입력해주세요.")

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if row is None:
            # 계정이 없으면 최초 로그인 시점에 자동으로 만들어준다 (데모용 간이 가입)
            name = payload.name or email.split("@")[0]
            cur = conn.execute(
                "INSERT INTO users (email, password_hash, name, birthplace, picture, provider, created_at) VALUES (?, ?, ?, ?, ?, 'email', ?)",
                (email, hash_password(payload.password), name, payload.birthplace, None, now_iso()),
            )
            row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
        elif not row["password_hash"] or not verify_password(payload.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

        token = create_session(conn, row["id"])

    return {"accessToken": token, "user": _user_json(row)}


@app.post("/api/auth/kakao")
async def auth_kakao(payload: KakaoAuthRequest):
    if not KAKAO_REST_API_KEY:
        raise HTTPException(status_code=503, detail="카카오 REST API 키가 설정되지 않았습니다.")
    if payload.redirectUri != KAKAO_REDIRECT_URI:
        raise HTTPException(status_code=400, detail="카카오 Redirect URI가 서버 설정과 일치하지 않습니다.")

    token_form = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_REST_API_KEY,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": payload.code,
    }
    if KAKAO_CLIENT_SECRET:
        token_form["client_secret"] = KAKAO_CLIENT_SECRET

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_response = await client.post(
                "https://kauth.kakao.com/oauth/token",
                data=token_form,
            )
            if token_response.status_code != 200:
                raise HTTPException(status_code=401, detail="카카오 인증 코드를 확인할 수 없습니다.")

            access_token = token_response.json().get("access_token")
            if not access_token:
                raise HTTPException(status_code=401, detail="카카오 액세스 토큰이 없습니다.")

            user_response = await client.get(
                "https://kapi.kakao.com/v2/user/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if user_response.status_code != 200:
                raise HTTPException(status_code=401, detail="카카오 사용자 정보를 가져오지 못했습니다.")
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="카카오 인증 서버에 연결할 수 없습니다.") from exc

    kakao_user = user_response.json()
    provider_user_id = str(kakao_user.get("id", ""))
    if not provider_user_id:
        raise HTTPException(status_code=401, detail="카카오 사용자 ID가 없습니다.")

    account = kakao_user.get("kakao_account") or {}
    profile = account.get("profile") or kakao_user.get("properties") or {}
    # Kakao can return the consented account_email without
    # `is_email_verified` (or with a separate validity flag).  Requiring the
    # verification flag to be exactly True discards an email that the user has
    # already agreed to provide, leaving the local fallback address in place.
    kakao_email = (account.get("email") or "").strip()
    email_needs_agreement = account.get("email_needs_agreement") is True
    email_is_invalid = account.get("is_email_valid") is False
    email = (
        kakao_email
        if kakao_email and not email_needs_agreement and not email_is_invalid
        else None
    )
    name = profile.get("nickname") or "카카오 사용자"
    picture = profile.get("profile_image_url") or profile.get("profile_image")

    return _social_login_response(
        provider="kakao",
        provider_user_id=provider_user_id,
        email=email,
        name=name,
        picture=picture,
    )


@app.post("/api/auth/google")
def auth_google(payload: GoogleAuthRequest):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google 클라이언트 ID가 설정되지 않았습니다.")

    try:
        google_user = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail="Google 로그인 검증에 실패했습니다. 프론트와 백엔드의 클라이언트 ID가 같은지 확인해주세요.",
        ) from exc

    provider_user_id = str(google_user.get("sub", ""))
    if not provider_user_id:
        raise HTTPException(status_code=401, detail="Google 사용자 ID가 없습니다.")

    email = google_user.get("email") if google_user.get("email_verified") else None
    name = google_user.get("name") or "Google 사용자"
    picture = google_user.get("picture")

    return _social_login_response(
        provider="google",
        provider_user_id=provider_user_id,
        email=email,
        name=name,
        picture=picture,
    )


class FindIdRequest(BaseModel):
    name: str
    birthplace: str


@app.post("/api/auth/find-id")
def find_id(payload: FindIdRequest):
    name = payload.name.strip()
    birthplace = payload.birthplace.strip()
    if not name or not birthplace:
        raise HTTPException(status_code=400, detail="이름과 태어난 지역을 입력해주세요.")

    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE name = ? AND birthplace = ?", (name, birthplace)
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="일치하는 계정을 찾을 수 없어요.")

    return {"maskedId": mask_email(row["email"])}


class ResetPasswordRequest(BaseModel):
    email: str


@app.post("/api/auth/reset-password/request")
def reset_password_request(payload: ResetPasswordRequest):
    email = payload.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="이메일을 입력해주세요.")

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="등록된 이메일을 찾을 수 없어요.")
        token = create_password_reset_token(conn, row["id"])

    send_reset_password_email(email, token)
    return {"sent": True}


class ResetPasswordConfirmRequest(BaseModel):
    token: str
    password: str


@app.post("/api/auth/reset-password/confirm")
def reset_password_confirm(payload: ResetPasswordConfirmRequest):
    if not payload.password or len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="비밀번호는 8자 이상이어야 해요.")

    with get_conn() as conn:
        reset_row = get_valid_password_reset(conn, payload.token)
        if reset_row is None:
            raise HTTPException(status_code=400, detail="유효하지 않거나 만료된 링크예요.")

        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(payload.password), reset_row["user_id"]),
        )
        mark_password_reset_used(conn, payload.token)

    return {"success": True}


# ---------------------------------------------------------------------------
# 자녀 프로필 (보호자 1명이 여러 자녀를 등록할 수 있음)
# ---------------------------------------------------------------------------
def _child_json(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "birthDate": row["birth_date"],
        "createdAt": row["created_at"],
    }


class ProfileUpdateRequest(BaseModel):
    name: str


@app.put("/api/profile")
def update_profile(payload: ProfileUpdateRequest, user=Depends(require_user)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="이름을 입력해주세요.")

    with get_conn() as conn:
        conn.execute("UPDATE users SET name = ? WHERE id = ?", (name, user["id"]))
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()

    return {"user": _user_json(row)}


@app.get("/api/children")
def list_children(user=Depends(require_user)):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM children WHERE user_id = ? ORDER BY created_at ASC",
            (user["id"],),
        ).fetchall()
    return {"children": [_child_json(row) for row in rows]}


class ChildCreateRequest(BaseModel):
    name: str
    birthDate: str | None = None


@app.post("/api/children")
def create_child(payload: ChildCreateRequest, user=Depends(require_user)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="자녀 이름을 입력해주세요.")

    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO children (user_id, name, birth_date, created_at) VALUES (?, ?, ?, ?)",
            (user["id"], name, payload.birthDate or None, now_iso()),
        )
        row = conn.execute("SELECT * FROM children WHERE id = ?", (cur.lastrowid,)).fetchone()

    return _child_json(row)


class ChildUpdateRequest(BaseModel):
    name: str
    birthDate: str | None = None


@app.put("/api/children/{child_id}")
def update_child(child_id: int, payload: ChildUpdateRequest, user=Depends(require_user)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="자녀 이름을 입력해주세요.")

    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM children WHERE id = ? AND user_id = ?",
            (child_id, user["id"]),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="자녀 정보를 찾을 수 없습니다.")
        conn.execute(
            "UPDATE children SET name = ?, birth_date = ? WHERE id = ?",
            (name, payload.birthDate or None, child_id),
        )
        row = conn.execute("SELECT * FROM children WHERE id = ?", (child_id,)).fetchone()

    return _child_json(row)


# ---------------------------------------------------------------------------
# YOLO 분석
# ---------------------------------------------------------------------------
def _score_from_detections(cavity_count: int) -> int:
    # 충치 1건당 15점 감점, 0~100점 사이로 고정
    return max(0, 100 - cavity_count * 15)


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    child_id: int | None = Form(None),
    user=Depends(optional_user),
):
    if model is None:
        raise HTTPException(status_code=503, detail="모델이 아직 로드되지 않았습니다.")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다.")

    contents = await file.read()
    try:
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(contents))).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="이미지를 읽을 수 없습니다.")

    results = model.predict(image, conf=0.25, verbose=False)
    r = results[0]

    detections = []
    class_names = r.names  # {0: 'cavity', 1: 'normal'}

    for box in r.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
        detections.append({
            "class": class_names[cls_id],
            "confidence": round(conf, 4),
            "box": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
        })

    cavity_count = sum(1 for d in detections if d["class"] == "cavity")
    normal_count = sum(1 for d in detections if d["class"] == "normal")
    score = _score_from_detections(cavity_count)

    if user is not None:
        with get_conn() as conn:
            if child_id is not None:
                child = conn.execute(
                    "SELECT id FROM children WHERE id = ? AND user_id = ?",
                    (child_id, user["id"]),
                ).fetchone()
                if child is None:
                    raise HTTPException(status_code=400, detail="선택한 자녀 정보를 확인할 수 없습니다.")
            cursor = conn.execute(
                """
                INSERT INTO analysis_records
                    (user_id, child_id, created_at, cavity_count, normal_count, total_detections, score, detections_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user["id"], child_id, now_iso(), cavity_count, normal_count, len(detections), score, json.dumps(detections)),
            )
            CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
            image_name = f"{user['id']}_{cursor.lastrowid}.jpg"
            image_path = CAPTURE_DIR / image_name
            try:
                stored_image = image.copy()
                stored_image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                stored_image.save(image_path, format="JPEG", quality=88, optimize=True)
            except OSError as exc:
                raise HTTPException(status_code=500, detail="촬영 이미지를 저장하지 못했습니다.") from exc
            conn.execute(
                "UPDATE analysis_records SET image_path = ? WHERE id = ?",
                (image_name, cursor.lastrowid),
            )

    return {
        "image_size": {"width": image.width, "height": image.height},
        "detections": detections,
        "summary": {
            "cavity_count": cavity_count,
            "normal_count": normal_count,
            "total_detections": len(detections),
            "score": score,
        },
    }


# ---------------------------------------------------------------------------
# 이력 / 리포트
# ---------------------------------------------------------------------------
def _days_since(iso_str: str) -> int:
    korea_timezone = timezone(timedelta(hours=9))
    created_date = datetime.fromisoformat(iso_str).astimezone(korea_timezone).date()
    today = datetime.now(korea_timezone).date()
    return max(1, (today - created_date).days + 1)


def _daily_score_series(rows) -> list[dict]:
    daily_scores: dict = {}
    korea_timezone = timezone(timedelta(hours=9))

    for row in rows:
        created_at = datetime.fromisoformat(row["created_at"]).astimezone(korea_timezone)
        day = created_at.date()
        daily_scores.setdefault(day, []).append(row["score"])

    return [
        {
            "date": day,
            "label": f"{day.month}/{day.day}",
            "score": round(sum(scores) / len(scores)),
            "scan_count": len(scores),
        }
        for day, scores in sorted(daily_scores.items())
    ]


def _calc_streak(created_ats: list[str]) -> int:
    if not created_ats:
        return 0
    korea_timezone = timezone(timedelta(hours=9))
    unique_days = sorted(
        {datetime.fromisoformat(c).astimezone(korea_timezone).date() for c in created_ats},
        reverse=True,
    )
    today = datetime.now(korea_timezone).date()
    if unique_days[0] not in (today, today - timedelta(days=1)):
        return 0
    streak = 1
    for i in range(1, len(unique_days)):
        if unique_days[i - 1] - unique_days[i] == timedelta(days=1):
            streak += 1
        else:
            break
    return streak


@app.get("/api/history")
def history(child_id: int | None = Query(None), user=Depends(require_user)):
    with get_conn() as conn:
        if child_id is not None:
            rows = conn.execute(
                """
                SELECT id, child_id, created_at, cavity_count, normal_count, total_detections, score, image_path
                FROM analysis_records WHERE user_id = ? AND child_id = ? ORDER BY created_at DESC
                """,
                (user["id"], child_id),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, child_id, created_at, cavity_count, normal_count, total_detections, score, image_path
                FROM analysis_records WHERE user_id = ? ORDER BY created_at DESC
                """,
                (user["id"],),
            ).fetchall()
    records = []
    for row in rows:
        record = dict(row)
        record["has_image"] = bool(record.pop("image_path", None))
        records.append(record)
    return {"records": records}


@app.get("/api/history/{record_id}/image")
def history_image(record_id: int, user=Depends(require_user)):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT image_path FROM analysis_records WHERE id = ? AND user_id = ?",
            (record_id, user["id"]),
        ).fetchone()

    if row is None or not row["image_path"]:
        raise HTTPException(status_code=404, detail="저장된 촬영 이미지가 없습니다.")

    image_path = (CAPTURE_DIR / Path(row["image_path"]).name).resolve()
    if image_path.parent != CAPTURE_DIR.resolve() or not image_path.is_file():
        raise HTTPException(status_code=404, detail="촬영 이미지 파일을 찾을 수 없습니다.")
    return FileResponse(image_path, media_type="image/jpeg")


@app.get("/api/report/summary")
def report_summary(child_id: int | None = Query(None), user=Depends(require_user)):
    with get_conn() as conn:
        if child_id is None:
            rows = conn.execute(
                "SELECT created_at, score FROM analysis_records WHERE user_id = ? ORDER BY created_at ASC",
                (user["id"],),
            ).fetchall()
        else:
            child = conn.execute(
                "SELECT id FROM children WHERE id = ? AND user_id = ?",
                (child_id, user["id"]),
            ).fetchone()
            if child is None:
                raise HTTPException(status_code=404, detail="자녀 정보를 찾을 수 없습니다.")
            rows = conn.execute(
                """
                SELECT created_at, score FROM analysis_records
                WHERE user_id = ? AND child_id = ? ORDER BY created_at ASC
                """,
                (user["id"], child_id),
            ).fetchall()

    total_scans = len(rows)
    current_score = rows[-1]["score"] if rows else 100
    streak_days = _calc_streak([r["created_at"] for r in rows])
    member_since_days = _days_since(user["created_at"])
    daily_scores = _daily_score_series(rows)
    korea_today = datetime.now(timezone(timedelta(hours=9))).date()
    recent = [item for item in daily_scores if item["date"] >= korea_today - timedelta(days=6)]
    monthly = [item for item in daily_scores if item["date"] >= korea_today - timedelta(days=29)]
    current_month_average = round(sum(item["score"] for item in monthly) / len(monthly)) if monthly else None
    score_change = daily_scores[-1]["score"] - daily_scores[-2]["score"] if len(daily_scores) >= 2 else None
    notifications = []
    for previous, current in zip(daily_scores, daily_scores[1:]):
        daily_change = current["score"] - previous["score"]
        if current["date"] >= korea_today - timedelta(days=29) and daily_change <= -10:
            notifications.append({
                "id": f"{child_id or 'all'}:{current['date'].isoformat()}:{current['score']}:{daily_change}",
                "date": current["date"].isoformat(),
                "date_label": f"{current['date'].month}월 {current['date'].day}일",
                "title": "구강 건강 점수 하락 감지",
                "message": f"이전 기록일 평균보다 {abs(daily_change)}점 낮아졌어요. 같은 환경에서 다시 촬영해 주세요.",
                "score": current["score"],
                "score_change": daily_change,
            })
    notifications.reverse()

    return {
        "current_score": current_score,
        "total_scans": total_scans,
        "recorded_days": len(daily_scores),
        "streak_days": streak_days,
        "member_since_days": member_since_days,
        "weekly_trend": {
            "labels": [item["label"] for item in recent],
            "scores": [item["score"] for item in recent],
            "scan_counts": [item["scan_count"] for item in recent],
        },
        "monthly_trend": {
            "labels": [item["label"] for item in monthly],
            "scores": [item["score"] for item in monthly],
            "scan_counts": [item["scan_count"] for item in monthly],
        },
        "monthly_average": current_month_average,
        "score_change": score_change,
        "attention_required": score_change is not None and score_change <= -10,
        "notifications": notifications,
    }
