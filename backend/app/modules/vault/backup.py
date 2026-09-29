from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.vault import service
from app.modules.vault.models import VaultAccessLog, VaultMasterLock, VaultSecret
from app.modules.vault.schemas import (
    VaultBackup,
    VaultEntryBackup,
    VaultLogBackup,
    VaultMasterBackup,
    VaultRestoreResult,
)


@dataclass(frozen=True)
class BackupComparison:
    configured: bool
    existing_entries: int
    new_entries: int


async def compare_backup(db: AsyncSession, backup: VaultBackup) -> BackupComparison:
    identities = [entry.id for entry in backup.entries]
    matching = (
        await db.scalar(
            select(func.count()).select_from(VaultSecret).where(VaultSecret.id.in_(identities))
        )
        if identities
        else 0
    )
    return BackupComparison(
        configured=(await db.scalar(select(VaultMasterLock.id).limit(1))) is not None,
        existing_entries=await db.scalar(select(func.count()).select_from(VaultSecret)) or 0,
        new_entries=len(backup.entries) - (matching or 0),
    )


async def export_backup(db: AsyncSession) -> str:
    master = await db.scalar(select(VaultMasterLock).limit(1))
    entries = (await db.scalars(select(VaultSecret).order_by(VaultSecret.created_at))).all()
    logs = (await db.scalars(select(VaultAccessLog).order_by(VaultAccessLog.created_at))).all()
    return VaultBackup(
        format="qa-portal-vault",
        schema_version=1,
        master_lock=VaultMasterBackup.model_validate(master) if master else None,
        entries=[VaultEntryBackup.model_validate(entry) for entry in entries],
        access_logs=[VaultLogBackup.model_validate(log) for log in logs],
    ).model_dump_json()


async def can_merge(db: AsyncSession, backup: VaultBackup) -> bool:
    current = await db.scalar(select(VaultMasterLock).limit(1))
    if current is None or backup.master_lock is None:
        return True
    return (
        current.pin_hash == backup.master_lock.pin_hash
        and current.kdf_salt == backup.master_lock.kdf_salt
    )


def master_model(source: VaultMasterBackup) -> VaultMasterLock:
    return VaultMasterLock(**source.model_dump())


def entry_model(source: VaultEntryBackup) -> VaultSecret:
    return VaultSecret(**source.model_dump())


def log_model(source: VaultLogBackup) -> VaultAccessLog:
    return VaultAccessLog(**source.model_dump())


async def restore_backup(
    db: AsyncSession, backup: VaultBackup, *, overwrite: bool
) -> VaultRestoreResult:
    if overwrite:
        service.clear_sessions()
        await db.execute(delete(VaultAccessLog))
        await db.execute(delete(VaultSecret))
        await db.execute(delete(VaultMasterLock))
        await db.flush()
        if backup.master_lock:
            db.add(master_model(backup.master_lock))
        db.add_all([entry_model(entry) for entry in backup.entries])
        db.add_all([log_model(log) for log in backup.access_logs])
        await db.flush()
        return VaultRestoreResult(restored=len(backup.entries), skipped=0)

    current = await db.scalar(select(VaultMasterLock).limit(1))
    if current and backup.master_lock and not await can_merge(db, backup):
        raise AppError(
            409,
            "Vault dalam backup memakai master lock berbeda. "
            "Pilih overwrite untuk mengganti Vault.",
        )
    if current is None and backup.master_lock:
        db.add(master_model(backup.master_lock))
    existing_entries = set(await db.scalars(select(VaultSecret.id)))
    existing_logs = set(await db.scalars(select(VaultAccessLog.id)))
    new_entries = [entry for entry in backup.entries if entry.id not in existing_entries]
    new_logs = [log for log in backup.access_logs if log.id not in existing_logs]
    db.add_all([entry_model(entry) for entry in new_entries])
    db.add_all([log_model(log) for log in new_logs])
    await db.flush()
    return VaultRestoreResult(
        restored=len(new_entries), skipped=len(backup.entries) - len(new_entries)
    )
