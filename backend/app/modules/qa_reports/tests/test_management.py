from copy import deepcopy
from datetime import date
from typing import Any, cast

import httpx
from sqlalchemy import func, select

from app.core.database import engine
from app.modules.qa_reports.models import DailyReport, ReportItem, ReportItemLink
from app.modules.qa_reports.service import generate_preview


async def setup(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/auth/setup",
        json={
            "username": "qa_test",
            "password": "test_dummy_password_only",
        },
    )
    assert response.status_code == 201


async def create(client: httpx.AsyncClient, day: int) -> dict[str, Any]:
    response = await client.post(
        "/api/qa-reports",
        json={
            "title": f"Test report {day}",
            "report_date": f"2026-09-{day:02}",
            "author_name": "Tester",
            "items": [
                {
                    "activity_code": f"QA-{day}",
                    "result": "Pass",
                    "environment": "Prod",
                    "current_status": "Passed prod",
                    "current_issue": "*Passed* with `code`",
                    "links": [
                        {
                            "url": f"https://example.test/coverage?activity={day}&source=copy_link",
                            "label": "Coverage",
                        }
                    ],
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


async def test_list_ascending_pagination_and_delete_cascade(client: httpx.AsyncClient) -> None:
    await setup(client)
    reports = [await create(client, day) for day in (3, 1, 2)]
    first = (await client.get("/api/qa-reports?order=asc&page_size=2")).json()
    second = (await client.get("/api/qa-reports?order=asc&page_size=2&page=2")).json()
    assert [report["report_date"] for report in first["reports"]] == ["2026-09-01", "2026-09-02"]
    assert second["reports"][0]["report_date"] == "2026-09-03"
    assert (await client.get("/api/qa-reports?order=invalid")).status_code == 422
    for report in reports:
        path = f"/api/qa-reports/{report['id']}"
        assert (await client.delete(path)).status_code == 422
        assert (await client.delete(path + "?version=99")).status_code == 409
        assert (await client.get(path)).status_code == 200
        edit = {
            "title": report["title"] + " updated in another tab",
            "report_date": report["report_date"],
            "author_name": report["author_name"],
            "version": 1,
            "items": [
                {key: value for key, value in item.items() if key != "sort_order"}
                for item in report["items"]
            ],
        }
        saved = await client.put(path, json=edit)
        assert saved.status_code == 200, saved.text
        assert saved.json()["version"] == 2
        assert (await client.delete(path + "?version=1")).status_code == 409
        assert (await client.get(path)).json()["title"] == edit["title"]
        assert (
            await client.delete(
                path + "?version=2", headers={"Origin": "https://untrusted.example"}
            )
        ).status_code == 403
        assert (await client.delete(path + "?version=2")).status_code == 204
        assert (await client.get(path)).status_code == 404
        assert (await client.delete(path + "?version=1")).status_code == 404
    async with engine.connect() as connection:
        for model in (DailyReport, ReportItem, ReportItemLink):
            assert await connection.scalar(select(func.count()).select_from(model)) == 0
    assert (await client.get("/api/qa-reports/monthly?month=2026-09")).json()["total"] == 0


async def test_backup_roundtrip_skip_existing_preserve_locked_and_all_filters(
    client: httpx.AsyncClient,
) -> None:
    assert (await client.get("/api/qa-reports/backup")).status_code == 401
    assert (await client.post("/api/qa-reports/restore", json={})).status_code == 401
    await setup(client)
    old, current = await create(client, 1), await create(client, 2)
    old_path = f"/api/qa-reports/{old['id']}"
    finalized = (await client.post(old_path + "/finalize", json={"version": 1})).json()
    download = await client.get("/api/qa-reports/backup?search=not-found")
    assert download.status_code == 200
    assert "attachment" in download.headers["content-disposition"]
    assert "no-store" in download.headers["cache-control"]
    data = download.json()
    assert data["format"] == "qa-portal-reports" and data["schema_version"] == 3
    assert len(data["reports"]) == 2
    assert "test_dummy_password_only" not in download.text
    assert set(data) == {"format", "schema_version", "exported_at", "reports", "templates"}
    assert (await client.delete(old_path + f"?version={finalized['version']}")).status_code == 204
    restored = await client.post("/api/qa-reports/restore", json=data)
    assert restored.status_code == 200, restored.text
    assert restored.json() == {"restored": 1, "skipped": 1}
    all_reports = (await client.get("/api/qa-reports?order=asc")).json()["reports"]
    assert all_reports[0]["id"] != old["id"]
    recovered = (await client.get("/api/qa-reports/" + all_reports[0]["id"])).json()
    assert recovered["status"] == "finalized"
    assert recovered["items"][0]["id"] != old["items"][0]["id"]
    assert recovered["items"][0]["links"] == old["items"][0]["links"]
    assert recovered["items"][0]["current_issue"] == old["items"][0]["current_issue"]
    assert (await client.get("/api/qa-reports/" + current["id"])).json() == current
    assert (await client.post("/api/qa-reports/restore", json=data)).json() == {
        "restored": 0,
        "skipped": 2,
    }
    assert (await client.get("/api/auth/status")).json()["authenticated"]


async def test_custom_template_is_reusable_and_snapshotted(client: httpx.AsyncClient) -> None:
    await setup(client)
    template_body = (
        "{{report_title}}\n"
        "{{#activities}}- {{activity_code}} / {{result}} / {{current_status}}\n{{/activities}}"
    )
    created_template = await client.post(
        "/api/qa-reports/templates",
        json={"name": "Standup ringkas", "description": "Untuk standup", "body": template_body},
    )
    assert created_template.status_code == 201, created_template.text
    template = created_template.json()
    assert template["usage_count"] == 0
    invalid = await client.post(
        "/api/qa-reports/templates",
        json={"name": "Invalid", "body": "{{#activities}}{{bad-name}}{{/activities}}"},
    )
    assert invalid.status_code == 422
    report_response = await client.post(
        "/api/qa-reports",
        json={
            "title": "Standup 3",
            "report_date": "2026-09-03",
            "template_id": template["id"],
            "items": [{"activity_code": "QA-3", "result": "Pass"}],
        },
    )
    assert report_response.status_code == 201, report_response.text
    report = report_response.json()
    assert report["template_name"] == "Standup ringkas"
    updated = await client.put(
        f"/api/qa-reports/templates/{template['id']}",
        json={
            "name": "Standup berubah",
            "expected_updated_at": template["updated_at"],
            "body": template_body.replace("/ {{result}}", " / {{environment}}"),
        },
    )
    assert updated.status_code == 200
    stale = await client.put(
        f"/api/qa-reports/templates/{template['id']}",
        json={
            "name": "Stale",
            "body": template_body,
            "expected_updated_at": template["updated_at"],
        },
    )
    assert stale.status_code == 409
    preview = await client.get(f"/api/qa-reports/{report['id']}/preview")
    assert preview.status_code == 200
    assert "/ Pass" in preview.json()["slack"]
    assert "/ Dev" not in preview.json()["slack"]
    assert (await client.get("/api/qa-reports/templates")).json()[0]["usage_count"] == 1
    assert (await client.delete(f"/api/qa-reports/templates/{template['id']}")).status_code == 204
    assert (await client.get(f"/api/qa-reports/{report['id']}/preview")).status_code == 200


async def test_restore_invalid_file_is_atomic_and_size_limited(client: httpx.AsyncClient) -> None:
    await setup(client)
    reports = [await create(client, day) for day in (1, 2)]
    original = (await client.get("/api/qa-reports/backup")).json()
    for report in reports:
        await client.delete(f"/api/qa-reports/{report['id']}?version=1")
    invalid = deepcopy(original)
    invalid["reports"][1]["items"][0]["activity_code"] = ""
    duplicates = deepcopy(original)
    duplicates["reports"][1]["report_date"] = duplicates["reports"][0]["report_date"]
    for body in (
        invalid,
        duplicates,
        {**original, "schema_version": 4},
        {**original, "format": "other"},
        {**original, "password": "test_dummy_do_not_echo"},
    ):
        response = await client.post("/api/qa-reports/restore", json=body)
        assert response.status_code == 422
        assert "test_dummy_do_not_echo" not in response.text
        assert (await client.get("/api/qa-reports")).json()["total"] == 0
    assert (await client.post("/api/qa-reports/restore", content="{bad")).status_code == 422
    assert (
        await client.post("/api/qa-reports/restore", content=b" " * (10 * 1024 * 1024 + 1))
    ).status_code == 413
    assert (await client.post("/api/qa-reports/restore", json=original)).json() == {
        "restored": 2,
        "skipped": 0,
    }


def test_markdown_formats_and_slack_control_character_safety() -> None:
    report = DailyReport(
        title="Daily <report>",
        report_date=date(2026, 9, 1),
        items=[
            ReportItem(
                activity_code="QA-1",
                environment="Dev",
                result="In progress",
                current_status="Retest",
                current_issue="*Bold* and _italic_ with `code` <!channel> & <script>",
                links=[ReportItemLink(url="https://example.test/a?x=1&y=2")],
            )
        ],
    )
    preview = generate_preview(report)
    assert preview.slack_mrkdwn.startswith("*Daily &lt;report&gt;*\nDate: September 1, 2026")
    assert "*Testing Summary:*" in preview.slack_mrkdwn
    assert "*Bold* and _italic_ with `code`" in preview.slack_mrkdwn
    assert "<!channel>" not in preview.slack_mrkdwn
    assert "&lt;!channel&gt;" in preview.slack_mrkdwn
    assert preview.markdown.startswith("# Daily <report>")
    assert "## Testing Summary:" in preview.markdown
    assert "https://example.test/a?x=1&y=2" in preview.markdown
    assert "<script>" not in preview.html
    assert (
        "*Testing Summary:*\n• Activity: QA-1\n  Environment: Dev\n  Result: In progress"
        in preview.slack_mrkdwn
    )
    assert "## Testing Summary:\n\n- Activity: QA-1  \n  Environment: Dev" in preview.markdown
    assert "*Current issues:*\n• QA-1:" in preview.slack_mrkdwn
    assert "*Current Status:*\n• QA-1: Retest" in preview.slack_mrkdwn
    assert "Test Coverage :\n- Activity: QA-1\n  https://example.test/a?x=1&y=2" in preview.slack
