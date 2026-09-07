# SYSTEM_ARCHITECTURE.md

**Personal QA & Developer Utilities Portal — Design & Technical Specification**

## 1. High-Level Architecture

A **modular monolith**: one Vue 3 frontend, one FastAPI backend, one PostgreSQL database — deployed together via Docker Compose, run locally under WSL 2. Modularity is enforced at the *code organization* level (see `AGENT_INSTRUCTIONS.md`), not via separate microservices, keeping local ops simple (one `docker compose up`) while keeping the codebase maintainable as features grow.

```
┌─────────────────────────────────────────────────────────────┐
│                        WSL 2 (Ubuntu)                         │
│                                                                 │
│   ┌───────────────┐      ┌───────────────┐      ┌──────────┐  │
│   │   frontend     │      │    backend     │      │    db    │  │
│   │  Vue3 + Vite   │◄────►│   FastAPI      │◄────►│ Postgres │  │
│   │  (Nginx serve  │ HTTP │  (uvicorn)     │ TCP  │    16    │  │
│   │   in prod-like │      │  Modular       │ 5432 │          │  │
│   │   mode)        │      │  Monolith      │      │          │  │
│   └───────────────┘      └───────────────┘      └──────────┘  │
│        :5173/:8080            :8000                :5432       │
│                                                                 │
│                    docker-compose.yml (bridge network)          │
└─────────────────────────────────────────────────────────────┘
                  ▲
                  │ localhost:PORT (via WSL2 <-> Windows networking)
                  │
            Windows Host Browser
```

## 2. Docker Compose Setup

### Implemented runtime (phases 2–3)

The checked-in `docker-compose.yml` is the runnable configuration. Only frontend `127.0.0.1:8080` is published to the host; backend 8000 and PostgreSQL 5432 stay inside the Compose network. The examples below describe the original plan and are not commands to replace that configuration.

Nginx proxies `/api/` to FastAPI on the same origin. Backend starts after the PostgreSQL healthcheck, runs Alembic, then starts one Uvicorn worker. Frontend waits for backend health. PostgreSQL persists in `qa-portal_postgres_data`; stopping Compose without `-v` preserves the data.

Authentication is disabled when `APP_ENV=local`, matching the local-only trusted-user deployment. Other environments use single-user auth: initial setup, PBKDF2-SHA256 password hashing (600,000 iterations), signed HttpOnly SameSite=Strict cookies, server-side revocation, 12-hour sessions, and a persistent one-minute login lock after five failures. Write requests require an allowed Origin and `X-QA-Request: 1`; CORS is not enabled. Host validation restricts local hostnames. The server does not trust a browser claim that a report is editable.

`backend/scripts/init_env.py` generates local app/database secrets once and never overwrites `.env`. Settings construct the SQLAlchemy URL from `POSTGRES_*` with correct credential escaping; a separate `DATABASE_URL` variable is not used in this implementation. Vault/encryption secrets are not initialized before those modules are implemented. Frontend receives no server environment variables. HTTP is restricted to loopback; an HTTPS deployment must enable `COOKIE_SECURE` and review origin/host settings. Do not expose this setup publicly.

Auth and API errors omit submitted values. Request-body logging and Uvicorn access/error traces are disabled in the shipped launch command to avoid leaking future secret payloads; healthchecks provide basic operational status. This is a local deployment baseline, not a complete production observability/security system.

The separate `docker-compose.test.yml` uses `qa_portal_test` on tmpfs with fake credentials, no published ports, and an explicit database-name guard before test cleanup. It never reads the user's `.env`.

Micro Utilities stays inside the same modular monolith: `/api/micro-utilities` mounts a session-protected router for HTTP send/history, HTTP collections, and dummy presets. Migration `0002_micro_tools` adds history/preset tables; migration `0005_http_collections` adds collection metadata and encrypted saved requests. The proxy validates resolved addresses, pins the connection IP while retaining original Host/TLS SNI, requires explicit permission for local/LAN targets, disables redirects/environment proxies, applies a total timeout, and limits text responses to 2 MB. Gzip or other compressed bodies are refused even if a target ignores the requested identity encoding. Only explicitly entered request headers are forwarded; portal session headers/cookies are never inherited.

HTTP request history and saved collection requests are AES-256-GCM encrypted with an HKDF-derived APP_SECRET_KEY, per-row random nonce and UUID AAD. Collection/request names, methods, counts, and timestamps remain plaintext metadata so tables can be listed without decryption. Response bodies stay in browser memory. Local/LAN permission is always reset before a saved request is loaded or persisted. Retention and collection count checks use transaction advisory locks in this single-user app. Database backup alone cannot restore encrypted HTTP data without the original app key; QA JSON backups remain QA-only. Collection export intentionally decrypts one authenticated collection into a versioned JSON document, so the downloaded file must be protected as sensitive data; import never overwrites an existing collection.

