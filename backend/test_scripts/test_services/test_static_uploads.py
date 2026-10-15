"""
Test: StaticUploads Service — save, list, get, delete, security validation.

Tests the static uploads service layer including file persistence,
metadata sidecar, security checks, cache invalidation, user filtering
and listing order.

Decision 36 (scope of uploaded files, red until it lands): the pure rule ``effective_scope(metadata)``, the scope
``save_upload`` writes into the sidecar, legacy sidecars without ``scope``, sidecars read fresh after another worker
rewrote or deleted them, and ``set_upload_scope`` replacing the sidecar atomically.

Every test runs on a data directory of its own under ``tmp_path`` (``_private_data_dir``): the lane's
``custom-uploads/`` is shared with every other unit of the lane and is never touched here.
"""

import copy
import json
import os
import sys
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
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
def _private_data_dir(tmp_path, monkeypatch):
    """Point the data directory at this test's own ``tmp_path``: an empty ``custom-uploads/`` that no neighbour shares.

    The lane's ``custom-uploads/`` belongs to every unit of the lane (the API tests' uploads, the seeded avatars and
    their marker), and this module used to empty it before and after each test. Every path of the service derives from
    ``get_data_dir()``, which reads ``LIBREFOLIO_TEST_DATA_DIR`` at each call, so the redirection reaches all of them;
    pytest removes ``tmp_path``, nothing is left to clean.
    """
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    uploads_dir = get_uploads_dir()
    assert uploads_dir.is_relative_to(tmp_path.resolve()), f"the uploads directory must be this test's own, under {tmp_path}, not {uploads_dir}"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    yield


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
# get_upload_mime_type
# ============================================================================


class TestUploadMetadataHelpers:
    """Tests for metadata helper functions.

    test_load_metadata_uses_cache_after_first_read lived here: it pinned that a sidecar deleted on disk is still served
    from the one-hour cache. Decision 36 asks the opposite, see TestCrossProcessFreshness.
    """

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


# ============================================================================
# Scope of uploaded files (decision 36) — helpers
# ============================================================================
#
# effective_scope() and set_upload_scope() do not exist before decision 36: each test imports what it needs in its own
# body, so that until they land only the tests needing them fail, on an ImportError that names them, and the collection
# of the module (every other test included) never breaks.


def _effective_scope() -> Callable[[dict], str]:
    """The scope rule under test, imported when the test runs."""
    from backend.app.services.files.static_uploads import effective_scope  # noqa: PLC0415 — red until decision 36: imported at module level it would stop the collection of every test

    return effective_scope


def _set_upload_scope() -> Callable[[str, str], UploadFileInfo | None]:
    """The scope change under test, imported when the test runs."""
    from backend.app.services.files.static_uploads import set_upload_scope  # noqa: PLC0415 — red until decision 36: imported at module level it would stop the collection of every test

    return set_upload_scope


def _png_bytes(width: int = 32, height: int = 24) -> bytes:
    """A real PNG (Pillow), so that the detected MIME type is image/png with or without libmagic."""
    from PIL import Image  # noqa: PLC0415 — test-only local import

    out = BytesIO()
    Image.new("RGB", (width, height), color=(0, 128, 255)).save(out, format="PNG")
    return out.getvalue()


def _sidecar(file_id: str) -> dict:
    """The metadata sidecar of an upload, as it is on disk."""
    return json.loads((get_uploads_dir() / f"{file_id}.json").read_text())


def _write_legacy_upload(name: str, content: bytes, mime_type: str, user_id: int) -> str:
    """Store a file the way uploads were stored before decision 36 — a sidecar without ``scope`` —; its id."""
    file_id = str(uuid.uuid4())
    ext = Path(name).suffix.lower()
    uploads_dir = get_uploads_dir()
    (uploads_dir / f"{file_id}{ext}").write_bytes(content)
    metadata = {
        "id": file_id,
        "original_name": name,
        "extension": ext,
        "mime_type": mime_type,
        "size_bytes": len(content),
        "uploaded_at": datetime.now(UTC).isoformat(),
        "uploaded_by_user_id": user_id,
        "description": None,
    }
    (uploads_dir / f"{file_id}.json").write_text(json.dumps(metadata, indent=2))
    return file_id


