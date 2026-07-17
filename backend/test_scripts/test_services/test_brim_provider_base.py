"""
Test Suite: BRIMProvider Abstract Base — default property contracts

Covers Phase 7 Part 3 Closure_2 G-batch6 (post-G coverage gap-fill):

The ``BRIMProvider.docs_url`` property had **0% coverage** because every
shipped subclass overrides it. This suite instantiates a minimal stub
subclass that omits the override and asserts the documented default
(``None``). We extend the same pattern to ``icon_url`` and
``plugin_version`` to lock down the rest of the abstract contract.

Plan: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md`` §G-batch6.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

from backend.app.schemas.brim import BRIMFileStatus, BRIMParseOutput
from backend.app.services import brim_provider
from backend.app.services.brim_provider import BRIMProvider


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
