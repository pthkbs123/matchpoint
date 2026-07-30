"""SMTP로 실제 이메일을 보내는 모듈 (비밀번호 재설정 링크 발송용)."""
import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
MAIL_FROM = os.environ.get("MAIL_FROM") or SMTP_USER or "no-reply@smileguard.app"
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def send_reset_password_email(to_email: str, token: str) -> None:
    reset_link = f"{FRONTEND_URL}/?resetToken={token}"

    message = EmailMessage()
    message["Subject"] = "[SmileGuard] 비밀번호 재설정 안내"
    message["From"] = MAIL_FROM
    message["To"] = to_email
    message.set_content(
        "SmileGuard 비밀번호 재설정을 요청하셨습니다.\n\n"
        f"아래 링크를 눌러 새 비밀번호를 설정해 주세요 (30분간 유효):\n{reset_link}\n\n"
        "본인이 요청하지 않았다면 이 메일은 무시하셔도 됩니다."
    )

    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        # SMTP 환경변수가 설정되지 않은 개발 환경에서는 메일 대신 콘솔에 링크를 출력해서
        # 화면 흐름을 테스트할 수 있게 한다. 실제 메일을 보내려면 backend/.env에
        # SMTP_HOST/SMTP_USER/SMTP_PASSWORD를 채워야 한다.
        print(f"[DEV] SMTP 설정이 없어 메일 대신 콘솔에 출력합니다 -> {to_email}\n{reset_link}")
        return

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(message)
