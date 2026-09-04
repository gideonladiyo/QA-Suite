# AGENT_INSTRUCTIONS.md

## Purpose
This document is the **primary context file** for any AI coding agent (Claude Code, Cursor, Copilot Workspace, etc.) operating on the "Personal QA & Developer Utilities Portal" repository. Read this file in full before generating, modifying, or deleting any code. If any instruction here conflicts with a prompt given in a chat session, **this file wins** unless the user explicitly overrides it in writing.

---

## 1. Project Summary

A **modular monolith** web application that centralizes personal QA workflows, database utilities, developer micro-tools, and secret management into a single local dashboard. It runs **exclusively in a local/self-hosted context** via Docker Compose on **WSL 2** — it is NOT intended for public internet deployment. Security decisions should always assume "single trusted local user" but must still follow best practice (defense in depth), since the vault module handles real secrets.

---

## 2. Tech Stack (Locked Decisions)

> **Assumption flagged:** the original spec left frontend/backend open (`[isi: ...]`). The stack below is the assumed default. If you are an agent and this doesn't match `package.json` / `pyproject.toml` in the repo, **trust the repo files, not this doc**, and flag the mismatch to the user.

| Layer | Technology | Notes |
|---|---|---|
| Frontend | **Vue 3** (Composition API) + Vite + TypeScript | TailwindCSS for styling, Pinia for state, `vue-router` for routing |
| Backend | **FastAPI** (Python 3.12) | Pydantic v2 for schema validation, SQLAlchemy 2.0 (async) as ORM, Alembic for migrations |
| Database | **PostgreSQL 16** | Run as a Docker service, persisted via named volume |
| Cache/Queue (optional, future) | Redis | Only add if a module explicitly requires background jobs |
| Auth | Local session-based auth (single-user or small multi-user), no external IdP required |
| Containerization | Docker Compose v2 | Must run cleanly under WSL 2 (Ubuntu distro) |
| Package Managers | `pnpm` (frontend), `uv` or `pip` + `venv` (backend) |

**Do not** introduce a new frontend framework, backend framework, or database engine without an explicit, written instruction from the user in the current session. Silent stack changes are considered a breaking violation of these instructions.

---

## 3. Modular Monolith Architecture Rules

The application is **one deployable unit** (one backend process, one frontend build) but internally organized as **independent feature modules**. Each module must be self-contained and loosely coupled from the others.

### 3.1 Backend Folder Structure (module-based, not layer-based)

```
backend/
├── app/
│   ├── core/                # shared: config, db session, security, logging
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   └── deps.py
│   ├── modules/
│   │   ├── qa_reports/
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── models.py
│   │   │   ├── service.py
│   │   │   └── tests/
│   │   ├── micro_utilities/
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   └── tests/
│   │   ├── supabase_hub/
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   ├── models.py
│   │   │   ├── service.py
│   │   │   ├── crypto.py
│   │   │   └── tests/
│   │   └── vault/
│   │       ├── router.py
│   │       ├── schemas.py
│   │       ├── models.py
│   │       ├── service.py
│   │       ├── crypto.py
│   │       └── tests/
│   ├── main.py               # mounts all module routers
│   └── alembic/               # single migration history across modules
├── pyproject.toml
└── Dockerfile
```

**Rule:** a module may import from `core/`, but modules must **never import directly from another module's internals**. If cross-module data is needed, expose it through a service-level function and call it explicitly, or emit an internal event. This keeps modules independently testable and removable.

### 3.2 Frontend Folder Structure

```
frontend/
├── src/
│   ├── modules/
│   │   ├── qa-reports/
│   │   │   ├── views/
│   │   │   ├── components/
│   │   │   ├── stores/          # Pinia store scoped to this module
│   │   │   └── api.ts
│   │   ├── micro-utilities/
│   │   ├── supabase-hub/
│   │   └── vault/
│   ├── shared/
│   │   ├── components/          # Sidebar, CommandPalette, DashboardShell
│   │   ├── composables/
│   │   └── utils/
│   ├── router/
│   │   └── index.ts             # aggregates per-module route files
│   └── main.ts
├── package.json
└── vite.config.ts
```

**Rule:** each module owns its own routes file (`routes.ts`) and exports them; the root router aggregates rather than hardcoding paths inline.

---

## 4. Coding Standards

