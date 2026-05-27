# Tasks: Rework Visual Datara

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 1,200–1,400 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | 3 PRs (Foundation → API Layer → Frontend) |
| Delivery strategy | auto-chain |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Scope | Base | Key files |
|------|-------|------|-----------|
| 1 | API infra + session + models + tests | main | `api/session_store.py`, `api/session_data.py`, `api/models/*`, `run.py`, `requirements.txt`, `tests/test_session_store*`, `tests/test_api_models*` |
| 2 | API routers + main + integration tests | PR 1 | `api/routers/*`, `api/main.py`, `api/dependencies.py`, `tests/test_api_routers*`, `tests/conftest.py` |
| 3 | Stitch frontend all screens | PR 2 | `frontend/*`, `frontend/screens/*` |

---

## Phase 1: Foundation — API Infrastructure & Session

- [x] 1.1 Create `api/__init__.py`, `api/session_data.py`, `api/session_store.py` — SessionData dataclass + SessionStore with TTL eviction
- [x] 1.2 Create `api/dependencies.py` — `get_session()` and `get_store()` FastAPI deps extracting `X-Session-Id`
- [x] 1.3 Create `api/models/errors.py` — ErrorResponse, ErrorCode enum
- [x] 1.4 Create `api/models/files.py` — FileMetadata, FilePreview, UploadResponse
- [x] 1.5 Create `api/models/chat.py` — MessageRequest, MessageResponse
- [x] 1.6 Create `api/models/dashboard.py` — DashboardItem, DashboardResponse
- [x] 1.7 Create `api/models/settings.py` — SettingsRequest, SettingsResponse
- [x] 1.8 Create `api/models/session.py` — SessionState, SessionResetResponse
- [x] 1.9 Create `api/models/__init__.py` — re-export all models
- [x] 1.10 Create `run.py` — uvicorn entry point (`python run.py`)
- [x] 1.11 Modify `requirements.txt` — add `fastapi>=0.115.0`, `uvicorn[standard]>=0.34.0`, `python-multipart>=0.0.20`
- [x] 1.12 Write `tests/test_session_store.py` — TTL eviction, isolation, reset, unknown ID returns None
- [x] 1.13 Write `tests/test_api_models.py` — Pydantic model creation, validation roundtrip, field constraints

**Fulfills**: REQ-SS-01, REQ-SS-02, REQ-SS-03, REQ-SS-05, REQ-SS-06, REQ-SS-07

## Phase 2: API Routers

- [x] 2.1 Create `api/routers/__init__.py` — aggregate routers into `api_router`
- [x] 2.2 Create `api/routers/session.py` — `GET /api/session`, `POST /api/session/reset`
- [x] 2.3 Create `api/routers/files.py` — `POST /api/files/upload`, `GET /api/files`, `DELETE /api/files/{filename}`, `GET /api/files/{filename}/preview`
- [x] 2.4 Create `api/routers/chat.py` — `POST /api/chat/message`, `GET /api/chat/history`, `DELETE /api/chat/clear`
- [x] 2.5 Create `api/routers/dashboard.py` — `GET /api/dashboard` (filter params), `POST /api/dashboard`, `DELETE /api/dashboard/{item_id}`
- [x] 2.6 Create `api/routers/settings.py` — `GET /api/settings`, `PUT /api/settings`
- [x] 2.7 Create `api/routers/export.py` — `GET /api/export/{mid}/chart`, `GET /api/export/{mid}/data`, `GET /api/export/session`
- [x] 2.8 Create `api/main.py` — app factory, CORS (localhost:8501/8000), lifespan (load .env, init store), static mount `frontend/`
- [x] 2.9 Write `tests/conftest.py` — TestClient fixture with mocked services
- [x] 2.10 Write `tests/test_api_routers.py` — integration per router: status codes + response shape + error states

**Fulfills**: REQ-API-00, REQ-API-00a, REQ-API-F01–F04, REQ-API-C01–C03, REQ-API-D01–D03, REQ-API-E01–E03, REQ-API-S01–S02, REQ-API-SS01–SS02

## Phase 3: Stitch Frontend

- [ ] 3.1 Create `frontend/api.js` — fetch wrapper with `X-Session-Id`, error toast, loading state
- [ ] 3.2 Create `frontend/app.js` — session init (sessionStorage check → POST /api/session/reset), screen router, sidebar refresh on nav
- [ ] 3.3 Create `frontend/styles.css` — layout grid, sidebar, toast, loading spinner, responsive
- [ ] 3.4 Create `frontend/index.html` — root HTML, plotly.js CDN, app container, script/style imports
- [ ] 3.5 Create `frontend/screens/sidebar.json` — nav buttons (Upload/Chat/Dashboard/Settings), file/message counts, active files, new session button
- [ ] 3.6 Create `frontend/screens/upload.json` — dropzone (drag/drop + click), file list, expandable preview, sheet selector, duplicate dialog
- [ ] 3.7 Create `frontend/screens/chat.json` — scrollable message list, text input, chart/table embeds, export buttons, no-files guard
- [ ] 3.8 Create `frontend/screens/dashboard.json` — KPI row, 2-column chart grid, filter bar, clear button
- [ ] 3.9 Create `frontend/screens/settings.json` — password API key input, model dropdown, apply, new session, app info

**Fulfills**: REQ-SF-01 through REQ-SF-28

## Phase 4: Integration & Polish

- [ ] 4.1 Verify static serving — FastAPI serves `index.html` at `/`, frontend loads without errors
- [ ] 4.2 Cross-screen E2E — upload file → navigate Chat → sidebar shows file count → session persists via X-Session-Id
- [ ] 4.3 Error/loading states — toast on API error, loading spinner during calls, no-files guard on Chat
- [ ] 4.4 Chart rendering — Plotly HTML injection renders inline, export PNG via `Plotly.downloadImage()`
