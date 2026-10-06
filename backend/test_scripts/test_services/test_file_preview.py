"""Tests for file preview service helpers."""

from __future__ import annotations

import importlib
import io
import shutil
import zipfile
from pathlib import Path
from typing import Callable
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


# ============================================================================
# F2 — THE PREVIEW OF A DAMAGED EXCEL WORKBOOK (Danske Bank, step 6)
# ============================================================================
#
# ``_read_excel_preview`` reads a workbook with two pandas calls, ``pd.ExcelFile`` and ``pd.read_excel``. Before F2 it
# mapped only ``ImportError`` (to ``UnsupportedPreviewError``), and a damaged workbook made those calls raise
# ``zipfile.BadZipFile``, ``KeyError``, ``xml.etree.ElementTree.ParseError`` or, on an ``.xls``, ``xlrd.XLRDError``,
# ``xlrd.compdoc.CompDocError``, ``IndexError`` or ``struct.error``: none is a ``ValueError``, so both preview endpoints
# (``brokers.py`` and ``uploads.py``) answered 500. The coordinator's decision, verbatim: «le 4 famiglie, prese solo
# attorno alle due chiamate pandas, in `UnreadablePreviewError(ValueError)`. API invariate; un rosso anche via
# `uploads.py`.» He then extended the xlrd family (D3) with ``xlrd.compdoc.CompDocError``, ``IndexError`` and
# ``struct.error``, still only around the two pandas calls. The new class is reached with ``getattr`` at run time: while
# it does not exist the reds fail on their assertions, not this module on its import. The guards hold before and after
# F2: a missing sheet stays a ``ValueError`` of its own, a missing engine an ``UnsupportedPreviewError``, any other
# exception escapes unchanged (the catch is narrow), and so does a ``KeyError`` or ``IndexError`` raised after the two
# calls (the catch is scoped to them). Every file is synthetic, built here, or a damaged copy of the committed public
# ``.xls`` sample.

# Bytes that are no workbook and not even a zip archive.
NOT_A_WORKBOOK = b"LibreFolio F2 synthetic bytes: not an Excel workbook and not a zip archive.\n" * 16
# The member openpyxl writes the first sheet ("Summary" in ``_create_workbook_file``) to.
FIRST_SHEET_XML = "xl/worksheets/sheet1.xml"
# The committed public sample that test_api/test_uploads_api.py previews whole (UPLOAD-005F); here only damaged copies of it.
SAMPLE_XLS = Path(__file__).resolve().parents[3] / "backend" / "staticResources" / "FilePreviewSamples" / "file_example_XLS_10.xls"
# The header of an OLE2 compound document, the container of an ``.xls``.
COMPOUND_HEADER_BYTES = 512
PREVIEW_LINKS = file_preview.FilePreviewLinks(source_url="/synthetic/source", download_url="/synthetic/download", preview_url=None)


def _unreadable_preview_error() -> type | None:
    """``file_preview.UnreadablePreviewError`` (F2), or None while it does not exist."""
    return getattr(file_preview, "UnreadablePreviewError", None)


def _describe(error: BaseException | None) -> str:
    if error is None:
        return "nothing"
    return f"{type(error).__module__}.{type(error).__qualname__}: {error}"


def _preview_failure(path: Path, filename: str, size_bytes: int) -> Exception:
    """What ``build_preview_response`` raises for ``path``, whatever its type: the type and its cause are what F2 asserts."""
    try:
        file_preview.build_preview_response(path, filename, None, size_bytes, PREVIEW_LINKS)
    except Exception as error:
        return error
    pytest.fail(f"the preview of the damaged {filename} raised nothing", pytrace=False)


def _not_a_workbook() -> bytes:
    return NOT_A_WORKBOOK


def _truncated_workbook() -> bytes:
    """A valid workbook cut to half its bytes: the zip's central directory, at its end, is gone."""
    valid = _create_workbook_file().read_bytes()
    return valid[: len(valid) // 2]


def _csv_text() -> bytes:
    """A CSV statement saved under an ``.xlsx`` name."""
    return b"date,type,amount,currency\n2025-01-01,DEPOSIT,1000.00,EUR\n2025-01-02,BUY,-500.00,EUR\n"


def _zip_of(members: dict[str, bytes]) -> bytes:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as written:
        for name, content in members.items():
            written.writestr(name, content)
    return archive.getvalue()


def _empty_zip() -> bytes:
    """A zip archive with no member at all, so no ``[Content_Types].xml``."""
    return _zip_of({})


def _zip_with_readme_only() -> bytes:
    """A zip archive holding only a ``readme.txt``, so no ``[Content_Types].xml``."""
    return _zip_of({"readme.txt": b"LibreFolio F2 synthetic archive: there is no workbook inside.\n"})


def _workbook_with_unparseable_sheet() -> bytes:
    """A valid workbook whose first sheet's XML is replaced by ``<not-xml``, every other member copied unchanged: it opens, its first sheet does not parse."""
    valid = _create_workbook_file().read_bytes()
    rebuilt = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(valid)) as original, zipfile.ZipFile(rebuilt, "w") as damaged:
        assert FIRST_SHEET_XML in original.namelist(), f"premise: openpyxl writes the first sheet as {FIRST_SHEET_XML}: {original.namelist()}"
        for member in original.infolist():
            damaged.writestr(member, b"<not-xml" if member.filename == FIRST_SHEET_XML else original.read(member))
    return rebuilt.getvalue()


