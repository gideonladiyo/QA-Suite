# PRD: QA Daily Report Engine

**Module ID:** `qa_reports`
**Owner:** Personal QA & Developer Utilities Portal
**Status:** Implemented; customizable templates revision, September 3, 2026

### Phase 3 implementation decisions — customizable report templates

- `/qa-reports/templates` lists reusable templates in a sortable, paginated table with use/edit/delete actions. Creation (`/qa-reports/templates/new`) and editing (`/qa-reports/templates/:templateId/edit`) use separate pages with a starter format, placeholder insertion, live sample preview, inline validation, unsaved-change protection, and a "Simpan & buat laporan" shortcut. Ordinary save returns to the list. Concurrent edits use the template's `updated_at` timestamp and a row lock; stale edits return 409.
- Report placeholders: `{{report_title}}`, `{{report_date}}`, `{{author_name}}`. Activity fields (`{{activity_code}}`, `{{environment}}`, `{{result}}`, `{{coverage_links}}`, `{{current_issue}}`, `{{current_status}}`) appear inside non-nested `{{#activities}}...{{/activities}}` blocks. Multiple blocks support separate summary, coverage, issue, and status sections.
- All formats share a template-driven flow: identity (date/title for storage, author for the standard format or when referenced, plus report-wide custom fields), then activities only if the template contains activity blocks. Activity fields follow their first appearance in the template, without duplicate inputs for repeated sections. Unused built-ins and coverage controls are hidden. Preview/save appear on the last step. Report-only templates need no activities. The standard format also uses two steps, deriving activity fields from the starter template without changing the existing export format. Next/save actions stay in normal page flow, never sticky.
- Additional placeholders outside blocks, such as `{{nama_proyek}}`, are filled once per report. Inside blocks, `{{next_step}}` and other custom fields are filled separately for each activity and follow that activity through reorder/copy/save/edit/backup. The same name in both scopes has independent values. Older snapshots fall back to their previous report-wide values until edited. All values are saved atomically. Unused Result/environment values are not fabricated; pass rate includes only populated Results and missing codes do not count as duplicate tickets.
- A report can choose the standard format or a saved template in step 1. Using a template from the library or saving a new report remembers the chosen template ID in this browser; no report contents are persisted in browser storage. Underscores escaped by pasted Markdown are normalized inside placeholders only.
- The selected template body and name are snapshotted on save. Editing a saved report preserves that snapshot unless the user explicitly selects another format. Deleting the source template leaves the snapshot and custom values intact. Legacy reports retain the standard format.
- Template text is preserved for Markdown/plaintext; Slack control characters and HTML are escaped. Placeholder values are never re-parsed or executed. Limits: 100 templates, 20,000 characters/template, 12 activity blocks, 30 custom placeholders, 10,000 characters/custom value, 2,000,000 characters/rendered custom output.
- JSON backup v3 includes the template library, report snapshots, and both scopes of custom values. Restore accepts v1, v2, and v3, skips existing report dates and template names, assigns fresh IDs, and commits atomically. Existing size/report limits remain in effect.

### Phase 2 implementation decisions (historical; Phase 3 supersedes the three-step flow)

