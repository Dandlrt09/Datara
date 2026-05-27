# Delta: Session State

## Description

The current Streamlit `st.session_state` mechanism (in-memory dict tied to Streamlit's internal session) shifts to an explicit session UUID stored server-side. The server manages per-session state in a dict keyed by UUID. The client sends `X-Session-Id` on every request.

---

## MODIFIED Requirements

### REQ-SS-01: File persistence

Uploaded files SHALL persist in memory for the duration of the session. Navigating between screens MUST NOT clear loaded files.
(Previously: files persisted in `st.session_state.file_service` dict tied to Streamlit session)

**Mechanism change**: Files are stored in a `dict[str, FileService]` keyed by session UUID. `FileService` itself is unchanged — it already holds an in-memory `_files` dict.

#### Scenario SS-S1: File persistence across pages
- GIVEN a user uploads "data.csv" on the Upload screen
- WHEN they navigate to the Chat screen
- THEN GET /api/files returns "data.csv" in the file list

### REQ-SS-02: Chat history

The conversation SHALL be stored server-side as a list of message dicts per session. Newest at the end.
(Previously: `st.session_state.chat_messages` list of ChatMessage objects)

#### Scenario SS-S2: Chat persists across navigation
- GIVEN a user sends 3 messages on the Chat screen
- WHEN they navigate to Dashboard and back to Chat
- THEN GET /api/chat/history returns all 3 messages in order

### REQ-SS-03: State isolation

Each session SHALL have isolated state. Data from one session MUST NOT be visible to another session.
(Previously: Streamlit's built-in per-tab isolation)

**Mechanism change**: Isolation now relies on the `X-Session-Id` header. The server maintains `sessions: dict[str, SessionData]`. Each `SessionData` holds independent `FileService`, `chat_messages`, and `dashboard_items`.

#### Scenario SS-S3: Session isolation
- GIVEN Session A loads "sales.csv" and Session B is empty
- WHEN GET /api/files is called with Session A's header
- THEN the response includes "sales.csv"
- WHEN GET /api/files is called with Session B's header
- THEN the response is an empty array

### REQ-SS-04: Session reset

The user SHALL have a "Nueva sesión" button that clears all files, chat history, dashboard items, and assigns a NEW session UUID.
(Previously: called `file_service.clear_all()`, cleared `chat_messages`, and navigated to Upload)

**Mechanism change**: The server creates a new UUID, allocates a fresh `SessionData`, and returns both old and new IDs. The client stores the new ID and uses it for all subsequent requests.

#### Scenario SS-S4: Reset session
- GIVEN a session with 3 loaded files and 10 messages
- WHEN the user clicks "Nueva sesión"
- THEN POST /api/session/reset returns `{old_session, new_session}`
- AND the client replaces the stored session ID
- AND subsequent GET /api/files returns []
- AND GET /api/chat/history returns []

### REQ-SS-05: State indicators

The UI SHALL show:
- Number of loaded files
- Number of messages in current conversation
- Active file names
(Previously: read directly from `st.session_state`)

**Mechanism change**: The sidebar fetches this data via `GET /api/session` on every navigation (or on a periodic refresh). The response includes `file_count`, `files[]`, `message_count`, and `provider`.

#### Scenario SS-S5: Indicators from API
- GIVEN a session with "ventas.csv" and 3 chat messages
- WHEN the sidebar renders
- THEN GET /api/session returns `{file_count: 1, files: ["ventas.csv"], message_count: 3}`
- AND the sidebar displays these values

---

## ADDED Requirements

### REQ-SS-06: Session ID lifecycle

The system SHALL generate a UUID v4 on session creation (first request or reset). The client SHALL store this ID in `sessionStorage` (lost on tab close) and send it as `X-Session-Id` header.

#### Scenario SS-S6: First request creates session
- GIVEN a client has no session ID
- WHEN it calls POST /api/session/reset
- THEN the server generates a new UUID
- AND returns it in the response body
- AND the client stores it for subsequent requests

### REQ-SS-07: Session cleanup

The server MAY evict sessions older than a configurable TTL (default: 1 hour of inactivity). Evicted sessions SHALL return `404` on any request with that ID, prompting the client to create a new session.
