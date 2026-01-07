"""
BRIM API Tests.

Tests for Broker Report Import Manager API endpoints:
- POST /brokers/import/upload: Upload broker report file
- GET /brokers/import/files: List uploaded files
- GET /brokers/import/files/{id}: Get file details
- DELETE /brokers/import/files/{id}: Delete file
- POST /brokers/import/files/{id}/parse: Parse file
- GET /brokers/import/plugins: List available plugins

See checklist: 01_test_brim_plan.md - Categories 5, 6
Note: E2E tests are in test_e2e/test_brim_e2e.py (Category 7)
Reference: backend/app/api/v1/brokers.py
"""
import io
import uuid
from pathlib import Path

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30

# Sample file paths
SAMPLE_DIR = Path(__file__).parent.parent.parent / "app" / "services" / "brim_providers" / "sample_reports"


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def test_server():
    """Start test server once for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


@pytest.fixture(scope="module")
def test_broker_id(test_server) -> int:
    """Create a test broker and return its ID."""
    import asyncio

    async def create_broker():
        async with httpx.AsyncClient() as client:
            unique_name = f"BRIM_API_Test_Broker_{uuid.uuid4().hex[:8]}"
            payload = [{"name": unique_name, "allow_cash_overdraft": True}]
            response = await client.post(
                f"{API_BASE}/brokers",
                json=payload,
                timeout=TIMEOUT,
                )
            assert response.status_code == 200, f"Failed to create broker: {response.text}"
            data = response.json()

            if data["results"] and data["results"][0]["success"]:
                return data["results"][0]["broker_id"]

            pytest.fail(f"Could not create broker: {data}")

    return asyncio.run(create_broker())


@pytest.fixture
def sample_csv_content() -> bytes:
    """Simple CSV content for upload tests."""
    return b"""date,type,quantity,amount,currency,description
2025-01-01,DEPOSIT,0,1000.00,EUR,Test deposit
2025-01-02,BUY,10,-500.00,EUR,Buy some shares
"""


@pytest.fixture
def sample_csv_with_assets() -> bytes:
    """CSV content with asset identifiers."""
    return b"""date,type,quantity,amount,currency,asset,description
