# Proposal: Chat Session Archive

## Intent

Sessions lose all context on server restart or TTL expiry — files, messages, history gone. Instead of a generic "Sesión expirada", auto-archive metadata and messages to disk so users can restore previous sessions.

## Scope

### In Scope
- Archive model + JSON persistence on disk
- 6 new API endpoints (list, get, archive, restore, delete, rename)
- Auto-archive on session reset
- Frontend: archived session list, detail view, restore flow
- Sidebar: "Tus sesiones anteriores" section
- Tests (unit + integration)

### Out of Scope
- Persisting raw DataFrames (metadata only: filename, columns, shape, dtypes)
- Background TTL watcher (archiving on reset/restart is enough)
- Multi-user auth
- Storing Plotly figure HTML (already in ChatMessage)

## Capabilities

### New Capabilities
- `session-archive`: Archive, list, restore, delete, and rename past sessions with full metadata

### Modified Capabilities
- `session-state`: REQ-SS-04 (session reset) changes — reset now auto-archives before clearing. New requirements for archive persistence and restore.

## Approach

Disk-based JSON archive. On session reset, serialize `SessionData` (file metadata + chat messages) to `archives/{archive_id}.json`. New `ArchiveService` handles CRUD. Frontend calls new endpoints to show archived sessions and trigger restore. Restore creates a fresh session, loads messages, returns file requirements for re-upload.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `models/session_archive.py` | New | SessionArchive dataclass + serialization |
| `services/archive_service.py` | New | JSON file CRUD on disk |
| `api/routers/archive.py` | New | 6 endpoints under `/api/session/archived` |
| `api/models/session.py` | Modified | New Pydantic models for archive responses |
| `api/session_store.py` | Modified | Add archive/restore methods |
| `api/routers/__init__.py` | Modified | Include archive router |
| `frontend/api.js` | Modified | Archive API methods |
| `frontend/screens/chat.html` | Modified | Archive UI, restore flow |
| `frontend/screens/sidebar.inc.html` | Modified | Archived sessions list |
| `tests/test_session_store.py` | Modified | Archive unit tests |
| `tests/test_api_routers.py` | Modified | Archive integration tests |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Disk write failure (full/permissions) | Low | Graceful error in response, log + toast |
| Large message payloads | Medium | Paginated GET for archive detail |
| Archive file corruption | Low | Validate JSON on read, skip corrupt entries |

## Rollback Plan

All new code — existing endpoints untouched. Revert: remove archive router, revert frontend changes, delete `models/session_archive.py` and `services/archive_service.py`. Existing endpoints keep working.

## Success Criteria

- [ ] Archived sessions survive server restart (read from disk on warm start)
- [ ] User can list, view, restore, rename, and delete archived sessions
- [ ] Auto-archive fires on reset when session has messages or files
- [ ] Restore flow shows required datasets; re-upload enables continued chat
