"""
Shared file preview helpers for static uploads and BRIM files.

The service is synchronous by design and should be executed via
``asyncio.to_thread(...)`` from async API handlers.
"""

from __future__ import annotations

import csv
import io
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd
from PIL import Image

from backend.app.schemas.uploads import FilePreviewResponse, FilePreviewType

IMAGE_PREVIEW_SIZE = "1600x1600"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".tiff", ".tif", ".ico"}
MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdown"}
TABLE_EXTENSIONS = {".csv", ".xlsx", ".xls"}
PDF_EXTENSIONS = {".pdf"}
TEXT_EXTENSIONS = {
    ".txt",
    ".log",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".html",
    ".htm",
    ".css",
    ".sql",
    ".csv",
}
TEXT_MIME_TYPES = {
    "application/json",
    "application/xml",
    "application/x-yaml",
    "application/yaml",
}


class UnsupportedPreviewError(ValueError):
    """Raised when a file does not support inline preview."""


@dataclass(frozen=True)
class FilePreviewLinks:
    """URLs associated with a previewable file."""

    source_url: str
    download_url: str
    preview_url: Optional[str] = None


def detect_preview_type(filename: str, mime_type: Optional[str] = None) -> FilePreviewType:
    """Detect preview type from filename and MIME type."""
    ext = Path(filename).suffix.lower()
    resolved_mime = (mime_type or "").split(";")[0].strip().lower()

    if resolved_mime.startswith("image/") or ext in IMAGE_EXTENSIONS:
        return FilePreviewType.IMAGE
    if resolved_mime == "application/pdf" or ext in PDF_EXTENSIONS:
        return FilePreviewType.PDF
    if ext in MARKDOWN_EXTENSIONS:
        return FilePreviewType.MARKDOWN
    if ext in TABLE_EXTENSIONS or resolved_mime in {"text/csv", "application/vnd.ms-excel"}:
        return FilePreviewType.TABLE
    if resolved_mime.startswith("text/") or resolved_mime in TEXT_MIME_TYPES or ext in TEXT_EXTENSIONS:
        return FilePreviewType.TEXT
    return FilePreviewType.UNSUPPORTED


def build_preview_response(
    file_path: Path,
    filename: str,
    mime_type: Optional[str],
    size_bytes: int,
    links: FilePreviewLinks,
    *,
    sheet_name: Optional[str] = None,
) -> FilePreviewResponse:
    """Build a structured preview response for a file."""
    resolved_mime = (mime_type or mimetypes.guess_type(filename)[0] or "application/octet-stream").split(";")[0].strip()
    preview_type = detect_preview_type(filename, resolved_mime)
    if preview_type == FilePreviewType.UNSUPPORTED:
        raise UnsupportedPreviewError(f"Preview is not supported for '{filename}'")

    base = FilePreviewResponse(
        preview_type=preview_type,
        filename=filename,
        mime_type=resolved_mime,
        size_bytes=size_bytes,
        source_url=links.source_url,
        download_url=links.download_url,
        preview_url=links.preview_url if preview_type == FilePreviewType.IMAGE else None,
    )

    if preview_type == FilePreviewType.IMAGE:
        width, height = _read_image_dimensions(file_path)
        return base.model_copy(update={"image_width": width, "image_height": height})

    if preview_type == FilePreviewType.PDF:
        return base

    if preview_type in {FilePreviewType.TEXT, FilePreviewType.MARKDOWN}:
        text_content, encoding = _read_text_content(file_path)
        total_lines = len(text_content.splitlines())
        return base.model_copy(
            update={
                "text_content": text_content,
                "detected_encoding": encoding,
                "total_lines": total_lines,
            }
        )

    if preview_type == FilePreviewType.TABLE:
        table_preview = _read_table_preview(file_path, filename, sheet_name=sheet_name)
        return base.model_copy(
            update={
                "table_rows": table_preview.rows,
                "total_rows": table_preview.total_rows,
                "total_cols": table_preview.total_cols,
                "sheet_names": table_preview.sheet_names,
                "active_sheet_name": table_preview.active_sheet_name,
                "csv_delimiter": table_preview.csv_delimiter,
            }
        )

    raise UnsupportedPreviewError(f"Preview is not supported for '{filename}'")


def build_image_preview_url(source_url: str) -> str:
    """Build the optimized image preview URL for modal usage."""
    separator = "&" if "?" in source_url else "?"
    return f"{source_url}{separator}img_preview={IMAGE_PREVIEW_SIZE}"


