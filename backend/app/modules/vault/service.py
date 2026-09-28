import asyncio
import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import password_hash, token_digest, verify_password
from app.modules.vault.models import VaultAccessLog, VaultMasterLock, VaultSecret
from app.modules.vault.schemas import (
    VaultCategory,
    VaultEntryDetail,
    VaultEntryInput,
    VaultEntrySummary,
    VaultSecretValue,
    VaultSort,
    VaultStatus,
    VaultUnlockResult,
)

MAX_ENTRIES = 1_000
KDF_ROUNDS = 600_000


@dataclass
class UnlockSession:
    key: bytearray
    last_activity: datetime
    timeout_minutes: int


sessions: dict[str, UnlockSession] = {}


def derive_key(secret: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", secret.encode(), salt, KDF_ROUNDS, dklen=32)


def forget(session: UnlockSession) -> None:
    session.key[:] = b"\x00" * len(session.key)


def clear_sessions() -> None:
    for session in sessions.values():
        forget(session)
    sessions.clear()


def cleanup_sessions() -> None:
    now = datetime.now(UTC)
    for digest, session in list(sessions.items()):
        if now - session.last_activity >= timedelta(minutes=session.timeout_minutes):
            forget(sessions.pop(digest))


def session_key(token: str | None, *, touch: bool = True) -> bytearray:
    cleanup_sessions()
    session = sessions.get(token_digest(token)) if token else None
    if session is None:
        raise AppError(423, "Vault terkunci. Buka kembali dengan Master PIN atau passphrase.")
    if touch:
        session.last_activity = datetime.now(UTC)
    return session.key


def session_active(token: str | None) -> bool:
    try:
        session_key(token, touch=False)
        return True
    except AppError:
        return False


async def master_lock(db: AsyncSession) -> VaultMasterLock:
    row = await db.scalar(select(VaultMasterLock).limit(1))
    if row is None:
        raise AppError(409, "Master lock belum disiapkan.")
    return row


async def status(db: AsyncSession, token: str | None) -> VaultStatus:
    configured = (await db.scalar(select(VaultMasterLock.id).limit(1))) is not None
    return VaultStatus(configured=configured, unlocked=configured and session_active(token))


def create_session(key: bytes, timeout_minutes: int) -> VaultUnlockResult:
    cleanup_sessions()
    if len(sessions) >= 20:
        oldest = min(sessions, key=lambda digest: sessions[digest].last_activity)
        forget(sessions.pop(oldest))
    token = secrets.token_urlsafe(32)
    sessions[token_digest(token)] = UnlockSession(
        key=bytearray(key), last_activity=datetime.now(UTC), timeout_minutes=timeout_minutes
    )
    return VaultUnlockResult(
        configured=True, unlocked=True, token=token, auto_lock_minutes=timeout_minutes
    )


async def setup(db: AsyncSession, secret: str, auto_lock_minutes: int) -> VaultUnlockResult:
    await db.execute(select(func.pg_advisory_xact_lock(731006)))
    if await db.scalar(select(VaultMasterLock.id).limit(1)):
        raise AppError(409, "Master lock sudah disiapkan. Buka Vault dengan master yang ada.")
    salt = os.urandom(16)
    hashed, key = await asyncio.gather(
        asyncio.to_thread(password_hash, secret),
        asyncio.to_thread(derive_key, secret, salt),
    )
    db.add(VaultMasterLock(pin_hash=hashed, kdf_salt=salt))
    db.add(VaultAccessLog(action="unlock_success", detail="Master lock dibuat"))
    await db.commit()
    return create_session(key, auto_lock_minutes)


async def unlock(db: AsyncSession, secret: str, auto_lock_minutes: int) -> VaultUnlockResult:
    row = await db.scalar(select(VaultMasterLock).with_for_update().limit(1))
    if row is None:
        raise AppError(409, "Master lock belum disiapkan.")
    now = datetime.now(UTC)
    if row.locked_until and row.locked_until > now:
        seconds = max(1, int((row.locked_until - now).total_seconds()) + 1)
        raise AppError(429, f"Terlalu banyak percobaan. Coba lagi dalam {seconds} detik.")
    try:
        valid = await asyncio.to_thread(verify_password, secret, row.pin_hash)
    except ValueError:
        raise AppError(409, "Konfigurasi Master Lock tidak valid.") from None
    if not valid:
        row.failed_attempts += 1
        delay = 0
        if row.failed_attempts >= 5:
            delay = min(3_600, 60 * 2 ** (row.failed_attempts - 5))
        elif row.failed_attempts >= 3:
            delay = 2 ** (row.failed_attempts - 2)
        row.locked_until = now + timedelta(seconds=delay) if delay else None
        db.add(VaultAccessLog(action="unlock_failed", detail="Master tidak cocok"))
        await db.commit()
        if delay:
            raise AppError(429, f"Master tidak cocok. Coba lagi dalam {delay} detik.")
        raise AppError(403, "Master PIN atau passphrase tidak cocok.")
    key = await asyncio.to_thread(derive_key, secret, row.kdf_salt)
    row.failed_attempts = 0
    row.locked_until = None
    db.add(VaultAccessLog(action="unlock_success", detail="Vault dibuka"))
    await db.commit()
    return create_session(key, auto_lock_minutes)


async def lock(db: AsyncSession, token: str | None) -> None:
    digest = token_digest(token) if token else None
    session = sessions.pop(digest, None) if digest else None
    if session:
        forget(session)
        db.add(VaultAccessLog(action="lock", detail="Vault dikunci"))
        await db.commit()


def encrypt(identity: UUID, field: bytes, value: str, key: bytearray) -> tuple[bytes, bytes]:
    nonce = os.urandom(12)
    ciphertext = AESGCM(bytes(key)).encrypt(nonce, value.encode(), field + identity.bytes)
    return ciphertext, nonce


def decrypt(identity: UUID, field: bytes, ciphertext: bytes, nonce: bytes, key: bytearray) -> str:
    try:
        return AESGCM(bytes(key)).decrypt(nonce, ciphertext, field + identity.bytes).decode()
    except (InvalidTag, UnicodeDecodeError):
        raise AppError(
            409, "Item tidak bisa dibuka. Master yang benar dan data terenkripsi asli diperlukan."
        ) from None


async def list_entries(
    db: AsyncSession,
    search: str,
    category: VaultCategory | None,
    sort: VaultSort,
) -> list[VaultEntrySummary]:
    statement = select(VaultSecret)
    if search.strip():
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                VaultSecret.title.ilike(pattern),
                VaultSecret.username.ilike(pattern),
                VaultSecret.category.ilike(pattern),
            )
        )
    if category:
        statement = statement.where(VaultSecret.category == category)
    if sort == "alphabetical":
        statement = statement.order_by(VaultSecret.title, VaultSecret.id)
    elif sort == "created":
        statement = statement.order_by(VaultSecret.created_at.desc(), VaultSecret.id.desc())
    else:
        statement = statement.order_by(
            VaultSecret.last_accessed_at.desc().nullslast(),
            VaultSecret.updated_at.desc(),
            VaultSecret.id.desc(),
        )
    rows = await db.scalars(statement.limit(MAX_ENTRIES))
    return [VaultEntrySummary.model_validate(row) for row in rows]