def _rewrite_like_another_worker(file_id: str, **changes) -> None:
    """Rewrite a sidecar the way another worker's write lands: a whole new file, then ``os.replace`` over the old one."""
    sidecar_path = get_uploads_dir() / f"{file_id}.json"
    metadata = {**json.loads(sidecar_path.read_text()), **changes}
    written_elsewhere = sidecar_path.with_name(f"{sidecar_path.name}.another-worker.tmp")
    written_elsewhere.write_text(json.dumps(metadata, indent=2))
    os.replace(written_elsewhere, sidecar_path)


# ============================================================================
# effective_scope — the rule (decision 36)
# ============================================================================

#: A stored "common" or "personal" wins, each case against the opposite outcome of the inheritance rule.
STORED_SCOPE_WINS = [
    pytest.param({"scope": "common", "mime_type": "text/plain", "uploaded_by_user_id": 5}, "common", id="stored-common-over-text"),
    pytest.param({"scope": "personal", "mime_type": "image/png", "uploaded_by_user_id": 5}, "personal", id="stored-personal-over-image"),
    pytest.param({"scope": "personal", "mime_type": "application/pdf", "uploaded_by_user_id": 0}, "personal", id="stored-personal-over-system"),
]

#: No scope, None or any other value: the system's files (user 0) and image/* are common, anything else personal.
INHERITED_SCOPE = [
    pytest.param({"mime_type": "text/plain", "uploaded_by_user_id": 0}, "common", id="missing-system-text"),
    pytest.param({"mime_type": "application/pdf", "uploaded_by_user_id": 0}, "common", id="missing-system-pdf"),
    pytest.param({"mime_type": "image/png", "uploaded_by_user_id": 5}, "common", id="missing-image-png"),
    pytest.param({"mime_type": "image/jpeg", "uploaded_by_user_id": 5}, "common", id="missing-image-jpeg"),
    pytest.param({"mime_type": "text/plain", "uploaded_by_user_id": 5}, "personal", id="missing-text"),
    pytest.param({"mime_type": "text/csv", "uploaded_by_user_id": 5}, "personal", id="missing-csv"),
    pytest.param({"mime_type": "application/pdf", "uploaded_by_user_id": 5}, "personal", id="missing-pdf"),
    pytest.param({"uploaded_by_user_id": 5}, "personal", id="missing-mime-type"),
    pytest.param({"scope": None, "mime_type": "image/png", "uploaded_by_user_id": 5}, "common", id="none-image"),
    pytest.param({"scope": None, "mime_type": "text/plain", "uploaded_by_user_id": 5}, "personal", id="none-text"),
    pytest.param({"scope": None, "mime_type": "text/plain", "uploaded_by_user_id": 0}, "common", id="none-system"),
    pytest.param({"scope": "public", "mime_type": "text/plain", "uploaded_by_user_id": 5}, "personal", id="other-value-text"),
    pytest.param({"scope": "public", "mime_type": "image/png", "uploaded_by_user_id": 5}, "common", id="other-value-image"),
    pytest.param({"scope": "", "mime_type": "text/plain", "uploaded_by_user_id": 0}, "common", id="empty-system"),
    pytest.param({"scope": "Common", "mime_type": "text/plain", "uploaded_by_user_id": 5}, "personal", id="other-case-text"),
]


class TestEffectiveScope:
    """effective_scope(metadata) -> "common" | "personal", a pure function of a sidecar's metadata (decision 36)."""

    @pytest.mark.parametrize(("metadata", "expected"), STORED_SCOPE_WINS)
    def test_a_stored_scope_wins(self, metadata: dict, expected: str):
        """A stored "common" or "personal" is the scope, whatever the inheritance rule would say."""
        print_section(f"effective_scope: stored {metadata['scope']!r} wins")
        effective_scope = _effective_scope()
        untouched = copy.deepcopy(metadata)

        assert effective_scope(metadata) == expected
        assert metadata == untouched, "effective_scope() reads the metadata and never writes them"
        print_success(f"{metadata} → {expected}")

    @pytest.mark.parametrize(("metadata", "expected"), INHERITED_SCOPE)
    def test_otherwise_the_inheritance_rule_applies(self, metadata: dict, expected: str):
        """No scope, None or any other value (a case variant included): user 0 → common, image/* → common, else personal."""
        print_section("effective_scope: inheritance rule")
        effective_scope = _effective_scope()
        untouched = copy.deepcopy(metadata)

        assert effective_scope(metadata) == expected
        assert metadata == untouched, "effective_scope() reads the metadata and never writes them"
        print_success(f"{metadata} → {expected}")


