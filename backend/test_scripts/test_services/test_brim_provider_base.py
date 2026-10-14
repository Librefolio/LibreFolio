"""
Test Suite: BRIMProvider Abstract Base — default property contracts and CSV text decoding

Covers Phase 7 Part 3 Closure_2 G-batch6 (post-G coverage gap-fill):

The ``BRIMProvider.docs_url`` property had **0% coverage** because every
shipped subclass overrides it. This suite instantiates a minimal stub
subclass that omits the override and asserts the documented default
(``None``). We extend the same pattern to ``icon_url`` and
``plugin_version`` to lock down the rest of the abstract contract.

Plan: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md`` §G-batch6.

It also covers how CSV exports are decoded (``TestTextEncodingFallback``):
the encoding chain ``TEXT_ENCODINGS``, the helpers built on it
(``_read_text``, ``_open_text``, ``_read_file_head``, ``detect_csv_delimiter``),
and the ``_brim_io`` readers, which must delegate to them.

Plan: Release_2 Phase_0 journal step 26, §4 (CSV encoding fix), step 1a.
"""

from __future__ import annotations

import csv
import datetime
import json
from pathlib import Path

import pytest

from backend.app.schemas.brim import BRIMFileStatus, BRIMParseOutput
from backend.app.services import brim_provider
from backend.app.services.brim_provider import BRIMProvider
from backend.app.services.brim_providers import _brim_io


class _StubBRIMProvider(BRIMProvider):
    """Minimal stub subclass — implements ONLY the abstract methods.

    By design we do NOT override ``docs_url``, ``icon_url`` or
    ``plugin_version`` so the inherited base-class defaults are exercised.
    """

    @property
    def provider_code(self) -> str:
        return "stub_for_tests"

    @property
    def provider_name(self) -> str:
        return "Stub For Tests"

    @property
    def description(self) -> str:
        return "Test-only stub used to assert BRIMProvider base defaults."

    def can_parse(self, file_path: Path) -> bool:
        return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        return BRIMParseOutput(transactions=[], warnings=[], extracted_assets={})


@pytest.fixture
def stub() -> _StubBRIMProvider:
    return _StubBRIMProvider()


@pytest.fixture
def isolated_brim_dir(tmp_path, monkeypatch):
    """Redirect BRIM storage to isolated test directory."""
    broker_reports_dir = tmp_path / "broker_reports"
    broker_reports_dir.mkdir()
    monkeypatch.setattr(brim_provider, "get_broker_reports_dir", lambda: broker_reports_dir)
    return broker_reports_dir


def test_docs_url_default_is_none(stub: _StubBRIMProvider) -> None:
    """G-batch6.14 — ``docs_url`` returns None when not overridden."""
    assert stub.docs_url is None


def test_icon_url_default_is_none(stub: _StubBRIMProvider) -> None:
    """G-batch6.15 — ``icon_url`` returns None when not overridden (parity check)."""
    assert stub.icon_url is None


def test_plugin_version_default(stub: _StubBRIMProvider) -> None:
    """G-batch6.16 — ``plugin_version`` defaults to ``'1.0.0'``."""
    assert stub.plugin_version == "1.0.0"


def test_to_plugin_info_propagates_default_docs_url(stub: _StubBRIMProvider) -> None:
    """G-batch6.17 — ``to_plugin_info`` carries the None default into the DTO."""
    info = stub.to_plugin_info()
    assert info.code == "stub_for_tests"
    assert info.docs_url is None
    assert info.icon_url is None
    assert info.plugin_version == "1.0.0"


def test_detect_csv_delimiter_detects_semicolon(stub: _StubBRIMProvider, tmp_path) -> None:
    """Base helper detects semicolon-delimited CSV exports."""
    file_path = tmp_path / "semicolon.csv"
    file_path.write_text("date;type;amount\n2025-01-01;BUY;100\n", encoding="utf-8")

    assert stub.detect_csv_delimiter(file_path) == ";"