- The latest September 2 user revision makes `/qa-reports` the report list, sorted by report date ascending: oldest first, newest at the bottom across pages. "Tambah laporan" opens a separate unsaved editor at `/qa-reports/new`; `/qa-reports/history` redirects to the list. Filters and backup controls are collapsible so the list stays prominent.
- First save posts metadata and items together, atomically, just like subsequent edits. Opening a blank form never creates a database record. A duplicate date links to the existing report without overwriting it. At least one valid activity is required by the input UI.
- The editor is a three-step workflow: (1) metadata and activity list with environment/result; (2) coverage links per activity; (3) issues/current status, then save. Lanjut validates the visible stage and advances without writing to the database. Back preserves all input. A numbered progress indicator and heading focus communicate stage changes. Successful saving opens the saved report preview.
- Saved editable reports use the visible label Tersimpan, not Draft. The internal `draft` status still means editable and remains unchanged for API/backup compatibility. No finalization or data migration is required. Unsaved form changes retain a separate warning.
- Report pages expose Laporan / title breadcrumbs. Ancestor Laporan returns to the list; new-date/back controls are bordered buttons, and delete uses a visible danger button.
- Environment defaults to `Dev` and remains non-empty, resolving the contradictory optional/required wording below and matching the database constraint. Custom environment/result values remain supported.
- The editor saves report metadata and all activity changes atomically. Existing activity IDs are retained; coverage links are replaceable value objects. Item order follows the editor's Up/Down controls.
- Each activity can be collapsed without losing input, with ticket/environment/result visible in its header. Open-all and close-all controls are available. Adding an activity folds earlier activities. Invalid required fields automatically reopen their activity before displaying validation.
- Changing stages opens activity sections for the newly relevant fields. Adding, removing, and reordering activities is available at stage 1; link/issue associations follow the activity object, not the row index.
- Copy from yesterday appends all activities from the previous calendar date to the unsaved draft. The user reviews them before saving. Browser-local dates avoid UTC day shifts.
- History opens read-only, with Edit for drafts. Finalization is permanent in v1; there is no reopen action. Unsaved edits prompt before navigation and remain mounted when reauthentication is required.
- Preview loads automatically for a non-empty saved report. Its format selector offers Slack markup, standard Markdown, and plaintext, with matching copy/download content. Date uses an English month and an unpadded day, e.g. `September 1, 2026`; the coverage heading is exactly `Test Coverage :`. Blank link rows are ignored; unsafe URLs remain inert text. HTML is escaped and downloadable, not rendered inline. Preview shows source text, not a simulated Slack rendering.
- Every activity is a bullet in each applicable export section: a literal bullet in Slack and a hyphen list in Markdown/plaintext. Continuation lines (environment/result, coverage links, multiline issues) are indented under the matching activity. Export changes apply when regenerating old saved reports too, without changing stored report data.
- "Simpan & ekspor Slack .md" saves before downloading. Dirty input never exports a stale preview. Preview failures after a successful save provide a retry without discarding saved data. Copy/export require neither finalization nor Slack/email settings. The previous delivery/finalization endpoints remain for compatibility, but their UI actions are removed from the daily workflow. Legacy locked reports remain read-only/exportable and can be deleted explicitly.
- Deleting requires confirmation of the saved title/date/activity count and a matching report version. The report and its activities/coverage links are permanently removed together. Deletion never removes already exported files or messages sent externally.
- Manual JSON backup contains all QA reports, regardless of list filters or pagination, but excludes accounts, sessions, and secrets. Versioned backup files are limited to 1,000 reports and 10 MiB. Restore validates the entire file, requires confirmation, skips existing dates without overwriting, generates fresh IDs, and commits all new reports atomically. Backup files are not encrypted; there is no scheduled backup or recycle bin.
- `sent` means at least one channel confirmed success. Copy/download never marks sent. All report statuses contribute to monthly metrics. Pass rate uses exact `Pass`; custom results stay in the denominator. Repeated entries count additional occurrences of an identical code within the same report/date.
- Limits: 500 activities/report, 50 coverage links/activity, 10,000 characters/issue. History is server-paginated in pages of 20. Monthly totals are aggregated in SQL; CSV includes all activities and neutralizes spreadsheet formula prefixes.

## 1. Overview

The QA Daily Report Engine lets the user log daily testing activity ticket-by-ticket, then auto-generate a formatted daily report (matching their existing Slack/email report style) without retyping it manually. Over time, entries roll up into a monthly metrics dashboard.

This module directly digitizes the user's existing manual workflow (see the "Gideon Daily QA Report" example) into structured data, so the free-text report becomes a **byproduct of structured input**, not something typed from scratch each day.

## 2. Goals
- Eliminate manual formatting of the daily report message.
- Make each day's testing activity structured, searchable, and reportable over time.
- Provide copy/export in Slack markup, Markdown, or plaintext without external service setup.
- Make large reports manageable with collapsible activities, explicit deletion, and manual backup/restore.
- Surface monthly trends (pass rate, issue frequency, environment distribution).

