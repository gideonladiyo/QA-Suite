from datetime import date

import httpx
import pytest

from app.modules.qa_reports.models import DailyReport, ReportItem
from app.modules.qa_reports.service import generate_preview
from app.modules.qa_reports.templates import custom_keys, render_body, validate_body


def test_safe_template_rendering_and_validation() -> None:
    source = (
        "{{nama_proyek}}\n{{#activities}}{{current_issue}}\n{{/activities}}"
        "{{#activities}}{{activity_code}}{{/activities}}"
    )
    assert custom_keys(source) == ["nama_proyek"]
    assert (
        render_body(
            source,
            {"nama_proyek": "Portal"},
            [{"current_issue": "{{report_title}} $&", "activity_code": "QA-1"}],
        )
        == "Portal\n{{report_title}} $&\nQA-1"
    )
    for invalid in (
        "{{bad-name}}",
        "{{unclosed",
        "{{/activities}}",
        "{{activity_code}}",
        "{{#activities}}{{#activities}}{{/activities}}",
    ):
        with pytest.raises(ValueError):
            validate_body(invalid)
    report = DailyReport(
        title="QA",
        report_date=date(2026, 9, 3),
        template_body=source,
        template_values={"nama_proyek": "<script>"},
        items=[
            ReportItem(
                activity_code="QA-1",
                environment="Dev",
                result="Pass",
                current_issue="<!channel> {{missing}}",
                links=[],
            )
        ],
    )
    preview = generate_preview(report)
    assert "<!channel>" not in preview.slack_mrkdwn
    assert "{{missing}}" in preview.slack_mrkdwn
    assert "<script>" not in preview.html


def test_standalone_activity_block_lines_do_not_add_blank_lines() -> None:
    body = "Next Step:\n{{#activities}}\n- {{activity_code}}\n  {{next_step}}\n{{/activities}}"
    assert (
        render_body(
            body,
            {},
            [{"activity_code": "QA-142", "next_step": "Contoh next step"}],
        )
        == "Next Step:\n- QA-142\n  Contoh next step"
    )


