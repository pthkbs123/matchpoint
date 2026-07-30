"""
로컬 YOLOv8 추론 + 로그인/이력 백엔드 서버
사용법:
    1) 학습 완료 후 best.pt 를 backend/model/best.pt 위치에 복사
    2) uvicorn main:app --reload --port 8000   (이 파일이 있는 backend/ 폴더에서 실행)
    3) React 프론트(개발서버 localhost:3000)에서 http://localhost:8000 으로 요청
"""
import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel
from ultralytics import YOLO

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

MODEL_PATH = Path(__file__).parent / "model" / "best.pt"

app = FastAPI(title="MatchPoint API")

# React 개발 서버(localhost:3000)에서의 요청 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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


def _user_json(user_row) -> dict:
    return {
        "name": user_row["name"],
        "email": user_row["email"],
        "picture": user_row["picture"] or "/profile-avatar.svg",
        "memberSince": user_row["created_at"],
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
def auth_kakao():
    raise HTTPException(status_code=501, detail="카카오 로그인은 아직 준비 중이에요.")


@app.post("/api/auth/google")
def auth_google():
    raise HTTPException(status_code=501, detail="구글 로그인은 아직 준비 중이에요.")


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
# YOLO 분석
# ---------------------------------------------------------------------------
def _score_from_detections(cavity_count: int) -> int:
    # 충치 1건당 15점 감점, 0~100점 사이로 고정
    return max(0, 100 - cavity_count * 15)


@app.post("/analyze")
async def analyze(file: UploadFile = File(...), user=Depends(optional_user)):
    if model is None:
        raise HTTPException(status_code=503, detail="모델이 아직 로드되지 않았습니다.")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다.")

    contents = await file.read()
    try:
        image = Image.open(io.BytesIO(contents)).convert("RGB")
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
            conn.execute(
                """
                INSERT INTO analysis_records
                    (user_id, created_at, cavity_count, normal_count, total_detections, score, detections_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user["id"], now_iso(), cavity_count, normal_count, len(detections), score, json.dumps(detections)),
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
    created = datetime.fromisoformat(iso_str)
    delta = datetime.now(timezone.utc) - created
    return max(0, delta.days)


def _short_date(iso_str: str) -> str:
    dt = datetime.fromisoformat(iso_str)
    return f"{dt.month}/{dt.day}"


def _calc_streak(created_ats: list[str]) -> int:
    if not created_ats:
        return 0
    unique_days = sorted({datetime.fromisoformat(c).date() for c in created_ats}, reverse=True)
    today = datetime.now(timezone.utc).date()
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
def history(user=Depends(require_user)):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, cavity_count, normal_count, total_detections, score
            FROM analysis_records WHERE user_id = ? ORDER BY created_at DESC
            """,
            (user["id"],),
        ).fetchall()
    return {"records": [dict(row) for row in rows]}


@app.get("/api/report/summary")
def report_summary(user=Depends(require_user)):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT created_at, score FROM analysis_records WHERE user_id = ? ORDER BY created_at ASC",
            (user["id"],),
        ).fetchall()

    total_scans = len(rows)
    current_score = rows[-1]["score"] if rows else 100
    streak_days = _calc_streak([r["created_at"] for r in rows])
    member_since_days = _days_since(user["created_at"])
    recent = rows[-7:]

    return {
        "current_score": current_score,
        "total_scans": total_scans,
        "streak_days": streak_days,
        "member_since_days": member_since_days,
        "weekly_trend": {
            "labels": [_short_date(r["created_at"]) for r in recent],
            "scores": [r["score"] for r in recent],
        },
    }
