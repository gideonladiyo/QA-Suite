# PRD: Local Password & Secret Manager ("Vault")

**Module ID:** `vault`
**Owner:** Personal QA & Developer Utilities Portal
**Status:** Draft v1.0

## 1. Overview

A local, AES-256-encrypted secret manager for storing passwords, API keys, and other sensitive strings the user needs during daily QA/dev work (test account logins, staging credentials, personal tokens). Protected behind a **Master Lock (PIN or passphrase)** so that even on a shared or unlocked machine, the vault contents aren't exposed at a glance.

This is the most security-sensitive module in the portal and should be built and reviewed with the most caution of all modules described in this document set.

## 2. Goals
- Store secrets encrypted at rest using AES-256.
- Require explicit unlock (Master PIN/passphrase) before any secret is viewable or copyable, each session.
- Make everyday retrieval fast (quick-copy) without ever displaying more of the secret than necessary.
- Auto-lock after inactivity.

## 3. Non-Goals
- Not a browser-extension-integrated password manager (no autofill into other websites in v1).
- Not designed for multi-user shared-secret access control in v1 (single local user / trusted household model).
- Not a replacement for a hardware security key or dedicated enterprise vault (e.g., HashiCorp Vault) for production secrets — this is for personal/dev/test-account convenience.

## 4. User Stories & Acceptance Criteria

### US-1: Set up the Master Lock (first run)
**As a** user setting up the portal for the first time
**I want to** set a Master PIN/passphrase for the Vault
**So that** my stored secrets are protected even if someone else uses my machine

**Acceptance Criteria:**
- On first visit to the Vault module, if no master lock is configured, the user is prompted to create one (minimum length enforced — 8 characters for passphrase mode, 6 digits for PIN mode).
- The Master PIN/passphrase is **never stored in plaintext**. Only a salted hash (e.g., Argon2id) is stored, used to verify unlock attempts.
- The actual AES-256 data-encryption key is derived from the Master PIN/passphrase via a key-derivation function (Argon2id or PBKDF2), **not stored anywhere** — meaning if the user forgets their Master PIN, stored secrets are unrecoverable by design. This trade-off must be shown to the user explicitly during setup ("If you forget this PIN, your vault cannot be recovered").
- User can optionally set up a recovery mechanism (e.g., a printable recovery code shown once at setup) — flagged as v1.1 if not shipped in v1, but the setup screen should not silently omit warning the user about the no-recovery default.

### US-2: Unlock the Vault
**As a** returning user
**I want to** unlock the Vault with my Master PIN/passphrase
**So that** I can view/copy my secrets

**Acceptance Criteria:**
- Vault module loads in a **locked state** by default on every fresh session/app load — no secret list or values are fetched from the backend until unlock succeeds.
- Incorrect PIN attempts are rate-limited (e.g., exponential backoff after 3 failed attempts; hard lockout of increasing duration after 5) to blunt brute-force attempts, even though this is a local-only tool.
- Successful unlock establishes a short-lived in-memory session (see US-4, auto-lock) — the derived encryption key is held only in backend memory for that session, never persisted to disk or sent to the frontend.
- The frontend never receives the Master PIN/passphrase or derived key in any API response — only a session token indicating "unlocked" state.

### US-3: Add / edit / delete a secret
**As a** user
**I want to** store a new secret with a label, value, and optional metadata
**So that** I can retrieve it later without remembering it

**Acceptance Criteria:**
- Fields: `Title*` (e.g., "Staging DB Admin"), `Username` (optional), `Secret Value*` (password/token/key — masked input), `Category` (optional: Password / API Key / Token / Note / Other), `URL` (optional), `Notes` (optional, also encrypted).
- Secret value is encrypted client-request → server-side using AES-256-GCM before being written to `vault_secrets`; plaintext never touches the database.
- Editing a secret requires the Vault to be currently unlocked; editing re-encrypts and overwrites, it does not create a new plaintext-adjacent draft anywhere.
- Deleting a secret requires confirmation and is a hard delete.
- A built-in password generator is available when creating a new "Password" category secret (configurable length, character set).

### US-4: Auto-lock on inactivity
**As a** security-conscious user
**I want to** the Vault to automatically re-lock after a period of inactivity
**So that** I'm not leaving secrets exposed if I walk away

**Acceptance Criteria:**
- Default auto-lock timer: 5 minutes of inactivity within the Vault module (configurable in settings, range 1–60 minutes).
- Auto-lock also triggers immediately on browser tab close or app/container restart (in-memory session key is never persisted, so a restart always requires re-unlock).
- A manual "Lock Now" button is always visible while unlocked.

### US-5: Quick-copy a secret
**As a** user
**I want to** copy a secret value to my clipboard without it being displayed on-screen unnecessarily
**So that** I minimize shoulder-surfing/screen-capture risk

**Acceptance Criteria:**
- Default list view shows secret values **masked** (`••••••••`); a "Reveal" toggle is required to view plaintext on-screen, separate from copying.
- A "Copy" button copies the decrypted value directly to clipboard **without requiring reveal first** (so the value never has to be shown just to be copied).
- Clipboard contents are automatically cleared after a short timeout (default 30 seconds) if the copied value hasn't been overwritten by something else — implemented via a frontend timer that, where browser permissions allow, overwrites clipboard content or at least warns the user proactively.
- Copy actions are logged at an audit level (timestamp + which secret's title, not the value) so the user can see "last accessed" per secret.

### US-6: Search & organize secrets
**As a** user with many stored secrets
**I want to** search and filter my vault
**So that** I can find what I need quickly

**Acceptance Criteria:**
- Search by title/username/category (never searches into the encrypted value itself server-side in a way that would require broad decryption — search operates on non-secret metadata fields only).
- Filter by category.
- Sort by most recently used / alphabetical / date added.

## 5. Encryption & Security Summary (full flow in `SYSTEM_ARCHITECTURE.md §4`)
- **Algorithm:** AES-256-GCM (authenticated encryption — protects both confidentiality and integrity).
- **Key derivation:** Argon2id (preferred) from Master PIN/passphrase + a per-install salt stored in `VAULT_PIN_HASH_SALT`.
- **At rest:** `vault_secrets.encrypted_value` stores ciphertext + nonce/IV + auth tag; never plaintext.
- **In transit (frontend ↔ backend):** even though this runs locally, all Vault traffic should be served over HTTPS in any non-`localhost` WSL setup (e.g., if the WSL host is reached from Windows via a mapped hostname) — see `SYSTEM_ARCHITECTURE.md`.
- **In memory:** the derived key exists only for the duration of an unlocked session and only in backend process memory; never written to disk, never logged, never included in error messages.

## 6. Edge Cases
- User forgets Master PIN and no recovery code was generated → vault data is permanently inaccessible; UI must state this plainly rather than implying support can help (there is no backdoor).
- Browser clipboard API permission denied → app falls back to a manual "select text to copy" reveal, with a clear warning that the auto-clear timeout can't be guaranteed in that fallback path.
- Concurrent access from two tabs → the second tab locks/unlocks independently (session state is per browser session/tab context, not shared), each requiring its own unlock.

## 7. Future Considerations (out of scope for v1)
- Printable/exportable encrypted backup file.
- Browser extension autofill integration.
- Shared vault entries between multiple local users with per-entry access control.
- TOTP/2FA secret storage with live code generation.
