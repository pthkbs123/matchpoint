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
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import cv2
import httpx
import numpy as np
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

from color_baseline import REQUIRED_SAMPLES as COLOR_BASELINE_REQUIRED_SAMPLES
from color_baseline import advance_running_baseline
from color_analysis import (
    BASELINE_A,
    BASELINE_B,
    MAX_A,
    MAX_B,
    PREPROCESS_MODES,
    PREPROCESS_WB_CLAHE,
    compute_gum_inflammation_details,
    compute_yellowing_details,
    health_index_from_baseline,
    measure_gum_lab_a,
    measure_yellowing_lab_b,
    preprocess_bgr,
)

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
from monthly_report import build_monthly_report_notification

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
    yellowing_count = row["yellowing_baseline_count"] or 0
    gum_count = row["gum_baseline_count"] or 0
    return {
        "id": row["id"],
        "name": row["name"],
        "birthDate": row["birth_date"],
        "reminderWeekday": row["reminder_weekday"],
        "colorBaseline": {
            "requiredSamples": COLOR_BASELINE_REQUIRED_SAMPLES,
            "yellowingSampleCount": yellowing_count,
            "yellowingReady": yellowing_count >= COLOR_BASELINE_REQUIRED_SAMPLES,
            "gumSampleCount": gum_count,
            "gumReady": gum_count >= COLOR_BASELINE_REQUIRED_SAMPLES,
        },
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


class ChildScheduleRequest(BaseModel):
    weekday: int


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


@app.put("/api/children/{child_id}/schedule")
def update_child_schedule(child_id: int, payload: ChildScheduleRequest, user=Depends(require_user)):
    if payload.weekday < 0 or payload.weekday > 6:
        raise HTTPException(status_code=400, detail="요일 설정이 올바르지 않습니다.")

    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM children WHERE id = ? AND user_id = ?",
            (child_id, user["id"]),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="자녀 정보를 찾을 수 없습니다.")
        conn.execute(
            "UPDATE children SET reminder_weekday = ? WHERE id = ?",
            (payload.weekday, child_id),
        )
        row = conn.execute("SELECT * FROM children WHERE id = ?", (child_id,)).fetchone()

    return _child_json(row)


# ---------------------------------------------------------------------------
# YOLO 분석
# ---------------------------------------------------------------------------
def _score_from_detections(cavity_count: int) -> int:
    # 충치 1건당 15점 감점, 0~100점 사이로 고정
    return max(0, 100 - cavity_count * 15)


def _detections_from_result(result) -> list[dict]:
    detections = []
    class_names = result.names
    for box in result.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        x1, y1, x2, y2 = [float(value) for value in box.xyxy[0]]
        detections.append({
            "class": class_names[cls_id],
            "confidence": round(conf, 4),
            "box": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
        })
    return detections


def _predict_detections(image: Image.Image) -> list[dict]:
    return _detections_from_result(model.predict(image, conf=0.25, verbose=False)[0])


def _color_comparison_metrics(image_bgr: np.ndarray, detections: list, mode: str) -> dict:
    preprocessed = preprocess_bgr(image_bgr, mode=mode)
    yellowing = compute_yellowing_details(preprocessed, detections)
    gum = compute_gum_inflammation_details(preprocessed, detections)
    return {
        "mode": mode,
        "yellowing_index": yellowing["score"],
        "gum_inflammation_index": gum["score"],
        "raw": {"yellowing": yellowing, "gum_inflammation": gum},
    }


def _child_baseline_payload(child_row) -> dict:
    if child_row is None:
        return {
            "available": False,
            "required_samples": COLOR_BASELINE_REQUIRED_SAMPLES,
            "ready": False,
            "generation": 0,
            "reset_at": None,
            "yellowing": {"sample_count": 0, "ready": False},
            "gum_inflammation": {"sample_count": 0, "ready": False},
        }
    yellowing_count = int(child_row["yellowing_baseline_count"] or 0)
    gum_count = int(child_row["gum_baseline_count"] or 0)
    return {
        "available": True,
        "required_samples": COLOR_BASELINE_REQUIRED_SAMPLES,
        "ready": (
            yellowing_count >= COLOR_BASELINE_REQUIRED_SAMPLES
            and gum_count >= COLOR_BASELINE_REQUIRED_SAMPLES
        ),
        "generation": int(child_row["color_baseline_generation"] or 1),
        "reset_at": child_row["color_baseline_reset_at"],
        "yellowing": {
            "sample_count": yellowing_count,
            "ready": yellowing_count >= COLOR_BASELINE_REQUIRED_SAMPLES,
            "value": child_row["yellowing_baseline_b"],
        },
        "gum_inflammation": {
            "sample_count": gum_count,
            "ready": gum_count >= COLOR_BASELINE_REQUIRED_SAMPLES,
            "value": child_row["gum_baseline_a"],
        },
    }


