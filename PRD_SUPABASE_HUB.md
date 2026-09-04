# PRD: Dynamic Supabase Manager ("Supabase Hub")

**Module ID:** `supabase_hub`
**Owner:** Personal QA & Developer Utilities Portal
**Status:** Draft v1.0

## 1. Overview

The Supabase Hub lets the user register and switch between **multiple external Supabase project connections** at runtime — without editing `.env`, restarting the container, or rebuilding the Docker image. Connection credentials (Project URL, API keys) are stored **encrypted** in the portal's own local Postgres database and decrypted on-demand when a request needs to reach that Supabase project.

This solves a real QA pain point: testing across several Supabase-backed environments (e.g., client projects, staging vs. prod Supabase instances) currently requires manually swapping credentials.

## 2. Goals
- Add, edit, remove, and switch between multiple Supabase project connections from the UI.
- Never require a container rebuild or restart to add a new connection.
- Store all Supabase keys encrypted at rest, decrypted only in-memory at request time.
- Provide a lightweight data browser/query surface per connected project.

## 3. Non-Goals
- Not a replacement for the Supabase Studio/dashboard — this is a QA-focused, minimal-footprint view (browse tables, run read queries, sanity-check data), not full project administration.
- No schema migration tooling against the external Supabase projects in v1.

## 4. Core Concept: Dynamic Runtime Connections

Unlike a typical app that hardcodes one `DATABASE_URL` at boot, this module treats each Supabase project as a **row in the `supabase_configs` table** (see `DATABASE_SCHEMA.md`), not an environment variable. Because credentials are looked up per-request from the DB (rather than baked into container env vars), no rebuild/restart is ever needed to add, disable, or remove a connection.

## 5. User Stories & Acceptance Criteria

### US-1: Register a new Supabase connection
**As a** QA/developer
**I want to** add a new Supabase project's connection details through the UI
**So that** I can start querying it immediately

**Acceptance Criteria:**
- Form fields: `Label*` (friendly name, e.g., "Client A – Staging"), `Project URL*`, `Anon/Public Key*`, `Service Role Key` (optional, marked high-sensitivity), `Notes` (optional).
- On save, both keys are **encrypted before being written to the database** (see §6, Encryption Flow). Plaintext keys are never persisted or logged.
- A "Test Connection" action pings the Supabase project's REST endpoint (e.g., a lightweight `/rest/v1/` health check) before saving, and shows success/failure inline.
- The new connection becomes selectable immediately — **no restart of the backend or frontend container is required.**

### US-2: Switch active connection
**As a** QA/developer
**I want to** switch which Supabase project I'm currently working against
**So that** I can move between client/environment projects quickly

**Acceptance Criteria:**
- A connection switcher (dropdown or Command Palette action) lists all saved connections by label.
- Switching updates the active context for the current session only (does not change any other user's or tab's active context — session-scoped, not global).
- The currently active connection is always visibly indicated in the module's UI (e.g., a persistent badge/header).

### US-3: Browse tables & run read queries
**As a** QA/developer
**I want to** view tables and run simple read queries against the active Supabase connection
**So that** I can verify data without leaving the portal

**Acceptance Criteria:**
- After selecting a connection, a table list is fetched (via Supabase's PostgREST metadata / `information_schema` through the service role key if provided, else via anon-key-permitted tables only).
- Clicking a table shows paginated rows (default page size 25) with column headers.
- A basic filter builder (column = value, contains, greater/less than) is available without requiring raw SQL.
- An "Advanced" raw SQL/PostgREST query mode is available for power use, clearly labeled as read-focused; **destructive operations (`DELETE`, `DROP`, `UPDATE`, `TRUNCATE`) are blocked by default** with an explicit "I understand the risk" confirmation required to allow a write query to run, and only when a Service Role key is present.
- Query results can be exported to CSV/JSON.

### US-4: Edit or remove a connection
**As a** QA/developer
**I want to** update or delete a saved connection
**So that** I can rotate keys or clean up unused projects

**Acceptance Criteria:**
- Edit form pre-fills the label/URL; key fields are shown masked (e.g., `sk_••••1234`) and only overwritten if the user explicitly types a new value.
- Delete requires a confirmation modal; deletion is a hard delete of the encrypted row (no soft-undo required in v1, but the confirmation copy must clearly say this is irreversible).
- If the deleted connection is currently "active" in any open session, that session is reset to "no active connection" gracefully (no crash on next action).

### US-5: Connection health & status indicator
**As a** QA/developer
**I want to** see at a glance whether a saved connection is currently reachable
**So that** I know if a project is down or credentials have expired before I try to use it

**Acceptance Criteria:**
- Each connection in the list shows a status badge (`Unknown / Healthy / Unreachable`), refreshed on-demand via a "Check" button (not polled continuously, to avoid unnecessary external calls).
- Failed health checks show the underlying HTTP status/error reason (e.g., 401 Unauthorized → likely bad/rotated key).

## 6. Encryption Flow (summary — full detail in `SYSTEM_ARCHITECTURE.md §4`)
1. User submits connection form with plaintext keys over HTTPS (or localhost HTTP in dev) to the backend.
2. Backend encrypts `anon_key` and `service_role_key` individually using AES-256-GCM, with the application-level `ENCRYPTION_KEY` (see `AGENT_INSTRUCTIONS.md §5`).
3. Ciphertext + nonce/IV are stored in `supabase_configs`; plaintext is discarded from memory immediately after encryption (no plaintext copy retained beyond the request lifecycle).
4. When a request needs to reach a specific Supabase project, the backend fetches the encrypted row, decrypts in-memory for the duration of that single outbound call, and never returns the decrypted key to the frontend in API responses (the frontend only ever sees masked values).
5. All decrypt operations are logged at an audit level (timestamp, connection ID, which internal action triggered it) **without logging the decrypted value itself.**

## 7. Edge Cases
- Supabase project URL changes (project migrated) but key stays valid → "Test Connection" surfaces the specific failure so the user knows to update the URL, not just "connection failed."
- Two connections with the same label → allowed but discouraged; UI shows the project URL alongside the label wherever ambiguity is possible.
- Service Role key omitted → table browser still works in read-only mode for tables exposed to the anon key/RLS policies; write mode UI is simply hidden rather than shown-and-blocked.

## 8. Future Considerations (out of scope for v1)
- Storing per-connection saved queries/snippets.
- Diffing schemas between two connections.
- Supabase Auth user browsing per connection.