def test_detect_csv_delimiter_detects_comma(stub: _StubBRIMProvider, tmp_path) -> None:
    """Base helper detects comma-delimited CSV exports."""
    file_path = tmp_path / "comma.csv"
    file_path.write_text("date,type,amount\n2025-01-01,BUY,100\n", encoding="utf-8")

    assert stub.detect_csv_delimiter(file_path) == ","


def test_build_file_info_from_metadata_for_uploaded_file(tmp_path) -> None:
    """Uploaded metadata sidecar deserializes with default optional fields."""
    meta_path = tmp_path / "uploaded.json"
    meta_path.write_text(
        json.dumps(
            {
                "file_id": "file-uploaded",
                "filename": "uploaded.csv",
                "size_bytes": 123,
                "status": "uploaded",
                "uploaded_at": "2026-01-02T03:04:05",
            }
        ),
        encoding="utf-8",
    )

    info = brim_provider._build_file_info_from_metadata(meta_path)

    assert info is not None
    assert info.file_id == "file-uploaded"
    assert info.status == BRIMFileStatus.UPLOADED
    assert info.uploaded_at == datetime.datetime.fromisoformat("2026-01-02T03:04:05").replace(tzinfo=datetime.UTC)
    assert info.processed_at is None
    assert info.compatible_plugins == []
    assert info.parse_is_stale is False


def test_build_file_info_from_metadata_marks_stale_parsed_file(tmp_path, monkeypatch) -> None:
    """Parsed metadata marks stale when registry version changed."""
    meta_path = tmp_path / "parsed.json"
    meta_path.write_text(
        json.dumps(
            {
                "file_id": "file-parsed",
                "filename": "parsed.csv",
                "size_bytes": 456,
                "status": "parsed",
                "uploaded_at": "2026-01-02T03:04:05",
                "processed_at": "2026-01-02T06:07:08",
                "compatible_plugins": ["broker_generic_csv"],
                "parsed_plugin_code": "broker_generic_csv",
                "parsed_plugin_version": "1.0.0",
            }
        ),
        encoding="utf-8",
    )

    class _PluginVersionBumped:
        plugin_version = "2.0.0"

    monkeypatch.setattr(
        brim_provider.BRIMProviderRegistry,
        "get_provider_instance",
        staticmethod(lambda code: _PluginVersionBumped() if code == "broker_generic_csv" else None),
    )

    info = brim_provider._build_file_info_from_metadata(meta_path)

    assert info is not None
    assert info.status == BRIMFileStatus.PARSED
    assert info.processed_at == datetime.datetime.fromisoformat("2026-01-02T06:07:08").replace(tzinfo=datetime.UTC)
    assert info.parsed_plugin_code == "broker_generic_csv"
    assert info.parsed_plugin_version == "1.0.0"
    assert info.parse_is_stale is True


def test_get_file_path_returns_broker_specific_file(isolated_brim_dir) -> None:
    """Stored file resolves to broker-specific status folder."""
    file_info = brim_provider.save_uploaded_file(
        content=b"date,type,amount\n2026-01-01,BUY,100\n",
        original_filename="broker_report.csv",
        user_id=7,
        broker_id=42,
    )

    file_path = brim_provider.get_file_path(file_info.file_id)

    expected = isolated_brim_dir / "uploaded" / "broker_42" / f"{file_info.file_id}.csv"
    assert file_path == expected
    assert file_path is not None and file_path.exists()


def test_get_file_path_falls_back_to_root_folder(isolated_brim_dir) -> None:
    """Legacy root-file layout still resolves when metadata has broker_id."""
    file_info = brim_provider.save_uploaded_file(
        content=b"date,type,amount\n2026-01-01,BUY,100\n",
        original_filename="broker_report.csv",
        user_id=7,
        broker_id=42,
    )
    broker_path = isolated_brim_dir / "uploaded" / "broker_42" / f"{file_info.file_id}.csv"
    fallback_path = isolated_brim_dir / "uploaded" / f"{file_info.file_id}.csv"
    broker_path.rename(fallback_path)

    file_path = brim_provider.get_file_path(file_info.file_id)

    assert file_path == fallback_path
    assert file_path is not None and file_path.exists()