class BaselineResetRequest(BaseModel):
    child_id: int | None = None


@app.get("/api/color-baseline/status")
def color_baseline_status(
    child_id: int | None = Query(None),
    user=Depends(require_user),
):
    if child_id is None:
        return {"baseline": _child_baseline_payload(None)}
    with get_conn() as conn:
        child = conn.execute(
            "SELECT * FROM children WHERE id = ? AND user_id = ?",
            (child_id, user["id"]),
        ).fetchone()
        if child is None:
            raise HTTPException(status_code=404, detail="자녀 정보를 찾을 수 없습니다.")
        return {"baseline": _child_baseline_payload(child)}


@app.post("/api/color-baseline/reset")
def reset_color_baseline(payload: BaselineResetRequest, user=Depends(require_user)):
    """기존 촬영 이력은 유지하고 선택한 자녀의 색상 기준만 새로 수집한다."""
    if payload.child_id is None:
        raise HTTPException(status_code=400, detail="기준을 재설정할 자녀를 먼저 선택해주세요.")
    reset_at = now_iso()
    with get_conn() as conn:
        child = conn.execute(
            "SELECT * FROM children WHERE id = ? AND user_id = ?",
            (payload.child_id, user["id"]),
        ).fetchone()
        if child is None:
            raise HTTPException(status_code=404, detail="자녀 정보를 찾을 수 없습니다.")
        conn.execute(
            """
            UPDATE children
            SET yellowing_baseline_b = NULL, yellowing_baseline_count = 0,
                gum_baseline_a = NULL, gum_baseline_count = 0,
                color_baseline_generation = color_baseline_generation + 1,
                color_baseline_reset_at = ?
            WHERE id = ?
            """,
            (reset_at, payload.child_id),
        )
        child = conn.execute("SELECT * FROM children WHERE id = ?", (payload.child_id,)).fetchone()
    return {
        "baseline": _child_baseline_payload(child),
        "message": "기존 촬영 기록은 유지하고 개인 기준 수집을 새로 시작합니다.",
    }


@app.post("/api/color-analysis/compare")
async def compare_color_preprocessing(
    file: UploadFile = File(...),
    _user=Depends(require_user),
):
    """저장 없이 동일 이미지의 세 전처리 조건을 비교하는 개발/보정용 API."""
    if model is None:
        raise HTTPException(status_code=503, detail="모델이 아직 로드되지 않았습니다.")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다.")
    contents = await file.read()
    try:
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(contents))).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="이미지를 읽을 수 없습니다.") from exc

    original_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    comparisons = []
    for mode in PREPROCESS_MODES:
        processed_bgr = preprocess_bgr(original_bgr, mode=mode)
        processed_image = Image.fromarray(cv2.cvtColor(processed_bgr, cv2.COLOR_BGR2RGB))
        detections = _predict_detections(processed_image)
        metrics = _color_comparison_metrics(original_bgr, detections, mode)
        cavity = [item for item in detections if item["class"] == "cavity"]
        normal = [item for item in detections if item["class"] == "normal"]
        comparisons.append({
            **metrics,
            "cavity_count": len(cavity),
            "normal_count": len(normal),
            "cavity_confidences": [item["confidence"] for item in cavity],
            "normal_confidences": [item["confidence"] for item in normal],
        })
    return {
        "image_size": {"width": image.width, "height": image.height},
        "comparisons": comparisons,
        "notice": "개발 보정용 비교 결과이며 의료 진단값이 아닙니다.",
    }


