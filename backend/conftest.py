from collections.abc import AsyncIterator

import httpx
import pytest_asyncio
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine
from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    # This fixture can only mutate the disposable test DB configured by compose.test.
    if get_settings().postgres_db != "qa_portal_test":
        raise RuntimeError("Tests require the isolated qa_portal_test database")
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE http_saved_requests, http_collections, http_client_history, "
                "dummy_data_presets, local_sessions, local_account, report_item_links, "
                "report_items, daily_reports, report_templates CASCADE"
            )
        )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        headers={"Origin": "http://testserver", "X-QA-Request": "1"},
    ) as value:
        yield value
    await engine.dispose()
