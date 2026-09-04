import asyncio
import base64
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID

import httpx
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select

from app.core.database import session_factory
from app.core.errors import AppError
from app.modules.micro_utilities import history, service
from app.modules.micro_utilities.models import HttpHistory, HttpSavedRequest
from app.modules.micro_utilities.schemas import HttpRequest, HttpResult, Pair

ROOT = "/api/micro-utilities"
CREDENTIALS = {"username": "micro_test", "password": "test_dummy_password_only"}


async def test_auth_csrf_and_validation(client: httpx.AsyncClient) -> None:
    assert (await client.get(f"{ROOT}/http/history")).status_code == 401
    assert (await client.get(f"{ROOT}/http/collections")).status_code == 401
    assert (await client.get(f"{ROOT}/presets")).status_code == 401
    await client.post("/api/auth/setup", json=CREDENTIALS)
    response = await client.post(
        f"{ROOT}/http/send",
        json={"url": "https://example.test"},
        headers={"Origin": "https://untrusted.example"},
    )
    assert response.status_code == 403
    response = await client.post(
        f"{ROOT}/http/send",
        json={"url": "https://example.test", "token": "DO_NOT_ECHO", "timeout": 900},
    )
    assert response.status_code == 422 and "DO_NOT_ECHO" not in response.text
    response = await client.post(
        f"{ROOT}/presets", json={"name": "bad\x00name", "fields": [{"name": "id", "type": "uuid"}]}
    )
    assert response.status_code == 422


def test_variables_auth_body_and_host() -> None:
    body = HttpRequest(
        method="POST",
        url="https://example.test:8443/{{path}}",
        body='{"value":"{{value}}"}',
        variables=[Pair(key="path", value="items"), Pair(key="value", value="test")],
        headers=[Pair(key="X-Test", value="{{value}}")],
        auth_type="bearer",
        token="{{value}}",
    )
    url, headers, content = service.prepare_request(body)
    assert str(url) == "https://example.test:8443/items"
    assert headers["host"] == "example.test:8443"
    assert headers["authorization"] == "Bearer test" and headers["x-test"] == "test"
    assert content == b'{"value":"test"}' and "cookie" not in headers
    body.auth_type = "basic"
    body.username, body.password = "{{value}}", "password"
    assert service.prepare_request(body)[1]["authorization"] == (
        "Basic " + base64.b64encode(b"test:password").decode()
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"url": "file:///etc/passwd"},
        {"url": "https://user:secret@example.test"},
        {"url": "https://example.test/#fragment"},
        {"url": "https://example.test/{{missing}}"},
        {"headers": [{"key": "Host", "value": "other.test"}]},
        {"headers": [{"key": "X-Test", "value": "x\r\nX-Inject: y"}]},
        {"headers": [{"key": "X-Test", "value": "a"}, {"key": "x-test", "value": "b"}]},
        {"body": "{}"},
        {"method": "POST", "body": "invalid-json"},
        {"auth_type": "bearer", "token": "invalid token"},
    ],
)
def test_invalid_outbound_requests(changes: dict[str, Any]) -> None:
    with pytest.raises(AppError):
        service.prepare_request(
            HttpRequest.model_validate({"url": "https://example.test", **changes})
        )


@pytest.mark.parametrize(
    "address", ["127.0.0.1", "::1", "10.0.0.1", "192.168.1.2", "::ffff:127.0.0.1"]
)
def test_local_requires_explicit_permission(address: str) -> None:
    with pytest.raises(AppError):
        service.validate_address(address, False)
    service.validate_address(address, True)


@pytest.mark.parametrize(
    "address",
    [
        "169.254.169.254",
        "fe80::1",
        "fd00:ec2::254",
        "0.0.0.0",
        "::",
        "224.0.0.1",
        "255.255.255.255",
        "100.100.100.200",
        "2002:7f00:1::",
    ],
)
def test_metadata_reserved_never_allowed(address: str) -> None:
    with pytest.raises(AppError):
        service.validate_address(address, True)


async def test_all_dns_answers_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    lookup = AsyncMock(
        return_value=[(2, 1, 6, "", ("8.8.8.8", 443)), (2, 1, 6, "", ("127.0.0.1", 443))]
    )
    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", lookup)
    with pytest.raises(AppError):
        await service.resolve_target(httpx.URL("https://example.test"), False)


