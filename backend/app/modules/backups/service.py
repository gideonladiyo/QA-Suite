import io
import re
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from fastapi import Request
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.backups.schemas import (
    BackupManifest,
    ImportPreview,
    ImportResult,
    ThemeBackup,
)
from app.modules.qa_reports import backup as report_backup
from app.modules.qa_reports.schemas import BackupReport, ReportBackup, TemplateOutput
from app.modules.vault import backup as vault_backup
from app.modules.vault.schemas import VaultBackup

MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 150 * 1024 * 1024
ARCHIVE_FILES_V1 = {"manifest.json", "qa-reports.json", "theme.json", "vault.json"}
ARCHIVE_FILES_V2 = {"manifest.json", "reports/templates.json", "theme.json", "vault.json"}
REPORT_FILE = re.compile(r"^reports/(\d{4}-\d{2})/(\d{4}-\d{2}-\d{2})\.json$")
REPORT_DIRECTORY = re.compile(r"^reports(?:/\d{4}-\d{2})?/$")
TEMPLATES = TypeAdapter(list[TemplateOutput])


@dataclass
class ArchiveData:
    manifest: BackupManifest
    reports: ReportBackup
    theme: ThemeBackup
    vault: VaultBackup


async def export_archive(db: AsyncSession, theme: ThemeBackup) -> bytes:
    manifest = BackupManifest(
        format="qa-portal-backup", schema_version=2, exported_at=datetime.now(UTC)
    )
    reports = ReportBackup.model_validate_json(await report_backup.export_backup(db))
    documents: dict[str, str | bytes] = {
        "manifest.json": manifest.model_dump_json(),
        "reports/templates.json": TEMPLATES.dump_json(reports.templates),
        "theme.json": theme.model_dump_json(),
        "vault.json": await vault_backup.export_backup(db),
    }
    documents.update(
        {
            f"reports/{report.report_date:%Y-%m}/{report.report_date.isoformat()}.json": (
                report.model_dump_json()
            )
            for report in reports.reports
        }
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, document in documents.items():
            archive.writestr(name, document)
    data = output.getvalue()
    if len(data) > MAX_ARCHIVE_BYTES:
        raise AppError(413, "Backup ZIP melebihi batas 100 MB.")
    return data


async def read_archive(request: Request) -> ArchiveData:
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_ARCHIVE_BYTES:
            raise AppError(413, "File backup ZIP maksimal 100 MB.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            all_names = [entry.filename for entry in entries]
            directories = [entry for entry in entries if entry.is_dir()]
            names = [entry.filename for entry in entries if not entry.is_dir()]
            if (
                len(all_names) != len(set(all_names))
                or any(entry.flag_bits & 1 for entry in entries)
                or any(
                    entry.file_size != 0 or REPORT_DIRECTORY.fullmatch(entry.filename) is None
                    for entry in directories
                )
                or sum(entry.file_size for entry in entries) > MAX_UNCOMPRESSED_BYTES
            ):
                raise ValueError
            manifest = BackupManifest.model_validate_json(archive.read("manifest.json"))
            if manifest.schema_version == 1:
                if set(names) != ARCHIVE_FILES_V1:
                    raise ValueError
                reports = ReportBackup.model_validate_json(archive.read("qa-reports.json"))
            else:
                report_files = set(names) - ARCHIVE_FILES_V2
                if not ARCHIVE_FILES_V2.issubset(names) or any(
                    REPORT_FILE.fullmatch(name) is None for name in report_files
                ):
                    raise ValueError
                report_entries = []
                for name in sorted(report_files):
                    report = BackupReport.model_validate_json(archive.read(name))
                    expected = (
                        f"reports/{report.report_date:%Y-%m}/{report.report_date.isoformat()}.json"
                    )
                    if name != expected:
                        raise ValueError
                    report_entries.append(report)
                reports = ReportBackup(
                    format="qa-portal-reports",
                    schema_version=4,
                    exported_at=manifest.exported_at,
                    reports=report_entries,
                    templates=TEMPLATES.validate_json(archive.read("reports/templates.json")),
                )
            return ArchiveData(
                manifest=manifest,
                reports=reports,
                theme=ThemeBackup.model_validate_json(archive.read("theme.json")),
                vault=VaultBackup.model_validate_json(archive.read("vault.json")),
            )
    except (
        KeyError,
        OSError,
        RuntimeError,
        UnicodeError,
        ValidationError,
        ValueError,
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
    ):
        raise AppError(422, "Backup ZIP tidak valid atau tidak kompatibel.") from None


async def preview_import(db: AsyncSession, archive: ArchiveData) -> ImportPreview:
    reports = await report_backup.compare_backup(db, archive.reports)
    vault = await vault_backup.compare_backup(db, archive.vault)
    return ImportPreview(
        exported_at=archive.manifest.exported_at,
        reports=len(archive.reports.reports),
        templates=len(archive.reports.templates),
        vault_entries=len(archive.vault.entries),
        has_theme=True,
        has_existing_data=any(
            [reports.existing_reports, reports.existing_templates, vault.configured]
        ),
        vault_mergeable=await vault_backup.can_merge(db, archive.vault),
        existing_reports=reports.existing_reports,
        existing_templates=reports.existing_templates,
        existing_vault_entries=vault.existing_entries,
        new_reports=reports.new_reports,
        new_templates=reports.new_templates,
        new_vault_entries=vault.new_entries,
    )


async def import_archive(
    db: AsyncSession, archive: ArchiveData, mode: Literal["missing", "overwrite"]
) -> ImportResult:
    try:
        if mode == "overwrite":
            reports = await report_backup.overwrite_backup(db, archive.reports, commit=False)
        else:
            reports = await report_backup.restore_backup(db, archive.reports, commit=False)
        vault = await vault_backup.restore_backup(db, archive.vault, overwrite=mode == "overwrite")
        await db.commit()
    except AppError:
        await db.rollback()
        raise
    except IntegrityError:
        await db.rollback()
        raise AppError(
            409, "Data berubah saat import. Tidak ada data yang diimport; coba kembali."
        ) from None
    return ImportResult(
        mode=mode,
        reports_restored=reports.restored,
        reports_skipped=reports.skipped,
        vault_restored=vault.restored,
        vault_skipped=vault.skipped,
        theme=archive.theme,
    )
