# Design: Rework Visual Datara

## Technical Approach

Single-process FastAPI server (uvicorn) serving both REST API (`/api/`) and static Stitch frontend (`/`). Stitch generates declarative screens as HTML/JS. Each screen communicates with the backend via fetch calls carrying `X-Session-Id`. Five FastAPI routers wrap existing services (FileService, CodeExecutor, LLMService, ExportService) — zero backend code changes. Plotly charts remain server-side: figures rendered as HTML strings and injected via `innerHTML` in the frontend. Session state lives in an in-memory `dict[str, SessionData]` with TTL eviction.

---

## Architecture Decisions

### ADR-1: FastAPI over Flask / raw Streamlit

| Option | Tradeoff | Decision |
|--------|----------|----------|
| **FastAPI** | Pydantic validation, async, OpenAPI docs, uvicorn-native | **Chosen** — matches Python 3.12+, auto request/response validation |
| Flask | More mature, larger community | Rejected — no native async, manual validation, no OpenAPI |
| Streamlit as REST bridge | Zero new code | Rejected — couples UI to Streamlit runtime, breaks independence |

### ADR-2: Config-based dashboard (figures rebuilt at render)

| Option | Tradeoff | Decision |
|--------|----------|----------|
| **Store config only, rebuild on GET** | Stateless, filterable, single source of truth | **Chosen** — dashboard_items stores chart_type + mappings; figure rebuilt per request with optional filter params |
| Store pre-rendered HTML | Fast response, no recompute | Rejected — can't apply filters, stale if data changes, per-item invalidation complexity |

### ADR-3: Client-side PNG export (no kaleido)

| Option | Tradeoff | Decision |
|--------|----------|----------|
| **Plotly.js `downloadImage()`** | No binary dep, uses plotly.js already loaded, async | **Chosen** — eliminates kaleido (heavy, binary, Windows ThreadPool issues). REQ-API-E01 returns HTML; client calls `Plotly.downloadImage()` |
| Server-side kaleido | Works in Streamlit | Rejected — kaleido 35MB binary, ThreadPoolExecutor hangs on Windows (observed), pytest compat issues |
| Hybrid fallback | Best of both | Rejected — complexity not justified; pure client works for MVP |

### ADR-4: In-memory sessions (no database)

| Option | Tradeoff | Decision |
|--------|----------|----------|
| **In-memory dict[str, SessionData]** | Loss on restart, no infra, matches current behavior | **Chosen** — Streamlit also loses state on restart. TTL eviction per REQ-SS-07. Zero migration |
| SQLite | Persists across restarts | Rejected — over-engineering for MVP; adds schema management, migration risk |
| Redis | Distributed, production-ready | Rejected — infra dependency for single-process app |

### ADR-5: `sessionStorage` over localStorage / cookies

| Option | Tradeoff | Decision |
|--------|----------|----------|
| **sessionStorage** | Lost on tab close, survives F5/nav, explicit header | **Chosen** — REQ-SS-06: session tied to browser tab. No auto-send (explicit `X-Session-Id`) |
| localStorage | Survives tab close | Rejected — session creep across unrelated browsing contexts |
| Cookie (httpOnly) | Auto-sent, no JS needed | Rejected — CSRF surface, harder to manage in Stitch declarative model |

---

## FastAPI Layer Design

### Project structure

```
api/
├── __init__.py
├── main.py                # app factory, CORS, lifespan, static mount
├── dependencies.py        # get_session(), get_store() FastAPI dependencies
├── session_store.py       # SessionStore class: dict[str, SessionData] + TTL
├── session_data.py        # SessionData dataclass
├── models/
│   ├── __init__.py
│   ├── files.py           # FileMetadata, FilePreview, UploadResponse
│   ├── chat.py            # MessageRequest, MessageResponse
│   ├── dashboard.py       # DashboardItem, DashboardResponse
│   ├── settings.py        # SettingsRequest, SettingsResponse
│   ├── session.py         # SessionState, SessionResetResponse
│   └── errors.py          # ErrorResponse, ErrorCode(str, Enum)
└── routers/
    ├── __init__.py         # include all routers into api_router
    ├── files.py            # prefix: /api/files
    ├── chat.py             # prefix: /api/chat
    ├── dashboard.py        # prefix: /api/dashboard
    ├── settings.py         # prefix: /api/settings
    ├── session.py          # prefix: /api/session
    └── export.py           # prefix: /api/export
```

