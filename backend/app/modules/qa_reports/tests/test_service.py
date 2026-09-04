from datetime import date

import httpx
import pytest

from app.core.errors import AppError
from app.modules.qa_reports.models import DailyReport, ReportItem, ReportItemLink
from app.modules.qa_reports.service import csv_cell, generate_preview, month_bounds


async def test_daily_input_save_reload_and_exact_export(client: httpx.AsyncClient) -> None:
    await client.post(
        "/api/auth/setup", json={"username": "qa_test", "password": "test_dummy_password_only"}
    )
    codes = ["AMTSK-166", "OIBTSK-66", "OIBTSK-59", "OIBTSK-65"]
    urls = [
        "https://docs.google.com/document/d/1VSvZicZadMa9oFHPVkkPcPsYsEHBmL98OLzYe9s4b5c/edit?tab=t.0",
        "https://example.test/Slack-integration?bot_conversation_agent_id=66",
        "https://example.test/RAG-bot-feedback?v=59&source=copy_link",
        "https://example.test/Knowledge-Base-Data-Source?source=copy_link",
    ]
    body = {
        "title": "Gideon Daily QA Report",
        "report_date": "2026-09-01",
        "author_name": "Gideon",
        "items": [
            {
                "activity_code": code,
                "environment": "Dev" if code == "OIBTSK-66" else "Prod",
                "result": "In progress" if index == 0 else "Pass",
                "current_status": "In progress" if index == 0 else "Passed prod",
                "current_issue": (
                    "Some results from API are stuck in `in progress` status"
                    if index == 0
                    else "Passed on production"
                ),
                "links": [{"url": urls[index]}],
            }
            for index, code in enumerate(codes)
        ],
    }
    created = await client.post("/api/qa-reports", json=body)
    assert created.status_code == 201, created.text
    report = created.json()
    assert report["version"] == 1 and report["status"] == "draft"
    path = f"/api/qa-reports/{report['id']}"
    reloaded = (await client.get(path)).json()
    assert [item["activity_code"] for item in reloaded["items"]] == codes
    assert [item["links"][0]["url"] for item in reloaded["items"]] == urls
    assert reloaded["items"][1]["current_status"] == "Passed prod"
    preview = (await client.get(path + "/preview")).json()
    expected = f"""Gideon Daily QA Report
Date: September 1, 2026

Testing Summary:
- Activity: AMTSK-166
  Environment: Prod
  Result: In progress
- Activity: OIBTSK-66
  Environment: Dev
  Result: Pass
- Activity: OIBTSK-59
  Environment: Prod
  Result: Pass
- Activity: OIBTSK-65
  Environment: Prod
  Result: Pass

Test Coverage :
- Activity: AMTSK-166
  {urls[0]}
- Activity: OIBTSK-66
  {urls[1]}
- Activity: OIBTSK-59
  {urls[2]}
- Activity: OIBTSK-65
  {urls[3]}

Current issues:
- AMTSK-166: Some results from API are stuck in `in progress` status
- OIBTSK-66: Passed on production
- OIBTSK-59: Passed on production
- OIBTSK-65: Passed on production

Current Status:
- AMTSK-166: In progress
- OIBTSK-66: Passed prod
- OIBTSK-59: Passed prod
- OIBTSK-65: Passed prod"""
    assert preview["slack"] == expected
    assert (await client.get(path)).json() == reloaded  # Export never locks or changes the report.
    duplicate = await client.post("/api/qa-reports", json={**body, "title": "Do not overwrite"})
    assert duplicate.status_code == 409 and duplicate.json()["existing_id"] == report["id"]
    assert (await client.get(path)).json() == reloaded
    filtered = (await client.get("/api/qa-reports?start=2026-09-01&end=2026-09-01")).json()
    assert filtered["total"] == 1 and filtered["reports"][0]["item_count"] == 4


async def test_invalid_create_never_leaves_an_empty_report(client: httpx.AsyncClient) -> None:
    from uuid import uuid4

    await client.post(
        "/api/auth/setup", json={"username": "qa_test", "password": "test_dummy_password_only"}
    )
    valid = {"activity_code": "QA-1", "result": "Pass"}
    metadata = {"report_date": "2026-09-01", "title": "QA"}
    for invalid in ({"activity_code": "", "result": "Pass"}, {**valid, "id": str(uuid4())}):
        rejected = await client.post(
            "/api/qa-reports", json={**metadata, "items": [valid, invalid]}
        )
        assert rejected.status_code == 422
        assert (await client.get("/api/qa-reports")).json()["total"] == 0
    created = await client.post("/api/qa-reports", json={**metadata, "items": [valid]})
    assert created.status_code == 201
    assert created.json()["items"][0]["current_status"] == "Pass"