async def test_custom_values_snapshot_edit_and_backup(client: httpx.AsyncClient) -> None:
    await client.post(
        "/api/auth/setup", json={"username": "qa_test", "password": "test_dummy_password_only"}
    )
    body = {
        "name": "Daily",
        "body": "{{nama_proyek}}\n{{#activities}}{{activity_code}}\n{{/activities}}",
    }
    template = (await client.post("/api/qa-reports/templates", json=body)).json()
    saved = await client.post(
        "/api/qa-reports",
        json={
            "title": "QA",
            "report_date": "2026-09-03",
            "template_id": template["id"],
            "template_values": {"nama_proyek": "Portal"},
            "items": [{"activity_code": "QA-3", "result": "Pass"}],
        },
    )
    assert saved.status_code == 201, saved.text
    report = saved.json()
    backup = (await client.get("/api/qa-reports/backup")).json()
    assert backup["templates"][0]["body"] == body["body"]
    assert backup["reports"][0]["template_values"] == {"nama_proyek": "Portal"}
    await client.delete(f"/api/qa-reports/templates/{template['id']}")
    edited = await client.put(
        f"/api/qa-reports/{report['id']}",
        json={
            "title": "QA edited",
            "report_date": "2026-09-03",
            "version": 1,
            "template_values": {"nama_proyek": "Updated"},
            "items": [{"activity_code": "QA-3", "result": "Pass"}],
        },
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["template_body"] == body["body"]
    assert (
        (await client.get(f"/api/qa-reports/{report['id']}/preview"))
        .json()["slack"]
        .startswith("Updated")
    )
    await client.delete(f"/api/qa-reports/{report['id']}?version=2")
    restored = await client.post("/api/qa-reports/restore", json=backup)
    assert restored.status_code == 200, restored.text
    restored_templates = (await client.get("/api/qa-reports/templates")).json()
    assert len(restored_templates) == 1
    assert restored_templates[0]["id"] != template["id"]
    restored_id = (await client.get("/api/qa-reports")).json()["reports"][0]["id"]
    assert (
        (await client.get(f"/api/qa-reports/{restored_id}/preview"))
        .json()["slack"]
        .startswith("Portal")
    )
    # Old backups remain importable without template fields.
    old_backup = {**backup, "schema_version": 1}
    old_backup.pop("templates")
    for key in ("template_id", "template_body", "template_name", "template_values"):
        old_backup["reports"][0].pop(key)
    assert (await client.post("/api/qa-reports/restore", json=old_backup)).status_code == 200


async def test_adaptive_activity_values_edit_reorder_and_backup(client: httpx.AsyncClient) -> None:
    await client.post(
        "/api/auth/setup", json={"username": "qa_test", "password": "test_dummy_password_only"}
    )
    body = (
        "{{report_title}}\nDate: {{report_date}}\nTesting Result:\n"
        "{{#activities}}- {{activity_code}} {{environment}} {{current_status}}\n"
        "Summary:\n{{current_issue}}\nNext step:\n{{next_step}}\n{{/activities}}"
    )
    template = (
        await client.post(
            "/api/qa-reports/templates", json={"name": "Adaptive", "body": body.replace("_", r"\_")}
        )
    ).json()
    assert template["body"] == body
    metadata = {"title": "Adaptive QA", "report_date": "2026-09-04", "template_id": template["id"]}
    response = await client.post(
        "/api/qa-reports",
        json={
            **metadata,
            "items": [
                {
                    "activity_code": f"QA-{number}",
                    "environment": "Staging",
                    "current_status": "Retest",
                    "current_issue": f"Summary {number}",
                    "template_values": {"next_step": f"Next {number}"},
                }
                for number in (1, 2)
            ],
        },
    )
    assert response.status_code == 201, response.text
    report = response.json()
    path = f"/api/qa-reports/{report['id']}"
    assert all(item["result"] == "" and item["links"] == [] for item in report["items"])
    preview = (await client.get(path + "/preview")).json()["slack"]
    assert "Summary 1\nNext step:\nNext 1" in preview
    assert "Summary 2\nNext step:\nNext 2" in preview
    items = [
        {k: v for k, v in item.items() if k != "sort_order"} for item in reversed(report["items"])
    ]
    items[0]["template_values"] = {"next_step": "<!channel> {{result}} $&"}
    await client.post("/api/qa-reports", json={**metadata, "report_date": "2026-09-08"})
    conflict = await client.put(
        path, json={**metadata, "report_date": "2026-09-08", "version": 1, "items": items}
    )
    assert conflict.status_code == 409  # Selecting a template must not autoflush the date early.
    assert (await client.get(path)).json()["report_date"] == "2026-09-04"
    await client.delete(f"/api/qa-reports/templates/{template['id']}")
    edited = await client.put(
        path,
        json={
            "title": metadata["title"],
            "report_date": metadata["report_date"],
            "version": 1,
            "items": items,
        },
    )
    assert edited.status_code == 200, edited.text
    saved_preview = (await client.get(path + "/preview")).json()
    assert saved_preview["slack"].index("QA-2") < saved_preview["slack"].index("QA-1")
    assert "&lt;!channel&gt; {{result}} $&amp;" in saved_preview["slack_mrkdwn"]
    # Real results still drive the metric, omitted results are not fabricated.
    await client.post(
        "/api/qa-reports",
        json={
            "title": "Standard",
            "report_date": "2026-09-05",
            "items": [{"activity_code": "QA-3", "result": "Pass"}],
        },
    )
    metrics = (await client.get("/api/qa-reports/monthly?month=2026-09")).json()
    assert metrics["total"] == 3 and metrics["pass_rate"] == 100
    assert {"label": "Tidak diisi", "count": 2} in metrics["results"]
    invalid = await client.put(
        path, json={**metadata, "template_id": None, "version": 2, "items": items}
    )
    assert invalid.status_code == 422  # Standard format still requires a result.
    backup = (await client.get("/api/qa-reports/backup")).json()
    assert backup["schema_version"] == 3
    await client.delete(path + "?version=2")
    restored = await client.post("/api/qa-reports/restore", json=backup)
    assert restored.status_code == 200, restored.text
    restored_id = (await client.get("/api/qa-reports?start=2026-09-04&end=2026-09-04")).json()[
        "reports"
    ][0]["id"]
    assert (await client.get(f"/api/qa-reports/{restored_id}/preview")).json() == saved_preview


async def test_report_only_template_and_legacy_activity_fallback(client: httpx.AsyncClient) -> None:
    await client.post(
        "/api/auth/setup", json={"username": "qa_test", "password": "test_dummy_password_only"}
    )
    template = (
        await client.post(
            "/api/qa-reports/templates",
            json={"name": "Notes", "body": "{{report_title}}\n{{catatan}}"},
        )
    ).json()
    report = (
        await client.post(
            "/api/qa-reports",
            json={
                "title": "Notes",
                "report_date": "2026-09-06",
                "template_id": template["id"],
                "template_values": {"catatan": "Selesai"},
                "items": [],
            },
        )
    ).json()
    assert (await client.get(f"/api/qa-reports/{report['id']}/preview")).json()[
        "slack"
    ] == "Notes\nSelesai"
    backup = (await client.get("/api/qa-reports/backup")).json()
    backup["schema_version"] = 2
    legacy = backup["reports"][0]
    legacy["report_date"] = "2026-09-07"
    legacy["template_body"] = "{{#activities}}{{next_step}}\n{{/activities}}"
    legacy["template_values"] = {"next_step": "Legacy next step"}
    legacy["items"] = [
        {
            "id": report["id"],
            "sort_order": 0,
            "activity_code": "QA-7",
            "result": "Pass",
            "links": [],
        }
    ]
    restored = await client.post("/api/qa-reports/restore", json=backup)
    assert restored.status_code == 200, restored.text
    restored_id = (await client.get("/api/qa-reports?start=2026-09-07&end=2026-09-07")).json()[
        "reports"
    ][0]["id"]
    assert (await client.get(f"/api/qa-reports/{restored_id}/preview")).json()[
        "slack"
    ] == "Legacy next step"
