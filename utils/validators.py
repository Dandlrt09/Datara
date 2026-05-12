"""
File validation utilities.

Validates uploaded files for type, size, and content integrity
before attempting to parse them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Max file size: 200 MB
MAX_FILE_SIZE_BYTES = 200 * 1024 * 1024

ALLOWED_EXTENSIONS = {".csv", ".xlsx"}

# Common CSV MIME types for display purposes
SUPPORTED_FORMATS = {
    ".csv": "CSV (valores separados por comas)",
    ".xlsx": "Excel (.xlsx)",
}


@dataclass
class ValidationResult:
    """Result of file validation."""

    valid: bool
    error_message: str = ""
    warnings: list[str] = field(default_factory=list)


def validate_file(filename: str, file_size: int) -> ValidationResult:
    """
    Validate an uploaded file before processing.

    Checks:
      - File extension is .csv or .xlsx
      - File size does not exceed 200 MB
      - File is not empty

    Args:
        filename: Original filename from upload
        file_size: Size in bytes

    Returns:
        ValidationResult with valid flag and error message if invalid
    """
    ext = Path(filename).suffix.lower()

    # Check extension
    if ext not in ALLOWED_EXTENSIONS:
        supported = ", ".join(SUPPORTED_FORMATS[f] for f in ALLOWED_EXTENSIONS)
        return ValidationResult(
            valid=False,
            error_message=(
                f"Formato no soportado: '{ext}'. "
                f"Subí archivos en los siguientes formatos: {supported}."
            ),
        )

    # Check size
    if file_size > MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        limit_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        return ValidationResult(
            valid=False,
            error_message=(
                f"El archivo de {size_mb:.1f} MB excede el límite de "
                f"{int(limit_mb)} MB."
            ),
        )

    # Check empty
    if file_size == 0:
        return ValidationResult(
            valid=False,
            error_message="El archivo está vacío. Subí un archivo que contenga datos.",
        )

    return ValidationResult(valid=True)
