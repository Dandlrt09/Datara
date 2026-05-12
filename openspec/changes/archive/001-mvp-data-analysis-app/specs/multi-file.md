# Spec: Multi-File Support

## Description
The system MUST allow users to upload multiple files and ask questions that
reference or join data across those files.

## Requirements

### REQ-MF-01: Multiple uploads
The system SHALL accept multiple file uploads in the same session.

### REQ-MF-02: File listing
The system SHALL display a list of all uploaded files with their row counts
and column names.

### REQ-MF-03: Naming
Each file SHALL be identified by its filename. If the same filename is uploaded
again, the system SHALL ask the user whether to replace or keep both.

### REQ-MF-04: Cross-file questions
The user SHALL be able to ask questions that reference multiple files by name.
The LLM context SHALL include schemas from ALL loaded files.

### REQ-MF-05: Join/merge
The system SHALL be able to perform pandas merge operations across files when
the user asks relational questions (e.g., "Combiná ventas.csv con empleados.xlsx
por ID de empleado").

### REQ-MF-06: File removal
The user SHALL be able to remove an uploaded file from the session, which
clears it from memory.

## Scenarios

### Scenario MF-S1: Upload multiple files
**Given** a user has loaded "ventas.csv" (5 columns, 100 rows)
**When** they upload "empleados.xlsx" (3 columns, 50 rows)
**Then** both files appear in the file list
**And** the user can ask questions about either file

### Scenario MF-S2: Cross-file question
**Given** "ventas.xlsx" has columns [EmpleadoID, Monto]
**And** "empleados.csv" has columns [ID, Nombre, Departamento]
**When** the user asks "Mostrá las ventas totales por departamento"
**Then** the system merges both files on EmpleadoID=ID
**And** returns a bar chart of total sales by department

### Scenario MF-S3: Remove file
**Given** a session has 2 loaded files
**When** the user removes "ventas.csv"
**Then** the system no longer includes "ventas.csv" in context
**And** the file list updates to show only the remaining file

### Scenario MF-S4: Duplicate filename
**Given** "data.csv" is already loaded
**When** the user uploads a different "data.csv"
**Then** the system asks "Ya existe 'data.csv'. ¿Reemplazarlo o mantener ambos?"
**When** the user selects "Mantener ambos"
**Then** both files appear as "data.csv" and "data (2).csv"
