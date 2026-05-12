# Spec: Session State

## Description
The system MUST maintain session state so that uploaded files, chat history,
and analysis results persist across page interactions within a session.

## Requirements

### REQ-SS-01: File persistence
Uploaded files SHALL persist in memory for the duration of the session.
Navigating between pages MUST NOT clear loaded files.

### REQ-SS-02: Chat history
The conversation SHALL be displayed as a scrollable list of Q&A pairs,
with newest at the bottom.

### REQ-SS-03: State isolation
Each user session SHALL have isolated state. Data from one session MUST NOT
be visible to another session.

### REQ-SS-04: Session reset
The user SHALL have a "Nueva sesión" button that clears all files, chat
history, and resets the state.

### REQ-SS-05: State indicators
The UI SHALL show:
- Number of loaded files
- Number of messages in current conversation
- Active file names (highlighted)

## Scenarios

### Scenario SS-S1: File persistence across pages
**Given** a user uploads "data.csv" on the upload page
**When** they navigate to the chat page
**Then** "data.csv" is still available and the user can ask questions about it

### Scenario SS-S2: Session isolation
**Given** User A loads "sales.csv" in session 1
**When** User B opens the app in another tab
**Then** User B's session is empty with no files loaded

### Scenario SS-S3: Reset session
**Given** a session with 3 loaded files and 10 messages
**When** the user clicks "Nueva sesión"
**Then** all files are removed, chat is cleared
**And** the app returns to the initial upload state
