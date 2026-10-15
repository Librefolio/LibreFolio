"""
Test: StaticUploads Service — save, list, get, delete, security validation.

Tests the static uploads service layer including file persistence,
metadata sidecar, security checks, cache invalidation, user filtering
and listing order.
"""

import json
import shutil
import sys
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

import backend.app.services.files.static_uploads as static_uploads
from backend.app.schemas.uploads import UploadFileInfo
from backend.app.services.files.static_uploads import (
    UploadSecurityError,
    _detect_actual_mime_type,
    _load_metadata,
    delete_upload,
    get_upload_by_user,
    get_upload_info,
    get_upload_mime_type,
    get_upload_path,
    get_uploads_dir,
    list_uploads,
    save_upload,
    seed_default_avatars,
    validate_upload_security,
)
from backend.test_scripts.test_utils import print_section, print_success

# ============================================================================
# FIXTURE — isolated uploads directory
# ============================================================================


@pytest.fixture(autouse=True)
def _clean_uploads_dir():
    """Create a clean uploads directory before each test, clean up after."""
    uploads_dir = get_uploads_dir()
    # Clear any existing files
    if uploads_dir.exists():
        shutil.rmtree(uploads_dir)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    yield
    # Clean up after test
    if uploads_dir.exists():
        shutil.rmtree(uploads_dir)


# ============================================================================
# HELPERS
# ============================================================================


SAMPLE_CONTENT = b"Hello, this is a test file."
SAMPLE_PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # Minimal PNG-like header


# ============================================================================
# save_upload
# ============================================================================


class TestSaveUpload:
    """Tests for save_upload()."""

    def test_save_basic(self):
        """Save a simple text file and verify metadata."""
        print_section("save_upload: basic text file")
        info = save_upload(SAMPLE_CONTENT, "test.txt", user_id=1, description="Test file")
        assert info.original_name == "test.txt"
        assert info.size_bytes == len(SAMPLE_CONTENT)
        assert info.uploaded_by_user_id == 1
        assert info.description == "Test file"
        assert info.id  # UUID generated
        assert info.url.startswith("/api/v1/uploads/file/")
        print_success(f"Saved: {info.id}")

    def test_save_creates_file_and_metadata(self):
        """Verify both .ext and .json files exist on disk."""
        print_section("save_upload: file + metadata on disk")
        info = save_upload(SAMPLE_CONTENT, "data.csv", user_id=2)
        uploads_dir = get_uploads_dir()
        file_path = uploads_dir / f"{info.id}.csv"
        meta_path = uploads_dir / f"{info.id}.json"
        assert file_path.exists(), "Actual file should exist"
        assert meta_path.exists(), "Metadata sidecar should exist"
        assert file_path.read_bytes() == SAMPLE_CONTENT
        print_success("File and metadata created on disk")

    def test_save_blocked_extension(self):
        """Blocked extension → UploadSecurityError."""
        print_section("save_upload: blocked extension .exe")
        with pytest.raises(UploadSecurityError, match="not allowed"):
            save_upload(b"MZ\x90\x00", "virus.exe", user_id=1)
        print_success("UploadSecurityError raised for .exe")

    def test_save_blocked_extension_script(self):
        """Blocked script extension → UploadSecurityError."""
        print_section("save_upload: blocked extension .py")
        with pytest.raises(UploadSecurityError, match="not allowed"):
            save_upload(b"import os", "script.py", user_id=1)
        print_success("UploadSecurityError raised for .py")


# ============================================================================
# get_upload_info
# ============================================================================


