# Spec: Data Chat

## Description
The system MUST allow users to ask questions about their data in natural
language and receive AI-generated textual analysis.

## Requirements

### REQ-DC-01: Question input
The system SHALL provide a text input or chat interface where users type
natural language questions about their loaded data.

### REQ-DC-02: Context-aware
The system SHALL include the DataFrame schema (column names, types, sample rows)
in the context sent to the LLM so responses are data-aware.

### REQ-DC-03: Natural language responses
The system SHALL return answers in natural language (Spanish), not raw code.

### REQ-DC-04: Follow-up questions
The system SHALL maintain conversation context within a session so follow-up
questions can reference previous answers.

### REQ-DC-05: Unanswerable questions
If a question cannot be answered with the available data (e.g., "What is the
profit?" when there's no profit column), the system SHALL explain why and
suggest what CAN be answered.

### REQ-DC-06: Error handling
If the LLM call fails (timeout, API error), the system SHALL show a friendly
error and allow retry.

## Scenarios

### Scenario DC-S1: Simple question about data
**Given** a user has loaded a CSV with columns [Name, Age, Salary]
**When** they ask "¿Cuál es el salario promedio?"
**Then** the system responds with the average salary value in Spanish

### Scenario DC-S2: Follow-up question
**Given** a user asked "¿Cuántos empleados hay?" and received an answer
**When** they ask "¿Y cuántos ganan más de 50000?"
**Then** the system understands "empleados" from context and answers correctly

### Scenario DC-S3: Question missing required data
**Given** a DataFrame with columns [Name, Age, Salary]
**When** the user asks "¿Cuál es la ganancia neta?"
**Then** the system responds that "profit" data is not available
**And** suggests: "Los datos disponibles son: Nombre, Edad, Salario."

### Scenario DC-S4: API failure
**Given** a user has loaded data and asks a question
**When** the Groq API returns an error (e.g., rate limit exceeded)
**Then** the system shows "Hubo un error al procesar tu consulta. Intentá de nuevo."
