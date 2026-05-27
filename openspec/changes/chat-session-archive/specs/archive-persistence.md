# Session Archive Specification

## Purpose

Allow users to archive, list, restore, rename, and delete past chat sessions. Archives persist metadata (file info, messages, provider) as JSON on disk, surviving server restarts — enabling session continuity beyond in-memory TTL.

## Requirements

### REQ-ARCH-01: Archive model

The system MUST model an archive with: `archive_id`, `name`, `original_session_id`, `archived_at`, `message_count`, `datasets` (metadata only, no DataFrames), full message list, and `provider`.

#### Scenario: Archive model structure

- GIVEN a session with 2 datasets and 5 messages using provider "gemini"
- WHEN the session is archived
- THEN the archive contains all messages, file metadata (filename, columns, shape, dtypes, preview_rows), provider name, and auto-generated name

### REQ-ARCH-02: Archive persistence

Archives MUST survive server restart via JSON on disk. The archive directory SHOULD be configurable via `ARCHIVE_DIR` env var, defaulting to `{project_root}/archives/`.

#### Scenario: Persist across restart

- GIVEN an archived session saved to disk
- WHEN the server restarts and scans the archive directory
- THEN the archived session is available for listing and restoring

#### Scenario: Missing archive directory

- GIVEN `ARCHIVE_DIR` points to a non-existent path
- WHEN the server starts
- THEN the system SHOULD create the directory or fall back to the default

### REQ-ARCH-03: List archived sessions

GET /api/session/archived MUST return `archive_id`, `name`, `archived_at`, `message_count`, and dataset filenames. Results MUST be sorted by `archived_at` DESC (newest first). Empty archive list MUST return `[]`.

#### Scenario: List with archives

- GIVEN 3 archived sessions created at different times
- WHEN GET /api/session/archived is called
- THEN the response is an array sorted by archived_at descending
- AND each entry includes archive_id, name, archived_at, message_count, dataset filenames

#### Scenario: Empty archive list

- GIVEN no archived sessions exist
- WHEN GET /api/session/archived is called
- THEN the response is `[]`

### REQ-ARCH-04: Get archive detail

GET /api/session/archived/{archive_id} MUST return full archive metadata plus all messages. SHOULD paginate messages if > 100 (or return all, since chat sessions tend to be small).

#### Scenario: Get detail with messages

- GIVEN an archive with 10 messages
- WHEN GET /api/session/archived/{id} is called
- THEN the response includes all metadata and the 10 messages

#### Scenario: Archive not found

- GIVEN an invalid archive_id
- WHEN GET /api/session/archived/{id} is called
- THEN the response is 404

### REQ-ARCH-05: Archive current session

POST /api/session/archived MUST require a valid X-Session-Id header. MUST serialize file metadata (filename, columns, shape, dtypes, preview_rows) — NOT full DataFrames. MUST serialize all chat messages. MUST assign auto-increment name "Sesión N" based on existing archive count. Returns 200 with `archive_id`, `name`, `archived_at`. Returns 409 if session is empty (no messages AND no files).

#### Scenario: Archive non-empty session

- GIVEN a session with 2 datasets and 5 messages
- WHEN POST /api/session/archived with X-Session-Id
- THEN the response is 200 with archive_id, name "Sesión 1", archived_at
- AND the archive is persisted to disk with metadata only (no DataFrames)

#### Scenario: Archive empty session

- GIVEN a session with no datasets and no messages
- WHEN POST /api/session/archived with X-Session-Id
- THEN the response is 409

#### Scenario: Auto-increment naming

- GIVEN 3 existing archives named "Sesión 1", "Sesión 2", "Sesión 3"
- WHEN a new session is archived
- THEN the name is "Sesión 4"

### REQ-ARCH-06: Auto-archive on reset

When POST /api/session/reset is called with a valid session that has messages OR files, the system MUST auto-archive before creating the new session. The response MUST include the old archive info alongside the new session ID.

#### Scenario: Reset triggers auto-archive

