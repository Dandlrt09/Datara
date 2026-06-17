# Tasks: Chat Session Archive

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~800 (3 new + 12 modified files) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | 2 PRs: Backend → Frontend |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend — model, service, API, backend tests + startup | PR 1 | Base: main. Testable via TestClient alone. |
| 2 | Frontend — archive UI, restore flow, sidebar, polish | PR 2 | Base: main (or PR 1 branch if stacked). Depends on backend endpoints. |

## Phase 1: Foundation — Model + Service

- [x] 1.1 Create `models/session_archive.py` — `SessionArchive` + `ArchiveDataset` dataclasses with `to_dict()`/`from_dict()` JSON serialization
- [x] 1.2 Create `services/archive_service.py` — `ArchiveService` CRUD: list, get, save (atomic tmp+rename), delete, rename; thread-safe via `Lock()`; warm-start `_scan_existing()` skips corrupt JSON

## Phase 2: Backend — API

- [x] 2.1 Add `ArchiveSummary`, `ArchiveDetail`, `ArchiveDatasetMeta`, `ArchiveResponse` Pydantic models to `api/models/session.py`
- [x] 2.2 Add `archive_session()` and `restore_archive()` methods to `api/session_store.py`
- [x] 2.3 Create `api/routers/archive.py` — 6 endpoints: GET list, GET detail, POST archive current, POST restore, DELETE, PATCH rename
- [x] 2.4 Wire archive router in `api/routers/__init__.py`
- [x] 2.5 Add `get_archive_service()` factory dependency in `api/dependencies.py`
- [x] 2.6 Init `ArchiveService` in `api/main.py` lifespan, attach to `app.state`
- [x] 2.7 Modify `api/routers/session.py` — auto-archive on reset when session has messages or files

## Phase 3: Frontend

- [ ] 3.1 Add 6 archive API methods (list, get, archive, restore, delete, rename) to `frontend/api.js`
- [ ] 3.2 Add "Archivar sesión" button with confirmation, restore-result banner with dataset requirements, and archived-sessions panel to `frontend/screens/chat.html`
- [ ] 3.3 Add "Sesiones anteriores" collapsible section to `frontend/screens/sidebar.inc.html` with name, date, message count, action buttons
- [ ] 3.4 Add `archives/` to `.gitignore`

## Phase 4: Tests

- [x] 4.1 Write `ArchiveService` unit tests — all CRUD ops, corrupt JSON skip, empty dir, concurrent safety with Lock
- [x] 4.2 Write `SessionStore` archive/restore unit tests — correct field mapping, empty session edge case, message restoration
- [x] 4.3 Write archive router integration tests — all 6 endpoints + 404/409 via TestClient with `tmp_path` archive dir fixture
- [x] 4.4 Write resilience tests — corrupted JSON skip (warn log), atomic write, recover on restart, concurrent save

## Phase 5: Integration & Polish

- [ ] 5.1 Verify server starts with `ArchiveService` — `archives/` dir auto-created, warm-start scan logged
- [ ] 5.2 Verify archive/restore cycle: archive session → restart server → list → get detail → restore → messages in new session
- [ ] 5.3 Verify auto-archive on reset: session with messages → "Nueva sesión" → archive created in response, state cleared