# ============================================================================
# save_upload — the scope stored in the sidecar (decision 36)
# ============================================================================


class TestSaveUploadStoresTheScope:
    """save_upload() writes the scope into the sidecar: the one asked for, as given; without one, the rule's result, so
    the stored value stays explicit. POST /uploads passes its optional ``scope`` field through (keyword ``scope``)."""

    @pytest.mark.parametrize(
        ("name", "scope", "expected"),
        [
            pytest.param("photo.png", None, "common", id="image-without-scope"),
            pytest.param("notes.txt", None, "personal", id="text-without-scope"),
            pytest.param("photo.png", "personal", "personal", id="image-asked-personal"),
            pytest.param("notes.txt", "common", "common", id="text-asked-common"),
        ],
    )
    def test_scope_written_to_the_sidecar(self, name: str, scope: str | None, expected: str):
        print_section(f"save_upload: {name}, scope={scope} → sidecar scope {expected}")
        is_image = name.endswith(".png")
        asked = {} if scope is None else {"scope": scope}

        info = save_upload(_png_bytes() if is_image else SAMPLE_CONTENT, name, user_id=5, **asked)

        sidecar = _sidecar(info.id)
        assert sidecar["mime_type"].startswith("image/") == is_image, f"precondition: {name} was detected as {sidecar['mime_type']}"
        assert sidecar.get("scope") == expected, f"the sidecar of {name} (scope={scope}) stores scope {sidecar.get('scope')!r}, expected {expected!r}: {sidecar}"
        assert info.scope == expected
        print_success(f"{name}: sidecar and info say {expected}")


# ============================================================================
# Legacy sidecars — written before decision 36, without scope
# ============================================================================


class TestLegacySidecars:
    """Sidecars written before decision 36 carry no ``scope``: the inheritance rule classifies them when they are read,
    writing nothing (D36-2: read on the fly, no migration). A scope change stores the field."""

    @pytest.mark.parametrize(
        ("name", "mime_type", "user_id", "expected"),
        [
            pytest.param("logo.png", "image/png", 5, "common", id="png"),
            pytest.param("statement.pdf", "application/pdf", 5, "personal", id="pdf"),
            pytest.param("export.csv", "text/csv", 5, "personal", id="csv"),
            pytest.param("notes.txt", "text/plain", 5, "personal", id="text"),
            pytest.param("readme.txt", "text/plain", 0, "common", id="system-text"),
        ],
    )
    def test_legacy_sidecar_inherits_its_scope(self, name: str, mime_type: str, user_id: int, expected: str):
        print_section(f"legacy sidecar: {name} of user {user_id} → {expected}")
        file_id = _write_legacy_upload(name, _png_bytes() if mime_type.startswith("image/") else SAMPLE_CONTENT, mime_type, user_id)
        sidecar_path = get_uploads_dir() / f"{file_id}.json"
        as_written = sidecar_path.read_bytes()

        info = get_upload_info(file_id)
        assert info is not None, "a legacy sidecar is still an upload"
        assert info.scope == expected
        listed = {f.id: f for f in list_uploads()[0]}
        assert listed[file_id].scope == expected, "list_uploads() classifies a legacy sidecar the same way"
        assert sidecar_path.read_bytes() == as_written, "reading a legacy sidecar wrote it: the inheritance rule is applied on the fly, without writing (D36-2)"
        print_success(f"{name} → {expected}, sidecar untouched")

    def test_scope_change_stores_the_field_in_a_legacy_sidecar(self):
        """set_upload_scope() writes ``scope`` into a legacy sidecar, the inherited value included, and nothing else."""
        print_section("legacy sidecar: a scope change stores the field")
        set_upload_scope = _set_upload_scope()
        image_id = _write_legacy_upload("logo.png", _png_bytes(), "image/png", 5)  # inherited: common
        text_id = _write_legacy_upload("notes.txt", SAMPLE_CONTENT, "text/plain", 5)  # inherited: personal
        before = {file_id: _sidecar(file_id) for file_id in (image_id, text_id)}

        changed = set_upload_scope(image_id, "personal")
        same = set_upload_scope(text_id, "personal")  # the value the rule gives anyway: stored all the same, explicit from now on

        for file_id, info in ((image_id, changed), (text_id, same)):
            assert info is not None, f"set_upload_scope({file_id!r}) found nothing"
            assert (info.id, info.scope) == (file_id, "personal")
            after = _sidecar(file_id)
            assert after.get("scope") == "personal", f"the legacy sidecar was not given the scope: {after}"
            assert {key: after.get(key) for key in before[file_id]} == before[file_id], "a scope change rewrites the scope, nothing else"
        print_success("scope stored in both legacy sidecars")


