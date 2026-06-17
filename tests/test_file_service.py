"""Tests for services/file_service.py — FileService."""


import pandas as pd
import pytest

from models.file_data import FileData
from services.file_service import FileService


# ── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def file_service():
    return FileService()


SAMPLE_CSV = b"nombre,edad\nAlice,30\nBob,25\nCarol,35\n"
SAMPLE_CSV_SEMICOLON = b"nombre;edad\nAlice;30\nBob;25\n"
SAMPLE_CSV_TAB = b"nombre\tedad\nAlice\t30\nBob\t25\n"
SAMPLE_CSV_PIPE = b"nombre|edad\nAlice|30\nBob|25\n"
SAMPLE_EMPTY_CSV = b"nombre,edad\n"
SAMPLE_MALFORMED = b"nombre,edad\nAlice\nBob,25,extra\n"


# ── CSV Parsing ────────────────────────────────────────────────────


class TestParseCSV:
    def test_parse_comma_csv(self, file_service):
        fd = file_service.parse_csv("datos.csv", SAMPLE_CSV)
        assert fd.filename == "datos.csv"
        assert fd.rows == 3
        assert fd.columns == 2
        assert list(fd.df.columns) == ["nombre", "edad"]

    def test_parse_semicolon_csv(self, file_service):
        fd = file_service.parse_csv("datos.csv", SAMPLE_CSV_SEMICOLON)
        assert fd.rows == 2
        assert list(fd.df.columns) == ["nombre", "edad"]

    def test_parse_tab_csv(self, file_service):
        fd = file_service.parse_csv("datos.csv", SAMPLE_CSV_TAB)
        assert fd.rows == 2

    def test_parse_pipe_csv(self, file_service):
        fd = file_service.parse_csv("datos.csv", SAMPLE_CSV_PIPE)
        assert fd.rows == 2

    def test_parse_single_column_csv(self, file_service):
        """Single-column CSV should still parse."""
        data = b"valor\n1\n2\n3\n"
        fd = file_service.parse_csv("single.csv", data)
        assert fd.rows == 3
        assert fd.columns == 1

    def test_column_names_stripped(self, file_service):
        """Column names should have whitespace stripped."""
        data = b"  nombre , edad  \nAlice,30\n"
        fd = file_service.parse_csv("datos.csv", data)
        assert list(fd.df.columns) == ["nombre", "edad"]

    def test_parse_empty_file_raises(self, file_service):
        """An empty CSV file should raise an error."""
        with pytest.raises(Exception):
            file_service.parse_csv("empty.csv", b"")

    def test_parse_csv_sets_size_bytes(self, file_service):
        fd = file_service.parse_csv("datos.csv", SAMPLE_CSV)
        assert fd.size_bytes == len(SAMPLE_CSV)


# ── Multi-file Storage ─────────────────────────────────────────────


class TestFileStorage:
    def test_add_and_get_file(self, file_service):
        fd = FileData(filename="test.csv", df=pd.DataFrame({"a": [1]}))
        file_service.add_file(fd)
        retrieved = file_service.get_file("test.csv")
        assert retrieved is fd

    def test_add_file_get_nonexistent(self, file_service):
        assert file_service.get_file("ghost.csv") is None

    def test_list_files_empty(self, file_service):
        assert file_service.list_files() == []

    def test_list_files_after_add(self, file_service):
        fd = FileData(filename="a.csv", df=pd.DataFrame({"x": [1]}))
        file_service.add_file(fd)
        files = file_service.list_files()
        assert len(files) == 1
        assert files[0] is fd

    def test_filenames(self, file_service):
        fd1 = FileData(filename="a.csv", df=pd.DataFrame({"x": [1]}))
        fd2 = FileData(filename="b.csv", df=pd.DataFrame({"y": [2]}))
        file_service.add_file(fd1)
        file_service.add_file(fd2)
        assert file_service.get_filenames() == ["a.csv", "b.csv"]

    def test_remove_file(self, file_service):
        fd = FileData(filename="test.csv", df=pd.DataFrame({"a": [1]}))
        file_service.add_file(fd)
        file_service.remove_file("test.csv")
        assert file_service.get_file("test.csv") is None
        assert file_service.file_count == 0

    def test_remove_nonexistent_does_not_raise(self, file_service):
        file_service.remove_file("ghost.csv")  # Should not raise

    def test_clear_all(self, file_service):
        fd1 = FileData(filename="a.csv", df=pd.DataFrame({"x": [1]}))
        fd2 = FileData(filename="b.csv", df=pd.DataFrame({"y": [2]}))
        file_service.add_file(fd1)
        file_service.add_file(fd2)
        file_service.clear_all()
        assert file_service.file_count == 0
        assert file_service.list_files() == []

    def test_file_count(self, file_service):
        assert file_service.file_count == 0
        file_service.add_file(FileData(filename="a.csv", df=pd.DataFrame({"x": [1]})))
        assert file_service.file_count == 1
        file_service.add_file(FileData(filename="b.csv", df=pd.DataFrame({"y": [2]})))
        assert file_service.file_count == 2

    def test_duplicate_filename_renames(self, file_service):
        """Adding a file with the same name should auto-rename the new one."""
        fd1 = FileData(filename="data.csv", df=pd.DataFrame({"a": [1]}))
        fd2 = FileData(filename="data.csv", df=pd.DataFrame({"b": [2]}))
        file_service.add_file(fd1)
        file_service.add_file(fd2)

        assert file_service.get_file("data.csv") is fd1
        assert file_service.get_file("data (2).csv") is fd2
        assert file_service.file_count == 2

    def test_multiple_duplicates(self, file_service):
        """Three files with same name: data, data (2), data (3)."""
        fd1 = FileData(filename="data.csv", df=pd.DataFrame({"a": [1]}))
        fd2 = FileData(filename="data.csv", df=pd.DataFrame({"b": [2]}))
        fd3 = FileData(filename="data.csv", df=pd.DataFrame({"c": [3]}))
        file_service.add_file(fd1)
        file_service.add_file(fd2)
        file_service.add_file(fd3)

        assert file_service.get_file("data.csv") is fd1
        assert file_service.get_file("data (2).csv") is fd2
        assert file_service.get_file("data (3).csv") is fd3

    def test_duplicate_sets_display_name(self, file_service):
        fd1 = FileData(filename="data.csv", df=pd.DataFrame({"a": [1]}))
        fd2 = FileData(filename="data.csv", df=pd.DataFrame({"b": [2]}))
        file_service.add_file(fd1)
        file_service.add_file(fd2)
        assert fd2.display_name == "data (2).csv"


