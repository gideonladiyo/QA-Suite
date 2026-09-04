import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidTag
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.micro_utilities.history import cipher
from app.modules.micro_utilities.models import HttpCollection, HttpSavedRequest
from app.modules.micro_utilities.schemas import (
    CollectionDocument,
    CollectionExportData,
    CollectionExportRequest,
    CollectionInput,
    CollectionSummary,
    HttpRequest,
    SavedRequestDetail,
    SavedRequestInput,
    SavedRequestSummary,
)

MAX_COLLECTIONS = 100
MAX_REQUESTS = 100


def encrypted(identity: UUID, request: HttpRequest) -> tuple[bytes, bytes]:
    nonce = os.urandom(12)
    safe = request.model_copy(update={"allow_private": False})
    return nonce, cipher().encrypt(nonce, safe.model_dump_json().encode(), identity.bytes)


def decrypted(row: HttpSavedRequest) -> HttpRequest:
    try:
        content = cipher().decrypt(row.request_nonce, row.request_ciphertext, row.id.bytes)
        return HttpRequest.model_validate_json(content)
    except (InvalidTag, ValueError):
        raise AppError(
            409,
            "Request tersimpan tidak bisa dibuka. APP_SECRET_KEY harus sama dengan "
            "saat request disimpan.",
        ) from None


async def collection(db: AsyncSession, identity: UUID) -> HttpCollection:
    row = await db.get(HttpCollection, identity)
    if row is None:
        raise AppError(404, "Collection tidak ditemukan.")
    return row


async def list_collections(db: AsyncSession) -> list[CollectionSummary]:
    counts = (
        select(HttpSavedRequest.collection_id, func.count().label("request_count"))
        .group_by(HttpSavedRequest.collection_id)
        .subquery()
    )
    rows = (
        await db.execute(
            select(HttpCollection, func.coalesce(counts.c.request_count, 0))
            .outerjoin(counts, counts.c.collection_id == HttpCollection.id)
            .order_by(HttpCollection.name)
            .limit(MAX_COLLECTIONS)
        )
    ).all()
    return [
        CollectionSummary(
            id=row.id,
            name=row.name,
            description=row.description,
            request_count=count,
            updated_at=row.updated_at,
        )
        for row, count in rows
    ]


async def create_collection(db: AsyncSession, body: CollectionInput) -> CollectionSummary:
    await db.execute(select(func.pg_advisory_xact_lock(731003)))
    if (await db.scalar(select(func.count()).select_from(HttpCollection)) or 0) >= MAX_COLLECTIONS:
        raise AppError(422, "Maksimal 100 collection. Hapus collection yang tidak dipakai.")
    row = HttpCollection(name=body.name.strip(), description=body.description.strip())
    db.add(row)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "Nama collection sudah digunakan.") from None
    await db.refresh(row)
    return CollectionSummary.model_validate(row)


async def update_collection(
    db: AsyncSession, identity: UUID, body: CollectionInput
) -> CollectionSummary:
    row = await collection(db, identity)
    row.name, row.description = body.name.strip(), body.description.strip()
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "Nama collection sudah digunakan.") from None
    await db.refresh(row)
    count = await db.scalar(
        select(func.count())
        .select_from(HttpSavedRequest)
        .where(HttpSavedRequest.collection_id == row.id)
    )
    return CollectionSummary(
        id=row.id,
        name=row.name,
        description=row.description,
        request_count=count or 0,
        updated_at=row.updated_at,
    )


async def delete_collection(db: AsyncSession, identity: UUID) -> None:
    await db.delete(await collection(db, identity))
    await db.commit()


async def list_requests(db: AsyncSession, collection_id: UUID) -> list[SavedRequestSummary]:
    await collection(db, collection_id)
    rows = await db.scalars(
        select(HttpSavedRequest)
        .where(HttpSavedRequest.collection_id == collection_id)
        .order_by(HttpSavedRequest.name)
        .limit(MAX_REQUESTS)
    )
    return [SavedRequestSummary.model_validate(row) for row in rows]


async def request_row(db: AsyncSession, collection_id: UUID, request_id: UUID) -> HttpSavedRequest:
    row = await db.scalar(
        select(HttpSavedRequest).where(
            HttpSavedRequest.id == request_id,
            HttpSavedRequest.collection_id == collection_id,
        )
    )
    if row is None:
        raise AppError(404, "Request tersimpan tidak ditemukan.")
    return row


