"""
Tests for version utilities.

Covers:
- get_version_info: returns dict with version, is_dirty, is_release
- get_git_version: returns git describe string
"""

from types import SimpleNamespace

import backend.app.utils.version as version_utils
from backend.app.utils.version import get_git_version, get_version_info


class TestGetGitVersion:
    def test_returns_string(self):
        version = get_git_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_starts_with_v_or_unknown(self):
        version = get_git_version()
        assert version.startswith("v") or version == "unknown"

    def test_returns_tagged_version_from_git_describe(self, monkeypatch):
        get_git_version.cache_clear()
        monkeypatch.setattr(
            version_utils.subprocess,
            "run",
            lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="v1.2.3\n"),
        )

        version = get_git_version()

        assert version == "v1.2.3"
        get_git_version.cache_clear()

    def test_normalizes_hash_only_output(self, monkeypatch):
        get_git_version.cache_clear()
        monkeypatch.setattr(
            version_utils.subprocess,
            "run",
            lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="abcdef0\n"),
        )

        version = get_git_version()

        assert version == "v0.0.0-gabcdef0"
        get_git_version.cache_clear()

    def test_returns_unknown_when_git_describe_fails(self, monkeypatch):
        get_git_version.cache_clear()
        monkeypatch.setattr(
            version_utils.subprocess,
            "run",
            lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout=""),
        )

        version = get_git_version()

        assert version == "unknown"
        get_git_version.cache_clear()


class TestGetVersionInfo:
    def test_returns_dict_with_keys(self):
        info = get_version_info()
        assert isinstance(info, dict)
        assert "version" in info
        assert "is_dirty" in info
        assert "is_release" in info

    def test_is_dirty_is_bool(self):
        info = get_version_info()
        assert isinstance(info["is_dirty"], bool)

    def test_is_release_is_bool(self):
        info = get_version_info()
        assert isinstance(info["is_release"], bool)

    def test_dirty_snapshot_is_not_release(self, monkeypatch):
        monkeypatch.setattr(version_utils, "get_git_version", lambda: "v1.2.3-5-gabcdef-dirty")

        info = get_version_info()

        assert info == {
            "version": "v1.2.3-5-gabcdef-dirty",
            "is_dirty": True,
            "is_release": False,
        }

    def test_clean_tag_is_release(self, monkeypatch):
        monkeypatch.setattr(version_utils, "get_git_version", lambda: "v1.2.3")

        info = get_version_info()

        assert info == {
            "version": "v1.2.3",
            "is_dirty": False,
            "is_release": True,
        }
