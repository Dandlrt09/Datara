# Tasks: MVP Data Analysis App

## Phase 0: Project Setup

### 0.1 Initialize Python project
- [ ] Create `requirements.txt` with: streamlit, pandas, openpyxl, plotly, openai, python-dotenv
- [ ] Create `.env.example` with `GROQ_API_KEY=your-key-here`
- [ ] Create `.gitignore` (Python + Streamlit + .env)
- [ ] Create project scaffold: `app/`, `services/`, `models/`, `utils/`, `tests/`
- [ ] Run `pip install -r requirements.txt` and verify

### 0.2 Configure Groq API key
- [ ] User registers at https://console.groq.com and gets API key
- [ ] Sets `GROQ_API_KEY` in `.env`
- [ ] Quick test: call Groq API and print response

## Phase 1: Infrastructure (Scaffold)

### 1.1 Create data models
- [ ] `models/__init__.py`
- [ ] `models/file_data.py` — FileData dataclass: name, df, sheets, size, loaded_at
- [ ] `models/chat_message.py` — ChatMessage dataclass: role, content, figure, timestamp
- [ ] `models/analysis_result.py` — AnalysisResult: text, figure, dataframe, error

### 1.2 Create sandbox for safe code execution
- [ ] `utils/sandbox.py` — SafeExecutor class with restricted globals whitelist
- [ ] Whitelist: `pd` (pandas), `px` (plotly.express), `go` (plotly.graph_objects), `np` (numpy), `st` (streamlit — limited)
- [ ] Block: `os`, `subprocess`, `sys`, `__import__`, `eval`, `exec`, `open`, `shutil`
- [ ] Timeout: kill execution after 30 seconds
- [ ] Write test: `tests/test_sandbox.py`

### 1.3 Create LLM prompt templates
- [ ] `utils/prompts.py` — system prompt for code generation
- [ ] Prompt includes: DataFrame schema, allowed libraries, code-only output format, Spanish language
- [ ] Prompt includes: do NOT use file I/O, do NOT import outside whitelist, do NOT use subprocess

### 1.4 Create validators
- [ ] `utils/validators.py` — validate_file_size(), validate_file_type(), validate_file_content()

## Phase 2: File Service

### 2.1 Implement FileService.parse_csv()
- [ ] Pandas read_csv with UTF-8, auto-detect delimiter, handle headers
- [ ] Return DataFrame + metadata (rows, columns, dtypes)
- [ ] Handle encoding errors gracefully

### 2.2 Implement FileService.parse_excel()
- [ ] OpenPyXL + pandas read_excel
- [ ] List all sheet names
- [ ] Load selected sheet as DataFrame
- [ ] Return DataFrame + metadata + sheet names

### 2.3 Implement FileService.validate()
- [ ] Check file extension → .csv or .xlsx
- [ ] Check file size < 200 MB
- [ ] Check file not empty
- [ ] Return ValidationResult: valid bool, error_message

### 2.4 Implement FileService multi-file storage
- [ ] Store in dict: `filename → FileData`
- [ ] method: add_file(), remove_file(), get_file(), list_files()
- [ ] Handle duplicate filenames (ask to replace or rename)

### 2.5 Write tests for FileService
- [ ] `tests/test_file_service.py` — test each parse method, validation, edge cases

## Phase 3: LLM Service

### 3.1 Implement LLMService.call_grok()
- [ ] Use openai SDK with base_url = "https://api.groq.com/openai/v1"
- [ ] Model: mixtral-8x7b-32768 or llama3-70b-8192
- [ ] Handle API errors, rate limits, timeouts
- [ ] Return raw response text

### 3.2 Implement context builder
- [ ] Build context string from: system prompt + DataFrame schemas + sample rows (head(5)) + user question
- [ ] For multi-file: include ALL file schemas + sample rows
- [ ] Truncate context if too large (Groq 32K context window)

### 3.3 Implement code extraction
- [ ] Extract Python code block from LLM response (between ```python and ```)
- [ ] If no code block found, wrap entire response as text
- [ ] Fallback: if response has explanatory text before or after code, extract just the code for execution

