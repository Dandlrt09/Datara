# Proposal: Rework Visual Datara

## Intent

Replace Streamlit UI with a Google Stitch web frontend. Add FastAPI REST layer wrapping existing services. Decouple UI from Python runtime without touching backend code or 256 tests.

## Scope

### In Scope
- Stitch frontend, FastAPI REST, new session model (ID via REST)
- Screens: Upload, Chat, Dashboard, Settings, Sidebar/Nav | 12 endpoints
- Single process: API + static frontend

### Out of Scope
- Backend changes (services/, utils/, models/), database, auth, deployment

## Capabilities

### New
- `stitch-frontend`: Stitch-generated HTML/JS replacing Streamlit views
- `fastapi-layer`: REST API exposing services via FastAPI

### Modified
- `session-state`: REQ-SS-03 (isolation) / REQ-SS-05 (indicators) stay; mechanism shifts from Streamlit session_state to explicit session ID. Needs delta spec.

## Approach

Browser ←→ FastAPI REST ←→ services. Stitch generates declarative screens. Charts stay server-side Plotly HTML embedded as strings in the frontend.

## Screens

| Screen | Purpose | Endpoints |
|--------|---------|-----------|
| Upload | Dropzone, preview, file list | POST /files, GET /files, GET /files/{id}/preview |
| Chat | Message list, input, chart embeds | POST /chat, GET /chat, DELETE /chat |
| Dashboard | Chart grid (config-only, rebuilt at render) | GET/POST/DELETE /dashboard |
| Settings | LLM key, prefs form | GET/PUT /settings |
| Sidebar | File count, active file, session controls | GET /session, POST /session/reset |

## API Endpoints

| Group | Endpoints |
|-------|-----------|
| Files | `POST /api/files/upload`, `GET /api/files`, `DELETE /api/files/{id}`, `GET /api/files/{id}/preview` |
| Chat | `POST /api/chat/message`, `GET /api/chat/history`, `DELETE /api/chat/clear` |
| Export | `GET /api/export/{mid}/chart`, `GET /api/export/{mid}/data`, `GET /api/export/session` |
| Settings | `GET /api/settings`, `PUT /api/settings` |
| Session | `GET /api/session`, `POST /api/session/reset` |

## Key Decisions

- **State**: session UUID as header. Server stores DataFrames/chat in memory keyed by session. Client UI prefs in localStorage.
- **Charts**: Plotly HTML from server, injected via `innerHTML`. dashboard_items stores CONFIG only — figures rebuilt at render time.
- **Upload**: multipart/form-data POST → FileService.
- **Session**: in-memory dict keyed by explicit ID. Services never imported Streamlit — no backward compat issues.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Stitch HTML bloat | Low | Layout only |
| Plotly injection breaks interactivity | Med | Verify `plotly.js` standalone |

## Rollback

Streamlit app untouched. Revert: `streamlit run app/main.py`. FastAPI can coexist on another port during migration.

## Success Criteria

- [ ] 5 screens navigable in Stitch frontend
- [ ] 12 endpoints match existing service behavior
- [ ] 256 backend tests pass unmodified
- [ ] Session survives cross-screen navigation
- [ ] Chart rendering matches Streamlit output
- [ ] File upload → preview E2E
