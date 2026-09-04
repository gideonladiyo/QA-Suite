# DATABASE_SCHEMA.md

**PostgreSQL 16 — Complete DDL for Personal QA & Developer Utilities Portal**

This schema is the source of truth referenced by `AGENT_INSTRUCTIONS.md §6`. Any Alembic migration must converge to match this document; if they diverge, update this file in the same PR as the migration.

## Conventions

### Implemented migration scope

Migration `0001_auth_qa` creates local authentication and the three QA tables below. `0003_qa_report_templates` adds reusable templates and a snapshot of the selected template to each report; deleting a template does not change existing reports. `0002_micro_tools` adds encrypted HTTP request history and dummy schema presets; Supabase Hub and Vault remain planned. `daily_reports.version` is incremented under a row lock on save/finalize/send; a stale client version returns HTTP 409. DELETE checks the same version under a row lock before deleting the report and its children. QA-only JSON backup/restore requires no schema change; restoration creates new identities and skips existing report dates without overwriting them. It does not include Micro Tools data.

Authentication has two deliberate exceptions to the UUID/timestamp conventions: the single account uses `id = 1`, and sessions use a SHA-256 token digest as their primary key. Session rows expire after 12 hours and are revoked on logout. No plaintext password or session token is stored.

Template library updates use a row lock and the caller's `expected_updated_at` timestamp. `daily_reports.template_values` stores bounded report-wide custom strings; the template body/name snapshot remains after a source-template deletion. Migration `0004_activity_template_values` adds `report_items.template_values` for custom strings scoped to each activity (30 keys, 10,000 characters/value). Existing v2 report-wide values remain a rendering fallback for older snapshots. Backup v3 includes both scopes, library templates, and snapshots; v1/v2 remain readable. Restore skips existing template names and report dates without overwriting them. Custom reports can leave unused activity_code/environment/result fields as empty strings; standard reports still require them. Missing Result is excluded from the pass-rate denominator, and missing ticket codes are not counted as duplicates.

```sql
CREATE TABLE local_account (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    username VARCHAR(80) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE local_sessions (
    token_hash VARCHAR(64) PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES local_account(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_local_sessions_expires_at ON local_sessions(expires_at);
```

### General conventions
- All primary keys use `UUID` (via `gen_random_uuid()`, from the `pgcrypto` extension) rather than serial integers, to avoid leaking row counts and to keep IDs safe to reference in URLs.
- All tables have `created_at` / `updated_at` timestamps (`timestamptz`), maintained via a shared trigger.
- Encrypted columns are stored as `bytea` for ciphertext plus a separate `bytea` for the nonce/IV, never combined into a single opaque blob, to keep the crypto explicit and auditable.
- Soft-delete is **not** used by default (per the PRDs, deletions in Vault/Supabase Hub are explicit hard deletes); `daily_reports` also hard-deletes unless otherwise decided later.

