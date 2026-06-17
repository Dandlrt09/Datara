# Stitch Frontend — Screens Specification

## Purpose

Five declarative Stitch screens replacing the current Streamlit views. The frontend communicates exclusively via REST — no server-side Python rendering. Charts are Plotly HTML strings injected via `innerHTML`.

---

## 1. Upload Screen

### REQ-SF-01: File dropzone
The system SHALL provide a drag-and-drop zone accepting `.csv`, `.xlsx`, `.json`, and `.tsv` files. Multiple file selection SHALL be supported.

### REQ-SF-02: Upload flow
On drop or selection, the system SHALL POST each file to `POST /api/files/upload` (multipart/form-data) and display per-file status (uploading / success / error).

### REQ-SF-03: Duplicate handling
If the response indicates a duplicate filename, the system SHALL prompt the user to replace or keep both before proceeding.

### REQ-SF-04: Multi-sheet Excel
If the uploaded file is `.xlsx` with multiple sheets, the server returns sheet options. The system SHALL display a sheet selector and re-POST with the chosen sheet name.

### REQ-SF-05: File list
Below the dropzone, the system SHALL render a list of loaded files showing: display name, row count, column count, size, and a delete button per file.

### REQ-SF-06: Data preview
Clicking a file in the list SHALL expand an inline preview table with the first 10 rows, column names, and data types.

#### Upload Screen Scenarios

**Scenario SF-Upload-S1: Happy path CSV upload**
- GIVEN the upload screen is displayed
- WHEN the user drops a valid `ventas.csv` file
- THEN the system POSTs to `/api/files/upload`
- AND on success, the file appears in the list with row/column info

**Scenario SF-Upload-S2: Excel with multiple sheets**
- GIVEN the user drops `datos.xlsx` with 3 sheets
- WHEN the upload completes
- THEN the system shows a sheet selector with the 3 sheet names
- WHEN the user selects "Sheet2"
- THEN the system re-uploads with `sheet_name=Sheet2`

**Scenario SF-Upload-S3: Duplicate filename**
- GIVEN `data.csv` is already loaded
- WHEN the user uploads a different `data.csv`
- THEN the system displays "Replace" / "Keep both" prompt
- WHEN the user clicks "Keep both"
- THEN both files appear in the list as `data.csv` and `data (2).csv`

**Scenario SF-Upload-S4: Invalid file type**
- WHEN the user drops a `.pdf` file
- THEN the system shows "Unsupported format. Accepted: CSV, Excel, JSON, TSV."

---

## 2. Chat Screen

### REQ-SF-07: No-files guard
If no files are loaded, the system SHALL display a message: "Upload a file first to start chatting." with a link to the Upload screen.

### REQ-SF-08: Message list
The system SHALL display a scrollable list of Q&A pairs. Assistant messages SHALL render text, embedded Plotly charts (via `innerHTML` of the returned HTML string), and data tables (first 100 rows).

### REQ-SF-09: Text input
The system SHALL provide a chat text input at the bottom. On submit, it SHALL POST to `POST /api/chat/message` and append the response to the message list.

### REQ-SF-10: Response export
Each assistant message SHALL include a "Copy response" button that downloads that message as `.txt`.

### REQ-SF-11: Chart export
Each rendered Plotly chart SHALL include a "Download PNG" button that calls `GET /api/export/{mid}/chart`.

### REQ-SF-12: DataFrame export
Each rendered data table SHALL have a "Download CSV" button that calls `GET /api/export/{mid}/data`.

### REQ-SF-13: Conversation export
The screen SHALL have an "Export conversation" button at the top that calls `GET /api/export/session` and downloads a `.txt` file.

#### Chat Screen Scenarios

**Scenario SF-Chat-S1: Ask a question**
- GIVEN a file "ventas.csv" is loaded
- WHEN the user types "¿Cuál es el promedio de ventas?" and hits enter
- THEN the message appears in the list
- AND the assistant responds with text + optionally a chart

**Scenario SF-Chat-S2: No files loaded**
- GIVEN no files are loaded
- WHEN the user navigates to Chat
- THEN the system shows "Upload a file first" with a link to Upload

