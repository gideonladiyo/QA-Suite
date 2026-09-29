from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, Response

from app.core.auth import Db, require_user
from app.modules.backups import service
from app.modules.backups.schemas import ImportPreview, ImportResult, ThemeBackup

router = APIRouter(prefix="/api/backups", tags=["backups"], dependencies=[Depends(require_user)])


@router.post("")
async def download(body: ThemeBackup, db: Db) -> Response:
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return Response(
        await service.export_archive(db, body),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="backup_{timestamp}.zip"',
        },
    )


@router.post("/preview")
async def preview(request: Request, db: Db) -> ImportPreview:
    return await service.preview_import(db, await service.read_archive(request))


@router.post("/import")
async def restore(
    request: Request,
    db: Db,
    mode: Annotated[Literal["missing", "overwrite"], Query()] = "missing",
) -> ImportResult:
    return await service.import_archive(db, await service.read_archive(request), mode)
