# PRD: Developer & QA Micro Utilities

**Module ID:** `micro_utilities`
**Owner:** Personal QA & Developer Utilities Portal
**Status:** Implemented v1.0 in source (Docker deployment is an explicit separate step)

## 1. Overview

A collection of small, fast, single-purpose developer/QA tools accessible from one dashboard tab, replacing the need to open multiple external websites (Postman, jsonformatter.org, jwt.io, mockaroo, etc.) for quick everyday tasks. Each tool is a self-contained sub-view within this module.

## 2. Goals
- Replace ad-hoc use of public formatters/decoders. JSON, dummy data, and Base64/JWT stay in the browser; HTTP Client sends only the request the user explicitly composes to their chosen target.
- Keep every tool fast, keyboard-friendly, and accessible via the Command Palette.
- Persist recent inputs/history locally so repeated tasks (e.g., re-hitting the same API endpoint) are fast.

## 3. Non-Goals
- Not a replacement for full API testing suites (no test collections/environments like Postman — see "Future Considerations").
- No cloud sync of tool history in v1 (local DB only).

## 4. Sub-Tools

### 4.1 Minimalist HTTP Client

**As a** developer
**I want to** send a quick HTTP request and see the response
**So that** I can test an endpoint without opening Postman/Insomnia

**Acceptance Criteria:**
- Supports methods: `GET, POST, PUT, PATCH, DELETE`.
- URL bar, headers key-value editor, body editor (raw JSON / form-encoded / raw text).
- Response panel shows: status code (color-coded 2xx/3xx/4xx/5xx), response time (ms), response size, formatted headers, and formatted/raw response body (auto-pretty-prints JSON).
- "Save to History" happens automatically after each send; retain the last N requests (1–200, default 50). One click loads a request into the form; sending is a separate explicit action to prevent accidental replay of mutations.
- Requests support a simple `{{variable}}` substitution using per-request saved variables (e.g., `{{base_url}}/api/users`), stored locally — a lightweight stand-in for Postman "environments."
- Basic auth and Bearer token auth are supported as first-class header helpers (not just raw header entry).
- Requests are proxied through the backend (not fired directly from the browser) so CORS restrictions on target APIs don't block local testing; backend enforces a request timeout (default 15s) to avoid hangs.
- History lists only method/time/status/size metadata. URL, header, body, variables, and auth are encrypted together; details are loaded explicitly into the form with masked header/token values and a reveal toggle. Response bodies are not persisted.

### 4.2 JSONizer / Formatter

**As a** developer
**I want to** paste raw/minified/malformed JSON and get it formatted, validated, or converted
**So that** I can quickly read or debug payloads

**Acceptance Criteria:**
- Paste or type JSON into an input pane; output pane shows pretty-printed (2-space indent, configurable) result live.
- Invalid JSON shows an inline error with line/column of the syntax error, not just "invalid JSON."
- "Minify" mode collapses to a single line.
- "Sort keys" toggle (alphabetical, recursive).
- JSON ↔ YAML conversion (both directions).
- Tree view mode: collapsible/expandable node tree for large payloads, with a search-within-JSON field that highlights matching keys/values.
- "Copy formatted" and "Copy minified" quick actions.
- Handles large payloads (target: responsive up to ~2MB pasted JSON) without freezing the UI (processed with a debounce and/or web worker on the frontend).

### 4.3 Dummy Data Builder

**As a** QA tester / developer
**I want to** generate realistic fake data (names, emails, addresses, UUIDs, dates, etc.)
**So that** I can quickly populate test cases or seed data without manually inventing values

**Acceptance Criteria:**
- Field-type library includes at minimum: full name, first/last name, email, phone number, address, company, UUID, integer range, boolean, date range, Lorem Ipsum text, enum/pick-from-list.
- User defines a "schema" as a list of `{field_name, type, options}` rows via a simple form UI (not raw code).
- User specifies row count (e.g., 50 records) and generates output.
- Output export formats: JSON array, CSV, SQL `INSERT` statements (table name configurable).
- Generated schemas can be saved and reused (named presets, e.g., "User seed data").
- "Regenerate" button re-rolls random values while keeping the same schema.
- Deterministic mode: optional seed value so the same schema + seed always produces identical output (useful for reproducible test fixtures).