def read_supported_preview_type(filename: str, mime_type: Optional[str] = None) -> FilePreviewType:
    """Detect preview type and raise when the file is unsupported."""
    preview_type = detect_preview_type(filename, mime_type)
    if preview_type == FilePreviewType.UNSUPPORTED:
        raise UnsupportedPreviewError(f"Preview is not supported for '{filename}'")
    return preview_type


def _read_image_dimensions(file_path: Path) -> tuple[int, int]:
    with Image.open(file_path) as img:
        return img.size


def _read_text_content(file_path: Path) -> tuple[str, str]:
    raw_bytes = file_path.read_bytes()
    encodings = ("utf-8-sig", "utf-8", "cp1252", "latin-1")
    for encoding in encodings:
        try:
            return raw_bytes.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace"), "utf-8"


@dataclass(frozen=True)
class TablePreview:
    rows: list[list[str]]
    total_rows: int
    total_cols: int
    sheet_names: list[str]
    active_sheet_name: Optional[str]
    csv_delimiter: Optional[str]


def _read_table_preview(file_path: Path, filename: str, *, sheet_name: Optional[str] = None) -> TablePreview:
    ext = Path(filename).suffix.lower()
    if ext == ".csv":
        return _read_csv_preview(file_path)
    if ext in {".xlsx", ".xls"}:
        return _read_excel_preview(file_path, sheet_name=sheet_name)
    raise UnsupportedPreviewError(f"Table preview is not supported for '{filename}'")


def _read_csv_preview(file_path: Path) -> TablePreview:
    text_content, _ = _read_text_content(file_path)
    delimiter = _detect_csv_delimiter(text_content)
    reader = csv.reader(io.StringIO(text_content), delimiter=delimiter)
    rows = [list(row) for row in reader]
    total_rows = len(rows)
    total_cols = max((len(row) for row in rows), default=0)
    normalized_rows = [_normalize_row(row, total_cols) for row in rows]
    return TablePreview(
        rows=normalized_rows,
        total_rows=total_rows,
        total_cols=total_cols,
        sheet_names=[],
        active_sheet_name=None,
        csv_delimiter=delimiter,
    )


def _read_excel_preview(file_path: Path, *, sheet_name: Optional[str] = None) -> TablePreview:
    ext = file_path.suffix.lower()
    engine = _excel_engine_for_extension(ext)

    try:
        excel_file = pd.ExcelFile(file_path, engine=engine)
    except ImportError as e:
        raise UnsupportedPreviewError(_excel_engine_error_message(ext)) from e

    sheet_names = [str(name) for name in excel_file.sheet_names]
    active_sheet_name = sheet_name or (sheet_names[0] if sheet_names else None)
    if active_sheet_name is None:
        return TablePreview(rows=[], total_rows=0, total_cols=0, sheet_names=[], active_sheet_name=None, csv_delimiter=None)
    if active_sheet_name not in sheet_names:
        raise ValueError(f"Sheet '{active_sheet_name}' not found")

    try:
        dataframe = pd.read_excel(
            file_path,
            sheet_name=active_sheet_name,
            header=None,
            dtype=object,
            keep_default_na=False,
            engine=engine,
        )
    except ImportError as e:
        raise UnsupportedPreviewError(_excel_engine_error_message(ext)) from e

    rows = _dataframe_to_rows(dataframe)
    total_rows = len(rows)
    total_cols = max((len(row) for row in rows), default=0)
    normalized_rows = [_normalize_row(row, total_cols) for row in rows]
    return TablePreview(
        rows=normalized_rows,
        total_rows=total_rows,
        total_cols=total_cols,
        sheet_names=sheet_names,
        active_sheet_name=active_sheet_name,
        csv_delimiter=None,
    )


def _detect_csv_delimiter(text_content: str) -> str:
    sample = text_content[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
        return dialect.delimiter
    except csv.Error:
        return ","


def _dataframe_to_rows(dataframe: pd.DataFrame) -> list[list[str]]:
    if dataframe.empty:
        return []
    rows: list[list[str]] = []
    for row in dataframe.fillna("").itertuples(index=False, name=None):
        rows.append([_stringify_table_value(value) for value in row])
    return rows


def _excel_engine_for_extension(ext: str) -> str:
    if ext == ".xls":
        return "xlrd"
    return "openpyxl"


def _excel_engine_error_message(ext: str) -> str:
    if ext == ".xls":
        return "Legacy .xls preview requires xlrd on server"
    return "Excel preview requires openpyxl on server"


def _stringify_table_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _normalize_row(row: list[str], total_cols: int) -> list[str]:
    if len(row) >= total_cols:
        return row
    return row + [""] * (total_cols - len(row))