JSON/YAML conversion and dummy generation run in a cancellable browser worker (30-second ceiling). Faker's English locale is lazy-loaded only for generation. JSON input has a 2 MB, 100k-value, depth-64 budget; the tree renders a window of rows. Base64/JWT decoding and explicit Web Crypto signature verification run only in the browser. Pinia retains input in session memory across tool navigation, clears it on explicit logout, and never persists token/key/payload to web storage. All four views share existing UI components, ToolLayout, and route/command navigation.

### 2.1 Services

| Service | Image/Build | Purpose | Exposed Port (host) |
|---|---|---|---|
| `frontend` | build from `./frontend/Dockerfile` | Vue app (Vite dev server in dev, Nginx static serve in prod-like mode) | `5173` (dev) / `8080` (prod-like) |
| `backend` | build from `./backend/Dockerfile` | FastAPI app served via `uvicorn`/`gunicorn` | `8000` |
| `db` | `postgres:16-alpine` | Primary data store | `5432` |
| `adminer` *(optional dev-only)* | `adminer` | Lightweight DB browser for the portal's own DB during development | `8081` |

### 2.2 Example `docker-compose.yml` Structure (annotated, not literal file)

```yaml
services:
  db:
    image: postgres:16-alpine
    env_file: .env
    volumes:
      - portal_db_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./backend:/app        # dev-time hot reload
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend
    env_file: .env
    depends_on:
      - backend
    volumes:
      - ./frontend:/app       # dev-time hot reload
    ports:
      - "5173:5173"

volumes:
  portal_db_data:
    driver: local
```

### 2.3 Volumes
- `portal_db_data`: named volume persisting Postgres data across container restarts/rebuilds. **This is the single most important volume** — losing it means losing all daily reports, vault secrets, and Supabase configs.
- Bind mounts (`./backend:/app`, `./frontend:/app`) are used only in dev mode for hot reload; a production-like build stage should COPY source instead of bind-mounting, to match how the app would run if ever deployed beyond local use.

### 2.4 WSL 2 Considerations
- Docker Desktop (or native Docker Engine inside WSL 2) should have the project files living **inside the WSL filesystem** (e.g., `~/projects/qa-portal`), not on the Windows-mounted `/mnt/c/...` path — this avoids the well-known severe file I/O performance penalty of cross-filesystem bind mounts.
- `.env` and any local-only override files should be `.gitignore`d as per `AGENT_INSTRUCTIONS.md §5`.
- If accessing the app from Windows browser via `localhost`, standard WSL2 port-forwarding applies automatically for Docker Desktop; no manual `netsh portproxy` setup should be needed in the common case.

## 3. Frontend UI/UX Layout

### 3.1 Shell Layout
```
┌────────────────────────────────────────────────────────────┐
│  Top Bar: [Logo] [Active Supabase Connection Badge] [⌘K]     │
├───────────┬────────────────────────────────────────────────┤
│  Sidebar  │                Main Content Area                 │
│           │                                                    │
│ ▸ Dashboard│   (module views render here based on route)      │
│ ▸ QA Reports│                                                  │
│ ▸ Micro Tools│                                                 │
│   • HTTP Client                                                │
│   • JSONizer                                                   │
│   • Dummy Data                                                 │
│   • Base64/JWT                                                 │
│ ▸ Supabase Hub│                                                │
│ ▸ Vault 🔒│                                                     │
│ ▸ Settings│                                                    │
└───────────┴────────────────────────────────────────────────┘
```

- **Sidebar navigation:** collapsible, top-level entries per module (matches the module folder structure in `AGENT_INSTRUCTIONS.md`). The Vault entry always shows a lock icon reflecting current lock state (locked/unlocked) at a glance.
- **Command Palette (⌘K / Ctrl+K):** global fuzzy-search launcher — jumps to any module, any sub-tool (e.g., typing "jwt" opens the JWT decoder directly), or any recent QA report/history item. Built as a shared component (`shared/components/CommandPalette.vue`) so every module can register searchable actions into it.
- **Dashboard (home view):** a landing page summarizing: today's QA report status (draft/not started/sent), quick links to the 4 micro-tools, active Supabase connection, and a Vault lock-status widget. Not a deep analytics page — the QA module's own Monthly Metrics Dashboard (see `PRD_QA_REPORT_ENGINE.md`) is the place for testing analytics.