### 4.4 Base64 / JWT Decoder

**As a** developer
**I want to** decode Base64 strings and JWTs
**So that** I can quickly inspect tokens/payloads without pasting them into a public website

**Acceptance Criteria:**
- Base64 encode/decode, both directions, plain text and file-safe alphabet variants supported.
- JWT decoder: paste a JWT, see decoded **Header** and **Payload** as formatted JSON, plus the raw **Signature** segment.
- Standard claims (`exp`, `iat`, `nbf`) are shown as human-readable dates alongside raw values. Time status says expired, not yet active, no expiry, or not expired—not “valid”, since time alone proves no trust.
- Signature verification is **optional and explicit**: choose the expected algorithm and supply an HS256 secret or RS256 public key (SPKI PEM). Verification runs in browser Web Crypto; token/key never go to the backend. Issuer/audience/application authorization are not verified. No remote key lookup.
- Clear indication in the UI that decoding a JWT does **not** validate it unless a key was supplied — prevents false confidence about token trust.
- Copy buttons for header JSON, payload JSON, and each raw segment.

## 5. Cross-Tool Requirements
- All four tools are reachable from a single "Micro Utilities" sidebar entry with sub-tabs, and each is individually searchable/launchable via the Command Palette (e.g., typing "jwt" jumps straight to the JWT decoder).
- Each tool's state (current input) persists in the frontend store during the session (not lost on tab switch within the module) but is not required to persist across a full page reload unless explicitly saved.
- No tool in this module makes an outbound call to a third-party service except the HTTP Client, which only calls whatever URL the user explicitly enters.

## 6. Edge Cases
- HTTP Client: target endpoint unreachable/times out → show a clear network error state, not a generic 500.
- JSONizer: extremely deeply nested JSON → tree view virtualizes rendering to avoid DOM blowup.
- Dummy Data Builder: 1–100,000 rows, 1–30 fields, max 1 million cells / approximately 20 MB output. Above 10,000 rows requires confirmation; generation is isolated in a worker, cancellable and stopped after 30 seconds. Over-limit requests are rejected.

## Implementation limits and persistence

- JSON/YAML: 2 MB UTF-8 input, 100,000 values, max depth 64, 300 ms debounce, 30-second worker timeout. Tree is windowed; textual previews are limited to 100k characters, full bounded output is available for copy/download. Standard JSON values only; comments/anchors/custom tags are not retained. JavaScript number precision applies.
- HTTP: timeout 1–30 seconds, 2 MB text-response cap, no redirects, no ambient portal credentials, no proxy-environment inheritance. Private/local targets require explicit consent each replay; metadata/link-local/reserved/IPv6 transition addresses remain blocked. Non-identity compressed bodies are rejected rather than unbounded decompression. Form body is manually URL-encoded text, not multipart upload.
- Request history uses AES-256-GCM with a module-specific key derived from APP_SECRET_KEY. This is at-rest protection, not Vault unlock semantics. Keep the key safe alongside a separate full-database backup. QA JSON backup/restore does not include history or presets.
- Dummy schemas: max 100 named presets in the database; unique names, no overwrite/update endpoint in v1. Only schema is stored (plaintext; no secrets). Data uses Faker en with deterministic seed/version, reserved test email/phone values, and is not guaranteed unique. SQL export targets PostgreSQL and is never executed.
- Base64/JWT: 1 MB input, 16,384-character verification key. UTF-8 text, not binary file conversion. Inputs remain in Pinia only until reload/tab close/logout; temporary session expiry preserves them for reauthentication.
- JWT Decoder: malformed token (wrong number of segments) → explicit "not a valid JWT structure" message rather than a stack trace.

## 7. Future Considerations (out of scope for v1)
- Saved HTTP "collections" with folders (full Postman-lite experience).
- Regex tester tool.
- Cron expression builder/explainer.
- Diff tool (text/JSON diff viewer).