async def entry(db: AsyncSession, identity: UUID) -> VaultSecret:
    row = await db.get(VaultSecret, identity)
    if row is None:
        raise AppError(404, "Item Vault tidak ditemukan.")
    return row


async def create_entry(
    db: AsyncSession, body: VaultEntryInput, key: bytearray
) -> VaultEntrySummary:
    await db.execute(select(func.pg_advisory_xact_lock(731007)))
    count = await db.scalar(select(func.count()).select_from(VaultSecret))
    if (count or 0) >= MAX_ENTRIES:
        raise AppError(422, "Maksimal 1.000 item Vault. Hapus item yang tidak dipakai.")
    identity = uuid4()
    value_ciphertext, value_nonce = encrypt(
        identity, b"vault-value/v1", body.value.get_secret_value(), key
    )
    notes = body.notes.get_secret_value()
    notes_ciphertext, notes_nonce = (
        encrypt(identity, b"vault-notes/v1", notes, key) if notes else (None, None)
    )
    row = VaultSecret(
        id=identity,
        title=body.title,
        username=body.username.strip() or None,
        category=body.category,
        url=body.url or None,
        value_ciphertext=value_ciphertext,
        value_nonce=value_nonce,
        notes_ciphertext=notes_ciphertext,
        notes_nonce=notes_nonce,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return VaultEntrySummary.model_validate(row)


async def update_entry(
    db: AsyncSession, identity: UUID, body: VaultEntryInput, key: bytearray
) -> VaultEntrySummary:
    row = await entry(db, identity)
    value_ciphertext, value_nonce = encrypt(
        identity, b"vault-value/v1", body.value.get_secret_value(), key
    )
    notes = body.notes.get_secret_value()
    notes_ciphertext, notes_nonce = (
        encrypt(identity, b"vault-notes/v1", notes, key) if notes else (None, None)
    )
    row.title = body.title
    row.username = body.username.strip() or None
    row.category = body.category
    row.url = body.url or None
    row.value_ciphertext = value_ciphertext
    row.value_nonce = value_nonce
    row.notes_ciphertext = notes_ciphertext
    row.notes_nonce = notes_nonce
    await db.commit()
    await db.refresh(row)
    return VaultEntrySummary.model_validate(row)


async def delete_entry(db: AsyncSession, identity: UUID) -> None:
    await db.delete(await entry(db, identity))
    await db.commit()


async def reveal_entry(db: AsyncSession, identity: UUID, key: bytearray) -> VaultEntryDetail:
    row = await entry(db, identity)
    value = decrypt(row.id, b"vault-value/v1", row.value_ciphertext, row.value_nonce, key)
    notes = (
        decrypt(row.id, b"vault-notes/v1", row.notes_ciphertext, row.notes_nonce, key)
        if row.notes_ciphertext is not None and row.notes_nonce is not None
        else ""
    )
    row.last_accessed_at = datetime.now(UTC)
    db.add(VaultAccessLog(secret_id=row.id, action="reveal", detail=row.title))
    await db.commit()
    return VaultEntryDetail(value=value, notes=notes)


async def copy_entry(db: AsyncSession, identity: UUID, key: bytearray) -> VaultSecretValue:
    row = await entry(db, identity)
    value = decrypt(row.id, b"vault-value/v1", row.value_ciphertext, row.value_nonce, key)
    row.last_accessed_at = datetime.now(UTC)
    db.add(VaultAccessLog(secret_id=row.id, action="copy", detail=row.title))
    await db.commit()
    return VaultSecretValue(value=value)
