"""Tests for PreviewCache in uploads.py API module."""

import time
from types import SimpleNamespace

import backend.app.config as app_config
from backend.app.api.v1.uploads import PreviewCache


class TestPreviewCache:
    """Test in-memory LRU preview cache."""

    def setup_method(self):
        self.cache = PreviewCache()

    # --- load_config ---

    def test_load_config_sets_flag(self):
        assert not self.cache.config_loaded
        self.cache.load_config()
        assert self.cache.config_loaded

    def test_load_config_idempotent(self):
        self.cache.load_config()
        original_max = self.cache.max_bytes
        self.cache.load_config()
        assert self.cache.max_bytes == original_max

    def test_load_config_reads_settings_value(self, monkeypatch):
        monkeypatch.setattr(
            app_config,
            "get_settings",
            lambda: SimpleNamespace(PREVIEW_CACHE_MAX_MB=7),
        )
        self.cache.load_config()
        assert self.cache.max_bytes == 7 * 1024 * 1024

    # --- get / put ---

    def test_put_and_get(self):
        data = b"fake image data"
        self.cache.put("file1", "100x100", data, "image/png")
        result = self.cache.get("file1", "100x100")
        assert result is not None
        assert result[0] == data
        assert result[1] == "image/png"

    def test_get_missing_returns_none(self):
        assert self.cache.get("nonexistent", "100x100") is None

    def test_get_expired_returns_none(self):
        data = b"img"
        self.cache.put("file1", "100x100", data, "image/png")
        # Manually expire entry
        key = ("file1", "100x100")
        img_bytes, mime, _ = self.cache.entries[key]
        self.cache.entries[key] = (img_bytes, mime, time.time() - self.cache.TTL - 1)
        assert self.cache.get("file1", "100x100") is None

    def test_put_oversized_entry_rejected(self):
        """Entries larger than 10% of max_bytes are not cached."""
        self.cache.max_bytes = 100
        self.cache.config_loaded = True
        big_data = b"x" * 20  # > 10% of 100
        self.cache.put("file1", "100x100", big_data, "image/png")
        assert self.cache.get("file1", "100x100") is None

    def test_put_evicts_oldest_when_full(self):
        self.cache.max_bytes = 1000
        self.cache.config_loaded = True
        now = time.time()
        for idx in range(9):
            self.cache.entries[(f"file{idx}", "s")] = (b"x" * 100, "image/png", now + idx)
        self.cache.entries[("tail", "s")] = (b"y" * 50, "image/png", now + 10)
        self.cache.current_bytes = 950

        self.cache.put("fresh", "s", b"z" * 100, "image/png")

        assert ("file0", "s") not in self.cache.entries
        assert self.cache.get("fresh", "s") == (b"z" * 100, "image/png")

    def test_put_evicts_expired_entries_before_store(self):
        self.cache.max_bytes = 1000
        self.cache.config_loaded = True
        self.cache.entries[("stale", "s")] = (
            b"a" * 100,
            "image/png",
            time.time() - self.cache.TTL - 1,
        )
        self.cache.current_bytes = 100

        self.cache.put("fresh", "s", b"b" * 50, "image/png")

        assert ("stale", "s") not in self.cache.entries
        assert self.cache.get("fresh", "s") == (b"b" * 50, "image/png")

    def test_invalidate(self):
        self.cache.put("file1", "100x100", b"data1", "image/png")
        self.cache.put("file1", "200x200", b"data2", "image/png")
        self.cache.put("file2", "100x100", b"data3", "image/png")
        self.cache.invalidate("file1")
        assert self.cache.get("file1", "100x100") is None
        assert self.cache.get("file1", "200x200") is None
        assert self.cache.get("file2", "100x100") is not None

    def test_current_bytes_tracking(self):
        data = b"12345"
        self.cache.put("f1", "s", data, "image/png")
        assert self.cache.current_bytes == 5
        self.cache.invalidate("f1")
        assert self.cache.current_bytes == 0
