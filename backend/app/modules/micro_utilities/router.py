from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.core.auth import Db, require_user
from app.modules.micro_utilities import collections, history, service
from app.modules.micro_utilities.schemas import (
    CollectionDocument,
    CollectionInput,
    CollectionSummary,
    HistorySummary,
    HttpRequest,
    HttpResult,
    PresetInput,
    PresetOutput,
    SavedRequestDetail,
    SavedRequestInput,
    SavedRequestSummary,
)

router = APIRouter(
    prefix="/api/micro-utilities", tags=["micro_utilities"], dependencies=[Depends(require_user)]
)


@router.post("/http/send")
async def send(body: HttpRequest, db: Db) -> HttpResult:
    return await service.send_request(db, body)


@router.get("/http/history")
async def recent(db: Db) -> list[HistorySummary]:
    return await history.list_history(db)


@router.get("/http/history/{identity}")
async def open_request(identity: UUID, db: Db) -> HttpRequest:
    return await history.history_request(db, identity)


@router.delete("/http/history", status_code=204)
async def clear_history(db: Db) -> Response:
    await history.clear_history(db)
    return Response(status_code=204)


@router.get("/http/collections")
async def collection_list(db: Db) -> list[CollectionSummary]:
    return await collections.list_collections(db)


@router.post("/http/collections", status_code=201)
async def collection_create(body: CollectionInput, db: Db) -> CollectionSummary:
    return await collections.create_collection(db, body)


@router.post("/http/collections/import", status_code=201)
async def collection_import(body: CollectionDocument, db: Db) -> CollectionSummary:
    return await collections.import_collection(db, body)


@router.put("/http/collections/{collection_id}")
async def collection_update(
    collection_id: UUID, body: CollectionInput, db: Db
) -> CollectionSummary:
    return await collections.update_collection(db, collection_id, body)


@router.delete("/http/collections/{collection_id}", status_code=204)
async def collection_delete(collection_id: UUID, db: Db) -> Response:
    await collections.delete_collection(db, collection_id)
    return Response(status_code=204)


@router.get("/http/collections/{collection_id}/export")
async def collection_export(collection_id: UUID, db: Db) -> CollectionDocument:
    return await collections.export_collection(db, collection_id)


@router.get("/http/collections/{collection_id}/requests")
async def request_list(collection_id: UUID, db: Db) -> list[SavedRequestSummary]:
    return await collections.list_requests(db, collection_id)


@router.post("/http/collections/{collection_id}/requests", status_code=201)
async def request_create(
    collection_id: UUID, body: SavedRequestInput, db: Db
) -> SavedRequestSummary:
    return await collections.save_request(db, collection_id, body)


@router.get("/http/collections/{collection_id}/requests/{request_id}")
async def request_open(collection_id: UUID, request_id: UUID, db: Db) -> SavedRequestDetail:
    return await collections.load_request(db, collection_id, request_id)


@router.put("/http/collections/{collection_id}/requests/{request_id}")
async def request_update(
    collection_id: UUID, request_id: UUID, body: SavedRequestInput, db: Db
) -> SavedRequestSummary:
    return await collections.update_request(db, collection_id, request_id, body)


@router.delete("/http/collections/{collection_id}/requests/{request_id}", status_code=204)
async def request_delete(collection_id: UUID, request_id: UUID, db: Db) -> Response:
    await collections.delete_request(db, collection_id, request_id)
    return Response(status_code=204)


@router.get("/presets")
async def list_presets(db: Db) -> list[PresetOutput]:
    return await service.presets(db)


@router.post("/presets", status_code=201)
async def save_preset(body: PresetInput, db: Db) -> PresetOutput:
    return await service.create_preset(db, body)


@router.delete("/presets/{identity}", status_code=204)
async def remove_preset(identity: UUID, db: Db) -> Response:
    await service.delete_preset(db, identity)
    return Response(status_code=204)
