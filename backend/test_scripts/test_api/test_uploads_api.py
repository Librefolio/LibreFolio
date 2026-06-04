"""
Uploads API Tests.

Tests for static file upload endpoints:
- POST /uploads: Upload file
- GET /uploads: List files
- GET /uploads/{id}: File info
- GET /uploads/{id}/preview: Structured preview payload
- GET /uploads/file/{id}: Download file
- DELETE /uploads/{id}: Delete file
- GET /uploads/plugin/{type}/{path}: Serve plugin static asset
"""

import io
from datetime import datetime
from io import BytesIO
from pathlib import Path

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


def unique_username() -> str:
    """Generate a unique username."""
    timestamp = int(datetime.now().timestamp() * 1000)
    return f"upload_test_{timestamp}"


# ============================================================================
# HELPERS
# ============================================================================


async def create_user_and_login(client: httpx.AsyncClient) -> tuple[int, str]:
    """Create user, login, return (user_id, username)."""
    username = unique_username()
    email = f"{username}@test.com"
    password = "TestPass123!"

    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=TIMEOUT,
    )
    user_id = resp.json()["user"]["id"]

    login_resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)
    session = login_resp.cookies.get("session")
    if session:
        client.cookies.set("session", session)

    return user_id, username


def create_test_file(name: str = "test.txt", content: bytes = b"Hello World") -> tuple[str, bytes]:
    """Create a test file for upload."""
    return name, content


def create_png_bytes(width: int = 64, height: int = 48) -> bytes:
    """Create a real PNG image for preview tests."""
    from PIL import Image  # noqa: PLC0415 — test-only local import

    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def create_xlsx_bytes() -> bytes:
    """Create a workbook with sparse cells and multiple sheets."""
    from openpyxl import Workbook  # noqa: PLC0415 — test-only local import

    workbook = Workbook()
    summary = workbook.active
    summary.title = "Summary"
    summary["A1"] = "Name"
    summary["B1"] = "Amount"
    summary["A2"] = "Cash"
    summary["C3"] = "Sparse"

    details = workbook.create_sheet("Details")
    details["A1"] = "Date"
    details["B1"] = "Type"
    details["A2"] = "2025-01-01"
    details["B2"] = "BUY"

    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def create_minimal_pdf_bytes() -> bytes:
    """Create a tiny but valid PDF file."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]/Contents 4 0 R>>endobj\n"
        b"4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 72 120 Td (Preview PDF) Tj ET\nendstream endobj\n"
        b"xref\n0 5\n0000000000 65535 f \n"
        b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n256\n%%EOF\n"
    )


def read_sample_xls_bytes() -> bytes:
    """Read committed legacy XLS sample for preview coverage."""
    sample_path = Path(__file__).resolve().parents[3] / "backend" / "staticResources" / "FilePreviewSamples" / "file_example_XLS_10.xls"
    return sample_path.read_bytes()


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def test_server():
    """Start test server."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================================
# UPLOAD TESTS
# ============================================================================


class TestUpload:
    """Tests for POST /uploads."""

    @pytest.mark.asyncio
    async def test_upload_valid_file(self, test_server):
        """UPLOAD-001: Upload valid file."""
        print_section("UPLOAD-001: Upload valid file")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            filename, content = create_test_file("test_upload.txt", b"Test content")

            files = {"file": (filename, BytesIO(content), "text/plain")}
            response = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)

            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            assert data["success"] is True
            assert data["file"]["original_name"] == filename
            assert data["file"]["size_bytes"] == len(content)
            assert "id" in data["file"]

            print_success("✓ File uploaded successfully")

    @pytest.mark.asyncio
    async def test_upload_requires_auth(self, test_server):
        """UPLOAD: Upload requires authentication."""
        print_section("UPLOAD: Requires auth")

        async with httpx.AsyncClient() as client:
            filename, content = create_test_file()
            files = {"file": (filename, BytesIO(content), "text/plain")}

            response = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)

            assert response.status_code == 401

            print_success("✓ Upload requires auth")


# ============================================================================
# LIST TESTS
# ============================================================================


