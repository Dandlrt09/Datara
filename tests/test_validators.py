"""Tests for utils/validators.py"""

from utils.validators import validate_file, MAX_FILE_SIZE_BYTES


class TestValidateFile:
    """validate_file handles extension, size, and empty checks."""

    def test_valid_csv(self):
        result = validate_file("datos.csv", 1024)
        assert result.valid is True
        assert result.error_message == ""

    def test_valid_xlsx(self):
        result = validate_file("datos.xlsx", 4096)
        assert result.valid is True

    def test_invalid_extension(self):
        result = validate_file("datos.txt", 1024)
        assert result.valid is False
        assert "no soportado" in result.error_message
        assert ".txt" in result.error_message

    def test_invalid_extension_pdf(self):
        result = validate_file("reporte.pdf", 1024)
        assert result.valid is False
        assert ".pdf" in result.error_message

    def test_invalid_extension_no_extension(self):
        result = validate_file("README", 1024)
        assert result.valid is False

    def test_valid_json(self):
        result = validate_file("datos.json", 1024)
        assert result.valid is True

    def test_valid_tsv(self):
        result = validate_file("datos.tsv", 1024)
        assert result.valid is True

    def test_extension_case_insensitive(self):
        result = validate_file("datos.CSV", 1024)
        assert result.valid is True
        result = validate_file("datos.JSON", 1024)
        assert result.valid is True
        result = validate_file("datos.TSV", 1024)
        assert result.valid is True

    def test_extension_xlsx_uppercase(self):
        result = validate_file("datos.XLSX", 1024)
        assert result.valid is True

    def test_file_too_large(self):
        size = MAX_FILE_SIZE_BYTES + 1
        result = validate_file("datos.csv", size)
        assert result.valid is False
        assert "excede" in result.error_message
        assert "MB" in result.error_message

    def test_file_exactly_at_limit(self):
        result = validate_file("datos.csv", MAX_FILE_SIZE_BYTES)
        assert result.valid is True

    def test_empty_file(self):
        result = validate_file("datos.csv", 0)
        assert result.valid is False
        assert "vacío" in result.error_message

    def test_empty_file_excel(self):
        result = validate_file("datos.xlsx", 0)
        assert result.valid is False
        assert "vacío" in result.error_message

    def test_warnings_returned_when_no_error(self):
        """No warnings for valid files — maybe future use."""
        result = validate_file("datos.csv", 1024)
        assert result.warnings == []
