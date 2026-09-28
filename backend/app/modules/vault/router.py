from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response

from app.core.auth import Db, require_user
from app.modules.vault import service
from app.modules.vault.schemas import (
    VaultCategory,
    VaultEntryDetail,
    VaultEntryInput,
    VaultEntrySummary,
    VaultSecretValue,
    VaultSetup,
    VaultSort,
    VaultStatus,
    VaultUnlock,
    VaultUnlockResult,
)

router = APIRouter(prefix="/api/vault", tags=["vault"], dependencies=[Depends(require_user)])
VaultToken = Annotated[str | None, Header(alias="X-Vault-Session")]


def require_vault(token: VaultToken = None) -> bytearray:
    return service.session_key(token)


VaultKey = Annotated[bytearray, Depends(require_vault)]


@router.get("/status")
async def status(db: Db, token: VaultToken = None) -> VaultStatus:
    return await service.status(db, token)


@router.post("/setup", status_code=201)
async def setup(body: VaultSetup, db: Db) -> VaultUnlockResult:
    return await service.setup(db, body.secret.get_secret_value(), body.auto_lock_minutes)


@router.post("/unlock")
async def unlock(body: VaultUnlock, db: Db) -> VaultUnlockResult:
    return await service.unlock(db, body.secret.get_secret_value(), body.auto_lock_minutes)


@router.post("/lock", status_code=204)
async def lock(db: Db, token: VaultToken = None) -> Response:
    await service.lock(db, token)
    return Response(status_code=204)


@router.post("/touch", status_code=204)
async def touch(key: VaultKey) -> Response:
    return Response(status_code=204)


@router.get("")
async def entries(
    db: Db,
    key: VaultKey,
    search: str = "",
    category: VaultCategory | None = None,
    sort: Annotated[VaultSort, Query()] = "recent",
) -> list[VaultEntrySummary]:
    return await service.list_entries(db, search, category, sort)


@router.post("", status_code=201)
async def create(body: VaultEntryInput, db: Db, key: VaultKey) -> VaultEntrySummary:
    return await service.create_entry(db, body, key)


@router.put("/{identity}")
async def update(identity: UUID, body: VaultEntryInput, db: Db, key: VaultKey) -> VaultEntrySummary:
    return await service.update_entry(db, identity, body, key)


@router.delete("/{identity}", status_code=204)
async def delete(identity: UUID, db: Db, key: VaultKey) -> Response:
    await service.delete_entry(db, identity)
    return Response(status_code=204)


@router.post("/{identity}/reveal")
async def reveal(identity: UUID, db: Db, key: VaultKey) -> VaultEntryDetail:
    return await service.reveal_entry(db, identity, key)


@router.post("/{identity}/copy")
async def copy(identity: UUID, db: Db, key: VaultKey) -> VaultSecretValue:
    return await service.copy_entry(db, identity, key)
