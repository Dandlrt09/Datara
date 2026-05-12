# Spec: Export

## Description
The system MUST allow users to download analysis results, including
text responses and charts.

## Requirements

### REQ-EX-01: Export chart as PNG
Every chart SHALL have a download button that saves it as a PNG image.

### REQ-EX-02: Export data as CSV
The user SHALL be able to download any loaded DataFrame (original or
transformed after a query) as a CSV file.

### REQ-EX-03: Export response as text
The user SHALL be able to copy or download the text of any AI response.

### REQ-EX-04: Batch export
The user SHALL be able to export the full chat history as a single text file.

## Scenarios

### Scenario EX-S1: Download chart
**Given** a chart is displayed in the chat
**When** the user clicks "Descargar gráfico"
**Then** a PNG file is downloaded

### Scenario EX-S2: Download transformed data
**Given** the user asked "Agrupá las ventas por mes"
**And** the system returned aggregated data
**When** the user clicks "Descargar CSV"
**Then** a CSV file with the aggregated data is downloaded

### Scenario EX-S3: Export conversation
**Given** a session has 5 question-answer exchanges
**When** the user clicks "Exportar conversación"
**Then** a `.txt` file with all Q&A pairs is downloaded