# ============================================================================
# Cross-process freshness and atomic writes (decision 36)
# ============================================================================


class TestCrossProcessFreshness:
    """Each worker of ``dev.py server --workers N`` keeps its own one-hour cache of the sidecars, and the scope decides
    who may read a file: a sidecar another worker rewrote or deleted is read as it is on disk now, without anybody
    clearing a cache. A scope change replaces the sidecar atomically: written whole, then renamed over the old one."""

    def test_sidecar_rewritten_by_another_worker_is_read_fresh(self):
        print_section("freshness: a sidecar another worker rewrote")
        saved = save_upload(SAMPLE_CONTENT, "shared.txt", user_id=5, description="before")
        first = get_upload_info(saved.id)
        assert first is not None and first.description == "before"  # read once: now in this process's cache

        _rewrite_like_another_worker(saved.id, scope="common", description="after, from another worker")

        fresh = get_upload_info(saved.id)
        assert fresh is not None
        assert fresh.description == "after, from another worker", "get_upload_info() served the sidecar this process had cached, not the one another worker wrote since"
        assert fresh.scope == "common"
        listed = {f.id: f for f in list_uploads()[0]}[saved.id]
        assert (listed.description, listed.scope) == ("after, from another worker", "common"), "list_uploads() served a stale sidecar"
        print_success("the rewritten sidecar is read, no cache cleared")

    def test_sidecar_deleted_on_disk_is_no_longer_found(self):
        """Replaces test_load_metadata_uses_cache_after_first_read, which pinned the opposite (the cache served it)."""
        print_section("freshness: a sidecar deleted on disk")
        saved = save_upload(SAMPLE_CONTENT, "gone.txt", user_id=5)
        assert get_upload_info(saved.id) is not None  # read once: now in this process's cache

        (get_uploads_dir() / f"{saved.id}.json").unlink()

        assert get_upload_info(saved.id) is None, "get_upload_info() still finds a file whose sidecar is gone from disk: served from the cache"
        assert get_upload_path(saved.id) is None, "get_upload_path() still finds a file whose sidecar is gone from disk: served from the cache"
        print_success("a deleted sidecar is not found, no cache cleared")

    def test_scope_change_replaces_the_sidecar_atomically(self):
        print_section("set_upload_scope: atomic sidecar write")
        set_upload_scope = _set_upload_scope()
        saved = save_upload(SAMPLE_CONTENT, "switch.txt", user_id=5, description="kept as it was")
        uploads_dir = get_uploads_dir()
        sidecar_path = uploads_dir / f"{saved.id}.json"
        before = json.loads(sidecar_path.read_text())
        inode_before = sidecar_path.stat().st_ino

        updated = set_upload_scope(saved.id, "common")

        assert updated is not None and (updated.id, updated.scope) == (saved.id, "common")
        # The folder is this test's own (tmp_path): exactly the file and its sidecar, no temporary or partial file left.
        assert sorted(p.name for p in uploads_dir.iterdir()) == sorted([f"{saved.id}.txt", f"{saved.id}.json"])
        after = json.loads(sidecar_path.read_text())  # whole, and parses
        assert after.get("scope") == "common"
        assert {key: after.get(key) for key in before if key != "scope"} == {key: value for key, value in before.items() if key != "scope"}, "a scope change rewrites the scope, nothing else"
        # Rewritten in place (open with truncation), the same inode is emptied, then refilled under a concurrent reader's
        # eyes; written whole and renamed over the old one (os.replace), the sidecar is a new inode.
        assert sidecar_path.stat().st_ino != inode_before, "the sidecar was rewritten in place: a reader in another worker can read it half written"
        assert get_upload_info(saved.id).scope == "common"
        print_success("sidecar replaced whole, nothing left behind")

    def test_scope_change_of_a_missing_file_returns_none(self):
        print_section("set_upload_scope: missing id")
        set_upload_scope = _set_upload_scope()
        missing = str(uuid.uuid4())

        assert set_upload_scope(missing, "common") is None
        assert [p.name for p in get_uploads_dir().iterdir() if missing in p.name] == [], "a scope change of a missing file wrote something"
        print_success("None, nothing written")

    @pytest.mark.parametrize("delete_lands", ["before-the-write", "after-the-write"], ids=["delete-done-before-the-write", "file-removed-after-the-write"])
    def test_scope_change_racing_a_delete_leaves_nothing_behind(self, monkeypatch, delete_lands: str):
        """A delete runs while set_upload_scope() writes: the file is gone when it checks again after writing.

        Either the delete finished just before the write, which then puts a sidecar back for a file that no longer
        exists, or it has removed the file just after the write and not yet its sidecar. set_upload_scope() answers None
        and removes the sidecar it wrote: nothing of the deleted file is left in the folder."""
        print_section(f"set_upload_scope: a delete lands {delete_lands.replace('-', ' ')}")
        set_upload_scope = _set_upload_scope()
        saved = save_upload(SAMPLE_CONTENT, "raced.txt", user_id=5)
        uploads_dir = get_uploads_dir()
        real_save_metadata = static_uploads._save_metadata
        writes: list[str] = []

        def write_while_a_delete_lands(file_id: str, metadata: dict) -> None:
            if delete_lands == "before-the-write":
                assert delete_upload(file_id), "precondition: the delete removed the file"
                real_save_metadata(file_id, metadata)
            else:
                real_save_metadata(file_id, metadata)
                (uploads_dir / f"{file_id}.txt").unlink()  # the delete's first step; its sidecar step has not run yet
            writes.append(metadata["scope"])

        monkeypatch.setattr(static_uploads, "_save_metadata", write_while_a_delete_lands)

        result = set_upload_scope(saved.id, "common")

        assert writes == ["common"], "precondition: set_upload_scope() reached the sidecar write, where the delete lands"
        assert result is None, f"set_upload_scope() answered {result!r} for a file deleted while it wrote"
        assert not (uploads_dir / f"{saved.id}.json").exists(), "the sidecar written for a file deleted meanwhile is left behind"
        assert get_upload_info(saved.id) is None
        # The folder is this test's own (tmp_path): no content, no sidecar, no temporary file of the write.
        assert sorted(p.name for p in uploads_dir.iterdir()) == []
        print_success("None, nothing of the deleted file left")


