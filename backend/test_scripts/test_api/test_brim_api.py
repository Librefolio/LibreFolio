"""
BRIM API Tests.

Tests for Broker Report Import Manager API endpoints:
- POST /brokers/import/upload: Upload broker report file (optional batch_id: report sets)
- GET /brokers/import/files: List uploaded files
- GET /brokers/import/files/{id}: Get file details
- DELETE /brokers/import/files/{id}: Delete file
- POST /brokers/import/files/{id}/parse: Parse file
- GET /brokers/import/plugins: List available plugins
- POST /brokers/import/sets/preview and /sets/combine: report sets (phase A2)
- POST /brokers/import/gap-fix: the corrections that align LibreFolio with the bank (phase A3)
- GET /brokers/import/files and /files/{id} detect again the plugins of a file detected
  before item 8, whose sidecar has no detection signature (step 5, item 8: Category 13)
- DELETE /brokers/import/files/{id} waiting for the broker's metadata lock leaves its backend
  process responsive (step 5, item 8 + F1: Category 14)

See checklist: 01_test_brim_plan.md - Categories 5, 6
Note: E2E tests are in test_e2e/test_brim_e2e.py (Category 7)
Report sets: what a set contains is tested at service level, in
test_services/test_brim_report_sets.py (Category 8 below explains why).
Reference: backend/app/api/v1/brokers.py
"""

import io
import json
import os
import threading
import time
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, TextIO, Tuple

import httpx
import psutil
import pytest

from backend.app.config import PROJECT_ROOT, get_settings, get_test_data_dir
from backend.test_scripts.test_server_helper import _TestingServerManager, port_holder_pids
from backend.test_scripts.test_utils import print_section, print_success

try:
    import fcntl
except ImportError:  # not POSIX: the backend's broker lock is in-process only (Category 14 is skipped)
    fcntl = None

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30

# Sample file paths
SAMPLE_DIR = PROJECT_ROOT / "app" / "services" / "brim_providers" / "sample_reports"


# ============================================================================
# AUTH HELPERS
# ============================================================================


def unique_username() -> str:
    """Generate unique username for test isolation."""
    ts = int(time.time() * 1000) % 1000000
    return f"brim_test_{ts}_{uuid.uuid4().hex[:8]}"


async def create_test_user(client: httpx.AsyncClient) -> int:
    """Register and login a test user, return user_id."""
    username = unique_username()
    email = f"{username}@example.com"
    password = "testpass123"

    # Register
    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=TIMEOUT,
    )
    assert resp.status_code == 201, f"Register failed: {resp.text}"

    # Login
    resp = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": password},
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["user"]["id"]


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


async def create_test_broker(client: httpx.AsyncClient, user_id: int = None) -> int:
    """Create a broker for testing, return broker_id.

    Note: User must already be logged in (session cookie set).
    """
    unique_name = f"BRIM_Test_Broker_{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        f"{API_BASE}/brokers",
        json=[{"name": unique_name, "allow_cash_overdraft": True}],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Failed to create broker: {resp.text}"
    return resp.json()["results"][0]["broker_id"]