- GIVEN a session with 3 files and 8 messages
- WHEN POST /api/session/reset is called
- THEN the session is archived automatically
- AND the response includes archive_id, name, archived_at AND new session_id

### REQ-ARCH-07: Restore session from archive

POST /api/session/archived/{archive_id}/restore MUST create a new active session, load all messages into it, and return: `new_session_id`, `archive_name`, `datasets[]` (with metadata plus `needed: true`), and `messages[]`. MUST NOT auto-upload files — user re-uploads manually.

#### Scenario: Restore archive

- GIVEN an archive with 2 datasets ("ventas.csv", "clientes.xlsx") and 5 messages
- WHEN POST /api/session/archived/{id}/restore
- THEN a new session is created with all 5 messages loaded
- AND the response lists datasets with filenames and `needed: true`
- AND no files are auto-uploaded

### REQ-ARCH-08: Delete archived session

DELETE /api/session/archived/{archive_id} MUST remove the JSON file from disk. Returns 204 on success, 404 for unknown archive_id.

#### Scenario: Delete existing archive

- GIVEN an archived session on disk
- WHEN DELETE /api/session/archived/{id}
- THEN the JSON file is removed and response is 204

#### Scenario: Delete unknown archive

- GIVEN an invalid archive_id
- WHEN DELETE /api/session/archived/{id}
- THEN the response is 404

### REQ-ARCH-09: Rename archived session

PATCH /api/session/archived/{archive_id} MUST accept `{ "name": "..." }` in body, update the name field in the JSON file, and return updated archive metadata.

#### Scenario: Rename archive

- GIVEN an archived session named "Sesión 1"
- WHEN PATCH /api/session/archived/{id} with `{ "name": "Mi análisis" }`
- THEN the archive name is updated to "Mi análisis"
- AND the updated metadata is returned

### REQ-ARCH-10: Frontend — archived sessions list

Chat screen MUST show an "Sesiones anteriores" section when the current session is expired/empty. Each entry MUST display: name, message count, dataset list, and date. Each MUST have "Ver detalle" / "Restaurar" action buttons.

#### Scenario: Show archived sessions

- GIVEN the current session is expired and 2 archives exist
- WHEN the chat screen loads
- THEN "Sesiones anteriores" section appears with both archives
- AND each entry shows name, message count, datasets, and action buttons

### REQ-ARCH-11: Frontend — restore flow

After restoring, the UI MUST show a dataset requirements banner ("Esta sesión usaba: ventas.csv, clientes.xlsx"). Chat history MUST load into the message list. The UI MUST link to the Upload screen for file re-upload.

#### Scenario: Restore displays requirements

- GIVEN a user clicks "Restaurar" on an archive with 2 datasets
- WHEN the restore response is received
- THEN a banner shows the required dataset names
- AND chat history is populated in the message list
- AND a link to the Upload screen is displayed

### REQ-ARCH-12: Frontend — manual archive

Chat screen MUST have an "Archivar sesión" action. The system MUST confirm before archiving.

#### Scenario: Manual archive with confirmation

- GIVEN a chat screen with active messages
- WHEN the user clicks "Archivar sesión"
- THEN a confirmation dialog appears
- AND on confirm, POST /api/session/archived is called

### REQ-ARCH-13: Resilience

The system MUST handle corrupted archive JSON gracefully (skip corrupt entries, log warnings, return 500 with details on direct access). MUST handle disk full / permission errors gracefully. MUST handle concurrent operations via file-level locking or atomic write.

#### Scenario: Corrupted archive file

- GIVEN an archive file on disk with invalid JSON
- WHEN the archives list is requested
- THEN the system logs a warning and skips the corrupt entry
- AND a direct GET on that archive returns 500 with error details

#### Scenario: Disk write failure

- GIVEN the disk is full
- WHEN a session is archived
- THEN the response is a 500-level error with a descriptive message
- AND the error is logged server-side

#### Scenario: Concurrent archiving

- GIVEN two concurrent POST requests to archive different sessions
- WHEN both are processed simultaneously
- THEN neither write corrupts the other (file-level locking or atomic write prevents race)