async def finalized_fixture(client: httpx.AsyncClient) -> str:
    await client.post(
        "/api/auth/setup", json={"username": "qa_test", "password": "test_dummy_password_only"}
    )
    metadata = {"report_date": "2026-09-02", "title": "Test QA"}
    report = (await client.post("/api/qa-reports", json=metadata)).json()
    path = f"/api/qa-reports/{report['id']}"
    await client.put(
        path,
        json={**metadata, "version": 1, "items": [{"activity_code": "QA-17", "result": "Pass"}]},
    )
    await client.post(path + "/finalize", json={"version": 2})
    return path


async def test_mocked_delivery_success_duplicate_and_failure(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import AsyncMock, Mock

    from pydantic import SecretStr

    from app.core.config import get_settings
    from app.modules.qa_reports import delivery

    path = await finalized_fixture(client)
    settings = get_settings()
    monkeypatch.setattr(
        settings,
        "slack_webhook_url",
        SecretStr("https://hooks.slack.com/services/test_dummy_webhook"),
    )
    post = AsyncMock(
        return_value=httpx.Response(
            200,
            text="ok",
            request=httpx.Request("POST", "https://hooks.slack.com/services/test_dummy_webhook"),
        )
    )
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post = post
    monkeypatch.setattr(httpx, "AsyncClient", Mock(return_value=mock_client))
    sent = await client.post(path + "/send", json={"version": 3, "channel": "slack"})
    assert sent.status_code == 200 and sent.json()["status"] == "sent"
    assert sent.json()["slack_sent_at"] is not None
    duplicate = await client.post(path + "/send", json={"version": 4, "channel": "slack"})
    assert duplicate.status_code == 409 and post.await_count == 1
    monkeypatch.setattr(settings, "smtp_host", "test.invalid")
    monkeypatch.setattr(settings, "smtp_from", "test@example.com")
    mock_email = Mock(side_effect=OSError("test_dummy_transport_error"))
    monkeypatch.setattr(delivery, "send_email", mock_email)
    body = {"version": 4, "channel": "email", "recipient": "tester@example.com"}
    failed = await client.post(path + "/send", json=body)
    assert failed.status_code == 502 and "test_dummy_transport_error" not in failed.text
    unchanged = (await client.get(path)).json()
    assert unchanged["version"] == 4 and unchanged["email_sent_at"] is None
    mock_email.side_effect = None
    emailed = await client.post(path + "/send", json=body)
    assert emailed.status_code == 200 and emailed.json()["email_sent_at"] is not None


async def test_item_identity_and_atomic_concurrent_save(client: httpx.AsyncClient) -> None:
    import asyncio

    await client.post(
        "/api/auth/setup", json={"username": "qa_test", "password": "test_dummy_password_only"}
    )
    metadata = {"report_date": "2026-09-02", "title": "Test QA"}
    report = (await client.post("/api/qa-reports", json=metadata)).json()
    path = f"/api/qa-reports/{report['id']}"
    body = {**metadata, "version": 1, "items": [{"activity_code": "QA-17", "result": "Pass"}]}
    responses = await asyncio.gather(client.put(path, json=body), client.put(path, json=body))
    assert sorted(response.status_code for response in responses) == [200, 409]
    saved = (await client.get(path)).json()
    item_id = saved["items"][0]["id"]
    edited = await client.put(
        path,
        json={
            **metadata,
            "version": 2,
            "items": [
                {
                    "id": item_id,
                    "activity_code": "QA-17",
                    "environment": "Sandbox",
                    "result": "Retest",
                }
            ],
        },
    )
    assert edited.json()["items"][0]["id"] == item_id
    metrics = (await client.get("/api/qa-reports/monthly?month=2026-09")).json()
    assert metrics["results"] == [{"label": "Retest", "count": 1}]
    assert metrics["pass_rate"] == 0


def test_preview_escapes_html_omits_empty_sections_and_preserves_custom_results() -> None:
    report = DailyReport(
        title="Tester Daily QA Report",
        report_date=date(2026, 9, 2),
        items=[
            ReportItem(
                activity_code="<script>test</script>",
                environment="Sandbox",
                result="Retest",
                current_status="Retest",
                current_issue=None,
                links=[ReportItemLink(url="javascript:alert(1)")],
            )
        ],
    )
    preview = generate_preview(report)
    assert "Current issues:" not in preview.slack
    assert "Environment: Sandbox" in preview.slack
    assert "<script>" not in preview.html
    assert "&lt;script&gt;" in preview.html
    assert '<a href="javascript:' not in preview.html
    report.items = []
    with pytest.raises(AppError):
        generate_preview(report)


def test_month_bounds_and_csv_formula_safety() -> None:
    assert month_bounds("2024-02") == (date(2024, 2, 1), date(2024, 2, 29))
    for month in ("2026-13", "0000-01", "not-a-month"):
        with pytest.raises(AppError):
            month_bounds(month)
    assert csv_cell("=HYPERLINK(test)").startswith("'")
    assert csv_cell("  @SUM(1)").startswith("'")
    assert csv_cell("QA-17") == "QA-17"


async def test_report_workflow_conflict_filters_metrics_and_lock(client: httpx.AsyncClient) -> None:
    await client.post(
        "/api/auth/setup", json={"username": "qa_test", "password": "test_dummy_password_only"}
    )
    metadata = {"report_date": "2026-09-02", "title": "QA Daily Report", "author_name": "Tester"}
    created = await client.post("/api/qa-reports", json=metadata)
    assert created.status_code == 201, created.text
    report = created.json()
    path = f"/api/qa-reports/{report['id']}"
    duplicate = await client.post("/api/qa-reports", json=metadata)
    assert duplicate.status_code == 409 and duplicate.json()["existing_id"] == report["id"]
    assert (await client.get(path + "/preview")).status_code == 422
    assert (await client.post(path + "/finalize", json={"version": 1})).status_code == 422
    item = {
        "activity_code": "QA-17",
        "environment": "Dev",
        "result": "Pass",
        "links": [{"url": "not a valid URL"}, {"url": "https://example.test/coverage"}],
    }
    body = {
        **metadata,
        "version": 1,
        "items": [item, {**item, "result": "Fail", "current_issue": "Example issue"}],
    }
    saved = await client.put(path, json=body)
    assert saved.status_code == 200, saved.text
    report = saved.json()
    assert report["version"] == 2 and report["items"][0]["current_status"] == "Pass"
    assert len(report["items"][0]["links"]) == 2
    assert (await client.put(path, json=body)).status_code == 409
    filtered = await client.get("/api/qa-reports?search=QA-17&result=Fail&environment=Dev")
    assert filtered.json()["total"] == 1
    assert (await client.get("/api/qa-reports?search=not-found")).json()["total"] == 0
    metrics = (await client.get("/api/qa-reports/monthly?month=2026-09")).json()
    assert metrics["total"] == 2 and metrics["pass_rate"] == 50
    assert metrics["issue_count"] == 1 and metrics["repeated_entries"] == 1
    assert len(metrics["trend"]) == 30 and metrics["trend"][1]["count"] == 2
    assert (await client.get("/api/qa-reports/monthly?month=2026-13")).status_code == 422
    exported = await client.get("/api/qa-reports/monthly.csv?month=2026-09")
    assert exported.status_code == 200 and "QA-17" in exported.text
    preview = await client.get(path + "/preview")
    assert preview.status_code == 200 and "Current issues:" in preview.json()["slack"]
    finalized = await client.post(path + "/finalize", json={"version": 2})
    assert finalized.json()["status"] == "finalized"
    assert (await client.put(path, json={**body, "version": 3})).status_code == 409
    assert (
        await client.post(path + "/send", json={"version": 3, "channel": "slack"})
    ).status_code == 422


async def test_metadata_conflict_item_ownership_and_delete(client: httpx.AsyncClient) -> None:
    await client.post(
        "/api/auth/setup", json={"username": "qa_test", "password": "test_dummy_password_only"}
    )
    reports = []
    for day in (1, 2):
        reports.append(
            (
                await client.post(
                    "/api/qa-reports", json={"report_date": f"2026-09-0{day}", "title": "QA"}
                )
            ).json()
        )
    path = f"/api/qa-reports/{reports[0]['id']}"
    metadata = {"title": "QA", "report_date": "2026-09-01", "version": 1, "items": []}
    conflict = await client.put(path, json={**metadata, "report_date": "2026-09-02"})
    assert conflict.status_code == 409 and conflict.json()["existing_id"] == reports[1]["id"]
    invalid = await client.put(
        path,
        json={
            **metadata,
            "items": [{"id": reports[1]["id"], "activity_code": "QA-1", "result": "Pass"}],
        },
    )
    assert invalid.status_code == 422
    saved = (
        await client.put(
            path, json={**metadata, "items": [{"activity_code": "QA-1", "result": "Pass"}]}
        )
    ).json()
    assert saved["items"][0]["environment"] == "Dev"
    deleted = await client.put(path, json={**metadata, "version": 2})
    assert deleted.status_code == 200 and deleted.json()["items"] == []