## 3. Non-Goals
- This is not a full test-case management system (no test plans, no test suites).
- Not integrated with Jira/Linear APIs in v1 — ticket codes are entered manually as free text (e.g. `AMTSK-166`).

## 4. Data Model Summary (see `DATABASE_SCHEMA.md` for DDL)
A `daily_report` (one per date) has many `report_items` (one per ticket/activity tested that day). Each item carries:
- **Activity/Ticket Code** (e.g. `AMTSK-166`)
- **Environment** (`Dev`, `Staging`, `Prod`, custom)
- **Result/Status** (`Pass`, `Fail`, `In Progress`, `Blocked`, custom)
- **Coverage Link(s)** (one or more URLs — Notion, Google Docs, etc.)
- **Current Issue(s)** (free text, optional)
- **Current Status** (may differ from Result — e.g. Result = "In progress" during testing, Current Status = "Passed prod" once resolved)

## 5. User Stories & Acceptance Criteria

### US-1: Add a daily report entry
**As a** QA tester
**I want to** create a new daily report for today's date
**So that** I can start logging tickets I tested

**Acceptance Criteria:**
- GIVEN I open QA Reports, THEN the report list is shown. WHEN I choose "Tambah laporan", THEN a separate unsaved form opens with today's date, editable before saving. WHEN I save, metadata and activities are persisted together.
- GIVEN a report already exists for the selected date, WHEN I try to create another, THEN the system prompts to open the existing report instead of duplicating it.
- A report has an editable title (defaults to `"{User} Daily QA Report"`).

### US-2: Log a ticket/activity item
**As a** QA tester
**I want to** add an activity entry with code, environment, result, coverage link(s), and issue notes
**So that** each ticket I tested that day is captured in structured form

**Acceptance Criteria:**
- Form fields: `Activity Code*` (text), `Environment*` (select: Dev/Staging/Prod/Custom), `Result*` (select: Pass/Fail/In Progress/Blocked/Custom), `Coverage Link(s)` (repeatable URL field, 0..n), `Current Issue` (textarea, optional), `Current Status` (text, optional — defaults to Result if left blank).
- `Activity Code`, `Environment`, and `Result` are required; other fields are optional.
- Multiple coverage links per activity are supported (matches the example where one ticket links to a Notion doc, another to Google Docs).
- I can add multiple activity items to the same daily report before submitting.
- I can edit or delete an item after adding it, as long as the report hasn't been marked "finalized/sent."
- I can duplicate a previous day's item as a starting point (e.g., re-testing the same ticket the next day) via a "Copy from yesterday" action.
- I can fold one or all activity sections without changing their data; the header retains a ticket/environment/result summary and editing order controls. Saving reopens any activity containing an invalid required field.
- Activities are entered first, coverage second, issues/status last. I can return to earlier steps without losing input. Only the last-step save persists changes; unsaved navigation prompts before discarding them.

### US-3: Auto-generate formatted report text
**As a** QA tester
**I want to** generate a Slack- and Email-formatted version of today's report
**So that** I can paste it directly into Slack or send it as an email without manual formatting

**Acceptance Criteria:**
- Saving automatically produces a source preview with Slack markup, standard Markdown, and plaintext choices, plus optional escaped HTML download. No separate generate/finalize step is required.
- The Slack output structure matches the user's existing convention:
  ```
  {Name} Daily QA Report
  Date: {Month Day, Year}

  Testing Summary:
  - Activity: {code}
    Environment: {env}
    Result: {result}
  ...

  Test Coverage :
  - Activity: {code}
    {link}
  ...

  Current issues:
  - {code}: {issue text}
  ...

  Current Status:
  - {code}: {status}
  ...
  ```
- Sections with no data (e.g., no issues logged) are omitted entirely rather than shown empty.
- Copy and download use the selected saved format: `qa-report-YYYY-MM-DD-slack.md`, `qa-report-YYYY-MM-DD.md`, or `qa-report-YYYY-MM-DD.txt`. "Simpan & ekspor Slack .md" always saves the current input before exporting Slack markup.
- Generated section headings are bold in Slack markup and headings in standard Markdown. Free-text notes preserve the user's syntax without converting between the two dialects. Slack control characters are escaped. Actual paste rendering depends on Slack's composer; it is not guaranteed by this source preview.
- The report remains editable after copying/downloading. No direct send or finalization control appears in the current UI.