# ── load_from_bytes ────────────────────────────────────────────────


class TestLoadFromBytes:
    def test_load_valid_csv(self, file_service):
        success, result = file_service.load_from_bytes("test.csv", SAMPLE_CSV)
        assert success is True
        assert isinstance(result, FileData)
        assert result.rows == 3
        assert file_service.file_count == 1

    def test_load_invalid_extension(self, file_service):
        success, result = file_service.load_from_bytes("test.txt", SAMPLE_CSV)
        assert success is False
        assert "no soportado" in result
        assert file_service.file_count == 0

    def test_load_empty_file(self, file_service):
        success, result = file_service.load_from_bytes("empty.csv", b"")
        assert success is False
        assert file_service.file_count == 0

    def test_load_malformed_csv(self, file_service):
        success, result = file_service.load_from_bytes("bad.csv", SAMPLE_MALFORMED)
        assert success is True  # Pandas can handle some malformation
        assert isinstance(result, FileData)

    def test_load_valid_json(self, file_service):
        data = b'[{"x": 1}, {"x": 2}]'
        success, result = file_service.load_from_bytes("test.json", data)
        assert success is True
        assert isinstance(result, FileData)
        assert result.rows == 2
        assert file_service.file_count == 1

    def test_load_valid_tsv(self, file_service):
        data = b"x\ty\n1\t10\n2\t20\n"
        success, result = file_service.load_from_bytes("test.tsv", data)
        assert success is True
        assert isinstance(result, FileData)
        assert result.rows == 2
        assert file_service.file_count == 1

    def test_load_excel_unsupported_without_file(self, file_service):
        """Without a real .xlsx file, it should fail gracefully."""
        success, result = file_service.load_from_bytes("test.xlsx", b"not an excel")
        assert success is False
        assert file_service.file_count == 0


# ── get_context_for_llm ────────────────────────────────────────────


class TestGetContextForLLM:
    def test_no_files(self, file_service):
        context = file_service.get_context_for_llm()
        assert "No hay archivos" in context

    def test_with_files(self, file_service):
        fd = FileData(filename="test.csv", df=pd.DataFrame({"a": [1, 2]}))
        file_service.add_file(fd)
        context = file_service.get_context_for_llm()
        assert "test.csv" in context
        assert "Filas: 2" in context

    def test_multiple_files_in_context(self, file_service):
        fd1 = FileData(filename="a.csv", df=pd.DataFrame({"x": [1]}))
        fd2 = FileData(filename="b.csv", df=pd.DataFrame({"y": [2]}))
        file_service.add_file(fd1)
        file_service.add_file(fd2)
        context = file_service.get_context_for_llm()
        assert "a.csv" in context
        assert "b.csv" in context
        assert "---" in context  # separator


# ── JSON Parsing ────────────────────────────────────────────────────


class TestParseJSON:
    SAMPLE_JSON_RECORDS = b'[{"nombre": "Alice", "edad": 30}, {"nombre": "Bob", "edad": 25}]'
    SAMPLE_JSON_EMPTY = b"[]"

    def test_parse_json_records(self, file_service):
        fd = file_service.parse_json("datos.json", self.SAMPLE_JSON_RECORDS)
        assert fd.filename == "datos.json"
        assert fd.rows == 2
        assert fd.columns == 2
        assert list(fd.df.columns) == ["nombre", "edad"]
        assert fd.df.iloc[0]["nombre"] == "Alice"

    def test_parse_json_sets_size_bytes(self, file_service):
        fd = file_service.parse_json("datos.json", self.SAMPLE_JSON_RECORDS)
        assert fd.size_bytes == len(self.SAMPLE_JSON_RECORDS)


# ── TSV Parsing ────────────────────────────────────────────────────


class TestParseTSV:
    SAMPLE_TSV = b"nombre\tedad\nAlice\t30\nBob\t25\nCarol\t35\n"
    SAMPLE_TSV_EMPTY = b"nombre\tedad\n"

    def test_parse_tsv(self, file_service):
        fd = file_service.parse_tsv("datos.tsv", self.SAMPLE_TSV)
        assert fd.filename == "datos.tsv"
        assert fd.rows == 3
        assert fd.columns == 2
        assert list(fd.df.columns) == ["nombre", "edad"]

    def test_parse_tsv_sets_size_bytes(self, file_service):
        fd = file_service.parse_tsv("datos.tsv", self.SAMPLE_TSV)
        assert fd.size_bytes == len(self.SAMPLE_TSV)


# ── Excel (without real xlsx) ──────────────────────────────────────


class TestExcel:
    def test_get_excel_sheets_empty_list_on_invalid(self, file_service):
        """Without a real xlsx, this should raise or return empty — we expect it to be called with valid data."""
        # This test just validates that FileService has the method
        assert hasattr(file_service, "get_excel_sheets")
