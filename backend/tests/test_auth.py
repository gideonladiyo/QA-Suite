import httpx

from app.core.config import get_settings

CREDENTIALS = {"username": "qa_test", "password": "test_dummy_password_only"}


async def test_setup_login_cookie_logout_and_csrf(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/auth/status")).json()["setup_required"]
    assert (await client.get("/api/qa-reports")).status_code == 401
    rejected = await client.post(
        "/api/auth/setup", json=CREDENTIALS, headers={"Origin": "https://untrusted.example"}
    )
    assert rejected.status_code == 403
    created = await client.post("/api/auth/setup", json=CREDENTIALS)
    assert created.status_code == 201
    cookie = created.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/api" in cookie
    assert (await client.post("/api/auth/setup", json=CREDENTIALS)).status_code == 409
    assert (await client.get("/api/auth/status")).json()["authenticated"]
    old_cookie = client.cookies.get("qa_portal_session")
    assert (await client.post("/api/auth/logout")).status_code == 204
    assert (await client.get("/api/qa-reports")).status_code == 401
    client.cookies.set("qa_portal_session", old_cookie or "")
    assert (await client.get("/api/qa-reports")).status_code == 401
    client.cookies.clear()
    assert (await client.post("/api/auth/login", json=CREDENTIALS)).status_code == 200


async def test_password_validation_redaction_and_lockout(client: httpx.AsyncClient) -> None:
    secret = "tiny"
    response = await client.post("/api/auth/setup", json={"username": "qa", "password": secret})
    assert response.status_code == 422 and secret not in response.text
    await client.post("/api/auth/setup", json=CREDENTIALS)
    await client.post("/api/auth/logout")
    for _ in range(5):
        response = await client.post(
            "/api/auth/login", json={"username": "qa_test", "password": "wrong_test_password"}
        )
        assert response.status_code == 401 and "wrong_test_password" not in response.text
    assert (await client.post("/api/auth/login", json=CREDENTIALS)).status_code == 429


async def test_local_env_bypasses_portal_login(client: httpx.AsyncClient) -> None:
    settings = get_settings()
    previous_env = settings.app_env
    settings.app_env = "local"
    try:
        status = await client.get("/api/auth/status")
        assert status.json() == {
            "setup_required": False,
            "authenticated": True,
            "username": "local",
            "auth_disabled": True,
        }
        assert (await client.get("/api/qa-reports")).status_code == 200
        assert (await client.post("/api/auth/login", json=CREDENTIALS)).status_code == 404
    finally:
        settings.app_env = previous_env