### US-4: Edit report metadata
**As a** QA tester
**I want to** rename the report or change its date after creation
**So that** I can correct mistakes without starting over

**Acceptance Criteria:**
- Date and title are editable at any time before finalization.
- Changing the date checks for a duplicate report on that date and rejects the collision without overwriting either report.

### US-5: View report history
**As a** QA tester
**I want to** browse past daily reports in a calendar or list view
**So that** I can find and reuse historical data

**Acceptance Criteria:**
- The default QA Reports view lists reports chronologically, oldest at the top and newest at the bottom, filterable by date range and by environment/result. Pagination uses this ordering globally and provides a shortcut to the last page.
- Clicking a past report opens a read-only view with an "Edit" toggle.
- Search by ticket code across all historical reports is supported.

### US-6: Monthly metrics dashboard
**As a** QA tester / team lead
**I want to** see aggregated metrics for a given month
**So that** I can understand testing throughput and quality trends

**Acceptance Criteria:**
- Dashboard is filterable by month/year.
- Metrics displayed:
  - Total activities tested.
  - Pass rate (% `Pass` of all results logged).
  - Breakdown by environment (Dev/Staging/Prod distribution).
  - Breakdown by result status (Pass/Fail/In Progress/Blocked).
  - Count of activities with at least one logged issue.
  - Trend chart: activities tested per day across the month.
- All metrics are computed from `report_items` joined to `daily_reports` for the selected month; no separate materialized aggregation table required in v1 (computed on read, cached briefly if slow).
- Dashboard supports export to CSV for the selected month.

### US-7: Delete an incorrect report

**As a** QA tester, **I want to** remove a saved report after confirmation, **so that** accidental entries do not remain in history or monthly metrics.

**Acceptance Criteria:**
- Delete is available from the list and report detail, including finalized/sent reports.
- Confirmation identifies the saved title, date, and activity count and warns that deletion is permanent, including any unsaved local changes.
- A stale report version returns a conflict instead of deleting a report changed in another tab.
- Successful deletion removes all associated activities and links and refreshes the list. Nothing is posted to or deleted from external services.

### US-8: Back up and restore QA reports

**As a** QA tester, **I want to** download and restore a portable JSON backup, **so that** I can recover reports from a backup made before accidental deletion.

**Acceptance Criteria:**
- An authenticated user can download every QA report, including status, metadata, activities, and coverage links; active filters and pagination do not restrict the backup.
- The file identifies its format, schema version, and export time. Limits are 1,000 reports and 10 MiB; exceeding a limit returns an error, never a silently truncated backup.
- Selecting a file does not restore immediately. A confirmation explains that existing dates will be skipped, not overwritten.
- Invalid JSON, unsupported schema versions, duplicate dates within the file, and invalid report/activity fields are rejected before any report is inserted.
- Restore inserts missing dates atomically with fresh report/activity IDs, retains saved status and content, and reports restored/skipped counts. Repeating a restore safely skips existing dates.
- Accounts, credentials, sessions, environment configuration, and external messages are outside the backup scope. Files are unencrypted and should be stored privately.

## 6. Edge Cases
- Duplicate ticket code logged twice in the same day (e.g., re-tested after a fix): both entries are kept as separate rows; the dashboard should not double-count silently without indicating it's two entries for the same code.
- Empty report (created but no items added): excluded from "Generate Report" action with a friendly warning, not a silent empty message.
- Coverage link validation: must be a well-formed URL; invalid URLs are flagged inline but do not block saving the item (network access to validate link reachability is out of scope for v1).

## 7. Future Considerations (out of scope for v1)
- Jira/Linear API integration to auto-pull ticket titles/status.
- Scheduled auto-send (e.g., auto-post to Slack every weekday at 6pm).
- Team-wide aggregated dashboard (multi-user).
