"""
Tests for scripts/update_js_cache.py — the fail-loud contract (I1).

Before I1, a resource that could not be downloaded degraded the build
*silently*: the Docker image shipped a 404 on the emoji font for months and
flag glyphs rendered as letters. Now an undownloadable resource with no usable
cached copy — or a partially downloaded font — is a hard failure that turns
into a non-zero exit code from ``run_from_args``.

The module under test is import-time inert (all work happens inside
functions), so these tests monkeypatch the network boundary
(``download_file`` / ``get_remote_headers``) and point the filesystem side at
``tmp_path``. No DB, no server, no network, no writes outside tmp_path — PURE.
"""

from types import SimpleNamespace

import pytest

import scripts.update_js_cache as js_cache

JS_CONFIG = {"type": "js", "url": "https://cdn.example/lib.js", "target": "lib.js"}
FONT_CONFIG = {
    "type": "font",
    "css_url": "https://fonts.example/fake.css",
    "file_prefix": "fake-font",
    "css_file": "fake-font.css",
}

# Two subsets, the minimum that makes "partial" mean something.
FAKE_CSS = """
@font-face { font-family: 'Fake'; src: url(https://fonts.example/a.woff2); unicode-range: U+0000-00FF; }
@font-face { font-family: 'Fake'; src: url(https://fonts.example/b.woff2); unicode-range: U+1F300-1F5FF; }
"""


@pytest.fixture(autouse=True)
def _clean_failures():
    """_HARD_FAILURES is module-global — every test starts and ends empty."""
    js_cache._HARD_FAILURES.clear()
    yield
    js_cache._HARD_FAILURES.clear()


@pytest.fixture
def no_network(monkeypatch):
    """Every download fails; every HEAD probe finds nothing."""
    monkeypatch.setattr(js_cache, "download_file", lambda *a, **kw: None)
    monkeypatch.setattr(js_cache, "get_remote_headers", lambda *a, **kw: None)


class TestJsResource:
    def test_download_failure_without_cache_is_recorded_as_hard_failure(self, tmp_path, no_network):
        updated = js_cache.update_library(tmp_path, {}, "mylib", JS_CONFIG)

        assert updated is False
        assert len(js_cache._HARD_FAILURES) == 1
        assert "mylib" in js_cache._HARD_FAILURES[0]

    def test_download_failure_with_cached_copy_is_soft(self, tmp_path, no_network):
        # A usable cached copy: the file exists and the manifest names a hash.
        lib_dir = tmp_path / "mylib"
        lib_dir.mkdir(parents=True)
        (lib_dir / "lib.js").write_bytes(b"cached")
        manifest = {"libraries": {"mylib": {"current_hash": "abc123", "versions": []}}}

        updated = js_cache.update_library(tmp_path, manifest, "mylib", JS_CONFIG)

        assert updated is False
        assert js_cache._HARD_FAILURES == []


class TestFontResource:
    def test_css_failure_without_cache_is_a_hard_failure(self, tmp_path, no_network):
        updated = js_cache.update_library(tmp_path, {}, "fake-font", FONT_CONFIG)

        assert updated is False
        assert len(js_cache._HARD_FAILURES) == 1
        assert "fake-font" in js_cache._HARD_FAILURES[0]

    def test_css_failure_with_cached_copy_is_soft(self, tmp_path, no_network):
        (tmp_path / "fake-font.css").write_text("/* cached */")

        updated = js_cache.update_library(tmp_path, {}, "fake-font", FONT_CONFIG)

        assert updated is False
        assert js_cache._HARD_FAILURES == []

    def test_partial_subsets_are_a_hard_failure_and_no_partial_css_is_written(self, tmp_path, monkeypatch):
        # The CSS downloads fine; exactly one of the two woff2 subsets does not.
        # A partial font renders SOME glyph ranges as fallback letters — the
        # same silent degradation as a missing font, hence loud.
        def fake_download(url, *a, **kw):
            if url == FONT_CONFIG["css_url"]:
                return FAKE_CSS.encode()
            if url.endswith("a.woff2"):
                return b"woff2-a"
            return None  # b.woff2 fails

        monkeypatch.setattr(js_cache, "download_file", fake_download)

        updated = js_cache.update_library(tmp_path, {}, "fake-font", FONT_CONFIG)

        assert updated is False
        assert len(js_cache._HARD_FAILURES) == 1
        assert "1/2" in js_cache._HARD_FAILURES[0]
        # The previous cached version (if any) stays authoritative: no partial CSS.
        assert not (tmp_path / "fake-font.css").exists()


class TestExitCode:
    def test_run_from_args_returns_1_when_any_hard_failure_was_collected(self, monkeypatch):
        def fake_update_all(force=False):
            js_cache._hard_fail("mylib", "download failed, no cached version")

        monkeypatch.setattr(js_cache, "update_all_libraries", fake_update_all)

        assert js_cache.run_from_args(SimpleNamespace(force=False)) == 1

    def test_run_from_args_returns_0_when_everything_is_cached_or_downloaded(self, monkeypatch):
        monkeypatch.setattr(js_cache, "update_all_libraries", lambda force=False: 0)

        assert js_cache.run_from_args(SimpleNamespace(force=False)) == 0
