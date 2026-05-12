# Spec: File Upload

## Description
The system MUST allow users to upload CSV and Excel files, validate them,
and display a preview of the data.

## Requirements

### REQ-FU-01: File format support
The system SHALL accept files with extensions `.csv` and `.xlsx`.

### REQ-FU-02: CSV parsing
The system SHALL parse CSV files using UTF-8 encoding, auto-detect delimiter
(comma, semicolon, tab), and handle headers.

### REQ-FU-03: Excel parsing
The system SHALL parse `.xlsx` files and read all sheets. If multiple sheets
exist, the user MUST be able to select which sheet to load.

### REQ-FU-04: Validation
The system SHALL reject:
- Files larger than 200 MB
- Empty files
- Unsupported file types (with a clear error message)

### REQ-FU-05: Data preview
After loading, the system SHALL display a preview table showing:
- First N rows (configurable, default 10)
- Column names with data types
- Row count and column count

### REQ-FU-06: Error handling
If a file cannot be parsed, the system SHALL show a user-friendly error
message describing the problem (e.g., "Corrupted file", "Encoding not supported").

## Scenarios

### Scenario FU-S1: Successful CSV upload
**Given** a user is on the upload page
**When** they upload a valid CSV file with headers
**Then** the system displays a preview of the first 10 rows
**And** shows the column names, row count, and column count

### Scenario FU-S2: Invalid file type
**Given** a user is on the upload page
**When** they upload a `.pdf` file
**Then** the system shows an error message "Unsupported file format. Please upload CSV or Excel files."

### Scenario FU-S3: Excel with multiple sheets
**Given** a user uploads an Excel file with 3 sheets
**When** the file is parsed
**Then** the system displays a selector with the 3 sheet names
**When** the user selects "Sheet2"
**Then** the preview shows the data from Sheet2

### Scenario FU-S4: Empty file
**Given** a user is on the upload page
**When** they upload an empty CSV file
**Then** the system shows an error: "The file is empty. Please upload a file with data."

### Scenario FU-S5: File too large
**Given** a user is on the upload page
**When** they upload a 300 MB CSV file
**Then** the system shows an error: "File exceeds the 200 MB size limit."
