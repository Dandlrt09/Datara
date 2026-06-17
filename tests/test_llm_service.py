"""
Tests for services/llm_service.py — LLMService.

Covers:
  - API error handling (rate limiting, auth, quota, timeout, etc.)
  - Code extraction from LLM responses
  - Text extraction from LLM responses
  - is_configured property
  - generate_code high-level method
  - Provider info

All OpenAI client calls are mocked — no real API calls are made.
"""

from unittest.mock import MagicMock

import pytest

from services.llm_service import LLMService


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def service():
    """LLMService with a fake API key (no real calls in tests)."""
    return LLMService(api_key="valid-test-key")


@pytest.fixture
def mock_create(service, monkeypatch):
    """Mock the OpenAI client's chat.completions.create.

    Usage in tests:
        mock_create.return_value = ...
        mock_create.side_effect = SomeException(...)
    """
    mock_create = MagicMock()
    mock_client = MagicMock()
    mock_client.chat.completions.create = mock_create
    monkeypatch.setattr(service, "_client", mock_client)
    return mock_create


# ── is_configured ───────────────────────────────────────────────────


class TestIsConfigured:
    def test_with_valid_key(self):
        s = LLMService(api_key="sk-abc123")
        assert s.is_configured is True

    def test_with_empty_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        s = LLMService(api_key="")
        assert s.is_configured is False

    def test_with_placeholder_key(self):
        s = LLMService(api_key="your-key-here")
        assert s.is_configured is False

    def test_with_none_key_and_env_not_set(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        s = LLMService()
        assert s.is_configured is False

    def test_from_env_var(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "env-key-123")
        s = LLMService()
        assert s.is_configured is True
        assert s.api_key == "env-key-123"

    def test_from_env_var_model(self, monkeypatch):
        monkeypatch.setenv("GEMINI_MODEL", "models/gemini-2.0-flash")
        s = LLMService(api_key="key")
        assert s.model == "models/gemini-2.0-flash"

    def test_default_model_when_no_env(self, monkeypatch):
        monkeypatch.delenv("GEMINI_MODEL", raising=False)
        s = LLMService(api_key="key")
        assert s.model == "models/gemini-2.5-flash"


# ── provider_info ───────────────────────────────────────────────────


class TestProviderInfo:
    def test_default_model(self, monkeypatch):
        monkeypatch.delenv("GEMINI_MODEL", raising=False)
        s = LLMService(api_key="key")
        assert "Gemini" in s.provider_info
        assert "gemini-2.5-flash" in s.provider_info


# ── ask() — Happy path ──────────────────────────────────────────────


class TestAskSuccess:
    def test_returns_content(self, service, mock_create):
        """A normal API response returns the message content."""
        mock_message = MagicMock()
        mock_message.content = "```python\nresult_text = 'ok'\n```"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_create.return_value = mock_response

        result = service.ask("Some context")
        assert result == "```python\nresult_text = 'ok'\n```"

    def test_empty_content_returns_empty_string(self, service, mock_create):
        """When content is None, return empty string."""
        mock_message = MagicMock()
        mock_message.content = None
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_create.return_value = mock_response

        result = service.ask("Context")
        assert result == ""

    def test_not_configured_raises(self, monkeypatch):
        """Calling ask() without a valid API key raises RuntimeError."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        s = LLMService(api_key="")
        with pytest.raises(RuntimeError, match="API key"):
            s.ask("context")


# ── ask() — Error handling / rate limiting ──────────────────────────


class TestAskErrors:
    """All the error scenarios LLMService.ask() must handle."""

    def test_rate_limit_429(self, service, mock_create):
        """Rate limit (429) → ConnectionError with friendly message."""
        mock_create.side_effect = Exception("rate limit exceeded (429)")

        with pytest.raises(ConnectionError) as exc:
            service.ask("context")
        assert "Límite de tasa" in str(exc.value)

    def test_rate_limit_text_only(self, service, mock_create):
        """Rate limit detected by text alone (no status code)."""
        mock_create.side_effect = Exception("API rate limit exceeded")

        with pytest.raises(ConnectionError) as exc:
            service.ask("context")
        assert "Límite de tasa" in str(exc.value)

    def test_auth_error_401(self, service, mock_create):
        """Auth error (401) → RuntimeError about invalid key."""
        mock_create.side_effect = Exception("API key not valid (401)")

        with pytest.raises(RuntimeError) as exc:
            service.ask("context")
        assert "API key" in str(exc.value)
        assert "inválida" in str(exc.value)

    def test_auth_error_text_only(self, service, mock_create):
        """Auth error detected by text alone."""
        mock_create.side_effect = Exception("authentication failed")

        with pytest.raises(RuntimeError) as exc:
            service.ask("context")
        assert "API key" in str(exc.value)

    def test_quota_error_403(self, service, mock_create):
        """Quota exceeded (403) → ConnectionError."""
        mock_create.side_effect = Exception("quota exceeded (403)")

        with pytest.raises(ConnectionError) as exc:
            service.ask("context")
        assert "Cuota" in str(exc.value)

    def test_quota_by_text(self, service, mock_create):
        """Quota detected by text alone."""
        mock_create.side_effect = Exception("quota")

        with pytest.raises(ConnectionError) as exc:
            service.ask("context")
        assert "Cuota" in str(exc.value)

    def test_timeout(self, service, mock_create):
        """Timeout → ConnectionError."""
        mock_create.side_effect = Exception("request timed out")

        with pytest.raises(ConnectionError) as exc:
            service.ask("context")
        assert "timed out" in str(exc.value).lower()

    def test_timeout_alt_phrase(self, service, mock_create):
        """Timeout with alternative phrasing."""
        mock_create.side_effect = Exception("timeout after 30s")

        with pytest.raises(ConnectionError) as exc:
            service.ask("context")
        assert "timed out" in str(exc.value).lower()

    def test_model_not_found(self, service, mock_create):
        """Model not found → RuntimeError."""
        mock_create.side_effect = Exception("model_not_found")

        with pytest.raises(RuntimeError) as exc:
            service.ask("context")
        assert "Modelo" in str(exc.value) or "modelo" in str(exc.value)

    def test_model_not_found_by_text(self, service, mock_create):
        """Model not found by alternative text."""
        mock_create.side_effect = Exception("The model `foo` was not found")

        with pytest.raises(RuntimeError) as exc:
            service.ask("context")
        assert "Modelo" in str(exc.value) or "modelo" in str(exc.value)

    def test_generic_error(self, service, mock_create):
        """Any other error → ConnectionError with original message."""
        mock_create.side_effect = Exception("server error 500")

        with pytest.raises(ConnectionError) as exc:
            service.ask("context")
        assert "500" in str(exc.value) or "server" in str(exc.value).lower()

    def test_error_case_insensitive(self, service, mock_create):
        """Error matching should be case-insensitive."""
        mock_create.side_effect = Exception("RATE LIMIT")

        with pytest.raises(ConnectionError) as exc:
            service.ask("context")
        assert "Límite de tasa" in str(exc.value)


# ── extract_code ────────────────────────────────────────────────────


class TestExtractCode:
    """LLMService.extract_code static method — parse Python from LLM output."""

    def test_extract_python_block(self):
        response = """Aquí está el código:
```python
result_text = "hola"
```
"""
        code = LLMService.extract_code(response)
        assert code == 'result_text = "hola"'

    def test_extract_py_block(self):
        response = """```py
x = 1
```"""
        code = LLMService.extract_code(response)
        assert code == "x = 1"

    def test_extract_code_block_without_lang(self):
        """Fenced block without language specifier."""
        response = """```
result_text = "ok"
```"""
        code = LLMService.extract_code(response)
        assert code == 'result_text = "ok"'

    def test_no_code_block(self):
        response = "Solo texto explicativo."
        code = LLMService.extract_code(response)
        assert code is None

    def test_empty_code_block(self):
        response = "```python\n\n```"
        code = LLMService.extract_code(response)
        assert code is None

    def test_multiple_blocks_returns_first(self):
        response = """```python
first = 1
```
```python
second = 2
```"""
        code = LLMService.extract_code(response)
        assert code == "first = 1"

    def test_code_with_special_chars(self):
        response = "```python\nresult_text = f'Promedio: {df.age.mean():.2f}'\n```"
        code = LLMService.extract_code(response)
        assert "f'Promedio" in code

    def test_code_with_import_statement(self):
        response = "```python\nimport pandas as pd\nresult_df = pd.DataFrame()\n```"
        code = LLMService.extract_code(response)
        assert "import pandas" in code
        assert "result_df" in code

    def test_no_triple_backticks_at_all(self):
        response = "print('hello')"
        code = LLMService.extract_code(response)
        assert code is None


# ── extract_text ────────────────────────────────────────────────────


class TestExtractText:
    """LLMService.extract_text static method — get non-code text from response."""

    def test_text_before_and_after_code(self):
        response = """Analizando los datos...
```python
result_text = "ok"
```
Listo."""
        text = LLMService.extract_text(response)
        assert "Analizando" in text
        assert "Listo" in text
        assert "result_text" not in text

    def test_no_code_present(self):
        response = "Solo texto sin código."
        text = LLMService.extract_text(response)
        assert text == "Solo texto sin código."

    def test_only_code_no_text(self):
        response = "```python\nx = 1\n```"
        text = LLMService.extract_text(response)
        assert text == ""

    def test_inline_code_removed(self):
        """Inline backtick code like `df.head()` should also be removed."""
        response = "Usá `df.head()` para ver los datos."
        text = LLMService.extract_text(response)
        assert "df.head()" not in text
        assert "Usá" in text
        assert "ver los datos" in text

    def test_empty_response(self):
        text = LLMService.extract_text("")
        assert text == ""


# ── generate_code ───────────────────────────────────────────────────


class TestGenerateCode:
    """LLMService.generate_code high-level method."""

    def test_code_and_text_returned(self, service, monkeypatch):
        """Returns (code, text, raw) tuple."""

        def mock_ask(_context):
            return "Texto explicativo.\n```python\nresult_text = 'analizado'\n```\nFin."

        monkeypatch.setattr(service, "ask", mock_ask)

        code, text, raw = service.generate_code("context")
        assert code == "result_text = 'analizado'"
        assert "Texto explicativo" in text
        assert "Fin" in text
        assert raw is not None

    def test_text_only_response(self, service, monkeypatch):
        """No code block → code is empty string, text is the whole response."""

        def mock_ask(_context):
            return "Respuesta textual sin código."

        monkeypatch.setattr(service, "ask", mock_ask)

        code, text, raw = service.generate_code("context")
        assert code == ""
        assert text == "Respuesta textual sin código."

    def test_code_without_text(self, service, monkeypatch):
        """Only code, no surrounding text."""

        def mock_ask(_context):
            return "```python\nresult_text = 'solo codigo'\n```"

        monkeypatch.setattr(service, "ask", mock_ask)

        code, text, raw = service.generate_code("context")
        assert code == "result_text = 'solo codigo'"
        assert text == ""

    def test_empty_response(self, service, monkeypatch):
        """Completely empty response — text falls back to raw (empty)."""

        def mock_ask(_context):
            return ""

        monkeypatch.setattr(service, "ask", mock_ask)

        code, text, raw = service.generate_code("context")
        assert code == ""
        assert text == ""  # Falls back to raw (empty string)

    def test_raw_always_preserved(self, service, monkeypatch):
        """The raw argument is always the full response."""

        def mock_ask(_context):
            return "raw full response\n```python\nx=1\n```"

        monkeypatch.setattr(service, "ask", mock_ask)

        _code, _text, raw = service.generate_code("context")
        assert "raw full response" in raw
        assert "x=1" in raw

    def test_repeated_generate_code(self, service, monkeypatch):
        """Multiple calls work correctly (no state leakage)."""
        call_count = 0

        def mock_ask(_context):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "```python\nx = 1\n```"
            return "```python\nx = 2\n```"

        monkeypatch.setattr(service, "ask", mock_ask)

        code1, _t1, _r1 = service.generate_code("first")
        code2, _t2, _r2 = service.generate_code("second")

        assert code1 == "x = 1"
        assert code2 == "x = 2"


# ── Client lazy initialization ──────────────────────────────────────


class TestClientLazyInit:
    """The OpenAI client should only be created on first access."""

    def test_client_is_none_after_init(self):
        s = LLMService(api_key="key")
        assert s._client is None

    def test_client_created_on_access(self):
        s = LLMService(api_key="key")
        client = s.client
        assert client is not None
        # Second call returns the same instance
        assert s.client is client

    def test_client_uses_correct_base_url(self):
        s = LLMService(api_key="key")
        client = s.client
        assert "generativelanguage.googleapis.com" in str(client.base_url)
