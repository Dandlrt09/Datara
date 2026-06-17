# FastAPI Layer — REST API Specification

## Purpose

FastAPI server wrapping existing services (FileService, CodeExecutor, LLMService, ExportService). Runs as a single process serving both the REST API and the static Stitch frontend. Session identified via `X-Session-Id` header.

## Requirements

### REQ-API-00: Session identity
Every authenticated endpoint SHALL extract the session UUID from the `X-Session-Id` header. If absent, the endpoint SHALL return `400 Bad Request`.

### REQ-API-00a: Static serving
The FastAPI server SHALL serve the Stitch frontend static files from a configured directory. Requests to `/` or unknown routes SHALL return `index.html`.

---

## Files Endpoints

### REQ-API-F01: Upload file

`POST /api/files/upload`

- Accepts `multipart/form-data` with field `file` (required) and optional `sheet_name` (string).
- Calls `FileService.load_from_bytes()`. Returns `201 Created` with file metadata on success.
- Returns `409 Conflict` if filename already exists without explicit resolution — client must first resolve via `POST /api/files/upload?replace=true` or use a new filename.
- Returns `400 Bad Request` on validation failure (unsupported type, empty file, size exceeded).

**Request:**
```
POST /api/files/upload
X-Session-Id: a1b2c3d4-...
Content-Type: multipart/form-data

file: <binary>
```

**Response `201`:**
```json
{
  "filename": "ventas.csv",
  "display_name": "ventas.csv",
  "rows": 150,
  "columns": 8,
  "size_bytes": 12400,
  "dtypes": {"Mes": "object", "Ventas": "int64"}
}
```

**Scenario API-F01-S1: Successful upload**
- GIVEN a valid CSV file
- WHEN POST /api/files/upload with the file
- THEN returns 201 with file metadata
- AND the file is available in GET /api/files

**Scenario API-F01-S2: Duplicate filename**
- GIVEN "data.csv" is already loaded
- WHEN POST /api/files/upload with another "data.csv"
- THEN returns 409 with `{"error": "Duplicate filename", "filename": "data.csv"}`

**Scenario API-F01-S3: Invalid file type**
- WHEN POST /api/files/upload with a `.pdf` file
- THEN returns 400 with `{"error": "Unsupported file format. Supported: csv, xlsx, json, tsv"}`

### REQ-API-F02: List files

`GET /api/files`

Returns `200 OK` with an array of file metadata objects (same shape as upload response).

**Scenario API-F02-S1: List files**
- GIVEN 2 files are loaded
- WHEN GET /api/files
- THEN returns 200 with an array of 2 file metadata objects

### REQ-API-F03: Delete file

`DELETE /api/files/{filename}`

Removes a file from the session. Returns `204 No Content`. Returns `404 Not Found` if file doesn't exist.

**Scenario API-F03-S1: Delete existing file**
- GIVEN "ventas.csv" is loaded
- WHEN DELETE /api/files/ventas.csv
- THEN returns 204
- AND GET /api/files no longer includes it

### REQ-API-F04: File preview

`GET /api/files/{filename}/preview`

Returns `200 OK` with the first 10 rows as JSON. Query param `?rows=25` SHALL override the row count (max 100). Returns `404` if file not found.

**Response:**
```json
{
  "filename": "ventas.csv",
  "columns": ["Mes", "Ventas"],
  "dtypes": {"Mes": "object", "Ventas": "int64"},
  "total_rows": 150,
  "preview": [
    {"Mes": "Enero", "Ventas": 15000},
    {"Mes": "Febrero", "Ventas": 18000}
  ]
}
```

**Scenario API-F04-S1: Get preview**
- GIVEN "ventas.csv" is loaded with 150 rows
- WHEN GET /api/files/ventas.csv/preview?rows=5
- THEN returns 200 with filename, columns, dtypes, total_rows, and 5 preview rows

---

## Chat Endpoints

### REQ-API-C01: Send message

`POST /api/chat/message`

Body: `{"message": "string"}`. Calls `CodeExecutor.analyze()` with current session files. Returns `200 OK` with:

```json
{
  "role": "assistant",
  "content": "El promedio de ventas es $16,500.",
  "figure_html": "<div>...plotly html...</div>",
  "dataframe_json": null,
  "message_id": "msg_1745012345",
  "has_figure": true,
  "has_dataframe": false
}
```

Returns `503` if LLM is not configured. Returns `400` if message is empty.

**Scenario API-C01-S1: Send question**
- GIVEN a session with "ventas.csv" loaded
- WHEN POST /api/chat/message with `{"message": "¿Cuál es el promedio de ventas?"}`
- THEN returns 200 with text answer
- AND optionally figure_html or dataframe_json

