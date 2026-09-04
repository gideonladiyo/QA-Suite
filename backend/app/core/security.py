import hashlib
import hmac
import secrets

from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.core.config import get_settings

SESSION_SECONDS = 12 * 60 * 60
COOKIE_NAME = "qa_portal_session"


def password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000).hex()
    return f"pbkdf2_sha256$600000${salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    _, rounds, salt, expected = encoded.split("$")
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds)).hex()
    return hmac.compare_digest(actual, expected)


def signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        get_settings().app_secret_key.get_secret_value(), salt="qa-local-session-v1"
    )


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def read_cookie(cookie: str | None) -> str | None:
    if not cookie:
        return None
    try:
        token = signer().loads(cookie, max_age=SESSION_SECONDS)
        return token_digest(token) if isinstance(token, str) else None
    except BadSignature:
        return None