**Scenario SF-Chat-S3: Export individual response**
- GIVEN an assistant message is displayed
- WHEN the user clicks "Copy response"
- THEN a `.txt` file with that message content is downloaded

---

## 3. Dashboard Screen

### REQ-SF-14: Chart grid
The system SHALL display dashboard items in a responsive 2-column grid. Each card shows a title, the Plotly chart (rebuilt from config at render time), and a delete button.

### REQ-SF-15: KPI cards
KPI items SHALL render as metric cards in a single row above the chart grid. Each shows the label and computed value.

### REQ-SF-16: Global filters
The system SHALL provide a filter bar where the user can add column-based filters (column name + selected values). Filters SHALL recompute ALL charts and KPIs via `GET /api/dashboard` with filter parameters.

### REQ-SF-17: Clear dashboard
The system SHALL have a "Clear dashboard" button that removes all items via `DELETE /api/dashboard`.

#### Dashboard Scenarios

**Scenario SF-Dash-S1: Display charts**
- GIVEN the dashboard has 3 chart items and 2 KPI items
- WHEN the user navigates to Dashboard
- THEN 2 KPI cards display in the top row
- AND chart items appear in a 2-column grid
- AND each includes a delete button

**Scenario SF-Dash-S2: Apply filter**
- GIVEN a chart uses data with column "Region"
- WHEN the user adds a filter selecting "Region = Norte"
- THEN the chart rebuilds showing only Norte data

---

## 4. Settings Screen

### REQ-SF-18: API key input
The system SHALL render a password-type input for the Gemini API key, pre-filled with the current masked value from `GET /api/settings`.

### REQ-SF-19: Model selector
The system SHALL render a dropdown with available Gemini model options, pre-selected with the current model.

### REQ-SF-20: Apply settings
An "Apply" button SHALL PUT the API key and model to `/api/settings`. On success, the system SHALL show a confirmation.

### REQ-SF-21: Session reset
The screen SHALL have a "New session" button that calls `POST /api/session/reset` and navigates to the Upload screen.

### REQ-SF-22: App info
The screen SHALL display static version and stack info.

#### Settings Scenarios

**Scenario SF-Set-S1: Update API key**
- GIVEN the settings screen is displayed
- WHEN the user enters a new API key and selects "Gemini 2.0 Flash"
- AND clicks "Apply"
- THEN `PUT /api/settings` is called with the new values
- AND a success confirmation is shown

**Scenario SF-Set-S2: Reset session**
- WHEN the user clicks "New session"
- THEN `POST /api/session/reset` is called
- AND the app navigates to the Upload screen

---

## 5. Sidebar / Navigation

### REQ-SF-23: Navigation
A persistent sidebar SHALL contain navigation buttons for: Upload, Chat, Dashboard, Settings. The active screen SHALL be highlighted.

### REQ-SF-24: State indicators
The sidebar SHALL display:
- Number of loaded files (from `GET /api/session`)
- Active file names
- Message count
- Current LLM provider/model

### REQ-SF-25: Session controls
The sidebar SHALL include a "New session" button that calls `POST /api/session/reset`.

#### Sidebar Scenarios

**Scenario SF-Side-S1: Navigate between screens**
- GIVEN the user is on the Upload screen
- WHEN the user clicks "Chat" in the sidebar
- THEN the Chat screen renders
- AND the "Chat" button is highlighted

**Scenario SF-Side-S2: Indicators update after upload**
- GIVEN the sidebar shows "Files: 0"
- WHEN the user uploads `ventas.csv`
- THEN the sidebar updates to "Files: 1" and shows `ventas.csv`

---

## Cross-Cutting Requirements

### REQ-SF-26: Session header
Every API call SHALL include the `X-Session-Id` header, obtained from `POST /api/session/reset` at first load and stored in memory/`sessionStorage`.

### REQ-SF-27: Error toast
API errors (non-2xx) SHALL display as dismissible toast notifications in the top-right corner. Network failures SHALL show "Connection error. Check your internet."

### REQ-SF-28: Loading state
Every API call SHALL show a loading indicator (spinner or skeleton) until the response is received.