```sql
-- =========================================================
-- EXTENSIONS
-- =========================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =========================================================
-- SHARED: updated_at trigger function
-- =========================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =========================================================
-- MODULE: qa_reports
-- =========================================================

-- Enum-like check constraints kept as VARCHAR + CHECK rather than
-- native ENUM types, so new values (custom environments/results)
-- can be added without a schema migration.

CREATE TABLE report_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL UNIQUE,
    description     VARCHAR(255),
    body            TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_report_templates_updated_at
    BEFORE UPDATE ON report_templates
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE daily_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_date     DATE NOT NULL,
    title           VARCHAR(255) NOT NULL DEFAULT 'Daily QA Report',
    author_name     VARCHAR(255),
    template_id     UUID REFERENCES report_templates(id) ON DELETE SET NULL,
    template_name   VARCHAR(100),                    -- snapshot label for history
    template_body   TEXT,                            -- snapshot content for history
    template_values JSONB NOT NULL DEFAULT '{}',      -- custom placeholder values
    version         INTEGER NOT NULL DEFAULT 1,
    status          VARCHAR(20) NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'finalized', 'sent')),
    slack_sent_at   TIMESTAMPTZ,
    email_sent_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_daily_reports_date UNIQUE (report_date)
);

CREATE INDEX ix_daily_reports_template_id ON daily_reports(template_id);

CREATE TRIGGER trg_daily_reports_updated_at
    BEFORE UPDATE ON daily_reports
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE report_items (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    daily_report_id     UUID NOT NULL REFERENCES daily_reports(id) ON DELETE CASCADE,
    activity_code       VARCHAR(100) NOT NULL,      -- e.g. 'AMTSK-166'
    environment         VARCHAR(50) NOT NULL,        -- 'Dev' | 'Staging' | 'Prod' | custom
    result              VARCHAR(50) NOT NULL,        -- 'Pass' | 'Fail' | 'In Progress' | 'Blocked' | custom
    current_status      VARCHAR(100),                 -- e.g. 'Passed prod' (may differ from result)
    current_issue       TEXT,
    template_values     JSONB NOT NULL DEFAULT '{}', -- custom values per activity
    sort_order          INTEGER NOT NULL DEFAULT 0,   -- preserves manual ordering within a report
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_report_items_daily_report_id ON report_items(daily_report_id);
CREATE INDEX idx_report_items_activity_code ON report_items(activity_code);
CREATE INDEX idx_report_items_environment ON report_items(environment);
CREATE INDEX idx_report_items_result ON report_items(result);

CREATE TRIGGER trg_report_items_updated_at
    BEFORE UPDATE ON report_items
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Coverage links: one-to-many, since a single activity can have
-- multiple links (e.g. Notion + Google Docs, as in the example report).
CREATE TABLE report_item_links (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_item_id  UUID NOT NULL REFERENCES report_items(id) ON DELETE CASCADE,
    url             TEXT NOT NULL,
    label           VARCHAR(255),                    -- optional friendly label
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_report_item_links_report_item_id ON report_item_links(report_item_id);


-- =========================================================
-- MODULE: micro_utilities
-- =========================================================

-- HTTP Client request history
CREATE TABLE http_client_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    method          VARCHAR(10) NOT NULL CHECK (method IN ('GET','POST','PUT','PATCH','DELETE')),
    request_ciphertext BYTEA NOT NULL,                 -- AES-256-GCM encrypted HttpRequest JSON + tag
    request_nonce   BYTEA NOT NULL,                    -- random 12-byte nonce, UUID as AAD
    response_status INTEGER,
    response_time_ms INTEGER NOT NULL,
    response_size_bytes INTEGER NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_http_client_history_created_at ON http_client_history(created_at);

-- Request JSON includes URL, headers, body, variables, auth helpers and settings.
-- HKDF-SHA256 derives a 32-byte key from APP_SECRET_KEY with module-specific info.
-- No response body is stored. Losing/changing APP_SECRET_KEY makes old history unreadable.
-- A transaction advisory lock serializes insertion + retention (default 50, max 200).

-- Dummy Data Builder saved schema presets
CREATE TABLE dummy_data_presets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    schema_json     JSONB NOT NULL,                    -- [{name,type,minimum,maximum,start,end,choices}, ...]
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (name)
);

-- Presets are create/read/delete in v1; no update endpoint or trigger.
-- SQLAlchemy also supplies updated_at on ORM updates. App validation enforces
-- 1-30 unique field names per schema and at most 100 named presets.
-- Presets are plaintext schema definitions: never store secrets in enum values.


-- =========================================================
-- MODULE: supabase_hub
-- =========================================================

CREATE TABLE supabase_configs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    label                   VARCHAR(255) NOT NULL,           -- e.g. 'Client A - Staging'
    project_url             TEXT NOT NULL,

    -- Anon/public key, encrypted (AES-256-GCM)
    anon_key_ciphertext     BYTEA NOT NULL,
    anon_key_nonce          BYTEA NOT NULL,

    -- Service role key, encrypted, optional
    service_key_ciphertext  BYTEA,
    service_key_nonce       BYTEA,

    notes                   TEXT,
    last_health_status      VARCHAR(20) DEFAULT 'unknown'
                                CHECK (last_health_status IN ('unknown','healthy','unreachable')),
    last_health_checked_at  TIMESTAMPTZ,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_supabase_configs_label ON supabase_configs(label);

CREATE TRIGGER trg_supabase_configs_updated_at
    BEFORE UPDATE ON supabase_configs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Audit log for every decrypt/access event against a Supabase config
CREATE TABLE supabase_config_access_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id       UUID NOT NULL REFERENCES supabase_configs(id) ON DELETE CASCADE,
    action          VARCHAR(50) NOT NULL,          -- 'decrypt_for_request' | 'health_check' | 'query'
    detail          TEXT,                           -- non-secret context only, never the decrypted value
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_supabase_access_log_config_id ON supabase_config_access_log(config_id);
CREATE INDEX idx_supabase_access_log_created_at ON supabase_config_access_log(created_at DESC);


-- =========================================================
-- MODULE: vault
-- =========================================================

-- Single-row (or small, per local user) table holding the master
-- lock's hashed PIN/passphrase. Never stores the PIN itself.
CREATE TABLE vault_master_lock (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pin_hash            TEXT NOT NULL,               -- Argon2id hash
    kdf_salt            BYTEA NOT NULL,               -- salt used for key derivation (separate from hash salt)
    failed_attempts     INTEGER NOT NULL DEFAULT 0,
    locked_until        TIMESTAMPTZ,                  -- backoff lockout expiry, null if not locked out
    recovery_code_hash  TEXT,                          -- optional, hashed recovery code (v1.1+)
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_vault_master_lock_updated_at
    BEFORE UPDATE ON vault_master_lock
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE vault_secrets (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title               VARCHAR(255) NOT NULL,
    username            VARCHAR(255),
    category            VARCHAR(50) NOT NULL DEFAULT 'other'
                            CHECK (category IN ('password','api_key','token','note','other')),
    url                 TEXT,

    -- Encrypted secret value (AES-256-GCM)
    value_ciphertext    BYTEA NOT NULL,
    value_nonce         BYTEA NOT NULL,

    -- Encrypted notes (optional, also sensitive)
    notes_ciphertext    BYTEA,
    notes_nonce         BYTEA,

    last_accessed_at    TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_vault_secrets_title ON vault_secrets(title);
CREATE INDEX idx_vault_secrets_category ON vault_secrets(category);

CREATE TRIGGER trg_vault_secrets_updated_at
    BEFORE UPDATE ON vault_secrets
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Audit log for vault access (unlock attempts + secret copy/reveal events)
CREATE TABLE vault_access_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    secret_id       UUID REFERENCES vault_secrets(id) ON DELETE SET NULL,
    action          VARCHAR(50) NOT NULL,        -- 'unlock_success' | 'unlock_failed' | 'copy' | 'reveal' | 'lock'
    detail          TEXT,                          -- non-secret context only
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_vault_access_log_secret_id ON vault_access_log(secret_id);
CREATE INDEX idx_vault_access_log_created_at ON vault_access_log(created_at DESC);
```