# ============================================================================
# Ids the filesystem cannot name
# ============================================================================


class TestIdsTheFilesystemCannotName:
    """An id with an embedded NUL byte names no file: ``os.stat()`` raises ValueError on its path instead of OSError.
    It must read as a missing file, never as an exception, which the API would turn into a 500."""

    def test_nul_byte_id_is_a_missing_file(self):
        print_section("NUL byte in the id → missing file")
        set_upload_scope = _set_upload_scope()
        saved = save_upload(SAMPLE_CONTENT, "real.txt", user_id=5)
        nul_id = f"{saved.id}\x00"  # an existing file's id, then NUL: must not reach that file
        uploads_dir = get_uploads_dir()
        with pytest.raises(ValueError):  # the premise: the filesystem cannot name it, stat() raises
            (uploads_dir / f"{nul_id}.json").stat()

        assert get_upload_info(nul_id) is None
        assert get_upload_path(nul_id) is None
        assert get_upload_mime_type(nul_id) is None
        assert set_upload_scope(nul_id, "common") is None
        assert delete_upload(nul_id) is False

        # The real file next to it is untouched: no write, no delete reached it.
        assert sorted(p.name for p in uploads_dir.iterdir()) == sorted([f"{saved.id}.txt", f"{saved.id}.json"])
        info = get_upload_info(saved.id)
        assert info is not None and info.scope == "personal"
        print_success("None / False, no exception, the real file untouched")