def _sample_xls() -> bytes:
    assert SAMPLE_XLS.is_file(), f"premise: the committed public sample is missing: {SAMPLE_XLS}"
    return SAMPLE_XLS.read_bytes()


def _sample_xls_cut_to(fraction: float) -> bytes:
    """The ``.xls`` sample cut to ``fraction`` of its bytes."""
    sample = _sample_xls()
    return sample[: int(len(sample) * fraction)]


def _sample_xls_zeroed_after_header() -> bytes:
    """The ``.xls`` sample with its first 512 bytes (the compound document's header) kept and every byte after them zeroed: same length, no directory."""
    sample = _sample_xls()
    assert len(sample) > COMPOUND_HEADER_BYTES, f"premise: the sample is more than its header: {len(sample)} bytes"
    return sample[:COMPOUND_HEADER_BYTES] + bytes(len(sample) - COMPOUND_HEADER_BYTES)


def _exception_type(dotted_name: str) -> type[Exception]:
    """The exception class named ``module.Class``, e.g. ``xlrd.compdoc.CompDocError``."""
    module_name, _, class_name = dotted_name.rpartition(".")
    return getattr(importlib.import_module(module_name), class_name)


# (name the file is previewed under, how its bytes are built, the engine reading it, the exception that engine raises on it)
DAMAGED_WORKBOOKS = [
    pytest.param("damaged.xlsx", _not_a_workbook, "openpyxl", "zipfile.BadZipFile", id="garbage-bytes-xlsx"),
    pytest.param("truncated.xlsx", _truncated_workbook, "openpyxl", "zipfile.BadZipFile", id="truncated-xlsx"),
    pytest.param("statement.xlsx", _csv_text, "openpyxl", "zipfile.BadZipFile", id="csv-text-xlsx"),
    pytest.param("empty.xlsx", _empty_zip, "openpyxl", "builtins.KeyError", id="empty-zip-xlsx"),
    pytest.param("readme.xlsx", _zip_with_readme_only, "openpyxl", "builtins.KeyError", id="readme-only-zip-xlsx"),
    pytest.param("broken_sheet.xlsx", _workbook_with_unparseable_sheet, "openpyxl", "xml.etree.ElementTree.ParseError", id="unparseable-sheet-xml-xlsx"),
    pytest.param("damaged.xls", _not_a_workbook, "xlrd", "xlrd.XLRDError", id="garbage-bytes-xls"),
    pytest.param("truncated_5_percent.xls", lambda: _sample_xls_cut_to(0.05), "xlrd", "struct.error", id="sample-xls-truncated-5-percent"),
    pytest.param("truncated_half.xls", lambda: _sample_xls_cut_to(0.5), "xlrd", "builtins.IndexError", id="sample-xls-truncated-half"),
    pytest.param("zeroed_after_header.xls", _sample_xls_zeroed_after_header, "xlrd", "xlrd.compdoc.CompDocError", id="sample-xls-zeroed-after-header"),
]


def test_unreadable_preview_error_is_a_value_error_and_not_an_unsupported_one():
    """F2: ``UnreadablePreviewError`` exists, is a ``ValueError`` (both preview endpoints answer it with 400) and is not
    an ``UnsupportedPreviewError``: the format is supported, it is the file that cannot be read."""
    print_section("F2: file_preview.UnreadablePreviewError")

    unreadable = _unreadable_preview_error()

    assert isinstance(unreadable, type), f"file_preview.UnreadablePreviewError is {unreadable!r}: not implemented yet (F2)"
    assert issubclass(unreadable, ValueError), f"UnreadablePreviewError must be a ValueError, which both preview endpoints answer with 400: its MRO is {[cls.__name__ for cls in unreadable.__mro__]}"
    assert not issubclass(unreadable, UnsupportedPreviewError), "UnreadablePreviewError must not be an UnsupportedPreviewError: the format is supported, the file is damaged"

    print_success("✓ UnreadablePreviewError is a ValueError, apart from UnsupportedPreviewError")


