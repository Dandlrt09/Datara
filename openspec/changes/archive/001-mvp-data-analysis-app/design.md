# Design: MVP Data Analysis App

## Architecture Overview

**Pattern**: Container-Presentational + Service Layer

```
┌─────────────────────────────────────────────────┐
│                   Streamlit App                  │
│                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │  UploadPage  │  │  ChatPage   │  │ Settings │ │
│  └──────┬──────┘  └──────┬──────┘  └──────────┘ │
│         │                │                        │
│  ┌──────┴────────────────┴──────────────────────┐ │
│  │            Session State (st.session_state)   │ │
│  │  ┌─────────┐ ┌──────────┐ ┌───────────────┐  │ │
│  │  │ files[] │ │ chat[]   │ │ config        │  │ │
│  │  └─────────┘ └──────────┘ └───────────────┘  │ │
│  └───────────────────────────────────────────────┘ │
│                                                   │
│  ┌──────────────────────────────────────────────┐ │
│  │              Service Layer                    │ │
│  │  ┌──────────┐ ┌────────┐ ┌──────────────┐   │ │
│  │  │ FileSvc  │ │ LLMSvc │ │ CodeExecutor │   │ │
│  │  └──────────┘ └────────┘ └──────────────┘   │ │
│  └──────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

## Project Structure

```
data-analytica/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Entry point — Streamlit app bootstrap
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── upload.py           # File upload page
│   │   ├── chat.py             # Q&A chat page
│   │   └── settings.py         # API key config, preferences
│   └── components/
│       ├── __init__.py
│       ├── file_list.py        # File listing sidebar component
│       ├── data_preview.py     # Table preview component
│       ├── chat_message.py     # Chat bubble component
│       └── chart_download.py   # Chart + download button component
├── services/
│   ├── __init__.py
│   ├── file_service.py         # File parsing, validation, storage
│   ├── llm_service.py          # Groq API interaction
│   ├── code_executor.py        # Safe execution of LLM-generated code
│   └── export_service.py       # Export to CSV/PNG/TXT
├── models/
│   ├── __init__.py
│   ├── file_data.py            # File metadata dataclass
│   ├── chat_message.py         # Chat message dataclass
│   └── analysis_result.py      # Result from code execution
├── utils/
│   ├── __init__.py
│   ├── sandbox.py              # Restricted exec() environment
│   ├── prompts.py              # LLM prompt templates
│   └── validators.py           # File validation helpers
├── tests/
│   ├── __init__.py
│   ├── test_file_service.py
│   ├── test_llm_service.py
│   ├── test_code_executor.py
│   └── test_sandbox.py
├── requirements.txt
├── .env.example                # GROQ_API_KEY template
├── .gitignore
└── README.md
```

## Architecture Decisions

### AD-1: Code generation over structured output
**Status**: Accepted
**Context**: The LLM needs to perform data analysis that varies widely.
Structured output (JSON) limits what the LLM can express and requires
complex parsing logic.
**Decision**: Prompt the LLM to generate Python code (pandas + plotly)
and execute it in a sandbox.
**Consequence**: +flexibility, -security risk (mitigated by sandbox).

### AD-2: Restricted exec() sandbox
**Status**: Accepted
**Context**: Executing LLM-generated code is inherently dangerous.
**Decision**: Use Python's built-in `exec()` with a restricted globals dict
that whitelists ONLY `pandas`, `plotly`, `numpy`, and built-in functions.
Block `os`, `subprocess`, `sys`, `open`, `__import__`, `eval`, `exec`.
**Implementation**: `utils/sandbox.py` — `SafeExecutor` class.
**Consequence**: Safe but limits what the LLM can do (intentional).

### AD-3: Groq via OpenAI-compatible SDK
**Status**: Accepted
**Context**: Groq supports the OpenAI API format.
**Decision**: Use the `openai` Python library with a custom base URL
pointing to `https://api.groq.com/openai/v1`.
**Consequence**: Migrating to OpenAI later = change ONE config line.

### AD-4: Multi-page Streamlit over single page
**Status**: Accepted
**Context**: The app has distinct functional areas (upload, chat, settings).
**Decision**: Use Streamlit's native multi-page app (`pages/` folder).
**Consequence**: Cleaner separation, native navigation, but slightly more
complex state sharing (solved via `st.session_state`).

### AD-5: In-memory storage only
**Status**: Accepted
**Context**: MVP does not need persistence across sessions.
**Decision**: All data lives in `st.session_state`. No database.
**Consequence**: Data lost on refresh. Acceptable for MVP.

## Data Flow

### Upload Flow
```
User selects file → FileService.validate() → FileService.parse()
  → DataFrame stored in session_state.files[filename]
  → DataPreview component renders table
```

### Chat Flow
```
User types question → 
  1. Build LLM context: system prompt + DataFrame schemas + sample rows + question
  2. Call Groq API → receive generated Python code
  3. CodeExecutor.run(code) → DataFrame | Plotly figure | text
  4. If figure → render Plotly chart + download button
  5. If DataFrame → render table + CSV download button
  6. If text → render chat bubble
  7. Store Q&A in session_state.chat[]
```

### Multi-file Flow
```
User uploads File B →
  1. Existing File A in session_state.files["A"]
  2. File B added as session_state.files["B"]
  3. LLM context now includes schemas for A and B
  4. User asks "merge A and B on X" →
  5. LLM generates pd.merge() code → executed in sandbox
```

## Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `app/main.py` | Bootstrap, sidebar nav, session state init |
| `app/pages/upload.py` | File upload widget, validation feedback, data preview |
| `app/pages/chat.py` | Chat UI, question input, response rendering |
| `app/pages/settings.py` | Groq API key input, model selection |
| `app/components/file_list.py` | Sidebar showing loaded files with remove button |
| `app/components/data_preview.py` | DataFrame preview with pagination |
| `app/components/chat_message.py` | Chat bubble (user vs AI styling) |
| `app/components/chart_download.py` | Plotly chart render + PNG download |
| `services/file_service.py` | Parse CSV/Excel, validate, sheet selection |
| `services/llm_service.py` | Build prompts, call Groq API, parse response |
| `services/code_executor.py` | Extract code from LLM response, execute in sandbox |
| `services/export_service.py` | Generate CSV/PNG/TXT downloads |
| `utils/sandbox.py` | Restricted exec environment |
| `utils/prompts.py` | System prompt templates |
| `utils/validators.py` | File size, type, content validation |

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| App framework | Streamlit | >=1.35 |
| Data | Pandas | >=2.0 |
| Excel | OpenPyXL | >=3.1 |
| Charts | Plotly | >=5.20 |
| LLM client | openai (with Groq base_url) | >=1.30 |
| Linter/Formatter | Ruff | >=0.5 |
| Testing | Pytest | >=8.0 |

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Code injection via LLM output | Low | Critical | Sandbox with whitelist-only modules |
| Groq API rate limits (30 req/min) | Medium | Medium | Show friendly message, cache responses |
| LLM generates invalid Python | Medium | Low | Catch SyntaxError, retry with error in prompt |
| Large files exhaust memory | Medium | Medium | 200 MB limit, streaming parse |
| Streamlit state loss on rerun | Low | Medium | Use `st.session_state` properly with init guard |