2025-01-01,DEPOSIT,0,5000.00,EUR,,Initial deposit
2025-01-02,BUY,10,-1000.00,EUR,AAPL,Buy Apple
2025-01-03,BUY,5,-500.00,EUR,MSFT,Buy Microsoft
2025-01-04,SELL,-5,550.00,EUR,AAPL,Sell Apple partial
"""


# ============================================================================
# CATEGORY 5: FILE STORAGE TESTS
# ============================================================================

class TestFileStorage:
    """Tests for file upload and storage functionality."""

    @pytest.mark.asyncio
    async def test_upload_file_success(self, test_server, sample_csv_content):
        """FS-001: Upload a valid CSV file successfully."""
        async with httpx.AsyncClient() as client:
            files = {"file": ("test_upload.csv", io.BytesIO(sample_csv_content), "text/csv")}
            response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                timeout=TIMEOUT,
                )

            assert response.status_code == 200, f"Upload failed: {response.text}"
            data = response.json()

            assert "file_id" in data
            assert data["status"] == "uploaded"
            assert data["filename"] == "test_upload.csv"
            assert "compatible_plugins" in data
            assert len(data["compatible_plugins"]) > 0

    @pytest.mark.asyncio
    async def test_upload_empty_file(self, test_server):
        """FS-002: Reject empty file upload."""
        async with httpx.AsyncClient() as client:
            files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
            response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                timeout=TIMEOUT,
                )

            assert response.status_code == 400
            assert "empty" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_list_files(self, test_server, sample_csv_content):
        """FS-003: List uploaded files."""
        async with httpx.AsyncClient() as client:
            # Upload a file first
            files = {"file": ("list_test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                timeout=TIMEOUT,
                )
            assert upload_response.status_code == 200

            # List files
            list_response = await client.get(
                f"{API_BASE}/brokers/import/files",
                timeout=TIMEOUT,
                )

            assert list_response.status_code == 200
            data = list_response.json()
            assert isinstance(data, list)
            assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_list_files_by_status(self, test_server, sample_csv_content):
        """FS-004: Filter files by status."""
        async with httpx.AsyncClient() as client:
            # Upload a file
            files = {"file": ("status_test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                timeout=TIMEOUT,
                )

            # Filter by 'uploaded' status
            response = await client.get(
                f"{API_BASE}/brokers/import/files?status=uploaded",
                timeout=TIMEOUT,
                )

            assert response.status_code == 200
            data = response.json()
            for file_info in data:
                assert file_info["status"] == "uploaded"

    @pytest.mark.asyncio
    async def test_get_file_info(self, test_server, sample_csv_content):
        """FS-005: Get single file info."""
        async with httpx.AsyncClient() as client:
            # Upload a file
            files = {"file": ("info_test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                timeout=TIMEOUT,
                )
            file_id = upload_response.json()["file_id"]

            # Get file info
            response = await client.get(
                f"{API_BASE}/brokers/import/files/{file_id}",
                timeout=TIMEOUT,
                )

            assert response.status_code == 200
            data = response.json()
            assert data["file_id"] == file_id
            assert data["filename"] == "info_test.csv"

    @pytest.mark.asyncio
    async def test_get_file_not_found(self, test_server):
        """FS-006: 404 for non-existent file."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_BASE}/brokers/import/files/nonexistent-uuid",
                timeout=TIMEOUT,
                )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_file(self, test_server, sample_csv_content):
        """FS-007: Delete a file."""
        async with httpx.AsyncClient() as client:
            # Upload a file
            files = {"file": ("delete_test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                timeout=TIMEOUT,
                )
            file_id = upload_response.json()["file_id"]

            # Delete file
            delete_response = await client.delete(
                f"{API_BASE}/brokers/import/files/{file_id}",
                timeout=TIMEOUT,
                )

            assert delete_response.status_code == 200
            assert delete_response.json()["success"] is True

            # Verify file is gone
            get_response = await client.get(
                f"{API_BASE}/brokers/import/files/{file_id}",
                timeout=TIMEOUT,
                )
            assert get_response.status_code == 404


# ============================================================================
# CATEGORY 6: API ENDPOINTS TESTS
# ============================================================================

class TestParseEndpoint:
    """Tests for parse endpoint functionality."""

    @pytest.mark.asyncio
    async def test_parse_file_success(self, test_server, test_broker_id, sample_csv_content):
        """API-009: Parse file successfully."""
        async with httpx.AsyncClient() as client:
            # Upload file
            files = {"file": ("parse_test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                timeout=TIMEOUT,
                )
            file_id = upload_response.json()["file_id"]

            # Parse file
            parse_response = await client.post(
                f"{API_BASE}/brokers/import/files/{file_id}/parse",
                json={
                    "plugin_code": "broker_generic_csv",
                    "broker_id": test_broker_id,
                    },
                timeout=TIMEOUT,
                )

            if parse_response.status_code != 200:
                print(f"Parse error: {parse_response.text}")

            assert parse_response.status_code == 200, f"Parse failed: {parse_response.text}"
            data = parse_response.json()

            assert "transactions" in data
            assert "warnings" in data
            assert "asset_mappings" in data
            assert "duplicates" in data
            assert len(data["transactions"]) == 2  # DEPOSIT + BUY

    @pytest.mark.asyncio
    async def test_parse_returns_asset_mappings(self, test_server, test_broker_id, sample_csv_with_assets):
        """API-010: Parse returns asset mappings for transactions with assets."""
        async with httpx.AsyncClient() as client:
            # Upload file with assets
            files = {"file": ("assets_test.csv", io.BytesIO(sample_csv_with_assets), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                timeout=TIMEOUT,
                )
            file_id = upload_response.json()["file_id"]

            # Parse
            parse_response = await client.post(
                f"{API_BASE}/brokers/import/files/{file_id}/parse",
                json={
                    "plugin_code": "broker_generic_csv",
                    "broker_id": test_broker_id,
                    },
                timeout=TIMEOUT,
                )

            assert parse_response.status_code == 200
            data = parse_response.json()

            # Should have asset mappings for AAPL and MSFT
            assert len(data["asset_mappings"]) >= 2

            # Verify structure
            for mapping in data["asset_mappings"]:
                assert "fake_asset_id" in mapping
                assert "candidates" in mapping

    @pytest.mark.asyncio
    async def test_parse_returns_duplicates_report(self, test_server, test_broker_id, sample_csv_content):
        """API-011: Parse returns duplicates report."""
        async with httpx.AsyncClient() as client:
            # Upload file
            files = {"file": ("dup_test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                timeout=TIMEOUT,
                )
            file_id = upload_response.json()["file_id"]

            # Parse
            parse_response = await client.post(
                f"{API_BASE}/brokers/import/files/{file_id}/parse",
                json={
                    "plugin_code": "broker_generic_csv",
                    "broker_id": test_broker_id,
                    },
                timeout=TIMEOUT,
                )

            assert parse_response.status_code == 200
            data = parse_response.json()

            # Duplicates report structure
            duplicates = data["duplicates"]
            assert "tx_unique_indices" in duplicates
            assert "tx_possible_duplicates" in duplicates
            assert "tx_likely_duplicates" in duplicates

    @pytest.mark.asyncio
    async def test_parse_file_not_found(self, test_server, test_broker_id):
        """API-012: 404 when parsing non-existent file."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE}/brokers/import/files/nonexistent-uuid/parse",
                json={
                    "plugin_code": "broker_generic_csv",
                    "broker_id": test_broker_id,
                    },
                timeout=TIMEOUT,
                )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_parse_invalid_plugin(self, test_server, test_broker_id, sample_csv_content):
        """API-013: 400 for invalid plugin code."""
        async with httpx.AsyncClient() as client:
            # Upload file
            files = {"file": ("plugin_test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                timeout=TIMEOUT,
                )
            file_id = upload_response.json()["file_id"]

            # Parse with invalid plugin
            response = await client.post(
                f"{API_BASE}/brokers/import/files/{file_id}/parse",
                json={
                    "plugin_code": "nonexistent_plugin",
                    "broker_id": test_broker_id,
                    },
                timeout=TIMEOUT,
                )

            assert response.status_code == 400
            assert "plugin" in response.json()["detail"].lower()


class TestPluginsEndpoint:
    """Tests for plugins listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_plugins(self, test_server):
        """API-008: List available plugins."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_BASE}/brokers/import/plugins",
                timeout=TIMEOUT,
                )

            assert response.status_code == 200
            data = response.json()

            assert isinstance(data, list)
            assert len(data) > 0

            # Verify structure
            for plugin in data:
                assert "code" in plugin
                assert "name" in plugin
                assert "description" in plugin

            # Should include generic CSV plugin
            codes = [p["code"] for p in data]
            assert "broker_generic_csv" in codes


# ============================================================================
# Note: E2E tests are in test_e2e/test_brim_e2e.py
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