### Route organization

One router per resource group. `api/routers/__init__.py` aggregates them into an `api_router` via `include_router()`. `api/main.py` mounts this under the FastAPI app. Each router uses `dependencies=[Depends(get_session)]` at the router level — all endpoints require `X-Session-Id`.

### Dependencies

- `fastapi>=0.115.0` — framework
- `uvicorn[standard]>=0.34.0` — server (standard extras for websocket support, though not used yet)
- `python-multipart>=0.0.20` — file upload parsing
- `pydantic>=2.0` — already a FastAPI dep, explicit for settings

### Session management

UUID v4 generated server-side on `POST /api/session/reset`. Returned in response body. Client stores in `sessionStorage` and sends as `X-Session-Id` header. Server holds `SessionStore`:

```python
@dataclass
class SessionData:
    file_service: FileService
    chat_messages: list[ChatMessage]
    dashboard_items: list[dict]
    created_at: float
    last_active: float

class SessionStore:
    _sessions: dict[str, SessionData]
    _ttl: int  # seconds, default 3600

    def get(self, sid: str) -> SessionData | None
    def create(self) -> str  # returns new UUID
    def reset(self, sid: str) -> str  # returns new UUID
    def _evict_expired(self)
```

### Request/response models

Pydantic v2 models in `api/models/`. Every response wraps data directly (not in an envelope). Errors use a uniform shape:

```json
{"error": "Human-readable message", "code": "ERROR_CODE"}
```

HTTP codes: 400 (bad request / missing session), 404 (not found / expired session), 409 (duplicate filename), 503 (service unavailable — LLM not configured).

### CORS

Allow `http://localhost:8501` (Streamlit dev) and `http://localhost:8000` (FastAPI self). Methods: GET, POST, PUT, DELETE, OPTIONS. Headers: Content-Type, X-Session-Id.

### Startup

`lifespan` context manager: load `.env`, instantiate `SessionStore`. No global state — store lives as app state (`request.app.state.store`).

---

## Stitch Frontend Design

### How Stitch is used

Stitch generates HTML/JS from JSON screen definitions. Each screen is a separate `.json` file in `frontend/screens/`. These are loaded by a small JS router (`frontend/app.js`) that swaps content in a root `<div>` on navigation. Stitch handles layout and component rendering; custom JS handles API calls, session management, and Plotly chart injection.

### Screen definitions

| Screen | File | Key Components |
|--------|------|----------------|
| Upload | `upload.json` | Dropzone, file list, expandable preview table, duplicate/resolution dialog |
| Chat | `chat.json` | Scrollable message list, text input, message card (text + chart + table) |
| Dashboard | `dashboard.json` | KPI card row, 2-column chart grid, filter bar, clear button |
| Settings | `settings.json` | Password input, model dropdown, apply button, session reset, app info |
| Sidebar | `sidebar.json` | Nav buttons, file/message counts, active files, new session button |

### Component tree

