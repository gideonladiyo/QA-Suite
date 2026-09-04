import asyncio
import base64
import ipaddress
import json
import re
import socket
from time import perf_counter
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.micro_utilities.history import save_history
from app.modules.micro_utilities.models import DummyPreset
from app.modules.micro_utilities.schemas import (
    DummyField,
    HttpRequest,
    HttpResult,
    Pair,
    PresetInput,
    PresetOutput,
)

MAX_RESPONSE = 2 * 1024 * 1024
BLOCKED_HEADERS = {
    "host",
    "content-length",
    "transfer-encoding",
    "connection",
    "upgrade",
    "proxy-authorization",
    "proxy-connection",
    "te",
    "trailer",
    "x-qa-request",
}


def substitute(value: str, variables: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        if match[1] not in variables:
            raise AppError(422, "Ada variabel {{nama}} yang belum diisi.")
        return variables[match[1]]

    return re.sub(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}", replace, value)


def prepare_request(body: HttpRequest) -> tuple[httpx.URL, dict[str, str], bytes]:
    variables = {entry.key: entry.value for entry in body.variables if entry.key}
    if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) for name in variables):
        raise AppError(422, "Nama variabel harus berupa huruf, angka, atau underscore.")
    if len(variables) != len([entry for entry in body.variables if entry.key]):
        raise AppError(422, "Nama variabel tidak boleh duplikat.")
    try:
        url = httpx.URL(substitute(body.url.strip(), variables))
    except httpx.InvalidURL:
        raise AppError(422, "URL tidak valid.") from None
    if (
        url.scheme not in {"http", "https"}
        or not url.host
        or url.userinfo
        or url.fragment
        or len(str(url)) > 8192
    ):
        raise AppError(
            422,
            "Gunakan URL HTTP(S) tanpa username, password, atau fragmen. "
            "Gunakan kolom autentikasi.",
        )
    headers: dict[str, str] = {}
    for entry in body.headers:
        if not entry.key.strip():
            continue
        name, value = entry.key.strip().lower(), substitute(entry.value, variables)
        if name in BLOCKED_HEADERS or not re.fullmatch(r"[!#$%&'*+.^_`|~0-9a-z-]+", name):
            raise AppError(422, "Nama header tidak valid atau dikelola oleh HTTP Client.")
        if any(ord(char) < 32 or ord(char) > 126 for char in value):
            raise AppError(422, "Header harus berupa teks ASCII satu baris.")
        if name in headers:
            raise AppError(422, "Nama header tidak boleh duplikat.")
        headers[name] = value
    if body.auth_type == "bearer":
        token = substitute(body.token, variables)
        if not token or any(ord(c) <= 32 or ord(c) > 126 for c in token):
            raise AppError(422, "Bearer token harus diisi dalam satu baris tanpa spasi.")
        headers["authorization"] = f"Bearer {token}"
    elif body.auth_type == "basic":
        username, password = (
            substitute(body.username, variables),
            substitute(body.password, variables),
        )
        if ":" in username:
            raise AppError(422, "Username Basic Auth tidak boleh mengandung titik dua.")
        credentials = f"{username}:{password}".encode()
        headers["authorization"] = "Basic " + base64.b64encode(credentials).decode()
    content = substitute(body.body, variables).encode()
    if body.method == "GET" and content:
        raise AppError(422, "GET tidak memakai body. Kosongkan body atau pilih method lain.")
    if len(content) > 1024 * 1024:
        raise AppError(413, "Body request maksimal 1 MB setelah substitusi.")
    if content and body.body_type == "json":
        try:
            json.loads(content)
        except (ValueError, RecursionError):
            raise AppError(422, "Body JSON tidak valid.") from None
    if content:
        headers.setdefault(
            "content-type",
            {
                "json": "application/json",
                "form": "application/x-www-form-urlencoded",
                "text": "text/plain;charset=utf-8",
            }[body.body_type],
        )
    # Do not inherit proxy settings, cookie jars, portal headers, or redirect credentials.
    headers["host"] = url.netloc.decode()
    headers["accept-encoding"] = "identity"
    return url, headers, content