### Backend (Python / FastAPI)
- Formatting: `ruff format` (or `black`), linting: `ruff check`. Must pass before commit.
- Type hints are **mandatory** on all function signatures. `mypy` (or `pyright`) should report zero errors on new code.
- All request/response bodies must use Pydantic models — never raw `dict` passthroughs.
- All DB access goes through SQLAlchemy async sessions injected via FastAPI `Depends`. No raw psycopg2 connections.
- Every module's router file must declare its own `APIRouter(prefix="/api/<module>", tags=["<module>"])`.
- Business logic belongs in `service.py`, not in route handlers. Route handlers should be thin (parse → call service → return).

### Frontend (Vue 3 / TypeScript)
- `<script setup lang="ts">` only — no Options API in new code.
- Strict TypeScript (`strict: true` in `tsconfig.json`). No `any` unless explicitly justified with a comment.
- API calls go through a typed `api.ts` per module (thin wrapper over `fetch`/`axios`), never inline `fetch()` calls inside components.
- Shared UI primitives (buttons, modals, inputs) live in `shared/components/` and must be reused, not re-implemented per module.
- State that only one component needs stays local (`ref`/`reactive`); state shared across a module's views goes in that module's Pinia store.

### General
- Commit messages: Conventional Commits (`feat:`, `fix:`, `chore:`, `refactor:`, `docs:`).
- No commented-out dead code committed to `main`.
- Every new module ships with at least basic unit tests for its service layer before being considered "done."

---

## 5. Environment Variables & Secrets Handling

This is a **security-critical** section. The Vault and Supabase Hub modules deal with real credentials — mistakes here have real consequences even in a local-only tool.

### 5.1 Rules
1. **Never commit `.env` files.** Only `.env.example` (with placeholder values) is committed to the repo.
2. All secrets (DB password, `VAULT_MASTER_KEY_SALT`, `ENCRYPTION_KEY`, JWT signing key) are loaded via environment variables through `core/config.py` using `pydantic-settings`. No secret is ever hardcoded, logged, or printed — including in debug logs or error messages.
3. The application-level **encryption key used to protect the Vault and Supabase Hub tables must never be stored in plaintext in the database.** It is derived at runtime (see `SYSTEM_ARCHITECTURE.md §4` for the full encryption flow) from a value supplied via environment variable and/or a user-provided master PIN.
4. Docker Compose must read secrets from a `.env` file at the project root (git-ignored) via `env_file:`, not hardcoded in `docker-compose.yml`.
5. Any log line, exception trace, or API error response must be scrubbed of secret values before being written or returned. Coding agents must not add `print(settings.SECRET_KEY)`-style debug statements, even temporarily.
6. When generating example/test data, agents must use obviously fake values (e.g. `sk_test_dummy_1234`) — never real-looking production-style keys.

### 5.2 Required Environment Variables (baseline)

```env
# --- App ---
APP_ENV=local
APP_SECRET_KEY=

# --- Database ---
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/dbname

# --- Security / Encryption ---
ENCRYPTION_KEY=            # base64, 32-byte key for AES-256 (see Vault PRD)
VAULT_PIN_HASH_SALT=

# --- Integrations ---
SLACK_WEBHOOK_URL=
SMTP_HOST=
SMTP_USER=
SMTP_PASSWORD=
```

---

## 6. What an Agent Should Do Before Making Changes

1. Read this file.
2. Read the PRD of the specific module being touched (`PRD_*.md`).
3. Read `SYSTEM_ARCHITECTURE.md` if the change touches cross-module concerns, Docker Compose, or the DB schema.
4. Check `DATABASE_SCHEMA.md` before writing any migration — the schema doc is the source of truth; migrations should match it, and if a migration diverges, this doc must be updated in the same PR.
5. Confirm which module a new feature belongs to. If it doesn't fit an existing module, propose a new module folder rather than bolting it onto an existing one.

## 7. What an Agent Should Never Do
- Never merge module boundaries "for convenience."
- Never disable type checking or linting to unblock a commit.
- Never store secrets in the `daily_reports`, `report_items`, or any non-vault table.
- Never remove the master PIN/lock requirement from the Vault module, even for local dev convenience, without an explicit user instruction in-session.
- Never add third-party analytics, telemetry, or external calls beyond what a module's PRD explicitly specifies (this is a local-only, privacy-sensitive tool).
