# Proposal: MVP Data Analysis App

## Intent

Build a Streamlit web app where users can upload data files (CSV, Excel),
ask questions in natural language, and get AI-powered analysis with
automatic chart generation — all free, local-first, using Groq as the LLM backend.

## Scope

### In Scope (MVP)
1. **File upload**: CSV and Excel files — single and multiple
2. **Data preview**: show uploaded table(s) with pagination
3. **Natural language chat**: user asks questions → AI analyzes data → text response
4. **Auto chart generation**: AI generates Plotly charts when the question requires visualization
5. **Session history**: maintain chat history within the session
6. **Multi-file support**: upload multiple files, reference them in questions, join/relate data
7. **Export**: download responses and charts (CSV, PNG)

### Out of Scope
- User authentication / multi-tenant
- Persistent dashboard (real-time updates)
- Database storage (everything in-memory per session)
- Support for other file formats (Parquet, JSON, SQL) — future phase
- Streaming responses — Groq supports it but adds complexity for MVP

## Approach

### Tech Stack
- **Frontend/App**: Streamlit (single-page, multi-tab)
- **Data processing**: Pandas, OpenPyXL (Excel)
- **Visualization**: Plotly (interactive charts)
- **LLM**: Groq API (llama3-70b or mixtral) — OpenAI-compatible SDK
- **Code generation**: LLM generates Python code (pandas + plotly) that we exec safely
- **State management**: Streamlit `st.session_state`

### Architecture Pattern
**Container-Presentational + Service Layer**
- `app/` → Streamlit pages and UI components
- `services/` → Business logic (file parsing, LLM interaction, code execution)
- `models/` → Data classes and schemas
- `utils/` → Helpers (sanitization, safe execution)

### LLM Strategy
Prompt the LLM to generate **pure Python code** (pandas + plotly) that we execute
in a sandboxed environment. This avoids the complexity of parsing structured
LLM output and lets the model use its coding ability directly.

The prompt will include:
- The user's question
- A sample of the loaded DataFrame(s)
- Available functions (pandas, plotly)
- Strict instructions to output ONLY executable Python code

### Key Risk
**Code injection**: executing LLM-generated code is inherently risky.
Mitigation: use a restricted `exec()` environment with a whitelist of allowed
modules (pandas, plotly, numpy). No file I/O, no subprocess, no imports beyond
whitelist.

## Capabilities (Spec Areas)

Each capability maps to a spec file:

1. `file-upload` — upload CSV/Excel, validation, preview
2. `data-chat` — natural language Q&A with data context
3. `chart-generation` — auto-generate Plotly charts
4. `multi-file` — multiple files, relationships between them
5. `export` — download results and charts
6. `session-state` — history, file persistence within session