def validate_address(value: str, allow_private: bool) -> None:
    if "%" in value:
        raise AppError(422, "Alamat scoped/metadata ditolak.")
    address = ipaddress.ip_address(value)
    if address == ipaddress.ip_address("fd00:ec2::254"):
        raise AppError(422, "Alamat metadata ditolak.")
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped:
            address = address.ipv4_mapped
        elif address.sixtofour or address.teredo:
            raise AppError(422, "Alamat transisi IPv6 tidak didukung.")
    if (
        address.is_link_local
        or address.is_multicast
        or address.is_unspecified
        or (address.is_reserved and not address.is_loopback)
    ):
        raise AppError(422, "Alamat metadata/link-local, multicast, dan reserved ditolak.")
    if not address.is_global and not (
        allow_private and (address.is_private or address.is_loopback)
    ):
        raise AppError(
            422, "Alamat lokal/LAN ditolak. Aktifkan izin lokal hanya untuk endpoint milikmu."
        )


async def resolve_target(url: httpx.URL, allow_private: bool) -> str:
    # Validate every DNS answer, then connect to that exact IP: no second DNS lookup/rebinding.
    results = await asyncio.get_running_loop().getaddrinfo(
        url.host, url.port or (443 if url.scheme == "https" else 80), type=socket.SOCK_STREAM
    )
    addresses = list(dict.fromkeys(str(row[4][0]) for row in results))
    if not addresses:
        raise OSError("DNS lookup failed")
    for address in addresses:
        validate_address(address, allow_private)
    return addresses[0]


async def perform_request(body: HttpRequest) -> HttpResult:
    url, headers, content = prepare_request(body)
    started = perf_counter()
    result = HttpResult()
    try:
        async with asyncio.timeout(body.timeout):
            address = await resolve_target(url, body.allow_private)
            async with httpx.AsyncClient(
                timeout=body.timeout, follow_redirects=False, trust_env=False
            ) as client:
                async with client.stream(
                    body.method,
                    url.copy_with(host=address),
                    headers=headers,
                    content=content,
                    extensions={"sni_hostname": url.host},
                ) as response:
                    result.status = response.status_code
                    result.headers = [
                        Pair(key=key[:200], value=value[:10000])
                        for key, value in response.headers.multi_items()
                    ][:200]
                    if response.headers.get("content-encoding", "identity").lower() != "identity":
                        result.error = (
                            "Endpoint mengabaikan Accept-Encoding: identity. "
                            "Body terkompresi tidak dibaca demi batas memori yang aman."
                        )
                        result.elapsed_ms = round((perf_counter() - started) * 1000)
                        return result
                    parts = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        remaining = MAX_RESPONSE - len(parts)
                        parts.extend(chunk[:remaining])
                        if len(chunk) > remaining:
                            result.truncated = True
                            break
                    result.size_bytes = len(parts)
                    result.body = bytes(parts).decode("utf-8", errors="replace")
    except (TimeoutError, httpx.TimeoutException):
        result.error = (
            "Request melewati batas waktu. Endpoint mungkin sudah memprosesnya; "
            "jangan kirim ulang otomatis."
        )
    except (httpx.HTTPError, OSError):
        result.error = (
            "Endpoint tidak dapat dijangkau atau koneksi/TLS gagal. Periksa URL dan jaringan."
        )
    result.elapsed_ms = round((perf_counter() - started) * 1000)
    return result


async def send_request(db: AsyncSession, body: HttpRequest) -> HttpResult:
    result = await perform_request(body)
    try:
        await save_history(db, body, result)
        result.history_saved = True
    except SQLAlchemyError:
        await db.rollback()
        # A target request may have succeeded: return its response even if history failed.
    return result


async def presets(db: AsyncSession) -> list[PresetOutput]:
    rows = await db.scalars(select(DummyPreset).order_by(DummyPreset.name).limit(100))
    return [
        PresetOutput(
            id=row.id,
            name=row.name,
            fields=[DummyField.model_validate(field) for field in row.schema_json],
        )
        for row in rows
    ]


async def create_preset(db: AsyncSession, body: PresetInput) -> PresetOutput:
    await db.execute(select(func.pg_advisory_xact_lock(731002)))
    if (await db.scalar(select(func.count()).select_from(DummyPreset)) or 0) >= 100:
        raise AppError(422, "Maksimal 100 preset. Hapus preset yang tidak dipakai.")
    row = DummyPreset(
        name=body.name.strip(), schema_json=[field.model_dump(mode="json") for field in body.fields]
    )
    db.add(row)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError(
            409, "Nama preset sudah ada. Gunakan nama lain; preset lama tidak ditimpa."
        ) from None
    return PresetOutput(id=row.id, name=row.name, fields=body.fields)


async def delete_preset(db: AsyncSession, identity: UUID) -> None:
    row = await db.get(DummyPreset, identity)
    if row is None:
        raise AppError(404, "Preset tidak ditemukan.")
    await db.delete(row)
    await db.commit()