# =============================================================================
# TEXT ENCODING FALLBACK: CSV exports saved as Windows-1252 or Latin-1
# =============================================================================

# A ";" export as a Windows spreadsheet saves it: accents in the header, decimal
# comma, and "€", which is byte 0x80 in Windows-1252 and does not exist in Latin-1.
_CP1252_SEMICOLON_CSV = "Città;Importo €;Größe\nForlì;12,50 €;3\nCafé;7,00 €;1\n".encode("cp1252")

# A ";" export only Latin-1 can decode: 0x81 has no Windows-1252 mapping.
_LATIN1_SEMICOLON_CSV = "Città;Größe;Nota\nForlì;3;x\x81y\nCafé;1;z\n".encode("latin-1")

# UTF-8 exports with non-ASCII text, whose detection must not change.
_UTF8_BOM_SEMICOLON_CSV = "Città;Importo €;Größe\nForlì;12,50 €;3\n".encode("utf-8-sig")
_UTF8_COMMA_CSV = "Città,Importo,Größe\nForlì,12.50,3\n".encode()
_UTF8_TAB_CSV = "Città\tImporto\tGröße\nForlì\t12,50\t3\n".encode()


def _write_bytes(tmp_path: Path, name: str, data: bytes) -> Path:
    """Write ``data`` verbatim, so each test controls its encoding byte by byte."""
    path = tmp_path / name
    path.write_bytes(data)
    return path