class TestListUploads:
    """Tests for GET /uploads."""

    @pytest.mark.asyncio
    async def test_list_uploads(self, test_server):
        """UPLOAD-003: List all uploads."""
        print_section("UPLOAD-003: List uploads")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            # Upload a file first
            filename, content = create_test_file("list_test.txt", b"Content")
            files = {"file": (filename, BytesIO(content), "text/plain")}
            await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)

            # List
            response = await client.get(f"{API_BASE}/uploads", timeout=TIMEOUT)

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert len(data["items"]) >= 1

            print_success("✓ Listed uploads")

    @pytest.mark.asyncio
    async def test_list_my_files_only(self, test_server):
        """UPLOAD-004: List only my files."""
        print_section("UPLOAD-004: List my files only")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            # User 1 uploads
            user1_id, _ = await create_user_and_login(client1)
            files1 = {"file": ("user1_file.txt", BytesIO(b"User1"), "text/plain")}
            upload1_resp = await client1.post(f"{API_BASE}/uploads", files=files1, timeout=TIMEOUT)
            file1_id = upload1_resp.json()["file"]["id"]

            # User 2 uploads
            user2_id, _ = await create_user_and_login(client2)
            files2 = {"file": ("user2_file.txt", BytesIO(b"User2"), "text/plain")}
            await client2.post(f"{API_BASE}/uploads", files=files2, timeout=TIMEOUT)

            # User 2 lists only their files
            response = await client2.get(f"{API_BASE}/uploads", params={"my_files_only": True}, timeout=TIMEOUT)

            assert response.status_code == 200
            data = response.json()
            file_ids = [f["id"] for f in data["items"]]
            assert file1_id not in file_ids  # User 1's file should not be in user 2's list

            print_success("✓ Filtered to my files only")


# ============================================================================
# FILE INFO TESTS
# ============================================================================


