"""
Tests for BRIM plugin versioning + parse_is_stale detection.

Covers the Revision 2 caching semantics:
- ``BRIMProvider.plugin_version`` is persisted alongside the parse result
  in the metadata sidecar by :func:`save_parse_result` (derived from the
  registry — single source of truth).
- ``BRIMFileInfo.parse_is_stale`` is computed lazily by
  :func:`get_file_info` / :func:`list_files` comparing the recorded
  ``parsed_plugin_version`` with the current plugin version in the
  registry.

These tests do NOT require a running server or DB connection; they
exercise the filesystem sidecar flow directly.
"""

from __future__ import annotations

import shutil

import pytest

from backend.app.services import brim_provider
from backend.app.services.brim_provider import BRIMFileStatus
from backend.app.services.provider_registry import BRIMProviderRegistry


@pytest.fixture
def isolated_brim_dir(tmp_path, monkeypatch):
    """Redirect BRIM storage to a temp directory so tests are isolated."""
    tmp_root = tmp_path / "broker_reports"
    tmp_root.mkdir()
    monkeypatch.setattr(brim_provider, "get_broker_reports_dir", lambda: tmp_root)
    yield tmp_root
    shutil.rmtree(tmp_root, ignore_errors=True)


class TestPluginVersioning:
    """End-to-end filesystem flow for plugin_version + parse_is_stale."""

    def test_save_parse_result_persists_version_from_registry(self, isolated_brim_dir):
        """save_parse_result derives plugin_version from the registry."""
        # 1. Upload a minimal file
        file_info = brim_provider.save_uploaded_file(
            content=b"date,type,quantity,amount,currency,asset\n2025-01-01,DEPOSIT,0,100,EUR,\n",
            original_filename="vt.csv",
            user_id=1,
        )

        # 2. Save a fake parse result with plugin_code only
        ok = brim_provider.save_parse_result(
            file_info.file_id,
            parse_result={"transactions": [], "warnings": []},
            plugin_code="broker_generic_csv",
        )
        assert ok is True

        # 3. Verify metadata sidecar has parsed_plugin_version from registry
        reloaded = brim_provider.get_file_info(file_info.file_id)
        assert reloaded is not None
        assert reloaded.parsed_plugin_code == "broker_generic_csv"
        plugin = BRIMProviderRegistry.get_provider_instance("broker_generic_csv")
        assert plugin is not None
        assert reloaded.parsed_plugin_version == plugin.plugin_version

    def test_parse_is_stale_flag_is_false_when_versions_match(self, isolated_brim_dir):
        """Freshly parsed file → parse_is_stale == False."""
        file_info = brim_provider.save_uploaded_file(
            content=b"date,type,quantity,amount,currency,asset\n2025-01-01,DEPOSIT,0,100,EUR,\n",
            original_filename="vt.csv",
            user_id=1,
        )
        # Move file to PARSED status (parse_is_stale is only computed for PARSED files)
        brim_provider._move_file(file_info.file_id, BRIMFileStatus.PARSED)
        brim_provider.save_parse_result(
            file_info.file_id,
            parse_result={"transactions": [], "warnings": []},
            plugin_code="broker_generic_csv",
        )

        reloaded = brim_provider.get_file_info(file_info.file_id)
        assert reloaded is not None
        assert reloaded.status == BRIMFileStatus.PARSED
        assert reloaded.parse_is_stale is False

    def test_parse_is_stale_flag_is_true_when_plugin_version_bumped(self, isolated_brim_dir, monkeypatch):
        """If the plugin version changes after parsing, parse_is_stale flips to True."""
        file_info = brim_provider.save_uploaded_file(
            content=b"date,type,quantity,amount,currency,asset\n2025-01-01,DEPOSIT,0,100,EUR,\n",
            original_filename="vt.csv",
            user_id=1,
        )
        brim_provider._move_file(file_info.file_id, BRIMFileStatus.PARSED)
        brim_provider.save_parse_result(
            file_info.file_id,
            parse_result={"transactions": [], "warnings": []},
            plugin_code="broker_generic_csv",
        )

        # Sanity: not stale right after save
        assert brim_provider.get_file_info(file_info.file_id).parse_is_stale is False

        # Bump the plugin version at runtime (class-level property → patch the class)
        plugin_cls = type(BRIMProviderRegistry.get_provider_instance("broker_generic_csv"))
        monkeypatch.setattr(plugin_cls, "plugin_version", "9.9.9-stale-test")

        reloaded = brim_provider.get_file_info(file_info.file_id)
        assert reloaded is not None
        assert reloaded.parsed_plugin_version != "9.9.9-stale-test"
        assert reloaded.parse_is_stale is True

    def test_parse_is_stale_visible_via_list_files(self, isolated_brim_dir, monkeypatch):
        """list_files() also computes parse_is_stale via the shared helper."""
        file_info = brim_provider.save_uploaded_file(
            content=b"date,type,quantity,amount,currency,asset\n2025-01-01,DEPOSIT,0,100,EUR,\n",
            original_filename="vt.csv",
            user_id=1,
        )
        brim_provider._move_file(file_info.file_id, BRIMFileStatus.PARSED)
        brim_provider.save_parse_result(
            file_info.file_id,
            parse_result={"transactions": [], "warnings": []},
            plugin_code="broker_generic_csv",
        )
        plugin_cls = type(BRIMProviderRegistry.get_provider_instance("broker_generic_csv"))
        monkeypatch.setattr(plugin_cls, "plugin_version", "9.9.9-stale-test")

        files = brim_provider.list_files()
        matching = [f for f in files if f.file_id == file_info.file_id]
        assert len(matching) == 1
        assert matching[0].parse_is_stale is True

    def test_re_save_parse_result_refreshes_version(self, isolated_brim_dir, monkeypatch):
        """Re-invoking save_parse_result picks up the current registry version."""
        file_info = brim_provider.save_uploaded_file(
            content=b"date,type,quantity,amount,currency,asset\n2025-01-01,DEPOSIT,0,100,EUR,\n",
            original_filename="vt.csv",
            user_id=1,
        )
        brim_provider._move_file(file_info.file_id, BRIMFileStatus.PARSED)
        brim_provider.save_parse_result(
            file_info.file_id,
            parse_result={"transactions": [], "warnings": []},
            plugin_code="broker_generic_csv",
        )

        # Bump and re-save
        plugin_cls = type(BRIMProviderRegistry.get_provider_instance("broker_generic_csv"))
        monkeypatch.setattr(plugin_cls, "plugin_version", "2.0.0")
        brim_provider.save_parse_result(
            file_info.file_id,
            parse_result={"transactions": [], "warnings": []},
            plugin_code="broker_generic_csv",
        )

        reloaded = brim_provider.get_file_info(file_info.file_id)
        assert reloaded.parsed_plugin_version == "2.0.0"
        assert reloaded.parse_is_stale is False
