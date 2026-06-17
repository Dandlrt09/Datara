# Design: Chat Session Archive

## Technical Approach

Disk-based JSON archive directory. On session reset or manual request, serialize `SessionData` metadata + messages into a standalone JSON file in `archives/`. A new `ArchiveService` wraps CRUD operations with atomic file writes + in-memory index rebuild on startup. Restore creates a fresh `SessionData`, loads messages into it, and returns dataset requirements for re-upload. This maps to the proposal's "Disk-based JSON archive" approach and satisfies all specs (REQ-ARCH-01 through REQ-ARCH-13).

## Architecture Decisions

### ADR-1: JSON file per archive vs single archive file vs SQLite

| Option | Tradeoff | Decision |
|--------|----------|----------|
| A: One JSON file per archive | Atomic per-file ops, easy to debug, no corruption cascade, trivial backup | ✅ **Chosen** |
| B: Single append-only log | Single point of corruption, rename deletes/re-writes entire file, parallelism hazard | ❌ |
| C: SQLite | Heavier dependency, schema migrations, overkill for metadata + message JSON blobs | ❌ |

**Rationale**: Per-file JSON gives us atomic reads/writes, trivial debugging (open any file), and natural isolation — one corrupt file doesn't lose all archives.

### ADR-2: File locking strategy for concurrent access

| Option | Tradeoff | Decision |
|--------|----------|----------|
| A: `threading.Lock` in `ArchiveService` | Same pattern as `SessionStore._lock` | ⚠️ Used alongside C |
| B: `fcntl`/`lockf` | Cross-process, but overengineered for single uvicorn worker | ❌ |
| C: Atomic write (tmp + rename) + best-effort | Prevents partial files without OS locks, zero cross-process needed | ✅ **Primary** |

**Rationale**: Write-to-tmp + `os.rename()` guarantees atomic file ops on the same filesystem. Wrap writes with `_lock` (same pattern as `SessionStore`) for Python-level safety. No cross-process locking needed (single worker).

### ADR-3: Archive naming — auto-increment vs UUID vs timestamp

| Option | Tradeoff | Decision |
|--------|----------|----------|
| A: `Sesión_1.json` | Rename forces filename change, breaks existing references | ❌ |
| B: `archive_{uuid}.json` | Collision-free, rename is metadata-only, clean | ✅ **Chosen** |
| C: `2026-05-22_15-30-00.json` | Readable but rename breaks filename, edge cases with same-second archives | ❌ |

**Rationale**: UUID filenames decouple file identity from user-facing name. Rename updates the `name` field inside JSON — the file stays put.

### ADR-4: Hook auto-archive in session router vs session store

| Option | Tradeoff | Decision |
|--------|----------|----------|
| A: Router calls `ArchiveService` before `store.create()` | Keeps `SessionStore` pure (no archiving concern), explicit in endpoint code | ✅ **Chosen** |
| B: `SessionStore.reset()` accepts `ArchiveService` callback | Couples store to archiving, breaks single-responsibility | ❌ |

**Rationale**: The router decides *when* to archive; the store decides *how* to store sessions. Router hook keeps concerns separated and makes the auto-archive flow explicit in `POST /api/session/reset`.

### ADR-5: Archive directory location

Default: `{project_root}/archives/`. Configurable via `ARCHIVE_DIR` env var. Created on first `ArchiveService` init if missing. Gitignored.

## Data Model

```python
@dataclass
class SessionArchive:
    archive_id: str           # "archive_{uuid4}"
    name: str                 # "Sesión N" (auto) or user-renamed
    original_session_id: str  # UUID of the archived session
    archived_at: float        # time.time()
    message_count: int
    datasets: list[ArchiveDataset]
    messages: list[ChatMessage]
    provider: str             # e.g. "Gemini (gemini-2.5-flash)"

@dataclass
class ArchiveDataset:
    filename: str
    columns: list[str]
    rows: int
    dtypes: dict[str, str]
    preview_rows: list[list]  # first 5 rows as Python lists
    is_large: bool            # True if rows > configurable threshold
```

## ArchiveService Design

```python
class ArchiveService:
    def __init__(self, archive_dir: str | Path):
        self._path = Path(archive_dir)
        self._path.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._scan_existing()           # warm index

    def list_archives(self) -> list[ArchiveSummary]
    def get_archive(self, archive_id: str) -> SessionArchive | None
    def save_archive(self, archive: SessionArchive) -> None   # atomic write
    def delete_archive(self, archive_id: str) -> bool
    def rename_archive(self, archive_id: str, new_name: str) -> SessionArchive

    # Internal
    def _next_archive_name(self) -> str     # "Sesión N" (scans existing names)
    def _archive_path(self, archive_id: str) -> Path  # archives/archive_{uuid}.json
    def _scan_existing(self) -> None        # rebuild index from disk, skip corrupt
    def _atomic_write(self, data: dict) -> None  # tmp + rename
```

Atomic write pattern:
```python
tmp = path.with_suffix(".tmp")
tmp.write_text(json_data, encoding="utf-8")
tmp.rename(path)  # atomic on same filesystem
```

## SessionStore Changes

```python
class SessionStore:
    # Existing methods unchanged

    def archive_session(self, sid: str, archive_service: ArchiveService) -> SessionArchive:
        """Serialize session data, save to disk, return SessionArchive."""
        data = self.get(sid)
        if data is None:
            raise ValueError("Session not found")
        archive = _build_archive(sid, data, archive_service._next_archive_name())
        archive_service.save_archive(archive)
        return archive

    def restore_archive(self, archive: SessionArchive) -> str:
        """Create new SessionData, load messages, return new session_id."""
        sid = self.create()
        data = self.get(sid)
        data.chat_messages = list(archive.messages)
        return sid
```