async def save_request(
    db: AsyncSession, collection_id: UUID, body: SavedRequestInput
) -> SavedRequestSummary:
    parent = await collection(db, collection_id)
    await db.execute(select(func.pg_advisory_xact_lock(731004)))
    count = await db.scalar(
        select(func.count())
        .select_from(HttpSavedRequest)
        .where(HttpSavedRequest.collection_id == collection_id)
    )
    if (count or 0) >= MAX_REQUESTS:
        raise AppError(422, "Maksimal 100 request per collection.")
    identity = uuid4()
    nonce, ciphertext = encrypted(identity, body.request)
    row = HttpSavedRequest(
        id=identity,
        collection_id=collection_id,
        name=body.name.strip(),
        method=body.request.method,
        request_nonce=nonce,
        request_ciphertext=ciphertext,
    )
    db.add(row)
    parent.updated_at = datetime.now(UTC)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "Nama request sudah digunakan dalam collection ini.") from None
    await db.refresh(row)
    return SavedRequestSummary.model_validate(row)


async def load_request(
    db: AsyncSession, collection_id: UUID, request_id: UUID
) -> SavedRequestDetail:
    row = await request_row(db, collection_id, request_id)
    return SavedRequestDetail(
        **SavedRequestSummary.model_validate(row).model_dump(), request=decrypted(row)
    )


async def update_request(
    db: AsyncSession, collection_id: UUID, request_id: UUID, body: SavedRequestInput
) -> SavedRequestSummary:
    row = await request_row(db, collection_id, request_id)
    parent = await collection(db, collection_id)
    nonce, ciphertext = encrypted(row.id, body.request)
    row.name, row.method = body.name.strip(), body.request.method
    row.request_nonce, row.request_ciphertext = nonce, ciphertext
    parent.updated_at = datetime.now(UTC)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(409, "Nama request sudah digunakan dalam collection ini.") from None
    await db.refresh(row)
    return SavedRequestSummary.model_validate(row)


async def delete_request(db: AsyncSession, collection_id: UUID, request_id: UUID) -> None:
    row = await request_row(db, collection_id, request_id)
    parent = await collection(db, collection_id)
    await db.delete(row)
    parent.updated_at = datetime.now(UTC)
    await db.commit()


async def export_collection(db: AsyncSession, identity: UUID) -> CollectionDocument:
    parent = await collection(db, identity)
    rows = await db.scalars(
        select(HttpSavedRequest)
        .where(HttpSavedRequest.collection_id == identity)
        .order_by(HttpSavedRequest.name)
    )
    return CollectionDocument(
        format="qa-portal-http-collection",
        schema_version=1,
        exported_at=datetime.now(UTC),
        collection=CollectionExportData(
            name=parent.name,
            description=parent.description,
            requests=[
                CollectionExportRequest(name=row.name, request=decrypted(row)) for row in rows
            ],
        ),
    )


async def import_collection(db: AsyncSession, body: CollectionDocument) -> CollectionSummary:
    await db.execute(select(func.pg_advisory_xact_lock(731003)))
    if (await db.scalar(select(func.count()).select_from(HttpCollection)) or 0) >= MAX_COLLECTIONS:
        raise AppError(422, "Maksimal 100 collection. Hapus collection yang tidak dipakai.")
    names = [entry.name.strip() for entry in body.collection.requests]
    if len(names) != len(set(names)):
        raise AppError(422, "Nama request dalam file import harus unik.")
    parent = HttpCollection(
        name=body.collection.name.strip(), description=body.collection.description.strip()
    )
    db.add(parent)
    try:
        await db.flush()
        for entry in body.collection.requests:
            identity = uuid4()
            nonce, ciphertext = encrypted(identity, entry.request)
            db.add(
                HttpSavedRequest(
                    id=identity,
                    collection_id=parent.id,
                    name=entry.name.strip(),
                    method=entry.request.method,
                    request_nonce=nonce,
                    request_ciphertext=ciphertext,
                )
            )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(
            409, "Nama collection atau request dari file import sudah digunakan."
        ) from None
    await db.refresh(parent)
    return CollectionSummary(
        id=parent.id,
        name=parent.name,
        description=parent.description,
        request_count=len(body.collection.requests),
        updated_at=parent.updated_at,
    )