async def test_proxy_pins_ip_sni_host_and_does_not_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[httpx.Request] = []
    real_client = httpx.AsyncClient

    def respond(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            302,
            headers={"location": "https://other.test", "x-test": "yes"},
            content=b"not followed",
        )

    def client(**kwargs: Any) -> httpx.AsyncClient:
        assert kwargs["trust_env"] is False and kwargs["follow_redirects"] is False
        return real_client(**kwargs, transport=httpx.MockTransport(respond))

    monkeypatch.setattr(service, "resolve_target", AsyncMock(return_value="8.8.8.8"))
    monkeypatch.setattr(httpx, "AsyncClient", client)
    result = await service.perform_request(HttpRequest(url="https://example.test/path"))
    assert result.status == 302 and result.body == "not followed"
    assert len(captured) == 1 and captured[0].url.host == "8.8.8.8"
    assert captured[0].headers["host"] == "example.test"
    assert captured[0].extensions["sni_hostname"] == "example.test"
    assert "cookie" not in captured[0].headers and "x-qa-request" not in captured[0].headers


async def test_size_timeout_and_compression(monkeypatch: pytest.MonkeyPatch) -> None:
    real_client = httpx.AsyncClient
    mode = "large"

    def respond(request: httpx.Request) -> httpx.Response:
        if mode == "timeout":
            raise httpx.ReadTimeout("DO_NOT_ECHO_SECRET")
        if mode == "compressed":
            # Empty body avoids decoding inside MockTransport before streaming begins.
            return httpx.Response(200, headers={"content-encoding": "gzip"})
        return httpx.Response(200, content=b"x" * (service.MAX_RESPONSE + 1))

    monkeypatch.setattr(service, "resolve_target", AsyncMock(return_value="8.8.8.8"))
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: real_client(**kw, transport=httpx.MockTransport(respond)),
    )
    request = HttpRequest(url="https://example.test")
    result = await service.perform_request(request)
    assert result.truncated and result.size_bytes == service.MAX_RESPONSE
    mode = "timeout"
    result = await service.perform_request(request)
    assert result.error and "DO_NOT_ECHO_SECRET" not in result.error
    mode = "compressed"
    assert "terkompresi" in (await service.perform_request(request)).error