## Entity Relationship Summary

```
daily_reports (1) ──< report_items (many) ──< report_item_links (many)
report_templates (1) ──< daily_reports (optional, snapshot retained)

supabase_configs (1) ──< supabase_config_access_log (many)

vault_master_lock (1)   [standalone — governs unlock, not FK-linked to secrets]
vault_secrets (1) ──< vault_access_log (many)

http_client_history        [standalone log table]
dummy_data_presets         [standalone preset table]
```

## Notes on Encrypted Columns
- Ciphertext and nonce are always stored as **separate columns**, never concatenated into one blob, so key rotation and auditing tooling can reason about them independently.
- No table in this schema stores a plaintext secret, plaintext API key, or plaintext PIN anywhere — this is a hard invariant enforced by both this schema and `AGENT_INSTRUCTIONS.md §5`.
- `vault_master_lock.kdf_salt` is distinct from the Argon2id hash's own internal salt; it is the salt used when deriving the **AES-256 data key** from the user's PIN, kept separate from password-hash verification for cleanest separation of concerns between "verify the PIN" and "derive the encryption key."

## Suggested Alembic Migration Order
1. Extensions + shared trigger function
2. `qa_reports` module tables
3. `micro_utilities` module tables
4. `supabase_hub` module tables
5. `vault` module tables

This order matches dependency-free build-up (no table here has a cross-module foreign key), so modules can, in principle, be migrated independently if one is temporarily disabled.
