# Spec: Chart Generation

## Description
The system MUST automatically generate Plotly charts when the user's question
requires or would benefit from visualization.

## Requirements

### REQ-CG-01: Automatic generation
When a question is best answered with a chart (e.g., "mostrá la tendencia de
ventas"), the system SHALL return BOTH a text response AND an interactive
Plotly chart.

### REQ-CG-02: Chart types
The system SHALL support at least: bar, line, scatter, pie, and histogram charts.

### REQ-CG-03: Chart rendering
Charts SHALL render inline in the chat interface using Plotly's interactive
HTML output (zoom, tooltip, pan).

### REQ-CG-04: Chart title and labels
Every chart SHALL include a descriptive title and labeled axes (where applicable).

### REQ-CG-05: Chart-only questions
If the user explicitly asks for a chart (e.g., "hacé un gráfico de barras"),
the system MAY respond with the chart alone (no text required).

## Scenarios

### Scenario CG-S1: Chart from data question
**Given** a DataFrame with [Month, Sales] columns
**When** the user asks "Mostrá la tendencia de ventas por mes"
**Then** the system returns a line chart with Month on X and Sales on Y
**And** a text summary of the trend

### Scenario CG-S2: Explicit chart request
**Given** loaded data with [Category, Quantity]
**When** the user asks "Hacé un gráfico de torta por categoría"
**Then** the system returns a pie chart showing quantity distribution

### Scenario CG-S3: Question that doesn't need chart
**Given** a DataFrame with [Name, Salary]
**When** the user asks "¿Cuál es el empleado con mayor salario?"
**Then** the system returns text only (no chart), since a single value
doesn't benefit from visualization
