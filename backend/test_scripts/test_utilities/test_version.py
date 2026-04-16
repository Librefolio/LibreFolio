"""
Tests for version utilities.

Covers:
- get_version_info: returns dict with version, is_dirty, is_release
- get_git_version: returns git describe string
"""

from backend.app.utils.version import get_version_info, get_git_version


class TestGetGitVersion:
    def test_returns_string(self):
        version = get_git_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_starts_with_v_or_unknown(self):
        version = get_git_version()
        assert version.startswith("v") or version == "unknown"


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