```
App
├── Sidebar (persistent)
│   ├── NavLink (Upload)
│   ├── NavLink (Chat)
│   ├── NavLink (Dashboard)
│   ├── NavLink (Settings)
│   ├── FileCount
│   ├── MessageCount
│   ├── ActiveFileList
│   └── NewSessionButton
│
└── ScreenContainer (dynamic)
    ├── Upload
    │   ├── Dropzone (drag/drop + file input)
    │   ├── DuplicateDialog (conditional)
    │   ├── SheetSelector (conditional)
    │   └── FileList
    │       └── FileCard → PreviewTable (expandable)
    │
    ├── Chat
    │   ├── ExportConversationButton
    │   ├── MessageList
    │   │   └── MessageCard (role, text, Plotly chart, table, export buttons)
    │   └── TextInput
    │
    ├── Dashboard
    │   ├── FilterBar
    │   ├── ClearButton
    │   ├── KPIRow
    │   │   └── KPICard (label + value)
    │   └── ChartGrid
    │       └── ChartCard (title + Plotly chart + delete)
    │
    └── Settings
        ├── ApiKeyInput (password)
        ├── ModelSelector (dropdown)
        ├── ApplyButton
        ├── SessionResetButton
        └── AppInfo
```

### State management

No framework — plain JS module pattern. `app.js` holds:
- `state.sessionId` — UUID string (from `sessionStorage`)
- `state.currentScreen` — string (`"upload"`, `"chat"`, etc.)
- Sidebar refreshes via `GET /api/session` on every screen transition

Stitch's own data-binding handles per-screen form state.

### Plotly chart rendering

Each MessageResponse and DashboardItem includes `figure_html` — a Plotly HTML `<div>` string generated server-side via `ExportService.chart_to_html()`. The frontend injects this into a container element via `innerHTML`. `plotly.js` (loaded from CDN in `index.html`) auto-initializes any `<div>` with class `plotly-graph-div`. No manual `Plotly.newPlot()` calls needed.

Export: `Plotly.downloadImage(graphDiv, {format: 'png', width: 1200, height: 800, scale: 2})` — no kaleido.

### API client layer

`frontend/api.js` — thin fetch wrapper:

```javascript
export async function api(method, path, body?, options?): Promise<Response> {
  const headers = { 'X-Session-Id': state.sessionId };
  if (body && !(body instanceof FormData)) headers['Content-Type'] = 'application/json';
  const res = await fetch(`/api${path}`, { method, headers, body: body instanceof FormData ? body : JSON.stringify(body) });
  if (!res.ok) { showToast(await res.json()); throw new Error(res.status); }
  return res;
}
```

### Session ID flow

```
Page load → sessionStorage has ID?
  ├── Yes → state.sessionId = stored ID → render
  └── No  → POST /api/session/reset → store returned UUID → render
Every API call → api() reads state.sessionId → X-Session-Id header
New Session button → POST /api/session/reset → replace stored ID → navigate to Upload
```

---

## Data Flow Diagrams

### Upload flow

```
Browser                    FastAPI                       FileService
  │                          │                              │
  │ POST /api/files/upload   │                              │
  │ multipart (file + sheet) │                              │
  ├─────────────────────────►│ load_from_bytes(filename,    │
  │                          │   content)                   │
  │                          ├─────────────────────────────►│
  │                          │◄── (True, FileData) ────────┤
  │                          │ add_file(FileData)           │
  │                          ├─────────────────────────────►│
  │◄── 201 FileMetadata ────┤                              │
```

### Chat flow

```
Browser               FastAPI              CodeExecutor         LLMService       Sandbox
  │                     │                      │                    │               │
  │ POST /api/chat/     │                      │                    │               │
  │ message              │                      │                    │               │
  │ {message}            │                      │                    │               │
  ├────────────────────►│ analyze(q, files,    │                    │               │
  │                     │   chat_history)       │                    │               │
  │                     ├─────────────────────►│ generate_code()    │               │
  │                     │                      ├───────────────────►│               │
  │                     │                      │◄── (code, text) ──┤               │
  │                     │                      │ execute(code, dfs) │               │
  │                     │                      ├──────────────────────────────────►│
  │                     │                      │◄── result ────────┤               │
  │◄── 200 MessageRes──┤                      │                    │               │
  │  {content,          │                      │                    │               │
  │   figure_html,      │                      │                    │               │
  │   message_id}        │                      │                    │               │
```

### Dashboard render flow

