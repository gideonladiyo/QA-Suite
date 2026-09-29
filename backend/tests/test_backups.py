import io
import json
import re
import zipfile
from typing import Any

import httpx

PORTAL_CREDENTIALS = {
    "username": "backup_test",
    "password": "test_dummy_portal_password",
}
MASTER = "test_dummy_master_passphrase"
THEME = {
    "theme": "dark",
    "color_palette": {
        "ink": "#123456",
        "violet": "#234567",
        "mauve": "#345678",
        "blush": "#456789",
    },
    "saved_palettes": [
        {
            "id": "saved-one",
            "name": "Saved one",
            "colors": {
                "ink": "#111111",
                "violet": "#222222",
                "mauve": "#333333",
                "blush": "#444444",
            },
        }
    ],
}


async def authenticate(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/auth/setup", json=PORTAL_CREDENTIALS)
    assert response.status_code == 201, response.text


async def create_report(client: httpx.AsyncClient, day: int) -> dict[str, Any]:
    response = await client.post(
        "/api/qa-reports",
        json={
            "title": f"Backup report {day}",
            "report_date": f"2026-09-{day:02}",
            "author_name": "Backup tester",
            "items": [
                {
                    "activity_code": f"QA-{day}",
                    "environment": "Prod",
                    "result": "Pass",
                    "current_status": "Done",
                    "current_issue": "No issue",
                    "duration_hours": 1.5,
                    "obstacle": "None",
                    "next_step": "Monitor",
                    "pic_guidance": "QA lead",
                    "deliverable": "Test result",
                    "links": [{"url": "https://example.test/coverage", "label": "Coverage"}],
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_vault_entry(client: httpx.AsyncClient, token: str, title: str) -> None:
    response = await client.post(
        "/api/vault",
        headers={"X-Vault-Session": token},
        json={
            "title": title,
            "username": "tester@example.test",
            "category": "password",
            "url": "https://example.test/login",
            "value": f"PLAIN_SECRET_{title}",
            "notes": "PLAIN_VAULT_NOTE",
        },
    )
    assert response.status_code == 201, response.text


def replace_zip_document(source: bytes, name: str, document: dict[str, Any]) -> bytes:
    output = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(source)) as original,
        zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as changed,
    ):
        for info in original.infolist():
            changed.writestr(
                info.filename,
                json.dumps(document) if info.filename == name else original.read(info.filename),
            )
    return output.getvalue()


async def test_zip_backup_preview_missing_and_overwrite(client: httpx.AsyncClient) -> None:
    assert (await client.post("/api/backups", json=THEME)).status_code == 401
    assert (await client.post("/api/backups/preview", content=b"bad zip")).status_code == 401
    await authenticate(client)
    await create_report(client, 1)
    template = await client.post(
        "/api/qa-reports/templates",
        json={"name": "Backup template", "description": "Test", "body": "{{report_title}}"},
    )
    assert template.status_code == 201, template.text
    setup = await client.post(
        "/api/vault/setup",
        json={"secret": MASTER, "confirmation": MASTER, "auto_lock_minutes": 5},
    )
    assert setup.status_code == 201, setup.text
    token = setup.json()["token"]
    await create_vault_entry(client, token, "Original")

    downloaded = await client.post("/api/backups", json=THEME)
    assert downloaded.status_code == 200, downloaded.text
    assert downloaded.headers["content-type"] == "application/zip"
    assert re.fullmatch(
        r'attachment; filename="backup_\d{8}_\d{6}\.zip"',
        downloaded.headers["content-disposition"],
    )
    archive = downloaded.content
    assert b"PLAIN_SECRET_Original" not in archive
    assert b"PLAIN_VAULT_NOTE" not in archive
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        assert set(zipped.namelist()) == {
            "manifest.json",
            "reports/templates.json",
            "reports/2026-09/2026-09-01.json",
            "theme.json",
            "vault.json",
        }
        manifest_document = json.loads(zipped.read("manifest.json"))
        report_document = json.loads(zipped.read("reports/2026-09/2026-09-01.json"))
        templates_document = json.loads(zipped.read("reports/templates.json"))
        assert manifest_document["schema_version"] == 2
        assert report_document["report_date"] == "2026-09-01"
        assert json.loads(zipped.read("theme.json")) == THEME
        vault_document = json.loads(zipped.read("vault.json"))

    legacy_output = io.BytesIO()
    with zipfile.ZipFile(legacy_output, "w", zipfile.ZIP_DEFLATED) as legacy:
        legacy.writestr("manifest.json", json.dumps(manifest_document | {"schema_version": 1}))
        legacy.writestr(
            "qa-reports.json",
            json.dumps(
                {
                    "format": "qa-portal-reports",
                    "schema_version": 4,
                    "exported_at": manifest_document["exported_at"],
                    "reports": [report_document],
                    "templates": templates_document,
                }
            ),
        )
        legacy.writestr("theme.json", json.dumps(THEME))
        legacy.writestr("vault.json", json.dumps(vault_document))
    legacy_preview = await client.post(
        "/api/backups/preview",
        content=legacy_output.getvalue(),
        headers={"Content-Type": "application/zip"},
    )
    assert legacy_preview.status_code == 200, legacy_preview.text
    assert legacy_preview.json()["reports"] == 1

    directory_output = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(archive)) as original,
        zipfile.ZipFile(directory_output, "w", zipfile.ZIP_DEFLATED) as with_directories,
    ):
        with_directories.writestr("reports/", "")
        with_directories.writestr("reports/2026-09/", "")
        for info in original.infolist():
            with_directories.writestr(info.filename, original.read(info.filename))
    directory_preview = await client.post(
        "/api/backups/preview",
        content=directory_output.getvalue(),
        headers={"Content-Type": "application/zip"},
    )
    assert directory_preview.status_code == 200, directory_preview.text
    assert directory_preview.json()["reports"] == 1

    await create_report(client, 2)
    await create_vault_entry(client, token, "Extra")
    preview = await client.post(
        "/api/backups/preview",
        content=archive,
        headers={"Content-Type": "application/zip"},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json() | {"exported_at": "ignored"} == {
        "exported_at": "ignored",
        "reports": 1,
        "templates": 1,
        "vault_entries": 1,
        "has_theme": True,
        "has_existing_data": True,
        "vault_mergeable": True,
        "existing_reports": 2,
        "existing_templates": 1,
        "existing_vault_entries": 2,
        "new_reports": 0,
        "new_templates": 0,
        "new_vault_entries": 0,
    }

    missing = await client.post(
        "/api/backups/import?mode=missing",
        content=archive,
        headers={"Content-Type": "application/zip"},
    )
    assert missing.status_code == 200, missing.text
    assert missing.json()["reports_restored"] == 0
    assert missing.json()["reports_skipped"] == 1
    assert missing.json()["vault_restored"] == 0
    assert missing.json()["vault_skipped"] == 1
    assert missing.json()["theme"] == THEME
    assert (await client.get("/api/qa-reports")).json()["total"] == 2
    assert len((await client.get("/api/vault", headers={"X-Vault-Session": token})).json()) == 2

    vault_document["master_lock"]["pin_hash"] = "different-master-hash"
    conflicting = replace_zip_document(archive, "vault.json", vault_document)
    conflict_preview = await client.post(
        "/api/backups/preview",
        content=conflicting,
        headers={"Content-Type": "application/zip"},
    )
    assert conflict_preview.status_code == 200
    assert conflict_preview.json()["vault_mergeable"] is False
    conflict = await client.post(
        "/api/backups/import?mode=missing",
        content=conflicting,
        headers={"Content-Type": "application/zip"},
    )
    assert conflict.status_code == 409
    assert (await client.get("/api/qa-reports")).json()["total"] == 2

    overwritten = await client.post(
        "/api/backups/import?mode=overwrite",
        content=archive,
        headers={"Content-Type": "application/zip"},
    )
    assert overwritten.status_code == 200, overwritten.text
    assert overwritten.json()["reports_restored"] == 1
    assert overwritten.json()["vault_restored"] == 1
    reports = (await client.get("/api/qa-reports?order=asc")).json()
    assert reports["total"] == 1
    assert reports["reports"][0]["report_date"] == "2026-09-01"
    assert len((await client.get("/api/qa-reports/templates")).json()) == 1
    unlocked = await client.post(
        "/api/vault/unlock", json={"secret": MASTER, "auto_lock_minutes": 5}
    )
    assert unlocked.status_code == 200, unlocked.text
    restored_vault = await client.get(
        "/api/vault", headers={"X-Vault-Session": unlocked.json()["token"]}
    )
    assert [entry["title"] for entry in restored_vault.json()] == ["Original"]


async def test_invalid_zip_is_rejected(client: httpx.AsyncClient) -> None:
    await authenticate(client)
    invalid = await client.post(
        "/api/backups/preview",
        content=b"not a zip",
        headers={"Content-Type": "application/zip"},
    )
    assert invalid.status_code == 422

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("unexpected.json", "{}")
    unexpected = await client.post(
        "/api/backups/import?mode=overwrite",
        content=output.getvalue(),
        headers={"Content-Type": "application/zip"},
    )
    assert unexpected.status_code == 422
    assert (await client.get("/api/qa-reports")).json()["total"] == 0