class TestFileInfo:
    """Tests for GET /uploads/{id}."""

    @pytest.mark.asyncio
    async def test_get_file_info(self, test_server):
        """UPLOAD-005: Get file info."""
        print_section("UPLOAD-005: Get file info")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            # Upload
            filename, content = create_test_file("info_test.txt", b"Info content")
            files = {"file": (filename, BytesIO(content), "text/plain")}
            upload_resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            # Get info
            response = await client.get(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == file_id
            assert data["original_name"] == filename

            print_success("✓ Got file info")


# ============================================================================
# STRUCTURED PREVIEW TESTS
# ============================================================================


class TestStructuredPreview:
    """Tests for GET /uploads/{id}/preview."""

    @pytest.mark.asyncio
    async def test_markdown_preview_payload(self, test_server):
        """UPLOAD-005B: Markdown preview returns raw content and metadata."""
        print_section("UPLOAD-005B: Markdown preview payload")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            files = {"file": ("notes.md", BytesIO(b"# Heading\n\nBody line\n"), "text/markdown")}
            upload_resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            response = await client.get(f"{API_BASE}/uploads/{file_id}/preview", timeout=TIMEOUT)

            assert response.status_code == 200, response.text
            data = response.json()
            assert data["preview_type"] == "markdown"
            assert data["text_content"] == "# Heading\n\nBody line\n"
            assert data["total_lines"] == 3
            assert data["download_url"].endswith("?download=true")

            print_success("✓ Markdown preview payload returned")

    @pytest.mark.asyncio
    async def test_image_preview_payload(self, test_server):
        """UPLOAD-005C: Image preview returns dimensions and optimized URL."""
        print_section("UPLOAD-005C: Image preview payload")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            files = {"file": ("chart.png", BytesIO(create_png_bytes(120, 90)), "image/png")}
            upload_resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            response = await client.get(f"{API_BASE}/uploads/{file_id}/preview", timeout=TIMEOUT)

            assert response.status_code == 200, response.text
            data = response.json()
            assert data["preview_type"] == "image"
            assert data["image_width"] == 120
            assert data["image_height"] == 90
            assert data["preview_url"].endswith("img_preview=1600x1600")

            print_success("✓ Image preview metadata returned")

    @pytest.mark.asyncio
    async def test_pdf_preview_payload(self, test_server):
        """UPLOAD-005D: PDF preview returns embeddable source URL."""
        print_section("UPLOAD-005D: PDF preview payload")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            files = {"file": ("sample.pdf", BytesIO(create_minimal_pdf_bytes()), "application/pdf")}
            upload_resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            response = await client.get(f"{API_BASE}/uploads/{file_id}/preview", timeout=TIMEOUT)

            assert response.status_code == 200, response.text
            data = response.json()
            assert data["preview_type"] == "pdf"
            assert data["source_url"].endswith(f"/api/v1/uploads/file/{file_id}")
            assert data["preview_url"] is None

            print_success("✓ PDF preview payload returned")

    @pytest.mark.asyncio
    async def test_excel_preview_sheet_selection(self, test_server):
        """UPLOAD-005E: Excel preview preserves sparse cells and sheet selection."""
        print_section("UPLOAD-005E: Excel preview sheet selection")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            files = {
                "file": (
                    "preview.xlsx",
                    BytesIO(create_xlsx_bytes()),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            }
            upload_resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            response = await client.get(
                f"{API_BASE}/uploads/{file_id}/preview",
                params={"sheet_name": "Summary"},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200, response.text
            data = response.json()
            assert data["preview_type"] == "table"
            assert data["sheet_names"] == ["Summary", "Details"]
            assert data["active_sheet_name"] == "Summary"
            assert data["total_rows"] == 3
            assert data["total_cols"] == 3
            assert data["table_rows"][0] == ["Name", "Amount", ""]
            assert data["table_rows"][2][2] == "Sparse"

            print_success("✓ Excel preview respects used range")

    @pytest.mark.asyncio
    async def test_legacy_xls_preview_payload(self, test_server):
        """UPLOAD-005F: Legacy XLS preview works when xlrd is available."""
        print_section("UPLOAD-005F: Legacy XLS preview payload")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            files = {
                "file": (
                    "preview.xls",
                    BytesIO(read_sample_xls_bytes()),
                    "application/vnd.ms-excel",
                )
            }
            upload_resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            response = await client.get(
                f"{API_BASE}/uploads/{file_id}/preview",
                timeout=TIMEOUT,
            )

            assert response.status_code == 200, response.text
            data = response.json()
            assert data["preview_type"] == "table"
            assert data["total_rows"] > 0
            assert data["total_cols"] > 0
            assert isinstance(data["table_rows"], list)
            assert len(data["table_rows"]) > 0

            print_success("✓ Legacy XLS preview returned table payload")


# ============================================================================
# DOWNLOAD TESTS
# ============================================================================


class TestDownload:
    """Tests for GET /uploads/file/{id}."""

    @pytest.mark.asyncio
    async def test_download_file(self, test_server):
        """UPLOAD-006: Download file."""
        print_section("UPLOAD-006: Download file")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            # Upload
            filename, content = create_test_file("download_test.txt", b"Download me!")
            files = {"file": (filename, BytesIO(content), "text/plain")}
            upload_resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            # Download
            response = await client.get(f"{API_BASE}/uploads/file/{file_id}", timeout=TIMEOUT)

            assert response.status_code == 200
            assert response.content == content

            print_success("✓ Downloaded file")


# ============================================================================
# DELETE TESTS
# ============================================================================


class TestDelete:
    """Tests for DELETE /uploads/{id}."""

    @pytest.mark.asyncio
    async def test_delete_own_file(self, test_server):
        """UPLOAD-007: Delete own file."""
        print_section("UPLOAD-007: Delete own file")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            # Upload
            files = {"file": ("delete_test.txt", BytesIO(b"Delete me"), "text/plain")}
            upload_resp = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            # Delete
            response = await client.delete(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)

            assert response.status_code == 200
            assert response.json()["success"] is True

            # Verify deleted
            get_resp = await client.get(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)
            assert get_resp.status_code == 404

            print_success("✓ Deleted own file")

    @pytest.mark.asyncio
    async def test_cannot_delete_others_file(self, test_server):
        """UPLOAD-008: Cannot delete other's file (non-superuser)."""
        print_section("UPLOAD-008: Cannot delete other's file")

        async with httpx.AsyncClient() as client1, httpx.AsyncClient() as client2:
            # User 1 uploads
            await create_user_and_login(client1)
            files = {"file": ("protected.txt", BytesIO(b"Protected"), "text/plain")}
            upload_resp = await client1.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            # User 2 tries to delete
            await create_user_and_login(client2)
            response = await client2.delete(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)

            assert response.status_code == 403

            print_success("✓ Cannot delete other's file")


# ============================================================================
# PLUGIN STATIC TESTS
# ============================================================================


class TestPluginStatic:
    """Tests for GET /uploads/plugin/{type}/{path}."""

    @pytest.mark.asyncio
    async def test_plugin_static_not_found(self, test_server):
        """UPLOAD-011: 404 for non-existent plugin asset."""
        print_section("UPLOAD-011: Plugin static not found")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)
            response = await client.get(f"{API_BASE}/uploads/plugin/brim/nonexistent/logo.png", timeout=TIMEOUT)

            assert response.status_code == 404

            print_success("✓ Got 404 for non-existent asset")


# ============================================================================
# FILE SIZE LIMIT TESTS
# ============================================================================


class TestFileSizeLimit:
    """Tests for max file upload size."""

    @pytest.mark.asyncio
    async def test_file_too_large_rejected(self, test_server):
        """UPLOAD-012: File larger than max_file_upload_mb is rejected."""
        print_section("UPLOAD-012: File too large rejected")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            # Get current max file size setting
            settings_resp = await client.get(f"{API_BASE}/settings/global", timeout=TIMEOUT)
            max_mb = 10  # Default fallback
            for setting in settings_resp.json().get("items", []):
                if setting.get("key") == "max_file_upload_mb":
                    max_mb = int(setting.get("value", 10))
                    break

            # Create file larger than max (max_mb + 1 MB)
            large_content = b"X" * ((max_mb + 1) * 1024 * 1024)
            files = {"file": ("large_file.bin", BytesIO(large_content), "application/octet-stream")}

            response = await client.post(f"{API_BASE}/uploads", files=files, timeout=60)  # Longer timeout for large file

            # Should be rejected with 413 or 400
            assert response.status_code in [
                400,
                413,
            ], f"Expected 400/413, got {response.status_code}"

            print_success("✓ Large file correctly rejected")


# ============================================================================
# SUPERUSER DELETE TESTS
# ============================================================================


class TestSuperuserDelete:
    """Tests for superuser file deletion capabilities."""

    @pytest.mark.asyncio
    async def test_superuser_can_delete_any_file(self, test_server):
        """UPLOAD-013: Superuser can delete any user's file."""
        print_section("UPLOAD-013: Superuser deletes any file")

        async with httpx.AsyncClient() as admin_client, httpx.AsyncClient() as user_client:
            # Create admin (first user)
            await create_user_and_login(admin_client)
            me_resp = await admin_client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
            is_superuser = me_resp.json().get("user", {}).get("is_superuser", False)

            if not is_superuser:
                pytest.skip("First user is not superuser")

            # Regular user uploads file
            await create_user_and_login(user_client)
            files = {"file": ("user_file.txt", BytesIO(b"User content"), "text/plain")}
            upload_resp = await user_client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
            file_id = upload_resp.json()["file"]["id"]

            # Superuser deletes it
            response = await admin_client.delete(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)

            assert response.status_code == 200
            assert response.json()["success"] is True

            print_success("✓ Superuser deleted user's file")


# ============================================================================
# SECURITY VALIDATION TESTS
# ============================================================================


class TestUploadSecurity:
    """Tests for upload security validation."""

    @pytest.mark.asyncio
    async def test_blocked_executable_extension(self, test_server):
        """UPLOAD-014: Executable file extension is blocked."""
        print_section("UPLOAD-014: Blocked executable extension")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            # Try to upload .exe file
            files = {"file": ("malware.exe", BytesIO(b"MZ\x90\x00"), "application/octet-stream")}
            response = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)

            assert response.status_code == 400
            assert "not allowed" in response.json()["detail"].lower()

            print_success("✓ Executable extension blocked")

    @pytest.mark.asyncio
    async def test_blocked_script_extension(self, test_server):
        """UPLOAD-015: Script file extension is blocked."""
        print_section("UPLOAD-015: Blocked script extension")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            # Try to upload .sh script
            files = {"file": ("script.sh", BytesIO(b"#!/bin/bash\nrm -rf /"), "text/plain")}
            response = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)

            assert response.status_code == 400
            assert "not allowed" in response.json()["detail"].lower()

            print_success("✓ Script extension blocked")

    @pytest.mark.asyncio
    async def test_allowed_image_upload(self, test_server):
        """UPLOAD-016: Image files are allowed."""
        print_section("UPLOAD-016: Image upload allowed")

        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)

            # PNG magic bytes
            png_header = b"\x89PNG\r\n\x1a\n"
            files = {"file": ("test.png", BytesIO(png_header + b"\x00" * 100), "image/png")}
            response = await client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)

            assert response.status_code == 200
            assert response.json()["success"] is True

            print_success("✓ Image upload allowed")