class TestFileStorage:
    """Tests for file upload and storage functionality."""

    @pytest.mark.asyncio
    async def test_upload_file_success(self, test_server, sample_csv_content):
        """FS-001: Upload a valid CSV file successfully."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)

            files = {"file": ("test_upload.csv", io.BytesIO(sample_csv_content), "text/csv")}
            response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                data={"broker_id": broker_id},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200, f"Upload failed: {response.text}"
            data = response.json()

            assert "file_id" in data
            assert data["status"] == "uploaded"
            assert data["filename"] == "test_upload.csv"
            assert "compatible_plugins" in data
            assert len(data["compatible_plugins"]) > 0
            # Verify multi-user fields
            assert data.get("target_broker_id") == broker_id
            assert data.get("uploaded_by_user_id") is not None

    @pytest.mark.asyncio
    async def test_upload_empty_file(self, test_server):
        """FS-002: Reject empty file upload."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)

            files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
            response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                data={"broker_id": broker_id},
                timeout=TIMEOUT,
            )

            assert response.status_code == 400
            assert "empty" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_list_files(self, test_server, sample_csv_content):
        """FS-003: List uploaded files."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)

            # Upload a file first
            files = {"file": ("list_test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                data={"broker_id": broker_id},
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
            await create_test_user(client)
            broker_id = await create_test_broker(client)

            # Upload a file
            files = {"file": ("status_test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                data={"broker_id": broker_id},
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
            await create_test_user(client)
            broker_id = await create_test_broker(client)

            # Upload a file
            files = {"file": ("info_test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                data={"broker_id": broker_id},
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
            await create_test_user(client)
            response = await client.get(
                f"{API_BASE}/brokers/import/files/nonexistent-uuid",
                timeout=TIMEOUT,
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_file(self, test_server, sample_csv_content):
        """FS-007: Delete a file."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)

            # Upload a file
            files = {"file": ("delete_test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                data={"broker_id": broker_id},
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

    @pytest.mark.asyncio
    async def test_preview_file_payload(self, test_server, sample_csv_content):
        """FS-008: Structured preview payload for BRIM CSV files."""
        print_section("FS-008: BRIM preview payload")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)

            files = {"file": ("preview.csv", io.BytesIO(sample_csv_content), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                data={"broker_id": broker_id},
                timeout=TIMEOUT,
            )
            file_id = upload_response.json()["file_id"]

            response = await client.get(
                f"{API_BASE}/brokers/import/files/{file_id}/preview",
                timeout=TIMEOUT,
            )

            assert response.status_code == 200, response.text
            data = response.json()
            assert data["preview_type"] == "table"
            assert data["filename"] == "preview.csv"
            assert data["csv_delimiter"] == ","
            assert data["table_rows"][1] == ["2025-01-01", "DEPOSIT", "0", "1000.00", "EUR", "Test deposit"]
            assert "download=false" in data["source_url"]

            print_success("✓ BRIM preview payload returned")

    @pytest.mark.asyncio
    async def test_download_inline_mode(self, test_server, sample_csv_content):
        """FS-009: BRIM download endpoint supports inline rendering."""
        print_section("FS-009: BRIM inline download mode")

        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)

            files = {"file": ("inline.csv", io.BytesIO(sample_csv_content), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                data={"broker_id": broker_id},
                timeout=TIMEOUT,
            )
            file_id = upload_response.json()["file_id"]

            response = await client.get(
                f"{API_BASE}/brokers/import/files/{file_id}/download",
                params={"download": "false"},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200, response.text
            assert response.headers.get("content-type", "").startswith("text/csv")
            assert "inline" in response.headers.get("content-disposition", "").lower()

            print_success("✓ BRIM download endpoint supports inline mode")


# ============================================================================
# CATEGORY 6: API ENDPOINTS TESTS
# ============================================================================


class TestParseEndpoint:
    """Tests for parse endpoint functionality."""

    async def _create_broker_for_test(self, client: httpx.AsyncClient) -> int:
        """Authenticate and create a broker, return broker_id."""
        await create_test_user(client)
        unique_name = f"BRIM_Parse_Test_{uuid.uuid4().hex[:8]}"
        resp = await client.post(
            f"{API_BASE}/brokers",
            json=[{"name": unique_name, "allow_cash_overdraft": True}],
            timeout=TIMEOUT,
        )
        assert resp.status_code == 200, f"Failed to create broker: {resp.text}"
        return resp.json()["results"][0]["broker_id"]

    @pytest.mark.asyncio
    async def test_parse_file_success(self, test_server, sample_csv_content):
        """API-009: Parse file successfully."""
        async with httpx.AsyncClient() as client:
            broker_id = await self._create_broker_for_test(client)

            # Upload file
            files = {"file": ("parse_test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                data={"broker_id": broker_id},
                timeout=TIMEOUT,
            )
            file_id = upload_response.json()["file_id"]

            # Parse file
            parse_response = await client.post(
                f"{API_BASE}/brokers/import/files/{file_id}/parse",
                json={
                    "plugin_code": "broker_generic_csv",
                    "broker_id": broker_id,
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
    async def test_parse_returns_asset_mappings(self, test_server, sample_csv_with_assets):
        """API-010: Parse returns asset mappings for transactions with assets."""
        async with httpx.AsyncClient() as client:
            broker_id = await self._create_broker_for_test(client)

            # Upload file with assets
            files = {"file": ("assets_test.csv", io.BytesIO(sample_csv_with_assets), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                data={"broker_id": broker_id},
                timeout=TIMEOUT,
            )
            file_id = upload_response.json()["file_id"]

            # Parse
            parse_response = await client.post(
                f"{API_BASE}/brokers/import/files/{file_id}/parse",
                json={
                    "plugin_code": "broker_generic_csv",
                    "broker_id": broker_id,
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
    async def test_parse_returns_duplicates_report(self, test_server, sample_csv_content):
        """API-011: Parse returns duplicates report."""
        async with httpx.AsyncClient() as client:
            broker_id = await self._create_broker_for_test(client)

            # Upload file
            files = {"file": ("dup_test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                data={"broker_id": broker_id},
                timeout=TIMEOUT,
            )
            file_id = upload_response.json()["file_id"]

            # Parse
            parse_response = await client.post(
                f"{API_BASE}/brokers/import/files/{file_id}/parse",
                json={
                    "plugin_code": "broker_generic_csv",
                    "broker_id": broker_id,
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
    async def test_parse_file_not_found(self, test_server):
        """API-012: 404 when parsing non-existent file."""
        async with httpx.AsyncClient() as client:
            broker_id = await self._create_broker_for_test(client)

            response = await client.post(
                f"{API_BASE}/brokers/import/files/nonexistent-uuid/parse",
                json={
                    "plugin_code": "broker_generic_csv",
                    "broker_id": broker_id,
                },
                timeout=TIMEOUT,
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_parse_invalid_plugin(self, test_server, sample_csv_content):
        """API-013: 400 for invalid plugin code."""
        async with httpx.AsyncClient() as client:
            broker_id = await self._create_broker_for_test(client)

            # Upload file
            files = {"file": ("plugin_test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                data={"broker_id": broker_id},
                timeout=TIMEOUT,
            )
            file_id = upload_response.json()["file_id"]

            # Parse with invalid plugin
            response = await client.post(
                f"{API_BASE}/brokers/import/files/{file_id}/parse",
                json={
                    "plugin_code": "nonexistent_plugin",
                    "broker_id": broker_id,
                },
                timeout=TIMEOUT,
            )

            assert response.status_code == 400
            assert "plugin" in response.json()["detail"].lower()


class TestDuplicateCheckEndpoint:
    """Tests for POST /brokers/import/duplicates.

    ``/parse`` computes its duplicate report on the plugin's raw output, which goes stale
    the moment the user edits anything — and a row the plugin misread is exactly the row
    the user edits. This endpoint re-runs the comparison on the transactions in their
    current state, so what gets compared is what will actually be imported.
    """

    async def _create_broker_for_test(self, client: httpx.AsyncClient) -> int:
        await create_test_user(client)
        unique_name = f"BRIM_Dup_Test_{uuid.uuid4().hex[:8]}"
        resp = await client.post(
            f"{API_BASE}/brokers",
            json=[{"name": unique_name, "allow_cash_overdraft": True}],
            timeout=TIMEOUT,
        )
        assert resp.status_code == 200, f"Failed to create broker: {resp.text}"
        return resp.json()["results"][0]["broker_id"]

    async def _upload_and_parse(self, client: httpx.AsyncClient, broker_id: int, content: bytes, name: str) -> dict:
        files = {"file": (name, io.BytesIO(content), "text/csv")}
        upload = await client.post(
            f"{API_BASE}/brokers/import/upload",
            files=files,
            data={"broker_id": broker_id},
            timeout=TIMEOUT,
        )
        assert upload.status_code == 200, upload.text
        file_id = upload.json()["file_id"]
        parsed = await client.post(
            f"{API_BASE}/brokers/import/files/{file_id}/parse",
            json={"plugin_code": "broker_generic_csv", "broker_id": broker_id},
            timeout=TIMEOUT,
        )
        assert parsed.status_code == 200, parsed.text
        return parsed.json()

    @pytest.mark.asyncio
    async def test_duplicates_endpoint_matches_parse_on_untouched_data(self, test_server, sample_csv_content):
        """API-014: With nothing edited, the standalone check agrees with /parse."""
        async with httpx.AsyncClient() as client:
            broker_id = await self._create_broker_for_test(client)
            parse_data = await self._upload_and_parse(client, broker_id, sample_csv_content, "dup_endpoint.csv")

            response = await client.post(
                f"{API_BASE}/brokers/import/duplicates",
                json={
                    "broker_id": broker_id,
                    "transactions": parse_data["transactions"],
                    "asset_mappings": parse_data["asset_mappings"],
                },
                timeout=TIMEOUT,
            )

            assert response.status_code == 200, response.text
            report = response.json()
            assert sorted(report["tx_unique_indices"]) == sorted(parse_data["duplicates"]["tx_unique_indices"])
            assert len(report["tx_likely_duplicates"]) == len(parse_data["duplicates"]["tx_likely_duplicates"])
            assert len(report["tx_possible_duplicates"]) == len(parse_data["duplicates"]["tx_possible_duplicates"])

    @pytest.mark.asyncio
    async def test_duplicates_endpoint_reflects_edits(self, test_server):
        """API-015: Editing a transaction changes the verdict — the whole point.

        The transactions are imported, then re-checked: they now collide with the DB.
        Moving one of them to a different date must clear *that one* and only that one,
        proving the report is computed on the submitted state rather than on whatever
        the plugin happened to produce at parse time.
        """
        csv_content = b"""date,type,quantity,amount,currency,description
2025-03-01,DEPOSIT,0,4000.00,EUR,Dup check deposit
2025-03-02,WITHDRAWAL,0,-250.00,EUR,Dup check withdrawal
"""
        async with httpx.AsyncClient() as client:
            broker_id = await self._create_broker_for_test(client)
            parse_data = await self._upload_and_parse(client, broker_id, csv_content, "dup_edit.csv")
            transactions = parse_data["transactions"]
            assert len(transactions) == 2
            assert len(parse_data["duplicates"]["tx_unique_indices"]) == 2

            commit = await client.post(
                f"{API_BASE}/transactions/commit",
                json={"creates": transactions},
                timeout=TIMEOUT,
            )
            assert commit.status_code == 200, commit.text
            assert commit.json()["committed"] is True

            unchanged = await client.post(
                f"{API_BASE}/brokers/import/duplicates",
                json={"broker_id": broker_id, "transactions": transactions},
                timeout=TIMEOUT,
            )
            assert unchanged.status_code == 200, unchanged.text
            flagged = unchanged.json()
            flagged_rows = {c["tx_row_index"] for c in flagged["tx_likely_duplicates"] + flagged["tx_possible_duplicates"]}
            assert flagged_rows == {0, 1}, f"Both rows should now collide with the DB, got {flagged}"

            edited = [dict(tx) for tx in transactions]
            edited[1]["date"] = "2025-09-30"
            after_edit = await client.post(
                f"{API_BASE}/brokers/import/duplicates",
                json={"broker_id": broker_id, "transactions": edited},
                timeout=TIMEOUT,
            )
            assert after_edit.status_code == 200, after_edit.text
            report = after_edit.json()
            still_flagged = {c["tx_row_index"] for c in report["tx_likely_duplicates"] + report["tx_possible_duplicates"]}
            assert still_flagged == {0}, f"Only the untouched row should stay flagged, got {report}"
            assert 1 in report["tx_unique_indices"]

    @pytest.mark.asyncio
    async def test_duplicates_endpoint_rejects_a_buy_without_an_instrument(self, test_server):
        """API-017: the contract that forces the frontend to filter unresolved rows.

        The payload is validated as real transactions, so a BUY with no ``asset_id`` is
        refused outright. One unresolved instrument in a 200-row import used to fail the
        whole re-check with a 422, and the wizard fell back — silently — on the verdict
        computed *before* the user's corrections. The frontend now leaves such rows out of
        the question entirely; this test is why. A row with no instrument could not match
        anything anyway: there is nothing for the comparison to key on.
        """
        async with httpx.AsyncClient() as client:
            broker_id = await self._create_broker_for_test(client)

            response = await client.post(
                f"{API_BASE}/brokers/import/duplicates",
                json={
                    "broker_id": broker_id,
                    "transactions": [
                        {
                            "broker_id": broker_id,
                            "type": "BUY",
                            "date": "2025-04-01",
                            "quantity": "10",
                            "cash": {"code": "EUR", "amount": "-1000"},
                        }
                    ],
                },
                timeout=TIMEOUT,
            )

            assert response.status_code == 422, f"Expected 422 for an instrument-less BUY, got {response.status_code}: {response.text}"

    @pytest.mark.asyncio
    async def test_duplicates_endpoint_accepts_cash_rows_without_an_instrument(self, test_server):
        """API-018: the other half of the same contract.

        The frontend keeps a row whose *type* does not require an instrument. If the
        endpoint refused those too, the filter would have to drop everything and the
        re-check would never run on a cash-only file.
        """
        async with httpx.AsyncClient() as client:
            broker_id = await self._create_broker_for_test(client)

            response = await client.post(
                f"{API_BASE}/brokers/import/duplicates",
                json={
                    "broker_id": broker_id,
                    "transactions": [
                        {
                            "broker_id": broker_id,
                            "type": "DEPOSIT",
                            "date": "2025-04-02",
                            "quantity": "0",
                            "cash": {"code": "EUR", "amount": "500"},
                        }
                    ],
                },
                timeout=TIMEOUT,
            )

            assert response.status_code == 200, response.text
            assert response.json()["tx_unique_indices"] == [0]

    @pytest.mark.asyncio
    async def test_duplicates_endpoint_retyping_a_row_changes_what_it_collides_with(self, test_server):
        """API-019: the defect that started P1-bis, reduced to its API core.

        A Crédit Agricole ``COMPRAVENDITA`` row reaches the comparison as a cash
        withdrawal with no instrument, and is therefore compared against *cash
        movements*. Retyped into the purchase it always was, it must be compared against
        *purchases* instead. The verdict is a function of the submitted state, not of
        what the plugin first guessed.
        """
        async with httpx.AsyncClient() as client:
            broker_id = await self._create_broker_for_test(client)

            asset_resp = await client.post(
                f"{API_BASE}/assets",
                json=[{"display_name": f"BTP_dup_{uuid.uuid4().hex[:6]}", "currency": "EUR", "asset_type": "BOND"}],
                timeout=TIMEOUT,
            )
            assert asset_resp.status_code in (200, 201), asset_resp.text
            asset_id = asset_resp.json()["results"][0]["asset_id"]

            commit = await client.post(
                f"{API_BASE}/transactions/commit",
                json={
                    "creates": [
                        {"broker_id": broker_id, "type": "DEPOSIT", "date": "2025-05-01", "quantity": "0", "cash": {"code": "EUR", "amount": "5000"}},
                        {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2025-05-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                    ]
                },
                timeout=TIMEOUT,
            )
            assert commit.status_code == 200, commit.text
            assert commit.json()["committed"] is True

            misread = {"broker_id": broker_id, "type": "WITHDRAWAL", "date": "2025-05-02", "quantity": "0", "cash": {"code": "EUR", "amount": "-1000"}}
            before = await client.post(
                f"{API_BASE}/brokers/import/duplicates",
                json={"broker_id": broker_id, "transactions": [misread]},
                timeout=TIMEOUT,
            )
            assert before.status_code == 200, before.text
            assert before.json()["tx_unique_indices"] == [0], "a withdrawal must not collide with a purchase"

            corrected = {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2025-05-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}}
            after = await client.post(
                f"{API_BASE}/brokers/import/duplicates",
                json={"broker_id": broker_id, "transactions": [corrected]},
                timeout=TIMEOUT,
            )
            assert after.status_code == 200, after.text
            report = after.json()
            flagged = {c["tx_row_index"] for c in report["tx_likely_duplicates"] + report["tx_possible_duplicates"]}
            assert flagged == {0}, f"the corrected row must now be seen as already imported, got {report}"

    @pytest.mark.asyncio
    async def test_duplicates_endpoint_denies_foreign_broker(self, test_server, sample_csv_content):
        """API-016: A user without EDITOR access on the broker cannot probe it."""
        async with httpx.AsyncClient() as client:
            broker_id = await self._create_broker_for_test(client)
            parse_data = await self._upload_and_parse(client, broker_id, sample_csv_content, "dup_access.csv")

        async with httpx.AsyncClient() as other_client:
            await create_test_user(other_client)
            response = await other_client.post(
                f"{API_BASE}/brokers/import/duplicates",
                json={"broker_id": broker_id, "transactions": parse_data["transactions"]},
                timeout=TIMEOUT,
            )
            assert response.status_code == 403, response.text


class TestPluginsEndpoint:
    """Tests for plugins listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_plugins(self, test_server):
        """API-008: List available plugins."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
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
# CATEGORY 7: MULTI-USER BRIM TESTS
# ============================================================================


class TestMultiUserBRIM:
    """Tests for multi-user BRIM functionality."""

    @pytest.mark.asyncio
    async def test_upload_requires_broker_id(self, test_server, sample_csv_content):
        """MU-001: Upload fails without broker_id."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            files = {"file": ("test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            response = await client.post(
                f"{API_BASE}/brokers/import/upload",  # No broker_id
                files=files,
                timeout=TIMEOUT,
            )

            # Should fail with 422 (missing required param)
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_stores_user_and_broker(self, test_server, sample_csv_content):
        """MU-002: Upload stores user_id and broker_id correctly."""
        async with httpx.AsyncClient() as client:
            user_id = await create_test_user(client)
            broker_id = await create_test_broker(client)

            files = {"file": ("test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                data={"broker_id": broker_id},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()

            assert data["uploaded_by_user_id"] == user_id
            assert data["target_broker_id"] == broker_id

    @pytest.mark.asyncio
    async def test_list_files_filter_by_broker(self, test_server, sample_csv_content):
        """MU-003: List files can filter by broker_ids."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker1 = await create_test_broker(client)
            broker2 = await create_test_broker(client)

            # Upload to broker1
            files = {"file": ("b1.csv", io.BytesIO(sample_csv_content), "text/csv")}
            await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                data={"broker_id": broker1},
                timeout=TIMEOUT,
            )

            # Upload to broker2
            files = {"file": ("b2.csv", io.BytesIO(sample_csv_content), "text/csv")}
            await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                data={"broker_id": broker2},
                timeout=TIMEOUT,
            )

            # List only broker1 files
            response = await client.get(
                f"{API_BASE}/brokers/import/files?broker_ids={broker1}",
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()

            # Should only contain broker1 files
            for file_info in data:
                if file_info.get("target_broker_id"):
                    assert file_info["target_broker_id"] == broker1

    @pytest.mark.asyncio
    async def test_upload_requires_broker_access(self, test_server, sample_csv_content):
        """MU-004: Upload fails if user has no access to broker."""
        async with httpx.AsyncClient() as client:
            # User1 creates broker
            await create_test_user(client)
            broker_id = await create_test_broker(client)

        # User2 tries to upload to User1's broker
        async with httpx.AsyncClient() as client2:
            await create_test_user(client2)  # Different user

            files = {"file": ("test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            response = await client2.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                data={"broker_id": broker_id},
                timeout=TIMEOUT,
            )

            # Should fail with 403 (no access)
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_cannot_upload(self, test_server, sample_csv_content):
        """MU-005: VIEWER role cannot upload files."""
        async with httpx.AsyncClient() as client:
            # User1 creates broker
            await create_test_user(client)
            _broker_id = await create_test_broker(client)

        # User2 becomes VIEWER on broker1's broker
        async with httpx.AsyncClient() as client2:
            _user2_id = await create_test_user(client2)

        # User1 adds User2 as VIEWER
        async with httpx.AsyncClient() as client:
            # Re-login as User1
            await create_test_user(client)  # Creates new user, we need to use original
            # Note: This test requires admin or broker owner to add access
            # For simplicity, we test that VIEWER cannot upload by checking the error
            # The add_access endpoint is tested separately

        # User2 tries to upload (even if they somehow got VIEWER access)
        # Since we can't easily add VIEWER in test, we just verify upload requires EDITOR+
        # The test_upload_requires_broker_access already covers "no access" case
        # This test would need broker access management to properly test VIEWER denial

    @pytest.mark.asyncio
    async def test_parse_caches_result(self, test_server, sample_csv_content):
        """MU-006: Parse result is cached for subsequent retrieval."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)

            # Upload file
            files = {"file": ("cache_test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                data={"broker_id": broker_id},
                timeout=TIMEOUT,
            )
            assert upload_response.status_code == 200
            file_id = upload_response.json()["file_id"]

            # Parse file
            parse_response = await client.post(
                f"{API_BASE}/brokers/import/files/{file_id}/parse",
                json={
                    "plugin_code": "broker_generic_csv",
                    "broker_id": broker_id,
                },
                timeout=TIMEOUT,
            )
            assert parse_response.status_code == 200
            parse_data = parse_response.json()

            # Get file info - should have cached result
            file_response = await client.get(
                f"{API_BASE}/brokers/import/files/{file_id}",
                timeout=TIMEOUT,
            )
            assert file_response.status_code == 200
            file_data = file_response.json()

            # last_parse_result should contain the cached data
            assert file_data.get("last_parse_result") is not None
            cached = file_data["last_parse_result"]
            assert "transactions" in cached
            assert len(cached["transactions"]) == len(parse_data["transactions"])

    @pytest.mark.asyncio
    async def test_get_last_parse_endpoint(self, test_server, sample_csv_content):
        """MU-007: GET /files/{id}/last-parse returns cached parse result."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)

            # Upload file
            files = {"file": ("last_parse_test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                data={"broker_id": broker_id},
                timeout=TIMEOUT,
            )
            assert upload_response.status_code == 200
            file_id = upload_response.json()["file_id"]

            # Before parse - should return null/empty
            last_parse_before = await client.get(
                f"{API_BASE}/brokers/import/files/{file_id}/last-parse",
                timeout=TIMEOUT,
            )
            assert last_parse_before.status_code == 200
            # Before parsing, result should be null
            assert last_parse_before.json() is None

            # Parse file
            parse_response = await client.post(
                f"{API_BASE}/brokers/import/files/{file_id}/parse",
                json={
                    "plugin_code": "broker_generic_csv",
                    "broker_id": broker_id,
                },
                timeout=TIMEOUT,
            )
            assert parse_response.status_code == 200

            # After parse - should return cached result
            last_parse_after = await client.get(
                f"{API_BASE}/brokers/import/files/{file_id}/last-parse",
                timeout=TIMEOUT,
            )
            assert last_parse_after.status_code == 200
            cached = last_parse_after.json()

            assert cached is not None
            assert "transactions" in cached
            assert "warnings" in cached

    @pytest.mark.asyncio
    async def test_editor_can_upload_and_parse(self, test_server, sample_csv_content):
        """MU-008: EDITOR role can upload and parse files."""
        async with httpx.AsyncClient() as client:
            # Create owner user and broker
            owner_id = await create_test_user(client)
            broker_id = await create_test_broker(client)

            # Add another user as EDITOR
            # First create user2
            async with httpx.AsyncClient() as client2:
                user2_id = await create_test_user(client2)

            # Owner adds user2 as EDITOR via bulk PUT
            add_access_response = await client.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[
                    {"user_id": owner_id, "role": "OWNER", "share_percentage": 1.0},
                    {"user_id": user2_id, "role": "EDITOR", "share_percentage": 0},
                ],
                timeout=TIMEOUT,
            )
            assert add_access_response.status_code == 200

        # User2 (EDITOR) uploads file
        async with httpx.AsyncClient() as client2:
            # Login as user2
            # Note: We created a fresh client, need to re-login
            # Since create_test_user creates AND logs in, we need to login again
            # Actually, we need to track the credentials. For now, create new user
            # This is a limitation - we'd need to refactor test helpers

            # For this test, let's verify the access was added correctly
            # by checking the access list
            pass  # Skip for now - requires test refactoring

    @pytest.mark.asyncio
    async def test_download_file(self, test_server, sample_csv_content):
        """MU-009: Download file endpoint works correctly."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)

            # Upload file
            files = {"file": ("download_test.csv", io.BytesIO(sample_csv_content), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                data={"broker_id": broker_id},
                timeout=TIMEOUT,
            )
            assert upload_response.status_code == 200
            file_id = upload_response.json()["file_id"]

            # Download file
            download_response = await client.get(
                f"{API_BASE}/brokers/import/files/{file_id}/download",
                timeout=TIMEOUT,
            )
            assert download_response.status_code == 200

            # Content should match uploaded file
            assert download_response.content == sample_csv_content


# ============================================================================
# CATEGORY 8: REPORT SETS (phase A2) — upload batch_id, /sets/*, parse fields
# ============================================================================
#
# Under the runner the test backend is a process of its own, and it parses through
# a process pool: the test-only report-set plugin of test_brim_report_sets.py
# cannot be registered there. What a set contains (roles, missing periods, H0,
# reuse, two brokers, the parse guard) is therefore tested at service level. Here,
# what HTTP shows without a report-set plugin: the upload batch_id, the routes, the
# EDITOR permission, body validation, error codes, the unchanged single-file parse.

SET_ENDPOINTS = ("preview", "combine")


def _detail_text(response: httpx.Response) -> str:
    """An error response's ``detail`` as text, whatever its shape (a string, or an object carrying a code)."""
    try:
        detail = response.json().get("detail")
    except ValueError:
        return response.text
    return detail if isinstance(detail, str) else json.dumps(detail)


async def _upload_csv(client: httpx.AsyncClient, broker_id: int, content: bytes, filename: str, **form: str) -> httpx.Response:
    """``POST /upload`` of one CSV, with any extra form field (e.g. ``batch_id``)."""
    files = {"file": (filename, io.BytesIO(content), "text/csv")}
    return await client.post(f"{API_BASE}/brokers/import/upload", files=files, data={"broker_id": broker_id, **form}, timeout=TIMEOUT)


async def _files_on(client: httpx.AsyncClient, broker_id: int) -> list:
    """The BRIM files stored on one broker; the list also returns legacy files with no broker, so the target is filtered."""
    response = await client.get(f"{API_BASE}/brokers/import/files", params={"broker_ids": broker_id}, timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    return [info for info in response.json() if info.get("target_broker_id") == broker_id]


def _set_url(endpoint: str) -> str:
    return f"{API_BASE}/brokers/import/sets/{endpoint}"


class TestUploadBatchId:
    """A2 — ``POST /upload`` takes an optional ``batch_id`` form field: the files of one upload action form one report set (D-S22)."""

    @pytest.mark.asyncio
    async def test_batch_id_is_stored_and_returned(self, test_server, sample_csv_content):
        """RS-001: two files uploaded with one batch_id carry it in the upload response, in GET /files/{id} and in GET /files."""
        print_section("RS-001: upload batch_id is stored and returned")
        batch = str(uuid.uuid4())
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)

            uploads = [await _upload_csv(client, broker_id, sample_csv_content, name, batch_id=batch) for name in ("batch_custody.csv", "batch_cash.csv")]

            assert [response.status_code for response in uploads] == [200, 200], [response.text for response in uploads]
            file_ids = [response.json()["file_id"] for response in uploads]
            assert [response.json()["batch_id"] for response in uploads] == [batch, batch]
            for file_id in file_ids:
                detail = await client.get(f"{API_BASE}/brokers/import/files/{file_id}", timeout=TIMEOUT)
                assert detail.status_code == 200, detail.text
                assert detail.json()["batch_id"] == batch
            listed = {info["file_id"]: info for info in await _files_on(client, broker_id)}
            assert {file_id: listed[file_id]["batch_id"] for file_id in file_ids} == dict.fromkeys(file_ids, batch)
            print_success("✓ batch_id stored and returned")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("bad_batch_id", ["not-a-uuid", "1234", "0b6f7a3e-5d1c-4c1e-9a53-2f0e4d9b7c1"], ids=["words", "digits", "one-hex-digit-short"])
    async def test_invalid_batch_id_is_rejected(self, test_server, sample_csv_content, bad_batch_id):
        """RS-002: a batch_id that is not a UUID answers 422, and nothing is stored."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            filename = f"bad_batch_{uuid.uuid4().hex[:8]}.csv"

            response = await _upload_csv(client, broker_id, sample_csv_content, filename, batch_id=bad_batch_id)

            assert response.status_code == 422, f"batch_id={bad_batch_id!r}: {response.status_code} {response.text}"
            assert filename not in {info["filename"] for info in await _files_on(client, broker_id)}

    @pytest.mark.asyncio
    async def test_upload_without_batch_id_has_none(self, test_server, sample_csv_content):
        """RS-003 — retro-compatibility guard (passes before and after A2): an old client sends no batch_id, and the file is an upload of its own."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)

            response = await _upload_csv(client, broker_id, sample_csv_content, "no_batch.csv")

            assert response.status_code == 200, response.text
            assert "batch_id" in response.json() and response.json()["batch_id"] is None


class TestReportSetEndpoints:
    """A2 — ``POST /sets/preview`` and ``POST /sets/combine``: routing, EDITOR permission, body validation, error codes.

    Every ``BRIMSetError`` maps to its status with its code in ``detail``. The code
    is asserted, not only the status: a bare 404 is also what a missing route says.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", SET_ENDPOINTS)
    async def test_unknown_plugin_is_404_with_its_code(self, test_server, endpoint):
        """RS-004: an unknown plugin code answers 404 with ``plugin_not_found``."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            body = {"broker_id": broker_id, "plugin_code": f"no_such_plugin_{uuid.uuid4().hex[:6]}", "batch_id": str(uuid.uuid4())}

            response = await client.post(_set_url(endpoint), json=body, timeout=TIMEOUT)

            assert response.status_code == 404, response.text
            assert "plugin_not_found" in _detail_text(response), response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", SET_ENDPOINTS)
    async def test_single_file_plugin_is_400_with_its_code(self, test_server, endpoint):
        """RS-005: a plugin without report roles cannot make a set: 400 with ``plugin_not_a_set``."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            body = {"broker_id": broker_id, "plugin_code": "broker_generic_csv", "batch_id": str(uuid.uuid4())}

            response = await client.post(_set_url(endpoint), json=body, timeout=TIMEOUT)

            assert response.status_code == 400, response.text
            assert "plugin_not_a_set" in _detail_text(response), response.text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", SET_ENDPOINTS)
    async def test_editor_role_is_required(self, test_server, endpoint):
        """RS-006: a VIEWER of the broker and a user without access get 403; the OWNER, with the same body, reaches the handler."""
        async with httpx.AsyncClient() as owner, httpx.AsyncClient() as viewer, httpx.AsyncClient() as stranger:
            owner_id = await create_test_user(owner)
            viewer_id = await create_test_user(viewer)
            await create_test_user(stranger)
            broker_id = await create_test_broker(owner)
            access = await owner.put(
                f"{API_BASE}/brokers/{broker_id}/access",
                json=[{"user_id": owner_id, "role": "OWNER", "share_percentage": 1.0}, {"user_id": viewer_id, "role": "VIEWER", "share_percentage": 0}],
                timeout=TIMEOUT,
            )
            assert access.status_code == 200, access.text
            body = {"broker_id": broker_id, "plugin_code": "broker_generic_csv", "batch_id": str(uuid.uuid4())}

            control = await owner.post(_set_url(endpoint), json=body, timeout=TIMEOUT)
            assert control.status_code == 400 and "plugin_not_a_set" in _detail_text(control), f"presence barrier, the owner reaches the handler: {control.status_code} {control.text}"
            for who, client in (("viewer", viewer), ("stranger", stranger)):
                response = await client.post(_set_url(endpoint), json=body, timeout=TIMEOUT)
                assert response.status_code == 403, f"{who}: {response.status_code} {response.text}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", SET_ENDPOINTS)
    @pytest.mark.parametrize(
        ("drop", "add", "field"),
        [
            pytest.param("batch_id", {}, "batch_id", id="missing-batch_id"),
            pytest.param(None, {"broker_id": 0}, "broker_id", id="broker_id-zero"),
            pytest.param(None, {"file_ids": ["f-1"]}, "file_ids", id="unknown-key"),
        ],
    )
    async def test_body_is_validated(self, test_server, endpoint, drop, add, field):
        """RS-007: ``BRIMSetRequest`` is strict: a missing field, a non-positive broker, an unknown key answer 422 naming the field."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            body = {"broker_id": broker_id, "plugin_code": "broker_generic_csv", "batch_id": str(uuid.uuid4())}
            body.pop(drop, None)
            body.update(add)

            response = await client.post(_set_url(endpoint), json=body, timeout=TIMEOUT)

            assert response.status_code == 422, response.text
            errors = response.json().get("detail")
            assert isinstance(errors, list) and any(error.get("loc", [])[-1:] == [field] for error in errors), errors


class TestParseReportSetFields:
    """A2 — ``POST /files/{id}/parse`` for a single-file plugin: unchanged, apart from the empty report-set fields."""

    @pytest.mark.asyncio
    async def test_single_file_parse_has_no_truth_points(self, test_server, sample_csv_content):
        """RS-008 — retro-compatibility guard (passes before and after A2): a generic CSV parses as before, into ``parsed``;
        the response and its cache carry ``checkpoints: []``, ``verifications: []`` and ``history_start: null``."""
        empty = {"checkpoints": [], "verifications": [], "history_start": None}
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            upload = await _upload_csv(client, broker_id, sample_csv_content, "single_file_parse.csv")
            assert upload.status_code == 200, upload.text
            file_id = upload.json()["file_id"]

            parsed = await client.post(f"{API_BASE}/brokers/import/files/{file_id}/parse", json={"plugin_code": "broker_generic_csv", "broker_id": broker_id}, timeout=TIMEOUT)

            assert parsed.status_code == 200, parsed.text
            data = parsed.json()
            assert len(data["transactions"]) == 2
            assert {key: data[key] for key in empty} == empty
            cached = await client.get(f"{API_BASE}/brokers/import/files/{file_id}/last-parse", timeout=TIMEOUT)
            assert cached.status_code == 200, cached.text
            assert {key: cached.json()[key] for key in empty} == empty
            info = await client.get(f"{API_BASE}/brokers/import/files/{file_id}", timeout=TIMEOUT)
            assert info.json()["status"] == "parsed"


# ============================================================================
# CATEGORY 9: GAP-FIX (phase A3) — POST /brokers/import/gap-fix
# ============================================================================
#
# The gap-fix accepts any registered plugin, because it reads only the plugin's
# history tag and name: unlike the set endpoints, its behaviour is proven over
# HTTP, with the generic CSV plugin (history tag "generic_csv"). Each test builds
# its own broker (and assets) through the API, writes LibreFolio's side with
# POST /transactions/commit, and deletes what it created. The complete rule set
# (tolerance, positions, explanation, three checkpoints, scenario 8) is tested
# at service level, in test_services/test_brim_gap_fix.py.

GAP_FIX_URL = f"{API_BASE}/brokers/import/gap-fix"
GAP_FIX_PLUGIN = "broker_generic_csv"
GAP_FIX_TAGS = ["import", "generic_csv", "gap_fix"]
GAP_FIX_PLUGIN_NAME = "Generic CSV"
GAP_FIX_EVE = "2024-12-31"
COST_TODO = ("cost_basis_override", "blocker", "gap_fix_cost")


def _route_missing(response: httpx.Response) -> bool:
    """The answer comes from the router, not from a handler: 404 ``Not Found``, or 405 because only the SPA catch-all GET matches the path."""
    return response.status_code == 405 or (response.status_code == 404 and _detail_text(response) == "Not Found")


async def _gap_fix(client: httpx.AsyncClient, body: dict) -> httpx.Response:
    """``POST /gap-fix``; while the route does not exist, the test fails saying so instead of on a status code."""
    response = await client.post(GAP_FIX_URL, json=body, timeout=TIMEOUT)
    if _route_missing(response):
        pytest.fail(f"POST /brokers/import/gap-fix does not exist yet (BRIM report sets, phase A3): {response.status_code} {response.text}", pytrace=False)
    return response


def _gap_fix_body(broker_id: int, **fields) -> dict:
    """A ``BRIMGapFixRequest`` body for the generic CSV plugin; ``fields`` add to it or override it."""
    return {"broker_id": broker_id, "plugin_code": GAP_FIX_PLUGIN, **fields}


def _checkpoint_json(kind: str = "opening", *, cash: dict = None, positions: list = ()) -> dict:
    """A checkpoint dated ``GAP_FIX_EVE``; ``cash`` is ``{currency: amount}``."""
    return {"as_of": GAP_FIX_EVE, "kind": kind, "cash": [{"currency": currency, "amount": amount} for currency, amount in (cash or {}).items()], "positions": list(positions)}


def _verification_json(as_of: str, currency: str, amount: str) -> dict:
    return {"as_of": as_of, "cash": [{"currency": currency, "amount": amount}]}


def _cash_movement(broker_id: int, tx_type: str, day: str, amount: str, currency: str = "EUR") -> dict:
    """A DEPOSIT or WITHDRAWAL as ``/transactions/commit`` and ``BRIMGapFixRequest`` both take it."""
    return {"broker_id": broker_id, "type": tx_type, "date": day, "quantity": "0", "cash": {"code": currency, "amount": amount}}


async def _commit_creates(client: httpx.AsyncClient, *creates: dict) -> list:
    """Save rows through ``POST /transactions/commit``; returns their ids, in order."""
    response = await client.post(f"{API_BASE}/transactions/commit", json={"creates": list(creates)}, timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data.get("committed") is True, response.text
    ids_by_index = {result["index"]: result["ids"] for result in data["results"]}
    return [ids_by_index[index][0] for index in range(len(creates))]


async def _broker_tx_ids(client: httpx.AsyncClient, broker_id: int) -> set:
    response = await client.get(f"{API_BASE}/transactions", params={"broker_id": broker_id}, timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    return {item["id"] for item in response.json()}


async def _create_gap_fix_asset(client: httpx.AsyncClient) -> int:
    response = await client.post(f"{API_BASE}/assets", json=[{"display_name": f"GapFix_{uuid.uuid4().hex[:10]}", "currency": "EUR", "asset_type": "STOCK"}], timeout=TIMEOUT)
    assert response.status_code in (200, 201), response.text
    return response.json()["results"][0]["asset_id"]


async def _delete_created(client: httpx.AsyncClient, broker_ids: list = (), asset_ids: list = ()) -> None:
    """Whoever writes cleans up: the brokers first (``force``: their transactions go with them), then the assets they held."""
    if broker_ids:
        response = await client.delete(f"{API_BASE}/brokers", params={"ids": list(broker_ids), "force": True}, timeout=TIMEOUT)
        assert response.status_code == 200 and response.json().get("success_count") == len(broker_ids), response.text
    if asset_ids:
        response = await client.delete(f"{API_BASE}/assets", params={"asset_ids": list(asset_ids)}, timeout=TIMEOUT)
        assert response.status_code == 200 and response.json().get("success_count") == len(asset_ids), response.text


def _one(results: list, as_of: str) -> dict:
    """The one result dated ``as_of`` (a checkpoint or a verification)."""
    found = [item for item in results if item["as_of"] == as_of]
    assert len(found) == 1, f"one result expected at {as_of}: {results}"
    return found[0]


def _money_rows(rows: list) -> dict:
    """``{currency: (bank, librefolio, difference)}`` of a result's cash rows, compared as numbers."""
    return {row["currency"]: (Decimal(row["bank"]), Decimal(row["librefolio"]), Decimal(row["difference"])) for row in rows}


def _cash_proposals(result: dict) -> list:
    """``[(type, currency, amount)]`` of a checkpoint's proposals."""
    return [(item["type"], item["cash"]["code"], Decimal(item["cash"]["amount"])) for item in result["proposals"]]


class TestGapFixEndpoint:
    """A3 — ``POST /brokers/import/gap-fix``: what the bank states against what LibreFolio has, and the corrections that close the gap. Writes nothing."""

    @pytest.mark.asyncio
    async def test_first_import_proposes_the_opening_deposit(self, test_server):
        """GF-001: an empty broker and one opening checkpoint: one DEPOSIT dated C, tagged and described for the plugin; nothing is saved."""
        print_section("GF-001: gap-fix on an empty broker proposes the opening deposit")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            try:
                response = await _gap_fix(client, _gap_fix_body(broker_id, checkpoints=[_checkpoint_json(cash={"EUR": "1523.40"})]))

                assert response.status_code == 200, response.text
                data = response.json()
                assert data["verifications"] == []
                result = _one(data["checkpoints"], GAP_FIX_EVE)
                assert result["kind"] == "opening"
                assert _money_rows(result["cash"]) == {"EUR": (Decimal("1523.40"), Decimal("0"), Decimal("1523.40"))}
                assert _cash_proposals(result) == [("DEPOSIT", "EUR", Decimal("1523.40"))]
                proposal = result["proposals"][0]
                assert (proposal["date"], proposal["broker_id"], proposal["tags"]) == (GAP_FIX_EVE, broker_id, GAP_FIX_TAGS)
                assert proposal["description"].startswith(f"Gap-fix {GAP_FIX_EVE}") and GAP_FIX_PLUGIN_NAME in proposal["description"], proposal["description"]
                assert await _broker_tx_ids(client, broker_id) == set(), "the gap-fix only proposes: nothing is saved"
                print_success("✓ opening deposit proposed, nothing saved")
            finally:
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    async def test_matching_state_proposes_nothing(self, test_server):
        """GF-002: LibreFolio already agrees with the bank at C and at V: no proposal, and the verification is ok."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            try:
                await _commit_creates(client, _cash_movement(broker_id, "DEPOSIT", "2024-06-03", "1000"), _cash_movement(broker_id, "WITHDRAWAL", "2024-09-02", "-250"))
                body = _gap_fix_body(broker_id, checkpoints=[_checkpoint_json(cash={"EUR": "750"})], verifications=[_verification_json("2025-01-17", "EUR", "750")])

                response = await _gap_fix(client, body)

                assert response.status_code == 200, response.text
                result = _one(response.json()["checkpoints"], GAP_FIX_EVE)
                assert (result["proposals"], result["todos"]) == ([], [])
                assert _money_rows(result["cash"]) == {"EUR": (Decimal("750"), Decimal("750"), Decimal("0"))}
                verification = _one(response.json()["verifications"], "2025-01-17")
                assert (verification["ok"], _money_rows(verification["cash"])) == (True, {"EUR": (Decimal("750"), Decimal("750"), Decimal("0"))})
            finally:
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    async def test_positions_with_and_without_a_unit_cost(self, test_server):
        """GF-003: an exact position held in part gets an ADJUSTMENT at the known unit cost; a missing minimum without cost gets one and a blocking todo."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            assets = []
            try:
                assets.append(await _create_gap_fix_asset(client))
                assets.append(await _create_gap_fix_asset(client))
                costed, uncosted = assets
                await _commit_creates(client, {"broker_id": broker_id, "asset_id": costed, "type": "BUY", "date": "2024-06-03", "quantity": "6", "cash": {"code": "EUR", "amount": "-60"}})
                positions = [{"asset_id": costed, "quantity": "10", "exactness": "exact", "unit_cost": {"code": "EUR", "amount": "12.50"}}, {"asset_id": uncosted, "quantity": "2", "exactness": "at_least"}]

                response = await _gap_fix(client, _gap_fix_body(broker_id, checkpoints=[_checkpoint_json(positions=positions)]))

                assert response.status_code == 200, response.text
                result = _one(response.json()["checkpoints"], GAP_FIX_EVE)
                rows = {row["asset_id"]: (row["exactness"], Decimal(row["bank"]), Decimal(row["librefolio"]), Decimal(row["difference"])) for row in result["positions"]}
                assert rows == {costed: ("exact", Decimal("10"), Decimal("6"), Decimal("4")), uncosted: ("at_least", Decimal("2"), Decimal("0"), Decimal("2"))}
                proposals = {item["asset_id"]: item for item in result["proposals"]}
                assert len(result["proposals"]) == 2 and set(proposals) == {costed, uncosted}, result["proposals"]
                cost = proposals[costed]["cost_basis_override"]
                assert (proposals[costed]["type"], Decimal(proposals[costed]["quantity"]), cost and cost["code"], cost and Decimal(cost["amount"])) == ("ADJUSTMENT", Decimal("4"), "EUR", Decimal("12.50"))
                assert (proposals[uncosted]["type"], Decimal(proposals[uncosted]["quantity"]), proposals[uncosted]["cost_basis_override"]) == ("ADJUSTMENT", Decimal("2"), None)
                assert [(todo["field"], todo["severity"], todo["reason_code"]) for todo in result["todos"]] == [COST_TODO]
                assert result["proposals"][result["todos"][0]["tx_index"]]["asset_id"] == uncosted
            finally:
                await _delete_created(client, broker_ids=[broker_id], asset_ids=assets)

    @pytest.mark.asyncio
    async def test_pending_deletes_are_honoured(self, test_server):
        """GF-004: a saved row the editor is deleting (``pending_delete_tx_ids``) is left out of LibreFolio's side; nothing is deleted."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            try:
                kept, deleting = await _commit_creates(client, _cash_movement(broker_id, "DEPOSIT", "2024-06-03", "1000"), _cash_movement(broker_id, "DEPOSIT", "2024-07-01", "500"))
                checkpoints = [_checkpoint_json("gap", cash={"EUR": "1000"})]

                counted = await _gap_fix(client, _gap_fix_body(broker_id, checkpoints=checkpoints))
                excluded = await _gap_fix(client, _gap_fix_body(broker_id, checkpoints=checkpoints, pending_delete_tx_ids=[deleting]))

                assert (counted.status_code, excluded.status_code) == (200, 200), (counted.text, excluded.text)
                assert _cash_proposals(_one(counted.json()["checkpoints"], GAP_FIX_EVE)) == [("WITHDRAWAL", "EUR", Decimal("-500"))], "presence barrier: without the pending delete both deposits count"
                result = _one(excluded.json()["checkpoints"], GAP_FIX_EVE)
                assert _money_rows(result["cash"]) == {"EUR": (Decimal("1000"), Decimal("1000"), Decimal("0"))}
                assert result["proposals"] == []
                assert await _broker_tx_ids(client, broker_id) == {kept, deleting}, "the gap-fix deletes nothing either"
            finally:
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    async def test_editor_rows_and_selection_are_counted(self, test_server):
        """GF-005: unsaved rows count up to C, pending in the editor or selected in the wizard; a selected row dated after C does not."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            try:
                body = _gap_fix_body(
                    broker_id,
                    checkpoints=[_checkpoint_json("gap", cash={"EUR": "550"})],
                    pending_creates=[_cash_movement(broker_id, "DEPOSIT", "2024-05-02", "300")],
                    selection=[_cash_movement(broker_id, "DEPOSIT", GAP_FIX_EVE, "200"), _cash_movement(broker_id, "DEPOSIT", "2025-01-02", "999")],
                )

                response = await _gap_fix(client, body)

                assert response.status_code == 200, response.text
                result = _one(response.json()["checkpoints"], GAP_FIX_EVE)
                assert _money_rows(result["cash"]) == {"EUR": (Decimal("550"), Decimal("500"), Decimal("50"))}
                assert _cash_proposals(result) == [("DEPOSIT", "EUR", Decimal("50"))]
            finally:
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    async def test_verification_ok_and_not_ok(self, test_server):
        """GF-006: a verification only compares: ok within a cent, not ok beyond, with the difference; without checkpoints there is nothing to propose."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            try:
                await _commit_creates(client, _cash_movement(broker_id, "DEPOSIT", "2025-01-02", "1000"))
                verifications = [_verification_json("2025-01-17", "EUR", "1000.01"), _verification_json("2025-01-18", "EUR", "1200")]

                response = await _gap_fix(client, _gap_fix_body(broker_id, verifications=verifications))

                assert response.status_code == 200, response.text
                data = response.json()
                assert data["checkpoints"] == []
                within, off = _one(data["verifications"], "2025-01-17"), _one(data["verifications"], "2025-01-18")
                assert (within["ok"], off["ok"]) == (True, False)
                assert _money_rows(off["cash"]) == {"EUR": (Decimal("1200"), Decimal("1000"), Decimal("200"))}
            finally:
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("plugin_code", "owner_status"), [pytest.param(GAP_FIX_PLUGIN, 200, id="registered-plugin"), pytest.param("no_such_plugin_a3", 404, id="unknown-plugin")])
    async def test_editor_role_is_checked_first(self, test_server, plugin_code, owner_status):
        """GF-007: a VIEWER of the broker and a user without access get 403, whatever the plugin; the OWNER, with the same body, reaches the handler."""
        async with httpx.AsyncClient() as owner, httpx.AsyncClient() as viewer, httpx.AsyncClient() as stranger:
            owner_id = await create_test_user(owner)
            viewer_id = await create_test_user(viewer)
            await create_test_user(stranger)
            broker_id = await create_test_broker(owner)
            try:
                access = await owner.put(
                    f"{API_BASE}/brokers/{broker_id}/access",
                    json=[{"user_id": owner_id, "role": "OWNER", "share_percentage": 1.0}, {"user_id": viewer_id, "role": "VIEWER", "share_percentage": 0}],
                    timeout=TIMEOUT,
                )
                assert access.status_code == 200, access.text
                body = _gap_fix_body(broker_id, plugin_code=plugin_code, checkpoints=[_checkpoint_json(cash={"EUR": "100"})])

                control = await _gap_fix(owner, body)

                assert control.status_code == owner_status, f"presence barrier, the owner reaches the handler: {control.status_code} {control.text}"
                for who, client in (("viewer", viewer), ("stranger", stranger)):
                    response = await _gap_fix(client, body)
                    assert response.status_code == 403, f"{who}: {response.status_code} {response.text}"
            finally:
                await _delete_created(owner, broker_ids=[broker_id])

    @pytest.mark.asyncio
    async def test_unknown_plugin_is_404_with_its_code(self, test_server):
        """GF-008: an unknown plugin code answers 404 with ``plugin_not_found``: the code is asserted, a bare 404 is also what a missing route says."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            try:
                body = _gap_fix_body(broker_id, plugin_code=f"no_such_plugin_{uuid.uuid4().hex[:6]}", checkpoints=[_checkpoint_json(cash={"EUR": "100"})])

                response = await _gap_fix(client, body)

                assert response.status_code == 404, response.text
                assert "plugin_not_found" in _detail_text(response), response.text
            finally:
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("drop", "add", "field"),
        [
            pytest.param("plugin_code", {}, "plugin_code", id="missing-plugin_code"),
            pytest.param(None, {"broker_id": 0}, "broker_id", id="broker_id-zero"),
            pytest.param(None, {"batch_id": "0b6f7a3e-5d1c-4c1e-9a53-2f0e4d9b7c10"}, "batch_id", id="unknown-key"),
            pytest.param(None, {"checkpoints": [{"as_of": GAP_FIX_EVE, "kind": "closing"}]}, "kind", id="checkpoint-kind"),
            pytest.param(None, {"pending_delete_tx_ids": ["not-an-id"]}, "pending_delete_tx_ids", id="pending-delete-ids"),
        ],
    )
    async def test_body_is_validated(self, test_server, drop, add, field):
        """GF-009: ``BRIMGapFixRequest`` is strict: a missing field, a non-positive broker, an unknown key, a bad checkpoint or id answer 422 naming the field."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            try:
                body = _gap_fix_body(broker_id)
                body.pop(drop, None)
                body.update(add)

                response = await _gap_fix(client, body)

                assert response.status_code == 422, response.text
                errors = response.json().get("detail")
                assert isinstance(errors, list) and any(field in [str(part) for part in error.get("loc", [])] for error in errors), errors
            finally:
                await _delete_created(client, broker_ids=[broker_id])


# ============================================================================
# CATEGORY 10: THE DANSKE BANK REPORT SET, END TO END (phase B)
# ============================================================================
#
# The first report-set plugin the test backend itself knows, so a whole set can go
# through HTTP: the two synthetic "main" exports uploaded together, preview, combine
# (then reused), a member refused on its own, the combined file parsed, and the
# gap-fix of that parse on a fresh broker. The test deletes the files and the broker
# it created. What a set contains, rule by rule, is in test_external/test_brim_danske_bank.py.
#
# RS-E01 (phase E, plan E.0 point 1) imports the same set on a broker that already holds
# a Danske history (one row tagged ``danske_bank``, before the set): a later import, whose
# first checkpoint closes a gap in that history and must say so (``kind == "gap"``).

DANSKE_CODE = "broker_danske_bank"
DANSKE_SAMPLE_DIR = PROJECT_ROOT / "backend" / "app" / "services" / "brim_providers" / "sample_reports"
DANSKE_MAIN = (("danske_bank-custody.xlsx", "custody"), ("danske_bank-cash.csv", "cash"))
DANSKE_GAP_FIX_TAGS = ["import", "danske_bank", "gap_fix"]
# A row of an earlier Danske import: the plugin's history tag, dated well before the main set's first checkpoint (2020-02-02).
DANSKE_HISTORY_TAGS = ["import", "danske_bank"]
DANSKE_HISTORY_DAY = "2019-06-03"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


async def _upload_sample(client: httpx.AsyncClient, broker_id: int, name: str, batch_id: str) -> httpx.Response:
    """``POST /upload`` of one sample export, with the batch it belongs to."""
    media_type = XLSX_MEDIA_TYPE if name.endswith(".xlsx") else "text/csv"
    files = {"file": (name, io.BytesIO((DANSKE_SAMPLE_DIR / name).read_bytes()), media_type)}
    return await client.post(f"{API_BASE}/brokers/import/upload", files=files, data={"broker_id": broker_id, "batch_id": batch_id}, timeout=TIMEOUT)


async def _require_plugin(client: httpx.AsyncClient, code: str) -> None:
    """Fail, saying so, while the test backend does not have the plugin."""
    response = await client.get(f"{API_BASE}/brokers/import/plugins", timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    if code not in {plugin["code"] for plugin in response.json()}:
        pytest.fail(f"the test backend has no {code} plugin: not implemented yet (BRIM report sets, phase B)", pytrace=False)


async def _delete_files(client: httpx.AsyncClient, file_ids: list) -> None:
    """Whoever uploads cleans up: every file this test stored, before its broker goes."""
    for file_id in file_ids:
        response = await client.delete(f"{API_BASE}/brokers/import/files/{file_id}", timeout=TIMEOUT)
        assert response.status_code in (200, 404), f"{file_id}: {response.status_code} {response.text}"


def _money_list(items: list) -> dict:
    """``{currency: amount}`` of JSON truth-cash entries, compared as numbers."""
    return {item["currency"]: Decimal(item["amount"]) for item in items}


class TestDanskeReportSetEndToEnd:
    """B — the Danske main samples through the report-set API, from the upload to the gap-fix: on a fresh broker (RS-B01), and after a saved history (RS-E01, phase E)."""

    @pytest.mark.asyncio
    async def test_main_set_from_upload_to_gap_fix(self, test_server):
        """RS-B01: preview 2020-02-03…06-26 without gaps; combine, then reuse; a member alone is 422; the combined parse
        brings the opening checkpoint, the verification and H0; the gap-fix proposes the opening deposit and checks the verification."""
        print_section("RS-B01: Danske main set, from upload to gap-fix")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            file_ids = []
            try:
                await _require_plugin(client, DANSKE_CODE)
                batch = str(uuid.uuid4())
                uploaded = {}
                for name, role in DANSKE_MAIN:
                    response = await _upload_sample(client, broker_id, name, batch)
                    assert response.status_code == 200, response.text
                    file_ids.append(response.json()["file_id"])
                    uploaded[role] = response.json()
                    assert (uploaded[role]["batch_id"], DANSKE_CODE in uploaded[role]["compatible_plugins"]) == (batch, True), uploaded[role]
                body = {"broker_id": broker_id, "plugin_code": DANSKE_CODE, "batch_id": batch}

                preview = await client.post(_set_url("preview"), json=body, timeout=TIMEOUT)
                assert preview.status_code == 200, preview.text
                shape = preview.json()
                assert (shape["complete"], shape["missing"], shape["gaps"]) == (True, [], [])
                assert shape["segments"] == [{"start": "2020-02-03", "end": "2020-06-26"}]
                assert {member["file_id"]: (member["role"], member["rows"]) for member in shape["members"]} == {uploaded["custody"]["file_id"]: ("custody", 15), uploaded["cash"]["file_id"]: ("cash", 32)}

                first = await client.post(_set_url("combine"), json=body, timeout=TIMEOUT)
                assert first.status_code == 200, first.text
                combined = first.json()["combined"]
                file_ids.append(combined["file_id"])
                assert first.json()["reused"] is False
                assert (combined["kind"], combined["compatible_plugins"], combined["batch_id"]) == ("combined", [DANSKE_CODE], batch)
                assert combined["filename"] == "Danske Bank — combined 2020-02-03…2020-06-26.csv"
                assert sorted(ref["role"] for ref in combined["derived_from"]) == ["cash", "custody"]
                again = await client.post(_set_url("combine"), json=body, timeout=TIMEOUT)
                assert again.status_code == 200, again.text
                assert (again.json()["reused"], again.json()["combined"]["file_id"]) == (True, combined["file_id"])

                member = uploaded["custody"]["file_id"]
                refused = await client.post(f"{API_BASE}/brokers/import/files/{member}/parse", json={"plugin_code": DANSKE_CODE, "broker_id": broker_id}, timeout=TIMEOUT)
                assert refused.status_code == 422, refused.text
                assert refused.json()["detail"]["code"] == "set_required"
                assert (await client.get(f"{API_BASE}/brokers/import/files/{member}", timeout=TIMEOUT)).json()["status"] == "uploaded"

                parsed = await client.post(f"{API_BASE}/brokers/import/files/{combined['file_id']}/parse", json={"plugin_code": DANSKE_CODE, "broker_id": broker_id}, timeout=TIMEOUT)
                assert parsed.status_code == 200, parsed.text
                result = parsed.json()
                assert (result["history_start"], len(result["transactions"])) == ("2020-02-03", 27)
                assert len(result["checkpoints"]) == 1 and len(result["verifications"]) == 1, (result["checkpoints"], result["verifications"])
                checkpoint, verification = result["checkpoints"][0], result["verifications"][0]
                assert (checkpoint["as_of"], checkpoint["kind"], _money_list(checkpoint["cash"]), len(checkpoint["positions"])) == ("2020-02-02", "opening", {"EUR": Decimal("2699.50")}, 3)
                assert (verification["as_of"], _money_list(verification["cash"])) == ("2020-06-26", {"EUR": Decimal("1994.46")})

                selection = [tx for tx in result["transactions"] if tx["date"] >= result["history_start"]]
                fix = await _gap_fix(client, {"broker_id": broker_id, "plugin_code": DANSKE_CODE, "checkpoints": result["checkpoints"], "verifications": result["verifications"], "selection": selection})
                assert fix.status_code == 200, fix.text
                opening = _one(fix.json()["checkpoints"], "2020-02-02")
                assert _cash_proposals(opening) == [("DEPOSIT", "EUR", Decimal("2699.50"))]
                assert (opening["proposals"][0]["date"], opening["proposals"][0]["tags"]) == ("2020-02-02", DANSKE_GAP_FIX_TAGS)
                assert opening["positions"] == [], "the positions of the bank are on fake ids until the wizard resolves them"
                unresolved = sorted(note["context"]["asset_id"] for note in opening["explanation"]["notes"] if note["code"] == "unresolved_asset")
                assert unresolved == sorted(position["asset_id"] for position in checkpoint["positions"])
                explanation = opening["explanation"]
                assert (explanation["absorbed_count"], explanation["absorbed_missing_count"], explanation["unexplained_cash"]) == (14, 14, [])
                check = _one(fix.json()["verifications"], "2020-06-26")
                assert (check["ok"], _money_rows(check["cash"])) == (True, {"EUR": (Decimal("1994.46"), Decimal("1994.46"), Decimal("0"))})
                assert await _broker_tx_ids(client, broker_id) == set(), "the set API and the gap-fix save nothing"
                print_success("✓ Danske main set: combined, parsed and aligned with the bank")
            finally:
                await _delete_files(client, file_ids)
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    async def test_a_later_set_closes_a_gap_in_the_history(self, test_server):
        """RS-E01 (phase E): the broker already holds a Danske history (one row tagged ``danske_bank`` on 2019-06-03, which is H0), and the main set comes later.

        Its parse keeps the 2020-02-02 checkpoint as a ``gap``: the plugin marks it ``opening`` because it cannot
        know the history, and the framework knows better. The gap-fix of that checkpoint answers ``gap`` too, so
        the step shows the correction "After the gap". The parse and the gap-fix write nothing.
        """
        print_section("RS-E01: a later Danske set closes a gap in the history")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            file_ids = []
            try:
                await _require_plugin(client, DANSKE_CODE)
                saved = await _commit_creates(client, {**_cash_movement(broker_id, "DEPOSIT", DANSKE_HISTORY_DAY, "100"), "tags": DANSKE_HISTORY_TAGS})
                batch = str(uuid.uuid4())
                for name, _role in DANSKE_MAIN:
                    response = await _upload_sample(client, broker_id, name, batch)
                    assert response.status_code == 200, response.text
                    file_ids.append(response.json()["file_id"])
                combined = await client.post(_set_url("combine"), json={"broker_id": broker_id, "plugin_code": DANSKE_CODE, "batch_id": batch}, timeout=TIMEOUT)
                assert combined.status_code == 200, combined.text
                combined_id = combined.json()["combined"]["file_id"]
                file_ids.append(combined_id)

                parsed = await client.post(f"{API_BASE}/brokers/import/files/{combined_id}/parse", json={"plugin_code": DANSKE_CODE, "broker_id": broker_id}, timeout=TIMEOUT)

                assert parsed.status_code == 200, parsed.text
                result = parsed.json()
                assert result["history_start"] == DANSKE_HISTORY_DAY, f"presence barrier: H0 comes from the saved history, so this parse is a later import: {result['history_start']}"
                checkpoint = _one(result["checkpoints"], "2020-02-02")
                assert (_money_list(checkpoint["cash"]), len(checkpoint["positions"]), checkpoint["absorbed"]["opening_cash"]) == ({"EUR": Decimal("2699.50")}, 3, []), "what a later import already gives: the bank's cash and positions, no opening balance"
                assert checkpoint["kind"] == "gap", f"the first checkpoint of a later set closes a gap in the saved history, it is still {checkpoint['kind']!r}: not implemented yet (BRIM report sets, phase E)"

                # No selection: LibreFolio's side at 2020-02-02 is the saved row alone, so the correction is 2699.50 - 100.
                fix = await _gap_fix(client, {"broker_id": broker_id, "plugin_code": DANSKE_CODE, "checkpoints": result["checkpoints"], "verifications": result["verifications"]})

                assert fix.status_code == 200, fix.text
                aligned = _one(fix.json()["checkpoints"], "2020-02-02")
                assert _cash_proposals(aligned) == [("DEPOSIT", "EUR", Decimal("2599.50"))]
                assert (aligned["kind"], aligned["explanation"]["opening_cash"]) == ("gap", [])
                assert await _broker_tx_ids(client, broker_id) == set(saved), "the parse and the gap-fix save nothing"
                print_success("✓ a later Danske set: its first checkpoint is a gap, in the parse and in the gap-fix")
            finally:
                await _delete_files(client, file_ids)
                await _delete_created(client, broker_ids=[broker_id])


# ============================================================================
# CATEGORY 11: THE FILES LEFT OUT OF A SET (phase G, plan §14 G.2, D)
# ============================================================================
#
# The user chooses how a set is read, so the set request names the originals of the
# upload left out of it: ``exclude_file_ids``, empty by default (every request above
# still works without it). Proven over HTTP with the Danske plugin the test backend
# knows, on the synthetic main set plus a third cash statement invented here (the
# sample's header and Latin-1 encoding, three rows of 2021 that continue its running
# balance): the cash role takes several files, so leaving the third one out keeps the
# set complete. An id that is not an original of the broker and upload answers 422 with
# ``exclude_unknown`` in the same ``{code, message}`` detail as the other set errors;
# leaving every member out is the 404 ``members_not_found`` of today. Each test deletes
# the files and the broker it created.

DANSKE_THIRD_CASH_NAME = "danske_bank-cash-2021.csv"
DANSKE_THIRD_CASH_ROWS = (
    "15.03.2021;Palvelumaksut 03/2021;-3,5;1900,96;Toteutunut;Ei",
    "10.02.2021;Matti Meikäläinen;250;1904,46;Toteutunut;Ei",
    "05.01.2021;Palvelumaksut 12/2020;-3,5;1654,46;Toteutunut;Ei",
)


def _danske_third_cash() -> bytes:
    """An invented third cash statement: the synthetic sample's header and encoding, newest row first, as the bank writes them."""
    header = (DANSKE_SAMPLE_DIR / "danske_bank-cash.csv").read_bytes().decode("latin-1").splitlines()[0]
    return ("\n".join([header, *DANSKE_THIRD_CASH_ROWS]) + "\n").encode("latin-1")


async def _upload_main_set_and_third_cash(client: httpx.AsyncClient, broker_id: int, file_ids: list) -> tuple:
    """The two main exports and the third cash statement in one upload batch; every stored id goes into ``file_ids`` for the cleanup."""
    batch = str(uuid.uuid4())
    uploaded = {}
    for name, role in DANSKE_MAIN:
        response = await _upload_sample(client, broker_id, name, batch)
        assert response.status_code == 200, response.text
        file_ids.append(response.json()["file_id"])
        uploaded[role] = response.json()
    third = await _upload_csv(client, broker_id, _danske_third_cash(), DANSKE_THIRD_CASH_NAME, batch_id=batch)
    assert third.status_code == 200, third.text
    file_ids.append(third.json()["file_id"])
    uploaded["third"] = third.json()
    # Premise: the invented statement is read like the sample cash statement — by the plugins that read the sample,
    # Danske among them; which ones is the detectors' business (since step G the generic CSV wants a ``date`` and a
    # ``type`` column, which neither names), not this category's.
    assert uploaded["third"]["batch_id"] == batch, f"premise: the invented statement is in the upload batch: {uploaded['third']}"
    assert uploaded["third"]["compatible_plugins"] == uploaded["cash"]["compatible_plugins"], f"premise: the invented statement is read like the sample cash statement: {uploaded['third']} vs {uploaded['cash']}"
    assert DANSKE_CODE in uploaded["third"]["compatible_plugins"], f"premise: Danske reads the invented statement: {uploaded['third']}"
    return batch, uploaded


def _set_error(response: httpx.Response) -> dict:
    """The ``detail`` of a set error: an object with its stable ``code`` and a ``message`` (``missing_roles`` too for an incomplete set)."""
    detail = response.json().get("detail")
    assert isinstance(detail, dict) and isinstance(detail.get("message"), str) and detail["message"], f"a set error carries {{code, message}}: {response.status_code} {response.text}"
    return detail


class TestReportSetExclusions:
    """G · D — ``POST /sets/preview`` and ``POST /sets/combine`` read ``exclude_file_ids`` from the body."""

    @pytest.mark.asyncio
    async def test_preview_leaves_the_named_files_out(self, test_server):
        """RS-G01: with nothing left out the third statement is a member; left out, it is not and the set stays complete;
        with the two cash statements left out, the cash role is missing and the set is incomplete."""
        print_section("RS-G01: the preview leaves the named files out")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            file_ids = []
            try:
                await _require_plugin(client, DANSKE_CODE)
                batch, uploaded = await _upload_main_set_and_third_cash(client, broker_id, file_ids)
                custody, cash, third = (uploaded[role]["file_id"] for role in ("custody", "cash", "third"))
                body = {"broker_id": broker_id, "plugin_code": DANSKE_CODE, "batch_id": batch}
                whole = await client.post(_set_url("preview"), json=body, timeout=TIMEOUT)
                assert whole.status_code == 200, whole.text
                assert {member["file_id"] for member in whole.json()["members"]} == {custody, cash, third}, "presence barrier: the third statement is a member of the upload"

                kept = await client.post(_set_url("preview"), json={**body, "exclude_file_ids": [third]}, timeout=TIMEOUT)

                assert kept.status_code == 200, kept.text
                assert {member["file_id"] for member in kept.json()["members"]} == {custody, cash}
                assert kept.json()["complete"] is True

                no_cash = await client.post(_set_url("preview"), json={**body, "exclude_file_ids": [cash, third]}, timeout=TIMEOUT)

                assert no_cash.status_code == 200, no_cash.text
                shape = no_cash.json()
                assert [member["file_id"] for member in shape["members"]] == [custody]
                assert {role["code"]: (role["status"], role["file_ids"]) for role in shape["roles"]} == {"custody": ("present", [custody]), "cash": ("missing", [])}
                assert ([item["role"] for item in shape["missing"]], shape["complete"]) == (["cash"], False)
                print_success("✓ the preview leaves the named files out")
            finally:
                await _delete_files(client, file_ids)
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    async def test_combine_holds_the_kept_members_and_reuses_them_for_the_same_exclusion(self, test_server):
        """RS-G02: leaving both statements out is 422 ``set_incomplete``; leaving the third out combines the other two, and the
        same exclusion reuses that file; without the exclusion, another combined file holds all three."""
        print_section("RS-G02: the combine keeps the kept members")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            file_ids = []
            try:
                await _require_plugin(client, DANSKE_CODE)
                batch, uploaded = await _upload_main_set_and_third_cash(client, broker_id, file_ids)
                custody, cash, third = (uploaded[role]["file_id"] for role in ("custody", "cash", "third"))
                body = {"broker_id": broker_id, "plugin_code": DANSKE_CODE, "batch_id": batch}

                incomplete = await client.post(_set_url("combine"), json={**body, "exclude_file_ids": [cash, third]}, timeout=TIMEOUT)

                assert incomplete.status_code == 422, incomplete.text
                assert (_set_error(incomplete)["code"], _set_error(incomplete).get("missing_roles")) == ("set_incomplete", ["cash"])

                first = await client.post(_set_url("combine"), json={**body, "exclude_file_ids": [third]}, timeout=TIMEOUT)

                assert first.status_code == 200, first.text
                combined = first.json()["combined"]
                file_ids.append(combined["file_id"])
                assert first.json()["reused"] is False
                assert {ref["file_id"] for ref in combined["derived_from"] if not ref["deleted"]} == {custody, cash}

                again = await client.post(_set_url("combine"), json={**body, "exclude_file_ids": [third]}, timeout=TIMEOUT)
                whole = await client.post(_set_url("combine"), json=body, timeout=TIMEOUT)

                assert again.status_code == 200, again.text
                assert (again.json()["reused"], again.json()["combined"]["file_id"]) == (True, combined["file_id"])
                assert whole.status_code == 200, whole.text
                file_ids.append(whole.json()["combined"]["file_id"])
                assert whole.json()["reused"] is False
                assert whole.json()["combined"]["file_id"] != combined["file_id"]
                assert {ref["file_id"] for ref in whole.json()["combined"]["derived_from"]} == {custody, cash, third}
                print_success("✓ the combine keeps the kept members, and reuses them for the same exclusion")
            finally:
                await _delete_files(client, file_ids)
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", SET_ENDPOINTS)
    @pytest.mark.parametrize("stranger", ["unknown-id", "another-upload"])
    async def test_a_file_that_is_not_an_original_of_the_upload_is_422_exclude_unknown(self, test_server, endpoint, stranger):
        """RS-G03: an id that does not exist, or an original of another upload of the same broker, answers 422 with ``exclude_unknown``."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            file_ids = []
            try:
                await _require_plugin(client, DANSKE_CODE)
                batch, _uploaded = await _upload_main_set_and_third_cash(client, broker_id, file_ids)
                if stranger == "unknown-id":
                    excluded = str(uuid.uuid4())
                else:
                    elsewhere = await _upload_csv(client, broker_id, _danske_third_cash(), DANSKE_THIRD_CASH_NAME, batch_id=str(uuid.uuid4()))
                    assert elsewhere.status_code == 200, elsewhere.text
                    excluded = elsewhere.json()["file_id"]
                    file_ids.append(excluded)

                response = await client.post(_set_url(endpoint), json={"broker_id": broker_id, "plugin_code": DANSKE_CODE, "batch_id": batch, "exclude_file_ids": [excluded]}, timeout=TIMEOUT)

                assert response.status_code == 422, response.text
                assert _set_error(response)["code"] == "exclude_unknown", response.text
                assert not [info for info in await _files_on(client, broker_id) if info.get("kind") == "combined"], "a refused request writes nothing"
            finally:
                await _delete_files(client, file_ids)
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", SET_ENDPOINTS)
    async def test_leaving_every_member_out_is_404_members_not_found(self, test_server, endpoint):
        """RS-G04: with every original of the upload left out there is no set: 404 ``members_not_found``, as for an empty upload."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            file_ids = []
            try:
                await _require_plugin(client, DANSKE_CODE)
                batch, uploaded = await _upload_main_set_and_third_cash(client, broker_id, file_ids)
                everything = [info["file_id"] for info in uploaded.values()]

                response = await client.post(_set_url(endpoint), json={"broker_id": broker_id, "plugin_code": DANSKE_CODE, "batch_id": batch, "exclude_file_ids": everything}, timeout=TIMEOUT)

                assert response.status_code == 404, response.text
                assert _set_error(response)["code"] == "members_not_found", response.text
            finally:
                await _delete_files(client, file_ids)
                await _delete_created(client, broker_ids=[broker_id])


# ============================================================================
# CATEGORY 12: WHY A PLUGIN REFUSES A FILE (phase G, plan G.5)
# ============================================================================
#
# Since phase G the generic CSV refuses a CSV whose header names no ``date`` or no ``type``
# column, so a parse forced on such a file stops at the guard of ``parse_file``. The developer's
# decision, verbatim: «Correggi dentro G con il metodo opzionale (Consigliato)» — the plugin says
# why (``cannot_parse_reason``) and the guard appends it: still a 400, the file still goes to
# ``failed`` with the same message, which now names the missing column. The name between the
# quotes is the stored one, ``{file_id}{ext}``, which G.5 does not change: not asserted. The
# rules of the message are tested at service level, in test_services/test_brim_parse_race.py.
# The test deletes the file and the broker it created.

GENERIC_CSV_CODE = "broker_generic_csv"
# A header with a ``type`` column and no date column under any alias the generic CSV knows (``HEADER_MAPPINGS``).
CSV_WITHOUT_DATE = b"type,amount,currency,description\nBUY,-1000.00,EUR,Buy some shares\nDEPOSIT,500.00,EUR,Top-up\n"


class TestParseRefusalReason:
    """G.5 — a parse forced with a plugin that refuses the file answers 400 with the plugin's reason, and the file goes to ``failed``."""

    @pytest.mark.asyncio
    async def test_forcing_the_generic_csv_on_a_csv_without_date_names_the_missing_column(self, test_server):
        """RS-G05: ``plugin_code="broker_generic_csv"`` on an uploaded CSV with ``type`` and no date column: 400, ``detail`` is
        "Plugin 'broker_generic_csv' cannot parse file '…': required column 'date' not found in the CSV header", and the
        file is ``failed`` with that message."""
        print_section("RS-G05: the forced generic CSV names the missing column")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            file_ids = []
            try:
                upload = await _upload_csv(client, broker_id, CSV_WITHOUT_DATE, f"no_date_{uuid.uuid4().hex[:8]}.csv")
                assert upload.status_code == 200, upload.text
                file_id = upload.json()["file_id"]
                file_ids.append(file_id)
                assert GENERIC_CSV_CODE not in upload.json()["compatible_plugins"], f"premise: the generic CSV does not offer itself for a CSV without a date column, so the parse forces it: {upload.json()}"

                response = await client.post(f"{API_BASE}/brokers/import/files/{file_id}/parse", json={"plugin_code": GENERIC_CSV_CODE, "broker_id": broker_id}, timeout=TIMEOUT)

                assert response.status_code == 400, response.text
                detail = _detail_text(response)
                assert detail.startswith(f"Plugin '{GENERIC_CSV_CODE}' cannot parse file '"), detail
                info = await client.get(f"{API_BASE}/brokers/import/files/{file_id}", timeout=TIMEOUT)
                assert info.status_code == 200, info.text
                assert (info.json()["status"], info.json()["error_message"]) == ("failed", detail), "the refused file goes to failed, with the message the user reads"
                assert detail.endswith("': required column 'date' not found in the CSV header"), f"the refusal does not say which column is missing: {detail!r}"
                print_success("✓ the forced generic CSV names the missing column, and the file is failed")
            finally:
                await _delete_files(client, file_ids)
                await _delete_created(client, broker_ids=[broker_id])


# ============================================================================
# CATEGORY 13: A FILE DETECTED BEFORE ITEM 8 IS DETECTED AGAIN (step 5, item 8)
# ============================================================================
#
# ``compatible_plugins`` is computed at upload and kept in the file's sidecar. Since item 8 the sidecar also keeps
# ``plugins_signature``, the signature of the plugin catalogue that computed it (the app version), and a read of an
# original whose signature is absent or old detects its plugins again and saves them. The test leaves on disk the
# sidecar of a Danske export detected before item 8 by a catalogue that did not read it: no ``plugins_signature``, no
# plugin, every other key as today's upload wrote it. That is not 1.1.0's sidecar: 1.1.0 recorded no ``batch_id``
# either, so its uploads are detected again but form no set (guarded at service level, in
# test_services/test_brim_report_sets.py). The sidecar is rewritten in this lane's test data directory
# (``get_test_data_dir``: the runner exports ``--data-dir`` to the backend under test and to pytest alike), then the
# test reads the file through the list and through the file endpoint. The rules of the detection are tested at service
# level, in test_services/test_brim_parse_race.py. The test deletes the file and the broker it created.

DANSKE_CASH_NAME = "danske_bank-cash.csv"


def _lane_sidecar(broker_id: int, file_id: str) -> Path:
    """Where the backend of this test lane keeps the sidecar of an uploaded file."""
    return get_test_data_dir() / "broker_reports" / "uploaded" / f"broker_{broker_id}" / f"{file_id}.json"


def _as_detected_before_item_8(sidecar: Path) -> None:
    """Leave a sidecar as a build before item 8 left it, its catalogue not reading the export: no ``plugins_signature``, and no plugin.

    Written atomically, as the backend writes it: a neighbour's file list reads every sidecar on disk.
    """
    metadata = json.loads(sidecar.read_text())
    metadata.pop("plugins_signature", None)
    metadata["compatible_plugins"] = []
    staged = sidecar.with_name(f"{sidecar.name}.tmp.{uuid.uuid4().hex}")
    staged.write_text(json.dumps(metadata, indent=2))
    staged.replace(sidecar)


class TestPluginRedetection:
    """Item 8 — the file list and the file endpoint give today's plugins for a file detected before item 8, and save them."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ["list", "file"])
    async def test_a_danske_export_detected_before_item_8_is_detected_again(self, test_server, endpoint):
        """RS-I801: the Danske cash statement, its sidecar left without the detection signature, read through ``GET /files`` or ``GET /files/{id}``: Danske."""
        print_section(f"RS-I801: a Danske export detected before item 8, read through the {endpoint} endpoint")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            file_ids = []
            try:
                await _require_plugin(client, DANSKE_CODE)
                upload = await _upload_csv(client, broker_id, (DANSKE_SAMPLE_DIR / DANSKE_CASH_NAME).read_bytes(), DANSKE_CASH_NAME)
                assert upload.status_code == 200, upload.text
                file_id = upload.json()["file_id"]
                file_ids.append(file_id)
                assert upload.json()["compatible_plugins"] == [DANSKE_CODE], f"premise: today's catalogue reads the sample as Danske only: {upload.json()}"
                sidecar = _lane_sidecar(broker_id, file_id)
                assert sidecar.is_file(), f"premise: the test reaches the data directory of the backend under test: no sidecar at {sidecar}"
                _as_detected_before_item_8(sidecar)

                if endpoint == "list":
                    listed = [info for info in await _files_on(client, broker_id) if info["file_id"] == file_id]
                    assert len(listed) == 1, f"{file_id} listed {len(listed)} times"
                    read = listed[0]
                else:
                    response = await client.get(f"{API_BASE}/brokers/import/files/{file_id}", timeout=TIMEOUT)
                    assert response.status_code == 200, response.text
                    read = response.json()

                assert read["compatible_plugins"] == [DANSKE_CODE], f"the {endpoint} endpoint still gives the plugins stored before item 8: {read['compatible_plugins']}"
                stored = json.loads(sidecar.read_text())
                assert stored["compatible_plugins"] == [DANSKE_CODE], f"the detection is not saved: {stored['compatible_plugins']}"
                assert isinstance(stored.get("plugins_signature"), str) and stored["plugins_signature"], f"the detection is saved without the catalogue's signature: {sorted(stored)}"
                print_success(f"✓ the {endpoint} endpoint detects again the plugins of a file detected before item 8")
            finally:
                await _delete_files(client, file_ids)
                await _delete_created(client, broker_ids=[broker_id])


# ============================================================================
# CATEGORY 14: A DELETE WAITING FOR THE BROKER'S LOCK LEAVES ITS BACKEND PROCESS RESPONSIVE (step 5, item 8 + F1)
# ============================================================================
#
# Every metadata write of a broker holds ``_broker_metadata_lock(broker_id)``: a re-entrant lock in the process, then
# ``fcntl.flock(LOCK_EX)`` on ``<data dir>/broker_reports/.locks/broker_<id>.lock``, exclusive across processes. F1 holds it
# for a whole combine, on a worker thread, so a write of the same broker may wait seconds for it. ``DELETE /files/{id}``
# (``delete_file``) and the parse endpoint's ``save_parse_result`` called such a write on the event loop itself, where the
# wait stalls every request of the backend process; both now run in ``asyncio.to_thread``. The test takes the broker's
# lock from its own process as the backend takes it, sends the DELETE from a thread, waits until the backend process has
# the lock file open (``_acquire_file_lock`` opens it and takes the lock with no ``await`` in between, so from then on the
# delete is inside ``flock``), then asks THAT process for ``GET /plugins``: it must answer while the lock is held, and the
# delete must still be pending. Released, the delete answers 200 and the file is gone from the list.
#
# The same process is the point. Under ``--workers N`` the runner's shared backend runs ceil(N / 2) uvicorn workers (one
# with the default ``--workers 1``, two with ``--workers 4``), and a worker whose event loop is stuck accepts no connection:
# a request on a fresh connection is served by another worker, however many times it is sent, and proves nothing. So,
# before the lock is taken, the test opens keep-alive connections and asks the OS which backend process serves each
# (``psutil``, among the listeners of the test port, found with ``lsof`` as ``test_server_helper`` finds them) until two
# share one — N listeners, at most N + 1 connections (pigeonhole) — and sends the DELETE on one, the GET on the other.
# ``save_parse_result`` is not covered here: it takes the lock right after ``move_to_parsed`` released it, a window no
# client can take the lock in. Every wait is bounded, the lock is released in ``finally``, and the test deletes the file
# and the broker it created.

PLUGINS_URL = f"{API_BASE}/brokers/import/plugins"
# Every wait for something that must happen is bounded by this.
_WAIT_SECONDS = 30.0
# How long the backend process is given to answer the light request while the lock is held. A free event loop answers in
# milliseconds, a stuck one not before the release: the bound only decides how soon the defect shows, is paid on the red
# path only, and stays far above what a loaded parallel run (two workers serving four clients) costs a free loop.
_PROBE_SECONDS = 10.0
# The pause between two looks at the backend's open files, while its delete makes its way to the lock.
_POLL_SECONDS = 0.05
# The DELETE outlives every wait the test makes before it releases the lock (the barrier and the probe).
_DELETE_SECONDS = 3 * _WAIT_SECONDS


class _InFlight:
    """One request on its own daemon thread, through a client of its own: what it answered or raised, and an Event set when it is done."""

    def __init__(self, name: str, send: Callable[[], httpx.Response]) -> None:
        self.name = name
        self.response: Optional[httpx.Response] = None
        self.error: Optional[Exception] = None
        self.done = threading.Event()
        self._send = send
        threading.Thread(target=self._run, name=name, daemon=True).start()

    def _run(self) -> None:
        try:
            self.response = self._send()
        except Exception as exc:  # reported by outcome(), never swallowed
            self.error = exc
        finally:
            self.done.set()

    def outcome(self) -> str:
        if self.error is not None:
            return f"raised {type(self.error).__name__}: {self.error}"
        if self.response is None:
            return "no answer yet"
        return f"{self.response.status_code} {self.response.text}"

    def finish(self) -> httpx.Response:
        """The answer, waited for with a bound: a request that never ends fails the test instead of hanging the suite."""
        assert self.done.wait(_WAIT_SECONDS), f"{self.name}: no answer {_WAIT_SECONDS}s after the broker's lock was released"
        assert self.response is not None, f"{self.name} {self.outcome()}"
        return self.response


def _lane_broker_lock_file(broker_id: int) -> Path:
    """The lock file the backend of this test lane takes for every metadata write of the broker (``brim_provider._acquire_file_lock``)."""
    return get_test_data_dir() / "broker_reports" / ".locks" / f"broker_{broker_id}.lock"


def _hold_broker_lock(lock_file: Path) -> TextIO:
    """Take the broker's lock as the backend does, ``open(..., "a+")`` then ``flock(LOCK_EX)``, but without waiting: nobody may hold the lock of a broker this test just created."""
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_file, "a+")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        pytest.fail(f"premise: the lock of the broker this test created is free once its upload answered, yet {lock_file} is held", pytrace=False)
    return handle


def _let_go(handle: TextIO) -> None:
    """Release the broker's lock and close its file; once closed, a second call does nothing (``finally`` calls it again)."""
    if handle.closed:
        return
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def _backend_processes() -> Set[int]:
    """The processes listening on the test port: the backend's worker(s) and supervisor, or this very process when the server runs in it."""
    pids = port_holder_pids(settings.TEST_PORT)
    assert pids, f"lsof names no process listening on port {settings.TEST_PORT} ({pids!r}): the test cannot tell which process serves which connection"
    return pids


def _connection_port(response: httpx.Response) -> int:
    """The local port of the keep-alive connection a response came over: it names the connection, hence the process that accepted it."""
    return response.extensions["network_stream"].get_extra_info("client_addr")[1]


def _serving_process(client_port: int, backend: Set[int]) -> Optional[int]:
    """The backend process holding the server end of the connection whose client end is local port ``client_port``."""
    for pid in sorted(backend):
        if any(conn.laddr.port == settings.TEST_PORT and conn.raddr and conn.raddr.port == client_port for conn in psutil.Process(pid).net_connections(kind="tcp")):
            return pid
    return None


def _pinned_pair(cookies: httpx.Cookies, backend: Set[int], opened: List[httpx.Client]) -> Tuple[httpx.Client, httpx.Client, int]:
    """Two clients of one keep-alive connection each, both served by one backend process, and that process.

    Each client opens its connection with ``GET /plugins`` and the OS tells which process accepted it: N processes listen,
    so N + 1 connections always put two on one. No client-side expiry: the pool must never swap the connection for a new
    one, which another worker could accept. Every client opened goes to ``opened``, which the caller closes.
    """
    served_by: Dict[int, httpx.Client] = {}
    for _ in range(len(backend) + 1):
        client = httpx.Client(cookies=cookies, timeout=TIMEOUT, limits=httpx.Limits(max_connections=1, max_keepalive_connections=1, keepalive_expiry=None))
        opened.append(client)
        response = client.get(PLUGINS_URL)
        assert response.status_code == 200, response.text
        port = _connection_port(response)
        pid = _serving_process(port, backend)
        assert pid is not None, f"none of the backend's processes {sorted(backend)} serves the connection from local port {port}"
        if pid in served_by:
            return served_by[pid], client, pid
        served_by[pid] = client
    pytest.fail(f"{len(backend) + 1} connections on {len(backend)} listening processes, never two on one: the backend's processes changed meanwhile", pytrace=False)


def _holds_open(pid: int, lock_file: Path, own_fd: int) -> bool:
    """Whether backend process ``pid`` has ``lock_file`` open; this test's own descriptor does not count (an in-process server shares its PID)."""
    target = os.path.realpath(lock_file)
    return any(os.path.realpath(entry.path) == target and (pid, entry.fd) != (os.getpid(), own_fd) for entry in psutil.Process(pid).open_files())


def _wait_until_waiting(pid: int, lock_file: Path, own_fd: int, delete: _InFlight) -> None:
    """Return once backend process ``pid`` has the broker's lock file open: its delete is then inside ``flock``, waiting for this test."""
    deadline = time.monotonic() + _WAIT_SECONDS
    while not _holds_open(pid, lock_file, own_fd):
        assert not delete.done.is_set(), f"the DELETE answered without waiting for the broker's lock this test holds: {delete.outcome()}"
        assert time.monotonic() < deadline, f"backend process {pid} did not open {lock_file} within {_WAIT_SECONDS}s of the DELETE: the delete never reached the broker's lock"
        delete.done.wait(_POLL_SECONDS)


def _probe(client: httpx.Client, pid: int) -> httpx.Response:
    """``GET /plugins`` on a pinned connection, bounded by ``_PROBE_SECONDS``: a process whose event loop waits for a lock never answers it."""
    try:
        return client.get(PLUGINS_URL, timeout=_PROBE_SECONDS)
    except httpx.TimeoutException:
        pytest.fail(f"backend process {pid} did not answer GET /plugins within {_PROBE_SECONDS}s while its DELETE waited for the broker's lock: the delete waits on the event loop, and every request of the process waits with it", pytrace=False)


@pytest.mark.skipif(fcntl is None, reason="no flock(2) on this platform: the backend's broker lock is in-process only, and the test has no lock to hold")
class TestBrokerLockOffTheEventLoop:
    """Item 8 + F1 — a delete waiting for the broker's metadata lock waits on a worker thread: its backend process keeps answering."""

    @pytest.mark.asyncio
    async def test_a_delete_waiting_for_the_broker_lock_leaves_the_backend_responsive(self, test_server, sample_csv_content):
        """RS-I802: the broker's lock held by the test process, ``DELETE /files/{id}`` waits for it while the backend process
        holding the delete answers ``GET /plugins``; released, the delete answers 200 and the file is no longer listed."""
        print_section("RS-I802: a delete waiting for the broker's lock leaves its backend process responsive")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            lock_file = _lane_broker_lock_file(broker_id)
            file_ids: List[str] = []
            opened: List[httpx.Client] = []
            lock: Optional[TextIO] = None
            delete: Optional[_InFlight] = None
            try:
                upload = await _upload_csv(client, broker_id, sample_csv_content, f"locked_{uuid.uuid4().hex[:8]}.csv")
                assert upload.status_code == 200, upload.text
                file_id = upload.json()["file_id"]
                file_ids.append(file_id)
                backend = _backend_processes()
                delete_client, probe_client, pid = _pinned_pair(client.cookies, backend, opened)

                lock = _hold_broker_lock(lock_file)
                assert not _holds_open(pid, lock_file, lock.fileno()), f"premise: backend process {pid} has no request on this broker before the DELETE, yet it has {lock_file} open"
                delete = _InFlight("RS-I802 DELETE", lambda: delete_client.delete(f"{API_BASE}/brokers/import/files/{file_id}", timeout=_DELETE_SECONDS))
                _wait_until_waiting(pid, lock_file, lock.fileno(), delete)

                probe = _probe(probe_client, pid)
                assert probe.status_code == 200, probe.text
                assert _serving_process(_connection_port(probe), backend) == pid, f"the light request was not served by backend process {pid}, which holds the delete: it proves nothing about that process's event loop"
                assert not delete.done.is_set(), f"the DELETE answered while this test still held the broker's lock: {delete.outcome()}"

                _let_go(lock)
                deleted = delete.finish()
                assert deleted.status_code == 200, deleted.text
                assert deleted.json() == {"success": True, "file_id": file_id}, deleted.text
                assert file_id not in {info["file_id"] for info in await _files_on(client, broker_id)}, f"{file_id} is still listed after its DELETE answered 200"
                print_success(f"✓ backend process {pid} answered while its DELETE waited for the broker's lock; released, the delete completed")
            finally:
                if lock is not None:
                    _let_go(lock)
                if delete is not None:
                    delete.done.wait(_WAIT_SECONDS)
                for pinned in opened:
                    pinned.close()
                await _delete_files(client, file_ids)
                await _delete_created(client, broker_ids=[broker_id])


# ============================================================================
# Note: E2E tests are in test_e2e/test_brim_e2e.py
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
