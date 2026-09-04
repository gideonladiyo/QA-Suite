import asyncio
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field, SecretStr, field_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.core.models import LocalAccount, LocalSession
from app.core.security import (
    COOKIE_NAME,
    SESSION_SECONDS,
    password_hash,
    read_cookie,
    signer,
    token_digest,
    verify_password,
)

Db = Annotated[AsyncSession, Depends(get_db)]
router = APIRouter(prefix="/api/auth", tags=["auth"])


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: SecretStr

    @field_validator("password")
    @classmethod
    def valid_password(cls, value: SecretStr) -> SecretStr:
        if not 12 <= len(value.get_secret_value()) <= 128:
            raise ValueError("Password must contain 12-128 characters")
        return value


class AuthState(BaseModel):
    setup_required: bool = False
    authenticated: bool = False
    username: str | None = None


async def session_account(request: Request, db: AsyncSession) -> LocalAccount | None:
    digest = read_cookie(request.cookies.get(COOKIE_NAME))
    if digest is None:
        return None
    accounts = await db.scalars(
        select(LocalAccount)
        .join(LocalSession)
        .where(
            LocalSession.token_hash == digest,
            LocalSession.expires_at > datetime.now(UTC),
        )
    )
    return accounts.first()


async def require_user(request: Request, db: Db) -> LocalAccount:
    account = await session_account(request, db)
    if account is None:
        raise AppError(401, "Sesi berakhir. Masuk kembali untuk melanjutkan.")
    return account


User = Annotated[LocalAccount, Depends(require_user)]


async def issue_session(db: AsyncSession, response: Response, request: Request) -> None:
    now = datetime.now(UTC)
    # Revoke the previous cookie as well as expired sessions; never reuse a session id.
    previous = read_cookie(request.cookies.get(COOKIE_NAME))
    await db.execute(
        delete(LocalSession).where(
            (LocalSession.expires_at <= now) | (LocalSession.token_hash == previous)
        )
    )
    token = secrets.token_urlsafe(32)
    db.add(
        LocalSession(
            token_hash=token_digest(token),
            account_id=1,
            expires_at=now + timedelta(seconds=SESSION_SECONDS),
        )
    )
    await db.commit()
    response.set_cookie(
        COOKIE_NAME,
        signer().dumps(token),
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="strict",
        path="/api",
    )


@router.get("/status")
async def status(request: Request, db: Db) -> AuthState:
    account = await session_account(request, db)
    exists = await db.get(LocalAccount, 1)
    return AuthState(
        setup_required=exists is None,
        authenticated=account is not None,
        username=account.username if account else None,
    )


@router.post("/setup", status_code=201)
async def setup(body: Credentials, request: Request, response: Response, db: Db) -> AuthState:
    if await db.get(LocalAccount, 1):
        raise AppError(409, "Akun lokal sudah disiapkan. Silakan masuk.")
    hashed = await asyncio.to_thread(password_hash, body.password.get_secret_value())
    db.add(LocalAccount(id=1, username=body.username, password_hash=hashed))
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "Akun lokal sudah disiapkan. Silakan masuk.") from None
    await issue_session(db, response, request)
    return AuthState(authenticated=True, username=body.username)


@router.post("/login")
async def login(body: Credentials, request: Request, response: Response, db: Db) -> AuthState:
    account = await db.scalar(select(LocalAccount).where(LocalAccount.id == 1).with_for_update())
    if account is None:
        raise AppError(409, "Buat akun lokal terlebih dahulu.")
    now = datetime.now(UTC)
    if account.locked_until and account.locked_until > now:
        raise AppError(429, "Terlalu banyak percobaan. Coba lagi setelah 1 menit.")
    valid = await asyncio.to_thread(
        verify_password, body.password.get_secret_value(), account.password_hash
    )
    if not valid or not secrets.compare_digest(body.username, account.username):
        account.failed_attempts += 1
        if account.failed_attempts >= 5:
            account.locked_until = now + timedelta(minutes=1)
            account.failed_attempts = 0
        await db.commit()
        raise AppError(401, "Username atau password tidak cocok.")
    account.failed_attempts = 0
    account.locked_until = None
    await issue_session(db, response, request)
    return AuthState(authenticated=True, username=account.username)


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, db: Db) -> None:
    digest = read_cookie(request.cookies.get(COOKIE_NAME))
    if digest:
        await db.execute(delete(LocalSession).where(LocalSession.token_hash == digest))
        await db.commit()
    response.delete_cookie(
        COOKIE_NAME,
        path="/api",
        httponly=True,
        samesite="strict",
        secure=get_settings().cookie_secure,
    )
