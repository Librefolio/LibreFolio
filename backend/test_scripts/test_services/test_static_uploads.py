"""
Test: StaticUploads Service — save, list, get, delete, security validation.

Tests the static uploads service layer including file persistence,
metadata sidecar, security checks, cache invalidation, and user filtering.
"""

import sys

import pytest

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

import shutil

from backend.app.services.static_uploads import (
    UploadSecurityError,
    delete_upload,
    get_upload_by_user,
    get_upload_info,
    get_upload_path,
    get_uploads_dir,
    list_uploads,
    save_upload,
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