def _update_child_color_baseline(conn, child_row, lab_b_mean, lab_a_mean) -> dict:
    yellowing_was_ready = (child_row["yellowing_baseline_count"] or 0) >= COLOR_BASELINE_REQUIRED_SAMPLES
    gum_was_ready = (child_row["gum_baseline_count"] or 0) >= COLOR_BASELINE_REQUIRED_SAMPLES
    yellowing_baseline, yellowing_count = advance_running_baseline(
        child_row["yellowing_baseline_b"],
        child_row["yellowing_baseline_count"],
        lab_b_mean,
    )
    gum_baseline, gum_count = advance_running_baseline(
        child_row["gum_baseline_a"],
        child_row["gum_baseline_count"],
        lab_a_mean,
    )
    conn.execute(
        """
        UPDATE children
        SET yellowing_baseline_b = ?, yellowing_baseline_count = ?,
            gum_baseline_a = ?, gum_baseline_count = ?
        WHERE id = ?
        """,
        (yellowing_baseline, yellowing_count, gum_baseline, gum_count, child_row["id"]),
    )
    return {
        "yellowing_baseline": yellowing_baseline,
        "yellowing_count": yellowing_count,
        "yellowing_was_ready": yellowing_was_ready,
        "gum_baseline": gum_baseline,
        "gum_count": gum_count,
        "gum_was_ready": gum_was_ready,
    }


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

    lab_b_mean = None
    lab_a_mean = None
    try:
        image_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        preprocessed = preprocess_bgr(image_bgr)
        lab_b_mean = measure_yellowing_lab_b(preprocessed, detections)
        lab_a_mean = measure_gum_lab_a(preprocessed, detections)
    except Exception as exc:
        print(f"색상 분석 실패(무시하고 진행): {exc}")

    baseline_source = "default"
    yellowing_baseline = BASELINE_B
    gum_baseline = BASELINE_A
    yellowing_sample_count = 0
    gum_sample_count = 0
    yellowing_ready = True
    gum_ready = True
    yellowing_comparison_available = True
    gum_comparison_available = True
    yellowing_index = health_index_from_baseline(lab_b_mean, yellowing_baseline, MAX_B)
    gum_inflammation_index = health_index_from_baseline(lab_a_mean, gum_baseline, MAX_A)
    yellowing_delta = round(lab_b_mean - yellowing_baseline, 3) if lab_b_mean is not None else None
    gum_inflammation_delta = round(lab_a_mean - gum_baseline, 3) if lab_a_mean is not None else None

    if user is not None:
        with get_conn() as conn:
            if child_id is not None:
                child = conn.execute(
                    "SELECT * FROM children WHERE id = ? AND user_id = ?",
                    (child_id, user["id"]),
                ).fetchone()
                if child is None:
                    raise HTTPException(status_code=400, detail="선택한 자녀 정보를 확인할 수 없습니다.")
                baseline_state = _update_child_color_baseline(conn, child, lab_b_mean, lab_a_mean)
                baseline_source = "personal"
                yellowing_baseline = baseline_state["yellowing_baseline"]
                gum_baseline = baseline_state["gum_baseline"]
                yellowing_sample_count = baseline_state["yellowing_count"]
                gum_sample_count = baseline_state["gum_count"]
                yellowing_ready = yellowing_sample_count >= COLOR_BASELINE_REQUIRED_SAMPLES
                gum_ready = gum_sample_count >= COLOR_BASELINE_REQUIRED_SAMPLES
                yellowing_comparison_available = baseline_state["yellowing_was_ready"]
                gum_comparison_available = baseline_state["gum_was_ready"]
                yellowing_index = health_index_from_baseline(
                    lab_b_mean,
                    yellowing_baseline if yellowing_comparison_available else None,
                    MAX_B,
                )
                gum_inflammation_index = health_index_from_baseline(
                    lab_a_mean,
                    gum_baseline if gum_comparison_available else None,
                    MAX_A,
                )
                yellowing_delta = (
                    round(lab_b_mean - yellowing_baseline, 3)
                    if lab_b_mean is not None and yellowing_comparison_available
                    else None
                )
                gum_inflammation_delta = (
                    round(lab_a_mean - gum_baseline, 3)
                    if lab_a_mean is not None and gum_comparison_available
                    else None
                )
            cursor = conn.execute(
                """
                INSERT INTO analysis_records
                    (user_id, child_id, created_at, cavity_count, normal_count, total_detections, score,
                     yellowing_index, gum_inflammation_index, lab_b_mean, lab_a_mean,
                     yellowing_baseline_b, gum_baseline_a, yellowing_delta, gum_inflammation_delta,
                     color_baseline_source, detections_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"], child_id, now_iso(), cavity_count, normal_count, len(detections), score,
                    yellowing_index, gum_inflammation_index, lab_b_mean, lab_a_mean,
                    yellowing_baseline if yellowing_ready else None,
                    gum_baseline if gum_ready else None,
                    yellowing_delta, gum_inflammation_delta, baseline_source, json.dumps(detections),
                ),
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
            "overall_score": score,
            "yellowing_index": yellowing_index,
            "gum_inflammation_index": gum_inflammation_index,
            "yellowing_delta": yellowing_delta,
            "gum_inflammation_delta": gum_inflammation_delta,
        },
        "color_baseline": {
            "source": baseline_source,
            "required_samples": COLOR_BASELINE_REQUIRED_SAMPLES,
            "yellowing": {
                "sample_count": yellowing_sample_count,
                "ready": yellowing_ready,
                "comparison_available": yellowing_comparison_available,
                "current_mean": lab_b_mean,
                "baseline": yellowing_baseline if yellowing_ready else None,
                "delta": yellowing_delta,
            },
            "gum": {
                "sample_count": gum_sample_count,
                "ready": gum_ready,
                "comparison_available": gum_comparison_available,
                "current_mean": lab_a_mean,
                "baseline": gum_baseline if gum_ready else None,
                "delta": gum_inflammation_delta,
            },
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


def _daily_metric_series(rows, column: str) -> list[dict]:
    daily_values: dict = {}
    korea_timezone = timezone(timedelta(hours=9))

    for row in rows:
        value = row[column]
        if value is None:
            continue
        created_at = datetime.fromisoformat(row["created_at"]).astimezone(korea_timezone)
        day = created_at.date()
        daily_values.setdefault(day, []).append(float(value))

    return [
        {
            "date": day,
            "label": f"{day.month}/{day.day}",
            "score": round(sum(values) / len(values)),
            "scan_count": len(values),
        }
        for day, values in sorted(daily_values.items())
    ]


def _daily_score_series(rows) -> list[dict]:
    return _daily_metric_series(rows, "score")


def _month_start_with_offset(day: date, month_offset: int) -> date:
    month_index = day.year * 12 + day.month - 1 + month_offset
    return date(month_index // 12, month_index % 12 + 1, 1)


def _monthly_score_series(
    daily_scores: list[dict],
    start_date: date,
    include_year: bool = True,
) -> list[dict]:
    monthly_scores: dict = {}
    for item in daily_scores:
        if item["date"] < start_date:
            continue
        month_key = (item["date"].year, item["date"].month)
        month = monthly_scores.setdefault(month_key, {"scores": [], "scan_count": 0})
        month["scores"].append(item["score"])
        month["scan_count"] += item["scan_count"]

    return [
        {
            "label": f"{str(year)[2:]}.{month}" if include_year else f"{month}월",
            "score": round(sum(values["scores"]) / len(values["scores"])),
            "scan_count": values["scan_count"],
        }
        for (year, month), values in sorted(monthly_scores.items())
    ]


def _trend_payload(series: list[dict]) -> dict:
    return {
        "labels": [item["label"] for item in series],
        "scores": [item["score"] for item in series],
        "scan_counts": [item["scan_count"] for item in series],
    }


def _average_for_period(series: list[dict], start_date: date, end_date: date) -> int | None:
    values = [item["score"] for item in series if start_date <= item["date"] <= end_date]
    return round(sum(values) / len(values)) if values else None


def _latest_metric_value(rows, column: str) -> int | float | None:
    for row in reversed(rows):
        value = row[column]
        if value is not None:
            return round(float(value), 1) if column != "score" else int(value)
    return None


def _build_metric_summary(
    rows,
    key: str,
    column: str,
    label: str,
    unit: str,
    korea_today: date,
) -> dict:
    daily = _daily_metric_series(rows, column)
    current_month_start = _month_start_with_offset(korea_today, 0)
    previous_month_start = _month_start_with_offset(korea_today, -1)
    previous_month_end = current_month_start - timedelta(days=1)
    current_month_average = _average_for_period(daily, current_month_start, korea_today)
    previous_month_average = _average_for_period(daily, previous_month_start, previous_month_end)
    month_change = (
        current_month_average - previous_month_average
        if current_month_average is not None and previous_month_average is not None
        else None
    )
    recent_daily = [item for item in daily if item["date"] >= korea_today - timedelta(days=55)]
    six_monthly = _monthly_score_series(
        daily,
        _month_start_with_offset(korea_today, -5),
        include_year=False,
    )
    yearly = _monthly_score_series(daily, _month_start_with_offset(korea_today, -11))
    latest_change = daily[-1]["score"] - daily[-2]["score"] if len(daily) >= 2 else None

    return {
        "key": key,
        "label": label,
        "unit": unit,
        "available": bool(daily),
        "latest": _latest_metric_value(rows, column),
        "current_month_average": current_month_average,
        "previous_month_average": previous_month_average,
        "month_change": month_change,
        "latest_change": latest_change,
        "current_month_scan_count": sum(
            item["scan_count"] for item in daily if current_month_start <= item["date"] <= korea_today
        ),
        "previous_month_scan_count": sum(
            item["scan_count"] for item in daily if previous_month_start <= item["date"] <= previous_month_end
        ),
        "recorded_days": len(daily),
        "weekly_trend": _trend_payload(recent_daily),
        "monthly_trend": _trend_payload(six_monthly),
        "yearly_trend": _trend_payload(yearly),
    }


def _shift_year(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year + years)
    except ValueError:
        return day.replace(year=day.year + years, day=28)


def _age_years(birth_date: str | None, today: date) -> int | None:
    if not birth_date:
        return None
    try:
        born = date.fromisoformat(birth_date)
    except ValueError:
        return None
    return max(0, today.year - born.year - ((today.month, today.day) < (born.month, born.day)))


def _recommended_capture_schedule(
    birth_date: str | None,
    today: date,
    reminder_weekday: int | None = None,
) -> tuple[int, str, str, str]:
    age = _age_years(birth_date, today)
    if age is None or age <= 6:
        weekday = reminder_weekday if reminder_weekday is not None and 0 <= reminder_weekday <= 6 else 6
        weekday_labels = ("월", "화", "수", "목", "금", "토", "일")
        return 7, "주 1회", f"매주 {weekday_labels[weekday]}요일", f"weekly_{weekday}"
    if age <= 12:
        return 14, "월 2회", "매월 1일·15일", "twice_monthly"
    return 30, "월 1회", "매월 1일", "monthly_first"


def _scheduled_dates_near(today: date, schedule_type: str) -> list[date]:
    if schedule_type.startswith("weekly_"):
        weekday = int(schedule_type.split("_", 1)[1])
        days_until_weekday = (weekday - today.weekday()) % 7
        nearest_weekday = today + timedelta(days=days_until_weekday)
        return [nearest_weekday + timedelta(days=7 * offset) for offset in range(-2, 3)]

    scheduled_days = (1, 15) if schedule_type == "twice_monthly" else (1,)
    dates = []
    for month_offset in range(-2, 3):
        month_start = _month_start_with_offset(today, month_offset)
        dates.extend(date(month_start.year, month_start.month, day) for day in scheduled_days)
    return sorted(dates)


def _capture_due_status(
    today: date,
    latest_scan_date: date | None,
    schedule_type: str,
) -> tuple[date, bool, bool]:
    if latest_scan_date is None:
        return today, True, False

    tolerance = timedelta(days=2)
    scheduled_dates = _scheduled_dates_near(today, schedule_type)
    current_schedule = max(day for day in scheduled_dates if day <= today + tolerance)
    current_schedule_completed = latest_scan_date >= current_schedule - tolerance

    if current_schedule_completed:
        target_date = min(day for day in scheduled_dates if day > current_schedule)
    else:
        target_date = current_schedule

    scan_due = today >= target_date - tolerance
    overdue = scan_due and today > target_date + tolerance and not current_schedule_completed
    return target_date, scan_due, overdue


def _calc_period_streak(created_ats: list[str], interval_days: int) -> int:
    if not created_ats:
        return 0
    korea_timezone = timezone(timedelta(hours=9))
    unique_days = sorted(
        {datetime.fromisoformat(c).astimezone(korea_timezone).date() for c in created_ats},
        reverse=True,
    )
    today = datetime.now(korea_timezone).date()
    tolerance_days = 3
    if (today - unique_days[0]).days > interval_days + tolerance_days:
        return 0

    streak = 1
    latest_counted_day = unique_days[0]
    minimum_gap = max(1, interval_days - tolerance_days)
    maximum_gap = interval_days + tolerance_days
    for previous_day in unique_days[1:]:
        gap = (latest_counted_day - previous_day).days
        if gap < minimum_gap:
            continue
        if gap <= maximum_gap:
            streak += 1
            latest_counted_day = previous_day
        else:
            break
    return streak


@app.get("/api/history")
def history(child_id: int | None = Query(None), user=Depends(require_user)):
    with get_conn() as conn:
        if child_id is not None:
            rows = conn.execute(
                """
                SELECT id, child_id, created_at, cavity_count, normal_count, total_detections,
                       score, yellowing_index, gum_inflammation_index,
                       yellowing_delta, gum_inflammation_delta, color_baseline_source, image_path
                FROM analysis_records WHERE user_id = ? AND child_id = ? ORDER BY created_at DESC
                """,
                (user["id"], child_id),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, child_id, created_at, cavity_count, normal_count, total_detections,
                       score, yellowing_index, gum_inflammation_index,
                       yellowing_delta, gum_inflammation_delta, color_baseline_source, image_path
                FROM analysis_records WHERE user_id = ? ORDER BY created_at DESC
                """,
                (user["id"],),
            ).fetchall()
    records = []
    for row in rows:
        record = dict(row)
        record["overall_score"] = record["score"]
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
    selected_child = None
    with get_conn() as conn:
        if child_id is None:
            rows = conn.execute(
                """
                SELECT created_at, score, yellowing_index, gum_inflammation_index, color_baseline_source
                FROM analysis_records WHERE user_id = ? ORDER BY created_at ASC
                """,
                (user["id"],),
            ).fetchall()
        else:
            child = conn.execute(
                "SELECT id, birth_date, reminder_weekday FROM children WHERE id = ? AND user_id = ?",
                (child_id, user["id"]),
            ).fetchone()
            if child is None:
                raise HTTPException(status_code=404, detail="자녀 정보를 찾을 수 없습니다.")
            rows = conn.execute(
                """
                SELECT created_at, score, yellowing_index, gum_inflammation_index, color_baseline_source
                FROM analysis_records
                WHERE user_id = ? AND child_id = ? ORDER BY created_at ASC
                """,
                (user["id"], child_id),
            ).fetchall()
            selected_child = child

    korea_today = datetime.now(timezone(timedelta(hours=9))).date()
    personal_color_rows = [row for row in rows if row["color_baseline_source"] == "personal"]
    metrics = {
        "overall": _build_metric_summary(rows, "overall", "score", "종합 점수", "점", korea_today),
        "yellowing": _build_metric_summary(
            personal_color_rows, "yellowing", "yellowing_index", "황변 변화", "점", korea_today
        ),
        "gum": _build_metric_summary(
            personal_color_rows, "gum", "gum_inflammation_index", "잇몸 변화", "점", korea_today
        ),
    }
    overall_metric = metrics["overall"]
    total_scans = len(rows)
    current_score = overall_metric["latest"]
    member_since_days = _days_since(user["created_at"])
    daily_scores = _daily_score_series(rows)
    interval_days, interval_label, schedule_label, schedule_type = _recommended_capture_schedule(
        selected_child["birth_date"] if selected_child else None,
        korea_today,
        selected_child["reminder_weekday"] if selected_child else None,
    )
    streak_periods = _calc_period_streak([r["created_at"] for r in rows], interval_days)
    current_month_average = overall_metric["current_month_average"]
    previous_month_average = overall_metric["previous_month_average"]
    month_change = overall_metric["month_change"]
    score_change = overall_metric["latest_change"]
    latest_scan_date = daily_scores[-1]["date"] if daily_scores else None
    next_scan_date, scan_due, scan_overdue = _capture_due_status(
        korea_today,
        latest_scan_date,
        schedule_type,
    )

    current_period_start = korea_today - timedelta(days=29)
    previous_period_end = _shift_year(korea_today, -1)
    previous_period_start = previous_period_end - timedelta(days=29)
    current_period_scores = [
        item["score"] for item in daily_scores
        if current_period_start <= item["date"] <= korea_today
    ]
    previous_period_scores = [
        item["score"] for item in daily_scores
        if previous_period_start <= item["date"] <= previous_period_end
    ]
    current_period_average = round(sum(current_period_scores) / len(current_period_scores)) if current_period_scores else None
    previous_period_average = round(sum(previous_period_scores) / len(previous_period_scores)) if previous_period_scores else None
    year_comparison_available = current_period_average is not None and previous_period_average is not None
    first_anniversary = _shift_year(daily_scores[0]["date"], 1) if daily_scores else None
    comparison_days_remaining = max(0, (first_anniversary - korea_today).days) if first_anniversary else 365
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
    if scan_due:
        notifications.insert(0, {
            "id": f"capture-due:{child_id or 'all'}:{next_scan_date.isoformat()}",
            "date": korea_today.isoformat(),
            "date_label": f"{korea_today.month}월 {korea_today.day}일",
            "title": "권장 촬영 시기예요",
            "message": f"{schedule_label} 맞춤 일정에 따라 같은 시간과 환경에서 구강 상태를 기록해 주세요.",
            "type": "capture_due",
            "score_change": None,
        })

    korea_timezone = timezone(timedelta(hours=9))
    monthly_measurements = [
        {
            "date": datetime.fromisoformat(row["created_at"]).astimezone(korea_timezone).date(),
            "score": row["score"],
        }
        for row in rows
    ]
    monthly_report_notification = build_monthly_report_notification(
        monthly_measurements,
        korea_today,
        f"child-{child_id}" if child_id is not None else "all",
    )
    if monthly_report_notification is not None:
        notifications.insert(0, monthly_report_notification)

    return {
        "current_score": current_score,
        "total_scans": total_scans,
        "recorded_days": len(daily_scores),
        "streak_periods": streak_periods,
        "streak_days": streak_periods,
        "member_since_days": member_since_days,
        "recommended_interval_days": interval_days,
        "recommended_interval_label": interval_label,
        "notification_schedule_label": schedule_label,
        "notification_schedule_type": schedule_type,
        "latest_scan_date": latest_scan_date.isoformat() if latest_scan_date else None,
        "next_scan_date": next_scan_date.isoformat(),
        "scan_due": scan_due,
        "scan_overdue": scan_overdue,
        "weekly_trend": overall_metric["weekly_trend"],
        "monthly_trend": overall_metric["monthly_trend"],
        "yearly_trend": overall_metric["yearly_trend"],
        "metrics": metrics,
        "year_comparison": {
            "available": year_comparison_available,
            "current_average": current_period_average,
            "previous_average": previous_period_average,
            "change": current_period_average - previous_period_average if year_comparison_available else None,
            "current_count": len(current_period_scores),
            "previous_count": len(previous_period_scores),
            "previous_period_label": f"{previous_period_start.year}.{previous_period_start.month}.{previous_period_start.day} ~ {previous_period_end.month}.{previous_period_end.day}",
            "days_remaining": comparison_days_remaining,
        },
        "monthly_average": current_month_average,
        "current_month_average": current_month_average,
        "previous_month_average": previous_month_average,
        "month_change": month_change,
        "current_month_scan_count": overall_metric["current_month_scan_count"],
        "previous_month_scan_count": overall_metric["previous_month_scan_count"],
        "score_change": score_change,
        "attention_required": score_change is not None and score_change <= -10,
        "notifications": notifications,
    }