class TestGetUploadInfo:
    """Tests for get_upload_info()."""

    def test_exists(self):
        """Get info for existing file."""
        print_section("get_upload_info: existing file")
        saved = save_upload(SAMPLE_CONTENT, "test.txt", user_id=1)
        info = get_upload_info(saved.id)
        assert info is not None
        assert info.id == saved.id
        assert info.original_name == "test.txt"
        print_success(f"Got info for {saved.id}")

    def test_not_found(self):
        """Non-existent UUID → None."""
        print_section("get_upload_info: not found")
        info = get_upload_info("00000000-0000-0000-0000-000000000000")
        assert info is None
        print_success("None for non-existent UUID")

    def test_missing_actual_file(self):
        """Metadata exists but file deleted from disk → None."""
        print_section("get_upload_info: metadata exists but file missing")
        saved = save_upload(SAMPLE_CONTENT, "test.txt", user_id=1)
        # Delete the actual file but keep metadata
        uploads_dir = get_uploads_dir()
        file_path = uploads_dir / f"{saved.id}.txt"
        file_path.unlink()
        info = get_upload_info(saved.id)
        assert info is None
        print_success("None when actual file is missing")


# ============================================================================
# _load_metadata / get_upload_mime_type
# ============================================================================


class TestUploadMetadataHelpers:
    """Tests for metadata helper functions."""

    def test_load_metadata_uses_cache_after_first_read(self):
        """Cached metadata remains available after sidecar removal."""
        print_section("_load_metadata: cache hit after first read")
        saved = save_upload(SAMPLE_CONTENT, "cached.txt", user_id=1)
        first = _load_metadata(saved.id)
        assert first is not None

        meta_path = get_uploads_dir() / f"{saved.id}.json"
        meta_path.unlink()

        second = _load_metadata(saved.id)
        assert second == first
        print_success("Metadata served from cache")

    def test_get_upload_mime_type_defaults_when_key_missing(self):
        """Missing mime_type key falls back to octet-stream."""
        print_section("get_upload_mime_type: default fallback")
        saved = save_upload(SAMPLE_CONTENT, "fallback.txt", user_id=1)
        uploads_dir = get_uploads_dir()
        meta_path = uploads_dir / f"{saved.id}.json"

        metadata = json.loads(meta_path.read_text())
        metadata.pop("mime_type", None)
        meta_path.write_text(json.dumps(metadata))
        static_uploads._upload_meta_cache.delete(saved.id)

        mime = get_upload_mime_type(saved.id)
        assert mime == "application/octet-stream"
        print_success("Missing mime_type → octet-stream")


# ============================================================================
# get_upload_path
# ============================================================================


class TestGetUploadPath:
    """Tests for get_upload_path()."""

    def test_exists(self):
        """Return path for existing file."""
        print_section("get_upload_path: existing")
        saved = save_upload(SAMPLE_CONTENT, "photo.png", user_id=1)
        path = get_upload_path(saved.id)
        assert path is not None
        assert path.exists()
        print_success(f"Path: {path}")

    def test_not_found(self):
        """Non-existent → None."""
        print_section("get_upload_path: not found")
        path = get_upload_path("nonexistent-uuid")
        assert path is None
        print_success("None for non-existent")


# ============================================================================
# list_uploads
# ============================================================================


class TestListUploads:
    """Tests for list_uploads()."""

    def test_empty(self):
        """Empty directory → ([], 0)."""
        print_section("list_uploads: empty directory")
        files, count = list_uploads()
        assert files == []
        assert count == 0
        print_success("Empty directory → ([], 0)")

    def test_with_files(self):
        """Multiple files listed, sorted by date desc."""
        print_section("list_uploads: multiple files")
        save_upload(b"file1", "a.txt", user_id=1)
        save_upload(b"file2", "b.txt", user_id=1)
        save_upload(b"file3", "c.txt", user_id=2)
        files, count = list_uploads()
        assert count == 3
        assert len(files) == 3
        print_success(f"Listed {count} files")

    def test_filter_by_user(self):
        """Filter by user_id returns only that user's files."""
        print_section("list_uploads: filter by user_id")
        save_upload(b"file1", "a.txt", user_id=1)
        save_upload(b"file2", "b.txt", user_id=2)
        save_upload(b"file3", "c.txt", user_id=1)
        files, count = list_uploads(user_id=1)
        assert count == 2
        for f in files:
            assert f.uploaded_by_user_id == 1
        print_success(f"User 1 has {count} files")


