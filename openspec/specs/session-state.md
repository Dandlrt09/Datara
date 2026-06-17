# Spec: Session State

## Description

The system MUST maintain session state so that uploaded files, chat history,
dashboard items, and analysis results persist across page interactions within
a session. State is managed server-side in a dict keyed by session UUID,
with the client sending `X-Session-Id` on every request.

## Requirements

### REQ-SS-01: File persistence

Uploaded files SHALL persist in memory for the duration of the session.
Navigating between screens MUST NOT clear loaded files.

**Mechanism**: Files are stored in a `dict[str, FileService]` keyed by session
UUID. `FileService` itself is unchanged — it already holds an in-memory `_files`
dict.

#### Scenario SS-S1: File persistence across pages
- GIVEN a user uploads "data.csv" on the Upload screen
- WHEN they navigate to the Chat screen
- THEN GET /api/files returns "data.csv" in the file list

### REQ-SS-02: Chat history

The conversation SHALL be stored server-side as a list of message dicts per
session. Newest at the end.

**Mechanism**: Messages stored in `SessionData.chat_messages: list[ChatMessage]`.

#### Scenario SS-S2: Chat persists across navigation
- GIVEN a user sends 3 messages on the Chat screen
- WHEN they navigate to Dashboard and back to Chat
- THEN GET /api/chat/history returns all 3 messages in order

### REQ-SS-03: State isolation

Each session SHALL have isolated state. Data from one session MUST NOT be
visible to another session.

**Mechanism**: Isolation relies on the `X-Session-Id` header. The server
maintains `sessions: dict[str, SessionData]`. Each `SessionData` holds
independent `FileService`, `chat_messages`, and `dashboard_items`.

#### Scenario SS-S3: Session isolation
- GIVEN Session A loads "sales.csv" and Session B is empty
- WHEN GET /api/files is called with Session A's header
- THEN the response includes "sales.csv"
- WHEN GET /api/files is called with Session B's header
- THEN the response is an empty array

### REQ-SS-04: Session reset

The user SHALL have a "Nueva sesión" button. When the session has messages
or files, the system MUST auto-archive the current session to disk before
clearing state. The API response MUST include the archived session's
`archive_id` and `archive_name` alongside the new `session_id`.
(Previously: Reset cleared state without archiving)

**Mechanism**: The server creates a new UUID, allocates a fresh `SessionData`,
and returns both old and new IDs. The client stores the new ID and uses it
for all subsequent requests.

#### Scenario SS-S4: Reset session with auto-archive
- GIVEN a session with 3 loaded files and 10 messages
- WHEN the user clicks "Nueva sesión"
- THEN the session is auto-archived to disk
- AND all files are removed, chat is cleared
- AND the response includes archive info (archive_id, name) and new session_id
- AND the app returns to the initial upload state

### REQ-SS-05: State indicators

The UI SHALL show:
- Number of loaded files
- Number of messages in current conversation
- Active file names
- Current LLM provider/model

**Mechanism**: The sidebar fetches this data via `GET /api/session` on every
navigation (or on a periodic refresh). The response includes `file_count`,
`files[]`, `message_count`, and `provider`.

#### Scenario SS-S5: Indicators from API
- GIVEN a session with "ventas.csv" and 3 chat messages
- WHEN the sidebar renders
- THEN GET /api/session returns `{file_count: 1, files: ["ventas.csv"], message_count: 3}`
- AND the sidebar displays these values

### REQ-SS-06: Session ID lifecycle

The system SHALL generate a UUID v4 on session creation (first request or
reset). The client SHALL store this ID in `sessionStorage` (lost on tab close)
and send it as `X-Session-Id` header.

#### Scenario SS-S6: First request creates session
- GIVEN a client has no session ID
- WHEN it calls POST /api/session/reset
- THEN the server generates a new UUID
- AND returns it in the response body
- AND the client stores it for subsequent requests

### REQ-SS-07: Session cleanup

The server MAY evict sessions older than a configurable TTL (default: 1 hour
of inactivity). Evicted sessions SHALL return `404` on any request with that
ID, prompting the client to create a new session.

#### Scenario SS-S7: TTL eviction
- GIVEN a session has been idle for more than the TTL
- WHEN any API call is made with that session ID
- THEN the server returns `404`
- AND the client creates a new session

### REQ-SS-08: Warm-start archive scan

On server startup, the system SHOULD scan the archive directory and log the count of recovered archives. A corrupt or missing directory MUST NOT crash the server.

#### Scenario SS-S8: Warm-start with valid archives
- GIVEN an archive directory with 5 valid JSON files
- WHEN the server starts
- THEN the system logs "Recovered 5 archived sessions"
- AND the server continues normally

#### Scenario SS-S9: Corrupt directory on startup
- GIVEN the archive directory contains unreadable files
- WHEN the server starts
- THEN the system logs a warning and continues without crashing
