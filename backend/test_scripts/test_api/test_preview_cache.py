"""Tests for PreviewCache in uploads.py API module."""

import time
from types import SimpleNamespace

import pytest

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


# ============================================================================
# P0-4 (audit 08) — _resize_image extraction + off-event-loop wiring
# ============================================================================


class TestResizeImage:
    """The extracted sync Pillow helper, both branches.

    The `None` return IS the contract the `ratio >= 1` → FileResponse branch of
    serve_file is built on: no bytes means "serve the original directly".
    """

    def test_resize_scales_down_to_the_requested_box(self, tmp_path):
        from PIL import Image  # noqa: PLC0415 — test-local

        from backend.app.api.v1.uploads import _resize_image  # noqa: PLC0415 — test-local

        source = tmp_path / "big.png"
        Image.new("RGB", (800, 600), (10, 20, 30)).save(source)

        out = _resize_image(source, 200, 150)

        assert out is not None
        from io import BytesIO  # noqa: PLC0415 — test-local

        resized = Image.open(BytesIO(out))
        assert resized.size == (200, 150)
        assert resized.format == "PNG"

    def test_resize_returns_none_when_the_source_is_already_smaller(self, tmp_path):
        from PIL import Image  # noqa: PLC0415 — test-local

        from backend.app.api.v1.uploads import _resize_image  # noqa: PLC0415 — test-local

        source = tmp_path / "small.png"
        Image.new("RGB", (100, 100), (200, 100, 50)).save(source)

        assert _resize_image(source, 200, 200) is None


@pytest.mark.asyncio
class TestServeFileOffEventLoop:
    """The P0-4 wiring: Pillow must run in a worker thread, not on the loop.

    A monkeypatch spy on `asyncio.to_thread` is honest here because the call is
    made in THIS process (in-process invocation of the endpoint function) — at
    the HTTP level the handler runs in the server process, where no test-side
    patch could see it. The spy delegates to the real `to_thread`, so the
    resize genuinely executes.
    """

    async def test_image_preview_resizes_via_asyncio_to_thread(self, tmp_path, monkeypatch):
        import asyncio  # noqa: PLC0415 — test-local

        from PIL import Image  # noqa: PLC0415 — test-local

        import backend.app.api.v1.uploads as uploads_module  # noqa: PLC0415 — test-local

        source = tmp_path / "big.png"
        Image.new("RGB", (800, 600), (10, 20, 30)).save(source)

        # The endpoint resolves file_id → path/mime through module-level helpers
        # imported into uploads' namespace — patch them there.
        monkeypatch.setattr(uploads_module, "get_upload_path", lambda file_id: source)
        monkeypatch.setattr(uploads_module, "get_upload_mime_type", lambda file_id: "image/png")

        calls: list = []
        real_to_thread = asyncio.to_thread

        async def _spy(func, *args, **kwargs):
            calls.append(func)
            return await real_to_thread(func, *args, **kwargs)

        monkeypatch.setattr(asyncio, "to_thread", _spy)

        from fastapi.responses import StreamingResponse  # noqa: PLC0415 — test-local

        response = await uploads_module.serve_file("p04-file", img_preview="200x150", _current_user=None)

        assert uploads_module._resize_image in calls, "the resize must go through asyncio.to_thread (off the event loop)"
        assert isinstance(response, StreamingResponse)

    async def test_already_small_image_still_checks_size_off_loop_then_serves_directly(self, tmp_path, monkeypatch):
        import asyncio  # noqa: PLC0415 — test-local

        from PIL import Image  # noqa: PLC0415 — test-local

        import backend.app.api.v1.uploads as uploads_module  # noqa: PLC0415 — test-local

        source = tmp_path / "small.png"
        Image.new("RGB", (100, 100), (200, 100, 50)).save(source)

        monkeypatch.setattr(uploads_module, "get_upload_path", lambda file_id: source)
        monkeypatch.setattr(uploads_module, "get_upload_mime_type", lambda file_id: "image/png")

        calls: list = []
        real_to_thread = asyncio.to_thread

        async def _spy(func, *args, **kwargs):
            calls.append(func)
            return await real_to_thread(func, *args, **kwargs)

        monkeypatch.setattr(asyncio, "to_thread", _spy)

        from fastapi.responses import FileResponse  # noqa: PLC0415 — test-local

        # Requested box LARGER than the source → _resize_image answers None →
        # the unchanged ratio>=1 branch serves the file directly.
        response = await uploads_module.serve_file("p04-file-small", img_preview="4000x3000", _current_user=None)

        assert uploads_module._resize_image in calls
        assert isinstance(response, FileResponse)
