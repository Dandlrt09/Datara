"""
File Service: handles file upload, parsing, validation, and multi-file storage.

Supports:
  - CSV: auto-detect delimiter, UTF-8 encoding
  - Excel (.xlsx): sheet selection, multi-sheet support
  - JSON (.json): array of records (orient='records') with fallback
  - TSV (.tsv): tab-separated values
  - Multiple files in session: add, remove, list, get
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

import pandas as pd

from models import FileData
from utils.validators import validate_file


class FileService:
    """Manages file uploads, parsing, and in-memory storage."""

    def __init__(self):
        self._files: dict[str, FileData] = {}

    # ─── Parsing ───────────────────────────────────────────────────

    def parse_csv(self, filename: str, content: bytes) -> FileData:
        """
        Parse a CSV file from bytes.

        Auto-detects delimiter (comma, semicolon, tab).
        """
        # Try common delimiters
        delimiters = [",", ";", "\t", "|"]
        df = None

        for delim in delimiters:
            try:
                df = pd.read_csv(
                    io.BytesIO(content),
                    delimiter=delim,
                    encoding="utf-8",
                    engine="python",
                    nrows=100,  # Read a sample first
                )
                # If we got more than 1 column, this delimiter is likely correct
                if len(df.columns) > 1:
                    # Now read the full file
                    df = pd.read_csv(
                        io.BytesIO(content),
                        delimiter=delim,
                        encoding="utf-8",
                        engine="python",
                    )
                    break
            except Exception:
                continue

        # If no delimiter worked, try default
        if df is None or df.empty:
            df = pd.read_csv(io.BytesIO(content), encoding="utf-8", engine="python")

        # Clean column names
        df.columns = [str(col).strip() for col in df.columns]

        return FileData(
            filename=filename,
            df=df,
            size_bytes=len(content),
        )

    def parse_excel(self, filename: str, content: bytes, sheet_name: str = "") -> FileData:
        """
        Parse an Excel file from bytes.

        If sheet_name is empty and the file has multiple sheets,
        returns the first sheet. The caller can get available sheet
        names via get_excel_sheets().
        """
        excel_file = pd.ExcelFile(io.BytesIO(content))

        if not sheet_name:
            sheet_name = excel_file.sheet_names[0]

        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        df.columns = [str(col).strip() for col in df.columns]

        return FileData(
            filename=filename,
            df=df,
            sheet_name=sheet_name,
            size_bytes=len(content),
        )

    def parse_json(self, filename: str, content: bytes) -> FileData:
        """
        Parse a JSON file from bytes.

        Expects a JSON array of records by default (orient='records'),
        with fallback to pandas' default detection.
        """
        try:
            # Try records-orientation first (most common: [{col: val}, ...])
            df = pd.read_json(io.BytesIO(content), orient="records")
        except ValueError:
            # Fallback to pandas default detection
            df = pd.read_json(io.BytesIO(content))

        df.columns = [str(col).strip() for col in df.columns]

        return FileData(
            filename=filename,
            df=df,
            size_bytes=len(content),
        )

    def parse_tsv(self, filename: str, content: bytes) -> FileData:
        """
        Parse a TSV (tab-separated) file from bytes.
        """
        df = pd.read_csv(
            io.BytesIO(content),
            delimiter="\t",
            encoding="utf-8",
            engine="python",
        )

        df.columns = [str(col).strip() for col in df.columns]

        return FileData(
            filename=filename,
            df=df,
            size_bytes=len(content),
        )

    def get_excel_sheets(self, content: bytes) -> list[str]:
        """Return available sheet names from an Excel file."""
        excel_file = pd.ExcelFile(io.BytesIO(content))
        return excel_file.sheet_names

    # ─── Multi-file Storage ────────────────────────────────────────

    def add_file(self, filedata: FileData) -> None:
        """Add a file to the session storage."""
        base_name = filedata.filename

        # Handle duplicate filenames
        if base_name in self._files:
            counter = 2
            while f"{Path(base_name).stem} ({counter}){Path(base_name).suffix}" in self._files:
                counter += 1
            new_name = f"{Path(base_name).stem} ({counter}){Path(base_name).suffix}"
            filedata.display_name = new_name
            self._files[new_name] = filedata
        else:
            self._files[base_name] = filedata

    def remove_file(self, filename: str) -> None:
        """Remove a file from session storage."""
        self._files.pop(filename, None)

    def get_file(self, filename: str) -> Optional[FileData]:
        """Get a specific file by name."""
        return self._files.get(filename)

    def list_files(self) -> list[FileData]:
        """Get all loaded files."""
        return list(self._files.values())

    def get_filenames(self) -> list[str]:
        """Get names of all loaded files."""
        return list(self._files.keys())

    def clear_all(self) -> None:
        """Remove all files from session."""
        self._files.clear()

    @property
    def file_count(self) -> int:
        return len(self._files)

    # ─── Convenience ───────────────────────────────────────────────

    def load_from_bytes(
        self, filename: str, content: bytes
    ) -> tuple[bool, FileData | str]:
        """
        Validate and load a file from raw bytes.

        Returns:
            Tuple of (success, FileData if success else error_message)
        """
        # Validate first
        validation = validate_file(filename, len(content))
        if not validation.valid:
            return False, validation.error_message

        # Parse based on extension
        ext = Path(filename).suffix.lower()
        try:
            if ext == ".csv":
                filedata = self.parse_csv(filename, content)
            elif ext == ".xlsx":
                filedata = self.parse_excel(filename, content)
            elif ext == ".json":
                filedata = self.parse_json(filename, content)
            elif ext == ".tsv":
                filedata = self.parse_tsv(filename, content)
            else:
                return False, f"Formato no soportado: {ext}"
        except pd.errors.EmptyDataError:
            return False, "El archivo no contiene datos."
        except pd.errors.ParserError as e:
            return False, f"Error al parsear el archivo: {e}"
        except Exception as e:
            return False, f"Error inesperado al leer el archivo: {e}"

        self.add_file(filedata)
        return True, filedata

    def get_context_for_llm(self) -> str:
        """Build a summary of all files for LLM context."""
        if not self._files:
            return "No hay archivos cargados."

        parts = []
        for fdata in self._files.values():
            parts.append(fdata.summary())
        return "\n---\n".join(parts)