async def test_encrypted_history_replay_retention_and_delete(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await client.post("/api/auth/setup", json=CREDENTIALS)
    monkeypatch.setattr(
        service,
        "perform_request",
        AsyncMock(return_value=HttpResult(status=200, body="RESPONSE_NOT_STORED")),
    )
    body = {
        "url": "https://example.test/URL_SECRET",
        "token": "TOKEN_SECRET",
        "auth_type": "bearer",
        "history_limit": 2,
    }
    for _ in range(3):
        response = await client.post(f"{ROOT}/http/send", json=body)
        assert response.status_code == 200 and response.json()["history_saved"]
    listing = await client.get(f"{ROOT}/http/history")
    assert len(listing.json()) == 2 and "SECRET" not in listing.text
    identity = listing.json()[0]["id"]
    loaded = await client.get(f"{ROOT}/http/history/{identity}")
    assert loaded.json()["token"] == "TOKEN_SECRET"
    async with session_factory() as db:
        row = await db.get(HttpHistory, UUID(identity))
        assert row and b"SECRET" not in row.request_ciphertext
        assert b"RESPONSE_NOT_STORED" not in row.request_ciphertext
        decrypted = history.cipher().decrypt(
            row.request_nonce, row.request_ciphertext, row.id.bytes
        )
        assert b"TOKEN_SECRET" in decrypted and b"RESPONSE_NOT_STORED" not in decrypted
    monkeypatch.setattr(history, "cipher", lambda: AESGCM(b"x" * 32))
    assert (await client.get(f"{ROOT}/http/history/{identity}")).status_code == 409
    assert (await client.delete(f"{ROOT}/http/history")).status_code == 204
    assert (await client.get(f"{ROOT}/http/history")).json() == []
    assert (await client.get(f"{ROOT}/http/history/{identity}")).status_code == 404


async def test_history_failure_does_not_lose_response(monkeypatch: pytest.MonkeyPatch) -> None:
    from sqlalchemy.exc import SQLAlchemyError

    monkeypatch.setattr(
        service, "perform_request", AsyncMock(return_value=HttpResult(status=201, body="created"))
    )
    monkeypatch.setattr(
        service, "save_history", AsyncMock(side_effect=SQLAlchemyError("db unavailable"))
    )
    db = AsyncMock()
    result = await service.send_request(db, HttpRequest(url="https://example.test"))
    assert result.status == 201 and result.body == "created" and not result.history_saved
    db.rollback.assert_awaited_once()


async def test_encrypted_http_collections_import_export_and_cascade(
    client: httpx.AsyncClient,
) -> None:
    await client.post("/api/auth/setup", json=CREDENTIALS)
    created = await client.post(
        f"{ROOT}/http/collections",
        json={"name": "Payment API", "description": "Request pembayaran"},
    )
    assert created.status_code == 201, created.text
    collection_id = created.json()["id"]
    saved = await client.post(
        f"{ROOT}/http/collections/{collection_id}/requests",
        json={
            "name": "Create payment",
            "request": {
                "method": "POST",
                "url": "https://example.test/URL_SECRET",
                "auth_type": "bearer",
                "token": "TOKEN_SECRET",
                "allow_private": True,
            },
        },
    )
    assert saved.status_code == 201, saved.text
    request_id = saved.json()["id"]
    listing = await client.get(f"{ROOT}/http/collections")
    assert listing.json()[0]["request_count"] == 1 and "SECRET" not in listing.text
    request_listing = await client.get(f"{ROOT}/http/collections/{collection_id}/requests")
    assert request_listing.json()[0]["name"] == "Create payment"
    assert "SECRET" not in request_listing.text
    detail = await client.get(f"{ROOT}/http/collections/{collection_id}/requests/{request_id}")
    assert detail.json()["request"]["token"] == "TOKEN_SECRET"
    assert detail.json()["request"]["allow_private"] is False
    async with session_factory() as db:
        row = await db.get(HttpSavedRequest, UUID(request_id))
        assert row and b"SECRET" not in row.request_ciphertext

    exported = await client.get(f"{ROOT}/http/collections/{collection_id}/export")
    assert exported.status_code == 200
    assert exported.json()["format"] == "qa-portal-http-collection"
    assert exported.json()["collection"]["requests"][0]["request"]["token"] == "TOKEN_SECRET"
    assert (await client.delete(f"{ROOT}/http/collections/{collection_id}")).status_code == 204
    async with session_factory() as db:
        assert await db.get(HttpSavedRequest, UUID(request_id)) is None

    imported = await client.post(f"{ROOT}/http/collections/import", json=exported.json())
    assert imported.status_code == 201, imported.text
    imported_id = imported.json()["id"]
    assert imported.json()["request_count"] == 1
    assert (
        await client.post(f"{ROOT}/http/collections/import", json=exported.json())
    ).status_code == 409
    imported_requests = await client.get(f"{ROOT}/http/collections/{imported_id}/requests")
    assert len(imported_requests.json()) == 1


async def test_presets_validation_unique_and_delete(client: httpx.AsyncClient) -> None:
    await client.post("/api/auth/setup", json=CREDENTIALS)
    body = {"name": "People", "fields": [{"name": "full_name", "type": "full_name"}]}
    response = await client.post(f"{ROOT}/presets", json=body)
    assert response.status_code == 201
    identity = response.json()["id"]
    assert len((await client.get(f"{ROOT}/presets")).json()) == 1
    assert (await client.post(f"{ROOT}/presets", json=body)).status_code == 409
    invalid = {
        "name": "Bad",
        "fields": [{"name": "value", "type": "integer", "minimum": 5, "maximum": 1}],
    }
    assert (await client.post(f"{ROOT}/presets", json=invalid)).status_code == 422
    assert (await client.delete(f"{ROOT}/presets/{identity}")).status_code == 204
    assert (await client.delete(f"{ROOT}/presets/{identity}")).status_code == 404
    async with session_factory() as db:
        assert (await db.scalars(select(HttpHistory))).all() == []