### 3.4 Write tests for LLMService
- [ ] `tests/test_llm_service.py` — mock Groq API, test context building, code extraction

## Phase 4: Code Executor

### 4.1 Implement CodeExecutor.run()
- [ ] Receive generated Python code string
- [ ] Execute in SafeExecutor sandbox
- [ ] Capture output: `last_figure` (Plotly), `last_df` (pandas), `last_text`
- [ ] Wrap execution in try/except with timeout

### 4.2 Implement error recovery
- [ ] If code raises SyntaxError → retry with error feedback to LLM (1 retry)
- [ ] If code raises NameError (using blocked import) → return friendly error
- [ ] If timeout → return "El análisis tomó demasiado tiempo"

### 4.3 Write tests for CodeExecutor
- [ ] `tests/test_code_executor.py` — test valid code, invalid code, blocked imports, timeout

## Phase 5: Streamlit App — Pages

### 5.1 Create app/main.py — entry point
- [ ] st.set_page_config(title, layout="wide")
- [ ] Initialize session state (files, chat, config)
- [ ] Sidebar navigation between pages
- [ ] Styling: custom CSS for better look

### 5.2 Create app/pages/upload.py
- [ ] File uploader widget (st.file_uploader)
- [ ] File validation feedback (success/error messages)
- [ ] Sheet selector for Excel files (st.selectbox)
- [ ] Data preview table (st.dataframe with pagination)
- [ ] Show file metadata: rows, columns, dtypes

### 5.3 Create app/pages/chat.py
- [ ] Display chat history (iterate session_state.chat)
- [ ] Question input at bottom (st.chat_input)
- [ ] Render AI responses: text + chart + table as needed
- [ ] Chart download button per response
- [ ] "Exportar conversación" button

### 5.4 Create app/pages/settings.py
- [ ] Groq API key input (st.text_input, password type)
- [ ] Model selector dropdown (mixtral vs llama)
- [ ] "Nueva sesión" reset button

## Phase 6: Streamlit App — Components

### 6.1 Create app/components/file_list.py
- [ ] Sidebar list of loaded files with remove button per file
- [ ] Show file name, rows, columns
- [ ] Handle file removal → update session state

### 6.2 Create app/components/data_preview.py
- [ ] Render DataFrame as interactive table
- [ ] Configurable rows per page (10, 25, 50)
- [ ] Show column dtypes in header

### 6.3 Create app/components/chat_message.py
- [ ] User message: right-aligned, colored bubble
- [ ] AI message: left-aligned, includes avatar/icon
- [ ] Render text, Plotly chart, or DataFrame inside AI message

### 6.4 Create app/components/chart_download.py
- [ ] Render Plotly chart
- [ ] Download button using plotly.io.write_image (PNG)
- [ ] Requires kaleido or orca for static export

## Phase 7: Export Service

### 7.1 Implement export_service.export_chart_png()
- [ ] Convert Plotly figure to PNG bytes
- [ ] Provide download link via st.download_button

### 7.2 Implement export_service.export_dataframe_csv()
- [ ] Convert DataFrame to CSV bytes
- [ ] Provide download link

### 7.3 Implement export_service.export_conversation()
- [ ] Format all Q&A pairs as text
- [ ] Provide download link as .txt file

## Phase 8: Integration & Polish

### 8.1 Wire everything together
- [ ] Upload page → FileService → session_state.files
- [ ] Chat page → LLMService → CodeExecutor → render output
- [ ] Multi-file support in chat context
- [ ] Export buttons wired to ExportService

### 8.2 Error handling polish
- [ ] Catch all Streamlit errors gracefully
- [ ] Show spinner during LLM calls (st.spinner)
- [ ] Cache Groq responses when possible

### 8.3 Testing pass
- [ ] Manual test of each spec scenario (FU-S1 to SS-S3)
- [ ] Verify all export functions
- [ ] Test multi-file merge
- [ ] Test session reset
