import os
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.micro_utilities.models import HttpHistory
from app.modules.micro_utilities.schemas import HistorySummary, HttpRequest, HttpResult


def cipher() -> AESGCM:
    key = HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None, info=b"qa-portal/http-history/v1"
    ).derive(get_settings().app_secret_key.get_secret_value().encode())
    return AESGCM(key)


async def save_history(db: AsyncSession, request: HttpRequest, result: HttpResult) -> None:
    # Serialize the bounded-history trim across concurrent requests in this single-user app.
    await db.execute(select(func.pg_advisory_xact_lock(731001)))
    identity, nonce = uuid4(), os.urandom(12)
    row = HttpHistory(
        id=identity,
        method=request.method,
        request_nonce=nonce,
        request_ciphertext=cipher().encrypt(
            nonce, request.model_dump_json().encode(), identity.bytes
        ),
        response_status=result.status,
        response_time_ms=result.elapsed_ms,
        response_size_bytes=result.size_bytes,
    )
    db.add(row)
    await db.flush()
    keep = (
        select(HttpHistory.id)
        .order_by(HttpHistory.created_at.desc(), HttpHistory.id.desc())
        .limit(request.history_limit)
    )
    await db.execute(delete(HttpHistory).where(HttpHistory.id.not_in(keep)))
    await db.commit()


async def clear_history(db: AsyncSession) -> None:
    await db.execute(select(func.pg_advisory_xact_lock(731001)))
    await db.execute(delete(HttpHistory))
    await db.commit()


async def list_history(db: AsyncSession) -> list[HistorySummary]:
    rows = await db.scalars(
        select(HttpHistory)
        .order_by(HttpHistory.created_at.desc(), HttpHistory.id.desc())
        .limit(200)
    )
    # Deliberately no URL/header/body in this list: any of those can contain secrets.
    return [HistorySummary.model_validate(row) for row in rows]


async def history_request(db: AsyncSession, identity: UUID) -> HttpRequest:
    row = await db.get(HttpHistory, identity)
    if row is None:
        raise AppError(404, "Riwayat tidak ditemukan.")
    try:
        content = cipher().decrypt(row.request_nonce, row.request_ciphertext, row.id.bytes)
        return HttpRequest.model_validate_json(content)
    except (InvalidTag, ValueError):
        raise AppError(
            409, "Riwayat tidak bisa dibuka. APP_SECRET_KEY harus sama dengan saat riwayat dibuat."
        ) from None