```
Browser               FastAPI              SessionData          CodeExecutor / ExportService
  │                     │                      │                         │
  │ GET /api/dashboard  │                      │                         │
  │ ?filter_col=X       │                      │                         │
  │ &filter_vals=A,B    │                      │                         │
  ├────────────────────►│ get dashboard_items  │                         │
  │                     ├─────────────────────►│                         │
  │                     │◄── [{id, title,      │                         │
  │                     │       type, config}] ─┤                         │
  │                     │ for each item:                                 │
  │                     │   filter df → rebuild figure from config       │
  │                     │   or compute KPI value                         │
  │◄── 200 {items: [    │                      │                         │
  │  {figure_html,      │                      │                         │
  │   title, id}]} ─────┤                      │                         │
```

### Session lifecycle

```
[Tab opens]
    │
    ├── sessionStorage has UUID?
    │      ├── Yes → use it
    │      └── No  → POST /api/session/reset
    │                  └── store returned new_session
    │
    ├── [All requests] → X-Session-Id: <UUID>
    │                      └── FastAPI → sessions[UUID] → SessionData
    │
    ├── [Tab closes] → sessionStorage lost → next open = new session
    │
    ├── [Idle > 1hr] → SessionStore TTL eviction → 404 on next request → client resets
    │
    └── [New Session click]
         └── POST /api/session/reset
              ├── old session stays (can be accessed until TTL)
              └── client stores new UUID
```

---

## File Structure

```
project-root/
├── api/
│   ├── __init__.py
│   ├── main.py                # CREATE
│   ├── dependencies.py        # CREATE
│   ├── session_store.py       # CREATE
│   ├── session_data.py        # CREATE
│   ├── models/
│   │   ├── __init__.py        # CREATE
│   │   ├── files.py           # CREATE
│   │   ├── chat.py            # CREATE
│   │   ├── dashboard.py       # CREATE
│   │   ├── settings.py        # CREATE
│   │   ├── session.py         # CREATE
│   │   └── errors.py          # CREATE
│   └── routers/
│       ├── __init__.py        # CREATE
│       ├── files.py           # CREATE
│       ├── chat.py            # CREATE
│       ├── dashboard.py       # CREATE
│       ├── settings.py        # CREATE
│       ├── session.py         # CREATE
│       └── export.py          # CREATE
├── frontend/
│   ├── index.html             # CREATE — Stitch root, plotly.js CDN
│   ├── app.js                 # CREATE — router, state, session init
│   ├── api.js                 # CREATE — fetch wrapper
│   ├── styles.css             # CREATE — layout, toast, grid
│   └── screens/
│       ├── upload.json        # CREATE
│       ├── chat.json          # CREATE
│       ├── dashboard.json     # CREATE
│       ├── settings.json      # CREATE
│       └── sidebar.json       # CREATE
├── run.py                     # CREATE — uvicorn entry point
├── requirements.txt           # MODIFY — add fastapi, uvicorn, python-multipart
└── app/                       # UNCHANGED — Streamlit keeps working
```

---

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | Pydantic models | Validate creation, serialization roundtrip, field constraints via `pydantic.BaseModel.model_validate()` |
| Unit | SessionStore | TTL eviction with `time_mock`, session isolation, reset creates new UUID, get returns None for unknown |
| Integration | Each router | `fastapi.testclient.TestClient` with mocked services. One test file per router. Verify status + response shape |
| Integration | Chat E2E | Mock CodeExecutor → return known AnalysisResult → assert MessageResponse has figure_html |
| Manual | 5 Stitch screens | Visual: screens render, navigation works, sidebar indicators update |
| E2E | Cross-screen session | Start: no ID → upload file → navigate to Chat → verify file persists via sidebar |

---

## Migration / Rollout

No migration required. FastAPI runs on port 8000 (default uvicorn). Streamlit continues on 8501. Deployment switch: `streamlit run app/main.py` → `python run.py`. Both can coexist during testing — CORS allows Streamlit dev to call FastAPI for incremental testing.

---

## Open Questions

None.
