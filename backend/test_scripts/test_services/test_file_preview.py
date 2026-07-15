"""Tests for file preview service helpers."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.schemas.uploads import FilePreviewType
from backend.app.services import file_preview
from backend.app.services.file_preview import UnsupportedPreviewError
from backend.test_scripts.test_utils import print_section, print_success

ARTIFACTS_DIR = Path(__file__).resolve().parents[3] / "backend" / "data" / "test" / "_file_preview_pytest"


@pytest.fixture(autouse=True)
def _clean_artifacts_dir():
    """Keep file-preview test artifacts isolated inside repository."""
    if ARTIFACTS_DIR.exists():
        shutil.rmtree(ARTIFACTS_DIR)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    yield
    if ARTIFACTS_DIR.exists():
        shutil.rmtree(ARTIFACTS_DIR)


def _artifact_path(name: str) -> Path:
    return ARTIFACTS_DIR / f"{uuid4().hex}_{name}"


def _write_bytes(name: str, content: bytes) -> Path:
    path = _artifact_path(name)
    path.write_bytes(content)
    return path


def _create_workbook_file() -> Path:
    pytest.importorskip("openpyxl")
    from openpyxl import Workbook  # noqa: PLC0415

    workbook = Workbook()
    summary = workbook.active
    summary.title = "Summary"
    summary["A1"] = "Name"
    summary["B1"] = 10
    summary["A2"] = "Cash"
    summary["C2"] = "Sparse"

    details = workbook.create_sheet("Details")
    details["A1"] = "Date"
    details["B1"] = "Type"
    details["A2"] = "2025-01-01"
    details["B2"] = "BUY"

    path = _artifact_path("preview.xlsx")
    workbook.save(path)
    return path


@pytest.mark.parametrize(
    ("filename", "mime_type", "expected"),
    [
        ("chart.png", "image/png; charset=binary", FilePreviewType.IMAGE),
        ("report.pdf", None, FilePreviewType.PDF),
        ("notes.markdown", None, FilePreviewType.MARKDOWN),
        ("table.xls", "application/vnd.ms-excel", FilePreviewType.TABLE),
        ("plain.txt", "text/plain; charset=utf-8", FilePreviewType.TEXT),
        ("archive.bin", "application/octet-stream", FilePreviewType.UNSUPPORTED),
    ],
)
def test_detect_preview_type(filename: str, mime_type: str | None, expected: FilePreviewType):
    """detect_preview_type() classifies main supported preview families."""
    print_section(f"file_preview.detect_preview_type: {filename}")

    assert file_preview.detect_preview_type(filename, mime_type) == expected

    print_success(f"✓ Detected {expected.value} for {filename}")


def test_read_supported_preview_type_supported_and_unsupported():
    """read_supported_preview_type() returns type or raises for unsupported files."""
    print_section("file_preview.read_supported_preview_type")

    assert file_preview.read_supported_preview_type("holdings.csv", "text/csv") == FilePreviewType.TABLE

    with pytest.raises(UnsupportedPreviewError, match="Preview is not supported"):
        file_preview.read_supported_preview_type("archive.bin", "application/octet-stream")

    print_success("✓ Supported type returned, unsupported file rejected")


def test_read_text_content_detects_utf8_sig_and_cp1252():
    """_read_text_content() decodes common happy-path encodings."""
    print_section("file_preview._read_text_content")

    utf8_path = _write_bytes("utf8.txt", "hello\nworld".encode("utf-8-sig"))
    cp1252_path = _write_bytes("cp1252.txt", "café".encode("cp1252"))

    utf8_text, utf8_encoding = file_preview._read_text_content(utf8_path)
    cp1252_text, cp1252_encoding = file_preview._read_text_content(cp1252_path)

    assert utf8_text == "hello\nworld"
    assert utf8_encoding == "utf-8-sig"
    assert cp1252_text == "café"
    assert cp1252_encoding == "cp1252"

    print_success("✓ Text content decoded with expected encodings")


def test_detect_csv_delimiter_sniffed_and_fallback():
    """_detect_csv_delimiter() sniffs delimiter, then falls back to comma."""
    print_section("file_preview._detect_csv_delimiter")

    assert file_preview._detect_csv_delimiter("name;amount\nCash;10\n") == ";"
    assert file_preview._detect_csv_delimiter("single value only\nsecond row\n") == ","

    print_success("✓ CSV delimiter sniff + fallback covered")


def test_excel_engine_error_message_variants():
    """_excel_engine_error_message() maps xls/xlsx engines to user messages."""
    print_section("file_preview._excel_engine_error_message")

    assert file_preview._excel_engine_error_message(".xls") == "Legacy .xls preview requires xlrd on server"
    assert file_preview._excel_engine_error_message(".xlsx") == "Excel preview requires openpyxl on server"

    print_success("✓ Excel engine error messages mapped")


def test_stringify_and_normalize_helpers():
    """_stringify_table_value() and _normalize_row() keep table cells consistent."""
    print_section("file_preview stringify + normalize helpers")

    assert file_preview._stringify_table_value(None) == ""
    assert file_preview._stringify_table_value(12.5) == "12.5"
    assert file_preview._normalize_row(["Cash"], 3) == ["Cash", "", ""]
    assert file_preview._normalize_row(["Cash", "10"], 2) == ["Cash", "10"]

    print_success("✓ Stringify + normalize helpers covered")


def test_read_excel_preview_reads_default_and_selected_sheet():
    """_read_excel_preview() returns normalized rows for default and explicit sheet."""
    print_section("file_preview._read_excel_preview")

    workbook_path = _create_workbook_file()

    summary_preview = file_preview._read_excel_preview(workbook_path)
    details_preview = file_preview._read_excel_preview(workbook_path, sheet_name="Details")

    assert summary_preview.sheet_names == ["Summary", "Details"]
    assert summary_preview.active_sheet_name == "Summary"
    assert summary_preview.total_rows == 2
    assert summary_preview.total_cols == 3
    assert summary_preview.rows == [["Name", "10", ""], ["Cash", "", "Sparse"]]
    assert summary_preview.csv_delimiter is None

    assert details_preview.active_sheet_name == "Details"
    assert details_preview.total_rows == 2
    assert details_preview.total_cols == 2
    assert details_preview.rows == [["Date", "Type"], ["2025-01-01", "BUY"]]

    print_success("✓ Excel preview reads default + selected sheet")