**Scenario API-C01-S2: No API key**
- GIVEN no API key is configured
- WHEN POST /api/chat/message with any question
- THEN returns 503 with `{"error": "API key not configured"}`

### REQ-API-C02: Get history

`GET /api/chat/history`

Returns `200 OK` with the full chat message array. Returns empty array if no messages.

### REQ-API-C03: Clear chat

`DELETE /api/chat/clear`

Removes all messages from the session. Returns `204 No Content`.

**Scenario API-C03-S1: Clear chat**
- GIVEN a session with 5 messages
- WHEN DELETE /api/chat/clear
- THEN returns 204
- AND GET /api/chat/history returns []

---

## Dashboard Endpoints

### REQ-API-D01: Get dashboard

`GET /api/dashboard`

Returns `200 OK` with dashboard items. Query params:
- `?filter_col=Region&filter_vals=Norte,Sur` — filters applied to all items at render time
- Filters SHALL be parsed as comma-separated values per column

**Response:**
```json
{
  "items": [
    {
      "id": "item_1745001",
      "title": "Ventas por mes",
      "type": "chart",
      "figure_html": "<div>...</div>",
      "config": {"chart_type": "Linea", "mappings": {"x": "Mes", "y": "Ventas"}}
    },
    {
      "id": "item_1745002",
      "title": "Promedio Ventas",
      "type": "kpi",
      "value": 16500.0,
      "config": {"column": "Ventas", "aggregation": "mean"}
    }
  ]
}
```

### REQ-API-D02: Add dashboard item

`POST /api/dashboard`

Body: `{"file": "filename", "title": "...", "config": {...}}`. The config SHALL be the same structure as current `dashboard_items` config (chart_type, mappings for charts; column, aggregation, group_by for KPIs).

Returns `201 Created` with the full item including server-generated `id`.

### REQ-API-D03: Delete dashboard item

`DELETE /api/dashboard/{item_id}`

Returns `204 No Content`.

**Scenario API-D01-S1: Get dashboard with filter**
- GIVEN 3 dashboard items exist
- WHEN GET /api/dashboard?filter_col=Region&filter_vals=Norte
- THEN all 3 items return with filter applied
- AND KPI values reflect the filtered data

---

## Export Endpoints

### REQ-API-E01: Export chart PNG

`GET /api/export/{message_id}/chart`

Returns `200 OK` with `Content-Type: image/png`. Returns `404` if message_id has no figure.

### REQ-API-E02: Export dataframe CSV

`GET /api/export/{message_id}/data`

Returns `200 OK` with `Content-Type: text/csv`. Returns `404` if message_id has no dataframe.

### REQ-API-E03: Export session

`GET /api/export/session`

Returns `200 OK` with `Content-Type: text/plain` containing the formatted conversation text.

**Scenario API-E01-S1: Download chart PNG**
- GIVEN message "msg_123" has a figure
- WHEN GET /api/export/msg_123/chart
- THEN returns 200 with image/png content

---

## Settings Endpoints

### REQ-API-S01: Get settings

`GET /api/settings`

Returns `200 OK`:
```json
{
  "api_key_configured": true,
  "api_key_masked": "AIzaSyA...xYz",
  "model": "models/gemini-2.5-flash",
  "available_models": ["models/gemini-2.5-flash", "models/gemini-2.0-flash"]
}
```

### REQ-API-S02: Update settings

`PUT /api/settings`

Body: `{"api_key": "...", "model": "..."}`. Rebuilds LLMService and CodeExecutor with new values. Returns `200 OK` with the updated settings (masked key).

**Scenario API-S01-S1: Update API key**
- GIVEN no API key is configured
- WHEN PUT /api/settings with `{"api_key": "AIzaSyA...", "model": "models/gemini-2.5-flash"}`
- THEN returns 200 with `api_key_configured: true`
- AND subsequent chat calls succeed

---

## Session Endpoints

### REQ-API-SS01: Get session state

`GET /api/session`

Returns `200 OK`:
```json
{
  "session_id": "a1b2c3d4-...",
  "file_count": 2,
  "files": ["ventas.csv", "empleados.xlsx"],
  "message_count": 5,
  "provider": "Gemini (models/gemini-2.5-flash)"
}
```

### REQ-API-SS02: Reset session

`POST /api/session/reset`

Clears all files, chat history, and dashboard items. Returns `200 OK` with the old session_id and a new session_id.

**Response:**
```json
{
  "old_session": "a1b2c3d4-...",
  "new_session": "e5f6g7h8-..."
}
```

**Scenario API-SS02-S1: Reset session**
- GIVEN a session with 3 files and 10 messages
- WHEN POST /api/session/reset
- THEN returns 200 with old_session and new_session
- AND GET /api/files returns []
- AND GET /api/chat/history returns []
- AND GET /api/dashboard returns `{"items": []}`
