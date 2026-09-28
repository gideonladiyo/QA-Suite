import httpx
from sqlalchemy import select

from app.core.database import session_factory
from app.modules.vault.models import VaultSecret

PORTAL_CREDENTIALS = {
    "username": "vault_test",
    "password": "test_dummy_portal_password",
}
MASTER = "test_dummy_master_passphrase"


async def authenticate(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/auth/setup", json=PORTAL_CREDENTIALS)
    assert response.status_code == 201


async def setup_vault(client: httpx.AsyncClient) -> str:
    response = await client.post(
        "/api/vault/setup",
        json={"secret": MASTER, "confirmation": MASTER, "auto_lock_minutes": 5},
    )
    assert response.status_code == 201
    token = response.json()["token"]
    assert isinstance(token, str)
    return token


async def test_secret_and_command_crud_stays_encrypted(client: httpx.AsyncClient) -> None:
    await authenticate(client)
    assert (await client.get("/api/vault/status")).json() == {
        "configured": False,
        "unlocked": False,
    }
    token = await setup_vault(client)
    headers = {"X-Vault-Session": token}

    password = {
        "title": "Staging admin",
        "username": "tester@example.test",
        "category": "password",
        "url": "https://example.test/login",
        "value": "TEST_PASSWORD_DO_NOT_STORE_PLAIN",
        "notes": "TEST_NOTE_DO_NOT_STORE_PLAIN",
    }
    command = {
        "title": "Restart worker",
        "username": "",
        "category": "command",
        "url": "",
        "value": "docker compose restart worker_TEST_COMMAND",
        "notes": "Run from project root",
    }
    created_password = await client.post("/api/vault", headers=headers, json=password)
    created_command = await client.post("/api/vault", headers=headers, json=command)
    assert created_password.status_code == created_command.status_code == 201

    listing = await client.get("/api/vault", headers=headers)
    assert listing.status_code == 200 and len(listing.json()) == 2
    assert "DO_NOT_STORE_PLAIN" not in listing.text and "TEST_COMMAND" not in listing.text
    filtered = await client.get(
        "/api/vault?search=Restart&category=command&sort=alphabetical", headers=headers
    )
    assert [entry["title"] for entry in filtered.json()] == ["Restart worker"]
    category_search = await client.get("/api/vault?search=command", headers=headers)
    assert [entry["title"] for entry in category_search.json()] == ["Restart worker"]

    password_id = created_password.json()["id"]
    revealed = await client.post(f"/api/vault/{password_id}/reveal", headers=headers)
    assert revealed.json() == {
        "value": password["value"],
        "notes": password["notes"],
    }
    copied = await client.post(f"/api/vault/{password_id}/copy", headers=headers)
    assert copied.json() == {"value": password["value"]}

    async with session_factory() as db:
        row = await db.scalar(select(VaultSecret).where(VaultSecret.id == password_id))
        assert row is not None
        assert b"DO_NOT_STORE_PLAIN" not in row.value_ciphertext
        assert row.notes_ciphertext and b"DO_NOT_STORE_PLAIN" not in row.notes_ciphertext

    command_id = created_command.json()["id"]
    command["value"] = "docker compose restart api_UPDATED_COMMAND"
    updated = await client.put(f"/api/vault/{command_id}", headers=headers, json=command)
    assert updated.status_code == 200
    detail = await client.post(f"/api/vault/{command_id}/reveal", headers=headers)
    assert detail.json()["value"].endswith("UPDATED_COMMAND")

    assert (await client.delete(f"/api/vault/{password_id}", headers=headers)).status_code == 204
    assert (await client.post("/api/vault/lock", headers=headers)).status_code == 204
    assert (await client.get("/api/vault", headers=headers)).status_code == 423


async def test_master_validation_and_unlock_backoff(client: httpx.AsyncClient) -> None:
    await authenticate(client)
    too_short = await client.post(
        "/api/vault/setup",
        json={"secret": "12345", "confirmation": "12345", "auto_lock_minutes": 5},
    )
    assert too_short.status_code == 422 and "12345" not in too_short.text
    token = await setup_vault(client)
    await client.post("/api/vault/lock", headers={"X-Vault-Session": token})
    for attempt in range(3):
        response = await client.post(
            "/api/vault/unlock",
            json={"secret": "wrong_dummy_master", "auto_lock_minutes": 5},
        )
        assert response.status_code == (429 if attempt == 2 else 403)
        assert "wrong_dummy_master" not in response.text
