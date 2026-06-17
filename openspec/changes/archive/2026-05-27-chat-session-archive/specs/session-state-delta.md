# Delta for Session State

## MODIFIED Requirements

### REQ-SS-04: Session reset

The user SHALL have a "Nueva sesión" button. When the session has messages or files, the system MUST auto-archive the current session to disk before clearing state. The API response MUST include the archived session's `archive_id` and `archive_name` alongside the new `session_id`.
(Previously: Reset cleared state without archiving)

#### Scenario SS-S3: Reset session with auto-archive

- GIVEN a session with 3 loaded files and 10 messages
- WHEN the user clicks "Nueva sesión"
- THEN the session is auto-archived to disk
- AND all files are removed, chat is cleared
- AND the response includes archive info (archive_id, name) and new session_id
- AND the app returns to the initial upload state

## ADDED Requirements

### REQ-SS-06: Warm-start archive scan

On server startup, the system SHOULD scan the archive directory and log the count of recovered archives. A corrupt or missing directory MUST NOT crash the server.

#### Scenario: Warm-start with valid archives

- GIVEN an archive directory with 5 valid JSON files
- WHEN the server starts
- THEN the system logs "Recovered 5 archived sessions"
- AND the server continues normally

#### Scenario: Corrupt directory on startup

- GIVEN the archive directory contains unreadable files
- WHEN the server starts
- THEN the system logs a warning and continues without crashing