## Data Flow Diagrams

```
1. Manual archive:
   User → [Click "Archivar"] → POST /api/session/current/archive
     → session router → session_store.archive_session(sid, archive_svc)
     → ArchiveService.save_archive() → tmp + rename → archives/archive_{uuid}.json
     → 200 { archive_id, name, archived_at }

2. Auto-archive on reset:
   POST /api/session/reset (X-Session-Id present)
     → session router → reads old session
     → if non-empty: ArchiveService.save_archive()
     → store.create() → new session
     → 200 { old_session, new_session, archived: {...} | null }

3. Restore:
   User → [Click "Restaurar"] → POST /api/session/archived/{id}/restore
     → ArchiveService.get_archive(id) → read JSON from disk
     → session_store.restore_archive(archive) → new SessionData + messages
     → 200 { new_session_id, archive_name, datasets[], messages[] }

4. Startup scan:
   lifespan() → ArchiveService.__init__()
     → mkdir archives/ (if missing)
     → glob("archive_*.json") → parse each → build in-memory index
     → corrupt files: log warning, skip
```

## API Endpoints

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/api/session/archived` | 200 | List all archives (sorted DESC by archived_at) |
| GET | `/api/session/archived/{archive_id}` | 200/404 | Full archive detail + messages |
| POST | `/api/session/current/archive` | 200/409 | Archive current session (409 if empty) |
| POST | `/api/session/archived/{archive_id}/restore` | 200/404 | Restore archive as new active session |
| DELETE | `/api/session/archived/{archive_id}` | 204/404 | Delete archive file |
| PATCH | `/api/session/archived/{archive_id}` | 200/404 | Rename archive `{ "name": "..." }` |

### Modified Endpoint

| Method | Path | Change |
|--------|------|--------|
| POST | `/api/session/reset` | Response includes `archived: ArchiveInfo \| null` |

### Pydantic Models (in `api/models/session.py`)

```python
class ArchiveSummary(BaseModel):
    archive_id: str
    name: str
    archived_at: float
    message_count: int
    datasets: list[str]  # filenames only

class ArchiveDetail(BaseModel):
    archive_id: str
    name: str
    original_session_id: str
    archived_at: float
    message_count: int
    datasets: list[ArchiveDatasetMeta]
    messages: list[MessageResponse]
    provider: str

class ArchiveDatasetMeta(BaseModel):
    filename: str
    columns: list[str]
    rows: int
    dtypes: dict[str, str]
    preview_rows: list[list]
    is_large: bool
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `models/session_archive.py` | Create | `SessionArchive` + `ArchiveDataset` dataclasses |
| `services/archive_service.py` | Create | `ArchiveService` — JSON CRUD with atomic writes |
| `api/routers/archive.py` | Create | 6 new endpoints under `/api/session/archived` |
| `api/models/session.py` | Modify | Add `ArchiveSummary`, `ArchiveDetail`, `ArchiveDatasetMeta` Pydantic models, extend `SessionResetResponse` |
| `api/session_store.py` | Modify | Add `archive_session()` and `restore_archive()` methods |
| `api/routers/session.py` | Modify | Auto-archive on reset when session has messages/files |
| `api/routers/__init__.py` | Modify | Include archive router |
| `api/main.py` | Modify | Init `ArchiveService` in lifespan, attach to `app.state` |
| `api/dependencies.py` | Modify | Add `get_archive_service()` dependency |
| `frontend/api.js` | Modify | Add 6 new archive API methods |
| `frontend/screens/chat.html` | Modify | Archive button, restore flow, archived sessions panel |
| `frontend/screens/sidebar.inc.html` | Modify | "Sesiones anteriores" collapsible section |
| `.gitignore` | Modify | Add `archives/` |
| `tests/test_session_store.py` | Modify | Add archive_session + restore_archive unit tests |
| `tests/test_api_routers.py` | Modify | Add archive router integration tests |

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | `ArchiveService` — list, get, save, delete, rename, corrupt JSON, empty dir | Temp directory per test, `pathlib.Path` fixtures |
| Unit | `SessionStore.archive_session` — correct archive data, edge cases (empty session) | Mock `ArchiveService`, assert serialized fields |
| Unit | `SessionStore.restore_archive` — creates session with messages | Assert `store.get(new_id).chat_messages` length |
| Integration | Archive endpoints via TestClient — status codes, response shapes | Pre-seed store + temp archive dir |
| Integration | Auto-archive on reset — archive created, response includes it | Seed session with messages, call reset, assert `archived` in response |
| Resilience | Corrupted JSON, disk write failure | Write bad JSON to file, assert log warning + skip; mock `open()` to raise |

Extra test config: Add `archive_dir` fixture using `tmp_path`, wire to TestClient app state.

## Migration / Rollout

- First run: `ArchiveService.__init__` creates `archives/` dir automatically
- No existing data to migrate (sessions are ephemeral)
- All new code — existing endpoints untouched
- Rollback: remove archive router, revert frontend, delete new files
- Add `archives/` to `.gitignore`

## Open Questions

- [ ] What constitutes "large" dataset for `is_large` flag? (configurable threshold, default 10k rows?)
- [ ] Preview rows: should we cap at a fixed number (e.g. 5) or make it configurable?