@pytest.mark.parametrize(("filename", "build", "engine", "reader_error"), DAMAGED_WORKBOOKS)
def test_damaged_workbook_preview_raises_unreadable_preview_error(filename: str, build: Callable[[], bytes], engine: str, reader_error: str):
    """F2: the preview of a damaged workbook raises ``UnreadablePreviewError``, chaining the reader's own exception as its cause."""
    print_section(f"F2: preview of a damaged workbook, {filename}")
    pytest.importorskip(engine)  # a case is skipped where the server lacks its engine: xlrd, for the .xls ones
    expected_cause = _exception_type(reader_error)
    content = build()
    path = _write_bytes(filename, content)

    raised = _preview_failure(path, filename, len(content))

    unreadable = _unreadable_preview_error()
    assert unreadable is not None and isinstance(raised, unreadable), f"the preview of {filename} raised {_describe(raised)}, not file_preview.UnreadablePreviewError: both preview endpoints answer 500 (F2)"
    assert isinstance(raised.__cause__, expected_cause), f"UnreadablePreviewError must chain the reader's {reader_error} as its cause (raise ... from ...): its cause is {_describe(raised.__cause__)}"

    print_success(f"✓ {filename}: UnreadablePreviewError from {reader_error}")


def test_missing_sheet_stays_a_value_error_of_its_own():
    """F2 guard: a sheet the workbook does not have is still a ``ValueError`` that is not an ``UnreadablePreviewError``: the workbook reads fine."""
    print_section("F2 guard: a missing sheet")
    workbook_path = _create_workbook_file()

    with pytest.raises(ValueError) as excinfo:
        file_preview.build_preview_response(workbook_path, "preview.xlsx", None, workbook_path.stat().st_size, PREVIEW_LINKS, sheet_name=f"Missing_{uuid4().hex[:8]}")

    unreadable = _unreadable_preview_error()
    assert unreadable is None or not isinstance(excinfo.value, unreadable), f"a missing sheet became an UnreadablePreviewError: {_describe(excinfo.value)}"

    print_success("✓ A missing sheet stays a ValueError of its own")


def test_missing_excel_engine_stays_an_unsupported_preview_error(monkeypatch):
    """F2 guard: an ``ImportError`` from the Excel engine is still an ``UnsupportedPreviewError`` that chains it."""
    print_section("F2 guard: a missing Excel engine")
    workbook_path = _create_workbook_file()
    missing = ImportError("synthetic: no Excel engine on this server")

    def _no_engine(*_args, **_kwargs):
        raise missing

    monkeypatch.setattr(file_preview.pd, "ExcelFile", _no_engine)

    with pytest.raises(UnsupportedPreviewError) as excinfo:
        file_preview.build_preview_response(workbook_path, "preview.xlsx", None, workbook_path.stat().st_size, PREVIEW_LINKS)

    assert excinfo.value.__cause__ is missing, f"the UnsupportedPreviewError does not chain the engine's ImportError: its cause is {_describe(excinfo.value.__cause__)}"

    print_success("✓ A missing Excel engine stays an UnsupportedPreviewError")


def test_unexpected_reader_error_escapes_unchanged(monkeypatch):
    """F2 guard: the catch is narrow, an exception outside the four families (a ``RuntimeError``) escapes unchanged, and the endpoints keep answering 500 for a server fault."""
    print_section("F2 guard: an unexpected reader error")
    workbook_path = _create_workbook_file()
    boom = RuntimeError("boom")

    def _explodes(*_args, **_kwargs):
        raise boom

    monkeypatch.setattr(file_preview.pd, "ExcelFile", _explodes)

    with pytest.raises(RuntimeError) as excinfo:
        file_preview.build_preview_response(workbook_path, "preview.xlsx", None, workbook_path.stat().st_size, PREVIEW_LINKS)

    assert excinfo.value is boom, f"the RuntimeError did not escape unchanged: {_describe(excinfo.value)}"

    print_success("✓ An unexpected reader error escapes unchanged")


@pytest.mark.parametrize("error_type", [KeyError, IndexError], ids=["key-error", "index-error"])
def test_caught_type_raised_outside_the_pandas_calls_escapes_unchanged(monkeypatch, error_type: type[Exception]):
    """F2 guard: the catch is scoped to the two pandas calls. A ``KeyError`` or an ``IndexError``, types it takes around
    them, raised after them (here by ``_dataframe_to_rows``, on a valid workbook) escapes unchanged: a fault of the
    server, not a damaged file."""
    print_section(f"F2 guard: a {error_type.__name__} outside the two pandas calls")
    workbook_path = _create_workbook_file()
    boom = error_type("boom")

    def _explodes(*_args, **_kwargs):
        raise boom

    monkeypatch.setattr(file_preview, "_dataframe_to_rows", _explodes)

    with pytest.raises(error_type) as excinfo:
        file_preview.build_preview_response(workbook_path, "preview.xlsx", None, workbook_path.stat().st_size, PREVIEW_LINKS)

    assert excinfo.value is boom, f"the {error_type.__name__} raised after the two pandas calls did not escape unchanged: {_describe(excinfo.value)}"

    print_success(f"✓ A {error_type.__name__} outside the two pandas calls escapes unchanged")
