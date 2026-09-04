"""Generate local deployment secrets once. Never overwrite an existing environment file."""
import secrets
from pathlib import Path


def main() -> None:
    target = Path(__file__).resolve().parents[2] / ".env"
    try:
        with target.open("x", encoding="utf-8") as file:
            file.write(
                "APP_ENV=local\n"
                f"APP_SECRET_KEY={secrets.token_urlsafe(48)}\n"
                "POSTGRES_USER=qa_portal\nPOSTGRES_DB=qa_portal\nPOSTGRES_HOST=db\n"
                f"POSTGRES_PASSWORD={secrets.token_urlsafe(32)}\n"
                "ALLOWED_ORIGINS=http://localhost:8080,http://127.0.0.1:8080,"
                "http://localhost:5173,http://127.0.0.1:5173\n"
                "COOKIE_SECURE=false\nSLACK_WEBHOOK_URL=\nSMTP_HOST=\nSMTP_PORT=587\n"
                "SMTP_USER=\nSMTP_PASSWORD=\nSMTP_FROM=\n"
            )
    except FileExistsError:
        print("Existing .env preserved; no values were read or printed.")
    else:
        print("Local .env created. Secrets are not displayed. Do not commit this file.")


if __name__ == "__main__":
    main()