### 3.2 Design Principles
- Keyboard-first: every primary action (new report, new secret, switch connection) has a shortcut surfaced in the Command Palette.
- Dense, utilitarian layout appropriate for a power-user internal tool — favor information density over marketing-site whitespace, while keeping WCAG-reasonable contrast and spacing for daily-use readability.
- Consistent "danger zone" pattern (red, confirmation modal) reused across all destructive actions (delete secret, delete connection, delete report).

## 4. Backend Architecture

### 4.1 Modular Monolith Structure
As detailed in `AGENT_INSTRUCTIONS.md §3.1` — each module (`qa_reports`, `micro_utilities`, `supabase_hub`, `vault`) is a self-contained package under `app/modules/`, each exposing its own `APIRouter`, mounted in `main.py`:

```python
# app/main.py (conceptual)
app = FastAPI(title="QA & Dev Utilities Portal")

app.include_router(qa_reports.router)
app.include_router(micro_utilities.router)
app.include_router(supabase_hub.router)
app.include_router(vault.router)
```

Shared cross-cutting concerns (DB session management, auth/session middleware, structured logging, config loading) live in `app/core/` and are the *only* thing modules are allowed to depend on outside themselves.

### 4.2 Request Lifecycle (typical)
```
Frontend (Vue) → REST call (JSON) → FastAPI router (module)
   → Pydantic schema validation
   → service.py (business logic)
   → SQLAlchemy async session (app/core/database.py)
   → PostgreSQL
   ← response mapped back through Pydantic response schema
   ← JSON → Frontend
```

### 4.3 Encryption / Decryption Flow (Vault & Supabase Hub)

Both the Vault and Supabase Hub modules use the same underlying `core` encryption utility (`app/core/security.py`) but with different key-derivation entry points, since Vault is protected by a user PIN and Supabase Hub is protected by the app-level `ENCRYPTION_KEY`.

**Shared primitive:** AES-256-GCM via Python's `cryptography` library.

```
Plaintext secret
      │
      ▼
[AES-256-GCM Encrypt] ── uses 32-byte key + random 12-byte nonce
      │
      ▼
Ciphertext + Nonce + Auth Tag  ──► stored in Postgres (bytea/text columns)
```

**Key sourcing differs per module:**

| Module | Key Source | Key Lifetime |
|---|---|---|
| `supabase_hub` | Derived once from `ENCRYPTION_KEY` env var at backend startup, held in an app-level singleton in memory | Lives as long as the backend process is running |
| `vault` | Derived per-unlock from the user's Master PIN/passphrase (Argon2id + `VAULT_PIN_HASH_SALT`) | Lives only for the unlocked session; discarded on lock/timeout/restart |

**Decrypt flow (both modules), conceptually:**
```python
def decrypt(ciphertext: bytes, nonce: bytes, key: bytes) -> str:
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
    return plaintext.decode()
```
- Decrypted values are used **in-process only** for the immediate purpose (e.g., making an outbound Supabase call, or returning a copy-to-clipboard payload over the already-authenticated local session) and are never written back to disk or included in logs.
- All decrypt calls pass through a thin wrapper that emits an audit log entry (who/what/when) without the decrypted value itself, per `AGENT_INSTRUCTIONS.md §5`.

### 4.4 Auth Model
- Single-user (or small trusted multi-user) local session auth: login issues a signed session cookie (or JWT stored httpOnly) scoped to `localhost`.
- The Vault's unlock state is a **separate, second-factor session layer** on top of the base app session — being logged into the portal does not imply the Vault is unlocked.

## 5. Cross-Module Interaction Rules
- Modules communicate only through explicit service-layer function calls within the backend, never by directly querying another module's tables.
- The frontend never assumes another module's data shape is "close enough" to reuse — each module exposes its own typed API contract.
- Only `supabase_hub` and `vault` touch the shared encryption utility in `app/core/security.py`; no other module should read or write encrypted columns.

## 6. Deployment/Runtime Notes
- This system is designed for **local-only use**. If ever exposed beyond `localhost` (e.g., accessed from another device on a home network), HTTPS termination (self-signed cert or a local reverse proxy like Caddy) and stronger auth (beyond a simple local session) should be added before doing so — this is called out explicitly rather than assumed, since the Vault and Supabase Hub modules increase the stakes of casual network exposure.
- Backups: since all state lives in the `portal_db_data` volume, a periodic `pg_dump` (manual or cron'd inside WSL) is the recommended backup strategy; encrypted columns remain encrypted in the dump, so the dump alone is not sufficient to recover secrets without the corresponding key material.