class TestTextEncodingFallback:
    """CSV exports saved as Windows-1252 or Latin-1 decode through one encoding chain.

    The bug: ``detect_csv_delimiter`` opened the file only as UTF-8. On a
    Windows-1252 or Latin-1 file with an accented character near the top, the
    decoding error was swallowed, the sample stayed empty and the fallback
    answered ``,`` for a ``;``-separated file. ``_read_file_head`` and
    ``_brim_io`` did try other encodings, but Latin-1 came before Windows-1252
    and Latin-1 never fails, so a Windows-1252 ``€`` (byte 0x80) came back as a
    control character.

    The contract: one chain, ``TEXT_ENCODINGS = ("utf-8-sig", "cp1252",
    "latin-1")``, applied to the whole file by ``_read_text`` and reused by
    ``_open_text`` (universal newlines, a drop-in for ``open()``),
    ``_read_file_head`` and ``detect_csv_delimiter``. ``_brim_io`` delegates to
    the base, so both give the same answer.

    Written red-first, before the fix. The tests whose docstring starts with
    "Parity guard" passed before the fix and must keep passing after it, as do
    the UTF-8 cases of the ``_brim_io`` parity test. Helpers are called on the
    class, because their contract is static; the ``DictReader`` test goes
    through an instance, as a plugin does. All data is synthetic and lives in
    ``tmp_path``.
    """

    # The chain.
    def test_text_encodings_order(self) -> None:
        """UTF-8 (BOM optional) first, then Windows-1252, then Latin-1, which decodes any byte."""
        assert brim_provider.TEXT_ENCODINGS == ("utf-8-sig", "cp1252", "latin-1")

    # _read_text: the whole file, decoded with the chain, newlines untouched.
    def test_read_text_strips_utf8_bom(self, tmp_path: Path) -> None:
        """A UTF-8 file with BOM comes back as ``str``, without the BOM."""
        path = _write_bytes(tmp_path, "bom.csv", "Città;Größe\n".encode("utf-8-sig"))

        text = BRIMProvider._read_text(path)

        assert isinstance(text, str)
        assert text == "Città;Größe\n"

    def test_read_text_prefers_utf8_over_cp1252(self, tmp_path: Path) -> None:
        """UTF-8 without BOM wins over Windows-1252, which would also accept these bytes, as mojibake."""
        path = _write_bytes(tmp_path, "utf8.csv", "Città;Importo €\n".encode())

        assert BRIMProvider._read_text(path) == "Città;Importo €\n"

    def test_read_text_decodes_cp1252_euro_sign(self, tmp_path: Path) -> None:
        """Windows-1252 comes before Latin-1: byte 0x80 is ``€``, not a control character."""
        path = _write_bytes(tmp_path, "cp1252.csv", "Importo;12,50 €\n".encode("cp1252"))

        assert BRIMProvider._read_text(path) == "Importo;12,50 €\n"

    def test_read_text_falls_back_to_latin1_for_byte_undefined_in_cp1252(self, tmp_path: Path) -> None:
        """A byte Windows-1252 leaves undefined (0x81) makes it fail, and Latin-1 decodes the file."""
        path = _write_bytes(tmp_path, "latin1.csv", "Café;x\x81y\n".encode("latin-1"))

        assert BRIMProvider._read_text(path) == "Café;x\x81y\n"

    def test_read_text_keeps_line_endings_verbatim(self, tmp_path: Path) -> None:
        """No newline translation: CRLF and bare CR survive, so a caller can still parse with ``newline=""``."""
        path = _write_bytes(tmp_path, "crlf.csv", "Città;Importo\r\nForlì;12\rCafé;7\n".encode())

        assert BRIMProvider._read_text(path) == "Città;Importo\r\nForlì;12\rCafé;7\n"

    def test_read_text_decodes_the_whole_file(self, tmp_path: Path) -> None:
        """The whole file is decoded, not a sample: a ``€`` after a long ASCII prefix (past the 15-line head and the first 8 KiB) still comes back as ``€``."""
        text = "".join(f"Riga {i:04d};{i}\n" for i in range(800)) + "Totale;12,50 €\n"
        path = _write_bytes(tmp_path, "long_cp1252.csv", text.encode("cp1252"))

        assert BRIMProvider._read_text(path) == text

    # _open_text: a drop-in for open(path, encoding="utf-8-sig").
    def test_open_text_yields_same_lines_as_utf8_sig_open(self, tmp_path: Path) -> None:
        """Iterating it gives the lines ``open(encoding="utf-8-sig")`` gives: BOM stripped, CRLF and bare CR read as LF."""
        path = _write_bytes(tmp_path, "mixed_newlines.csv", "Città;Importo\r\nForlì;12\rCafé;7\nGröße;3".encode("utf-8-sig"))
        with open(path, encoding="utf-8-sig") as f:
            expected = list(f)

        with BRIMProvider._open_text(path) as f:
            lines = list(f)

        assert expected == ["Città;Importo\n", "Forlì;12\n", "Café;7\n", "Größe;3"]
        assert lines == expected

    def test_open_text_feeds_csv_dictreader(self, stub: _StubBRIMProvider, tmp_path: Path) -> None:
        """A plugin can hand ``self._open_text(path)`` to ``csv.DictReader`` on a Windows-1252 export."""
        path = _write_bytes(tmp_path, "cp1252_rows.csv", "Città;Importo\r\nForlì;12,50 €\r\nCafé;7,00 €\r\n".encode("cp1252"))

        with stub._open_text(path) as f:
            rows = list(csv.DictReader(f, delimiter=";"))

        assert rows == [{"Città": "Forlì", "Importo": "12,50 €"}, {"Città": "Café", "Importo": "7,00 €"}]

    # _read_file_head: same contract, same chain.
    def test_read_file_head_decodes_cp1252_euro_sign(self, tmp_path: Path) -> None:
        """The first N lines of a Windows-1252 file carry ``€``, not the control character Latin-1 makes of 0x80."""
        path = _write_bytes(tmp_path, "cp1252_head.csv", _CP1252_SEMICOLON_CSV)

        assert BRIMProvider._read_file_head(path, num_lines=2) == "Città;Importo €;Größe\nForlì;12,50 €;3\n"

    def test_read_file_head_translates_crlf_to_lf(self, tmp_path: Path) -> None:
        """Parity guard: the head keeps text-mode newlines, since plugins split it on LF."""
        path = _write_bytes(tmp_path, "crlf_head.csv", "Città;Importo\r\nForlì;12\r\nCafé;7\r\n".encode())

        assert BRIMProvider._read_file_head(path, num_lines=2) == "Città;Importo\nForlì;12\n"

    def test_read_file_head_missing_file_returns_empty_string(self, tmp_path: Path) -> None:
        """Parity guard: an error that is not a decoding error still gives an empty string."""
        assert BRIMProvider._read_file_head(tmp_path / "missing.csv") == ""

    # detect_csv_delimiter: sniffs decoded text, whatever the encoding.
    def test_detect_csv_delimiter_cp1252_semicolon(self, tmp_path: Path) -> None:
        """The reported bug: a Windows-1252 ``;`` export with accents in its header was sniffed as ``,``."""
        path = _write_bytes(tmp_path, "cp1252_semicolon.csv", _CP1252_SEMICOLON_CSV)

        assert BRIMProvider.detect_csv_delimiter(path) == ";"

    def test_detect_csv_delimiter_latin1_semicolon(self, tmp_path: Path) -> None:
        """A ``;`` export only Latin-1 can decode is sniffed on its text, not on an empty sample."""
        path = _write_bytes(tmp_path, "latin1_semicolon.csv", _LATIN1_SEMICOLON_CSV)

        assert BRIMProvider.detect_csv_delimiter(path) == ";"

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(_UTF8_BOM_SEMICOLON_CSV, ";", id="utf8-bom-semicolon"),
            pytest.param(_UTF8_COMMA_CSV, ",", id="utf8-comma"),
            pytest.param(_UTF8_TAB_CSV, "\t", id="utf8-tab"),
        ],
    )
    def test_detect_csv_delimiter_utf8_unchanged(self, tmp_path: Path, data: bytes, expected: str) -> None:
        """Parity guard: UTF-8 exports with non-ASCII text are detected exactly as before."""
        path = _write_bytes(tmp_path, "utf8.csv", data)

        assert BRIMProvider.detect_csv_delimiter(path) == expected

    # _brim_io: delegates to the base, so there is one implementation.
    @pytest.mark.parametrize(
        "data",
        [
            pytest.param(_UTF8_BOM_SEMICOLON_CSV, id="utf8-bom-semicolon"),
            pytest.param(_UTF8_COMMA_CSV, id="utf8-comma"),
            pytest.param(_UTF8_TAB_CSV, id="utf8-tab"),
            pytest.param(_CP1252_SEMICOLON_CSV, id="cp1252-semicolon"),
            pytest.param(_LATIN1_SEMICOLON_CSV, id="latin1-semicolon"),
        ],
    )
    def test_brim_io_detect_delimiter_matches_base(self, tmp_path: Path, data: bytes) -> None:
        """``_brim_io.detect_delimiter`` answers what the base answers, whatever the encoding."""
        path = _write_bytes(tmp_path, "sample.csv", data)

        assert _brim_io.detect_delimiter(path) == BRIMProvider.detect_csv_delimiter(path)

    def test_brim_io_read_rows_decodes_cp1252_euro_sign(self, tmp_path: Path) -> None:
        """``read_rows`` decodes a Windows-1252 export with the base chain: ``€`` stays ``€``."""
        path = _write_bytes(tmp_path, "cp1252_rows.csv", _CP1252_SEMICOLON_CSV)

        assert _brim_io.read_rows(path) == [["Città", "Importo €", "Größe"], ["Forlì", "12,50 €", "3"], ["Café", "7,00 €", "1"]]

    def test_brim_io_read_rows_keeps_quoted_newline_in_one_cell(self, tmp_path: Path) -> None:
        """Parity guard: ``read_rows`` keeps ``newline=""`` csv semantics, so a quoted CRLF stays, verbatim, inside one cell."""
        path = _write_bytes(tmp_path, "quoted_newline.csv", 'Città;Nota\r\nForlì;"riga uno\r\nriga due"\r\nCafé;semplice\r\n'.encode("cp1252"))

        assert _brim_io.read_rows(path, delimiter=";") == [["Città", "Nota"], ["Forlì", "riga uno\r\nriga due"], ["Café", "semplice"]]