# ============================================================================
# list_uploads — one order, whatever order the directory lists (G-10)
# ============================================================================

# The instant shared by uploads that tie, as seed_default_avatars() gives one instant to all its avatars.
TIED_INSTANT = datetime(2026, 1, 15, 9, 30, tzinfo=UTC)

# Ids are chosen, not drawn: their order is known in advance and made to disagree with the name order.
FIXED_ID_NUMBERS = (1, 2, 3)

DEFAULT_AVATARS = [f"men_{n:02d}.png" for n in range(1, 16)] + [f"woman_{n:02d}.png" for n in range(1, 16)]


def _fixed_id(n: int) -> str:
    """A canonical UUID that sorts as ``n`` among the fixed ids."""
    return f"00000000-0000-4000-8000-{n:012d}"


def _save_upload_as(name: str, *, file_id: str, at: datetime) -> None:
    """The real save_upload(), with the id and the upload instant chosen by the test instead of drawn."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(static_uploads, "utcnow", lambda: at)
        mp.setattr(static_uploads, "uuid", SimpleNamespace(uuid4=lambda: uuid.UUID(file_id)))
        info = save_upload(SAMPLE_CONTENT, name, user_id=1)
    assert (info.id, info.original_name, info.uploaded_at) == (file_id, name, at)


def _list_uploads_with_directory_order(descending: bool) -> list[UploadFileInfo]:
    """list_uploads() while the uploads directory lists its entries in a forced order.

    Sidecars are named ``{id}.json``, so the forced order is the id order, ascending or descending: two calls see
    the same uploads in opposite orders, which no filesystem can make agree by chance. The ``Path`` subclass keeps
    the real directory and ``/`` keeps the subclass, so ``_ensure_dir()``, ``_load_metadata()`` and the file check
    all resolve to it; only ``glob()`` changes.
    """
    real_dir = get_uploads_dir()
    listed: list[str] = []

    class _ForcedOrderPath(type(real_dir)):
        def glob(self, pattern, **kwargs):
            entries = sorted(super().glob(pattern, **kwargs), key=lambda p: p.name, reverse=descending)
            listed.extend(p.name for p in entries)
            return iter(entries)

    sidecars = {p.name for p in real_dir.glob("*.json")}
    # Forget the cached sidecars, so that _load_metadata() reads every one of them through the forced directory too.
    for sidecar in sidecars:
        static_uploads._upload_meta_cache.delete(sidecar.removesuffix(".json"))

    forced_dir = _ForcedOrderPath(real_dir)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(static_uploads, "get_uploads_dir", lambda: forced_dir)
        files, _ = list_uploads()

    assert sidecars <= set(listed), "list_uploads() no longer lists the sidecars through get_uploads_dir().glob(): the forced order never reached it, so this harness proves nothing until it is adapted"
    return files


def _assert_listed_in_order(expected: list[str], label: Callable[[UploadFileInfo], str]) -> None:
    """Both forced directory orders must give exactly ``expected``; ``label`` renders one upload."""
    ascending = [label(f) for f in _list_uploads_with_directory_order(descending=False)]
    descending = [label(f) for f in _list_uploads_with_directory_order(descending=True)]
    message = "\n".join(
        [
            "list_uploads() must give the same, expected order whatever order the directory lists its entries in",
            f"  expected:                     {expected}",
            f"  ascending directory listing:  {ascending}",
            f"  descending directory listing: {descending}",
        ]
    )
    assert ascending == expected and descending == expected, message


def _name(info: UploadFileInfo) -> str:
    return info.original_name


def _name_and_id(info: UploadFileInfo) -> str:
    """The name plus the last digits of the fixed id, which tell apart uploads sharing a name."""
    return f"{info.original_name} #{info.id[-3:]}"


class TestListUploadsOrder:
    """list_uploads(): newest first, then by name ignoring case, then by id, whatever order the directory lists (G-10).

    Uploads sharing ``uploaded_at`` used to keep the directory's order, which follows their random UUID file names
    and the filesystem: seed_default_avatars() gives all its avatars one instant, so their listed order changed at
    every seed, and the documentation gallery with it. Each test lists the same uploads through two opposite
    directory orders, so no filesystem can make it pass by luck.
    """

    @pytest.fixture(autouse=True)
    def _forget_fixed_ids(self):
        """The fixed ids recur across tests: forget their cached metadata, as the module fixture removes their files."""
        yield
        for n in FIXED_ID_NUMBERS:
            static_uploads._upload_meta_cache.delete(_fixed_id(n))

    def test_same_instant_listed_by_name_ignoring_case(self):
        """Uploads sharing one instant are listed by name, ignoring case.

        Created b, A, C with ids 1, 3, 2: the expected A, b, C differs from the creation order, from the id order
        (b, C, A) and its reverse, and from a case-sensitive name order (A, C, b).
        """
        print_section("list_uploads: same instant → name order, ignoring case")
        for name, n in (("b.txt", 1), ("A.txt", 3), ("C.txt", 2)):
            _save_upload_as(name, file_id=_fixed_id(n), at=TIED_INSTANT)

        _assert_listed_in_order(["A.txt #003", "b.txt #001", "C.txt #002"], _name_and_id)
        print_success("Same instant → A.txt, b.txt, C.txt for both directory orders")

    def test_newest_first_beats_name_order(self):
        """A later upload comes first even when its name sorts last: the instant stays the primary key.

        Every upload has its own instant, so the directory order has nothing to decide.
        """
        print_section("list_uploads: newest first beats the name order")
        _save_upload_as("a.txt", file_id=_fixed_id(3), at=TIED_INSTANT)
        _save_upload_as("m.txt", file_id=_fixed_id(1), at=TIED_INSTANT + timedelta(seconds=1))
        _save_upload_as("z.txt", file_id=_fixed_id(2), at=TIED_INSTANT + timedelta(seconds=2))

        _assert_listed_in_order(["z.txt #002", "m.txt #001", "a.txt #003"], _name_and_id)
        print_success("Newest first → z.txt, m.txt, a.txt for both directory orders")

    def test_same_name_same_instant_listed_by_id(self):
        """Uploads sharing name and instant are listed by id: nothing is left to the directory."""
        print_section("list_uploads: same name and instant → id order")
        for n in (2, 3, 1):
            _save_upload_as("same.txt", file_id=_fixed_id(n), at=TIED_INSTANT)

        _assert_listed_in_order(["same.txt #001", "same.txt #002", "same.txt #003"], _name_and_id)
        print_success("Same name and instant → id order for both directory orders")

    def test_seeded_avatars_listed_by_name(self):
        """The seeded avatars share one instant and list men_01 … men_15, then woman_01 … woman_15."""
        print_section("list_uploads: seeded default avatars in name order")
        marker = get_uploads_dir() / ".avatars_seeded"
        assert not marker.exists(), "the uploads directory must start without the marker, or seed_default_avatars() seeds nothing"

        seeded = seed_default_avatars()

        assert seeded == len(DEFAULT_AVATARS), f"seed_default_avatars() seeded {seeded} avatars, expected {len(DEFAULT_AVATARS)}"
        _assert_listed_in_order(DEFAULT_AVATARS, _name)
        print_success(f"{seeded} seeded avatars → men_01 … woman_15 for both directory orders")


# ============================================================================
# delete_upload
# ============================================================================


class TestDeleteUpload:
    """Tests for delete_upload()."""

    def test_delete_exists(self):
        """Delete existing file → True, files removed from disk."""
        print_section("delete_upload: existing file")
        saved = save_upload(SAMPLE_CONTENT, "test.txt", user_id=1)
        uploads_dir = get_uploads_dir()
        file_path = uploads_dir / f"{saved.id}.txt"
        meta_path = uploads_dir / f"{saved.id}.json"

        result = delete_upload(saved.id)
        assert result is True
        assert not file_path.exists()
        assert not meta_path.exists()
        print_success("File and metadata deleted")

    def test_delete_not_found(self):
        """Delete non-existent UUID → False."""
        print_section("delete_upload: not found")
        result = delete_upload("00000000-0000-0000-0000-000000000000")
        assert result is False
        print_success("False for non-existent UUID")

    def test_delete_removes_from_list(self):
        """After delete, file no longer appears in list_uploads."""
        print_section("delete_upload: removed from list")
        saved = save_upload(SAMPLE_CONTENT, "test.txt", user_id=1)
        delete_upload(saved.id)
        files, count = list_uploads()
        assert count == 0
        print_success("Deleted file removed from listing")


# ============================================================================
# get_upload_by_user
# ============================================================================


class TestGetUploadByUser:
    """Tests for get_upload_by_user()."""

    def test_owner(self):
        """Owner user → info returned."""
        print_section("get_upload_by_user: owner")
        saved = save_upload(SAMPLE_CONTENT, "test.txt", user_id=1)
        info = get_upload_by_user(saved.id, user_id=1)
        assert info is not None
        assert info.id == saved.id
        print_success("Owner sees own file")

    def test_not_owner(self):
        """Different user → None."""
        print_section("get_upload_by_user: not owner")
        saved = save_upload(SAMPLE_CONTENT, "test.txt", user_id=1)
        info = get_upload_by_user(saved.id, user_id=999)
        assert info is None
        print_success("Non-owner gets None")


# ============================================================================
# validate_upload_security
# ============================================================================


class TestValidateUploadSecurity:
    """Tests for validate_upload_security()."""

    def test_safe_file(self):
        """Normal text file → MIME type returned."""
        print_section("validate_upload_security: safe file")
        mime = validate_upload_security(SAMPLE_CONTENT, "report.txt")
        assert mime is not None
        assert isinstance(mime, str)
        print_success(f"Validated MIME: {mime}")

    def test_blocked_extension(self):
        """Blocked extension → UploadSecurityError."""
        print_section("validate_upload_security: blocked extension")
        for ext in [".exe", ".sh", ".py", ".bat", ".dll"]:
            with pytest.raises(UploadSecurityError):
                validate_upload_security(b"data", f"file{ext}")
        print_success("All blocked extensions rejected")

    def test_unknown_extension(self):
        """Unknown extension → guessed or octet-stream."""
        print_section("validate_upload_security: unknown extension")
        mime = validate_upload_security(b"some data", "file.xyz123")
        assert mime is not None
        print_success(f"Unknown ext → {mime}")

    def test_safe_csv_file(self):
        """CSV file accepted with text MIME type."""
        print_section("validate_upload_security: CSV file")
        mime = validate_upload_security(b"col1,col2\nval1,val2", "data.csv")
        assert mime is not None
        print_success(f"CSV → {mime}")

    def test_safe_json_file(self):
        """JSON file accepted."""
        print_section("validate_upload_security: JSON file")
        mime = validate_upload_security(b'{"key": "value"}', "config.json")
        assert mime is not None
        print_success(f"JSON → {mime}")

    def test_safe_png_file(self):
        """PNG-like file accepted."""
        print_section("validate_upload_security: PNG file")
        mime = validate_upload_security(SAMPLE_PNG_HEADER, "photo.png")
        assert mime is not None
        print_success(f"PNG → {mime}")

    def test_blocked_js_extension(self):
        """JavaScript extension blocked."""
        print_section("validate_upload_security: .js blocked")
        with pytest.raises(UploadSecurityError):
            validate_upload_security(b"console.log('xss')", "script.js")
        print_success("JS extension rejected")

    def test_blocked_mjs_extension(self):
        """ES Module extension blocked."""
        print_section("validate_upload_security: .mjs blocked")
        with pytest.raises(UploadSecurityError):
            validate_upload_security(b"export default {}", "module.mjs")
        print_success("MJS extension rejected")

    def test_blocked_jar_extension(self):
        """JAR extension blocked."""
        print_section("validate_upload_security: .jar blocked")
        with pytest.raises(UploadSecurityError):
            validate_upload_security(b"PK\x03\x04", "app.jar")
        print_success("JAR extension rejected")

    def test_declared_mime_octet_stream(self):
        """Declared octet-stream is always accepted (generic)."""
        print_section("validate_upload_security: declared octet-stream")
        mime = validate_upload_security(b"binary data", "file.bin", declared_mime_type="application/octet-stream")
        assert mime is not None
        print_success(f"octet-stream declared → {mime}")

    def test_declared_mime_text_match(self):
        """Declared text/* matches actual text/* → accepted."""
        print_section("validate_upload_security: text/* declared match")
        mime = validate_upload_security(b"col1,col2\nval1,val2", "data.csv", declared_mime_type="text/csv")
        assert mime is not None
        print_success(f"text/csv declared → {mime}")

    def test_empty_content(self):
        """Empty file content → still returns MIME type."""
        print_section("validate_upload_security: empty content")
        mime = validate_upload_security(b"", "empty.txt")
        assert mime is not None
        print_success(f"Empty → {mime}")


class TestValidateUploadSecurityDetectedMime:
    """Tests for validate_upload_security() when MIME detection succeeds."""

    def test_detect_actual_mime_type_with_magic(self, monkeypatch):
        """magic.from_buffer result is returned when library available."""
        print_section("_detect_actual_mime_type: magic branch")

        class _FakeMagic:
            @staticmethod
            def from_buffer(_content: bytes, mime: bool = True) -> str:
                assert mime is True
                return "text/plain"

        monkeypatch.setattr(static_uploads, "MAGIC_AVAILABLE", True)
        monkeypatch.setattr(static_uploads, "magic", _FakeMagic, raising=False)

        mime = _detect_actual_mime_type(b"hello")
        assert mime == "text/plain"
        print_success("magic branch returned detected MIME")

    def test_declared_mime_exact_match_uses_detected_value(self, monkeypatch):
        """Detected MIME wins when client declaration matches actual base type."""
        print_section("validate_upload_security: exact detected MIME match")
        monkeypatch.setattr(static_uploads, "_detect_actual_mime_type", lambda _content: "text/plain")

        mime = validate_upload_security(
            b"hello world",
            "report.txt",
            declared_mime_type="text/plain; charset=utf-8",
        )

        assert mime == "text/plain"
        print_success("Exact detected MIME accepted")

    def test_declared_mime_text_family_variation_allowed(self, monkeypatch):
        """Different text/* declarations are accepted for detected text payloads."""
        print_section("validate_upload_security: text family variation")
        monkeypatch.setattr(static_uploads, "_detect_actual_mime_type", lambda _content: "text/plain")

        mime = validate_upload_security(
            b"col1,col2\n1,2\n",
            "report.csv",
            declared_mime_type="text/csv",
        )

        assert mime == "text/plain"
        print_success("text/* variation accepted")

    def test_declared_octet_stream_uses_detected_mime(self, monkeypatch):
        """Generic client MIME falls back to detected MIME."""
        print_section("validate_upload_security: octet-stream with detected MIME")
        monkeypatch.setattr(static_uploads, "_detect_actual_mime_type", lambda _content: "application/pdf")

        mime = validate_upload_security(
            b"%PDF-1.4\n",
            "report.pdf",
            declared_mime_type="application/octet-stream",
        )

        assert mime == "application/pdf"
        print_success("Detected MIME used for octet-stream declaration")
