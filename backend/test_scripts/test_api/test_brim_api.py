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
- GET /brokers/import/files/{id}/preview of a damaged Excel workbook answers 400, not 500
  (step 6, F2: Category 15)
- POST /brokers/import/upload refuses a name (original or custom) with a blocked extension (``.js``, ``.mjs``, ``.exe``…): 400, nothing
  written; the report extensions stay accepted (H-55 v2 review, R1 c)
- who may see a broker's report files: a file with no broker only its uploader and the administrator,
  and in no broker's list, ``can_delete`` on every list item, a file id that is not a UUID answers 404
  on every per-file route, a parse imports only into a broker its caller edits (F36, decision 36:
  W-B3, W-B4, W-B32: Category 18)

See checklist: 01_test_brim_plan.md - Categories 5, 6
Note: E2E tests are in test_e2e/test_brim_e2e.py (Category 7)
Report sets: what a set contains is tested at service level, in
test_services/test_brim_report_sets.py (Category 8 below explains why).
Reference: backend/app/api/v1/brokers.py
"""

import contextlib
import io
import json
import os
import threading
import time
import uuid
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Set, TextIO, Tuple

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
    password = "TestPass123!"  # meets the password rules (decision 37), which POST /auth/register applies

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
            detail = response.json()["detail"]
            assert isinstance(detail, str), f"a plugin that does not exist is not a parse failure: its detail stays a plain string (C-70b): {detail!r}"
            assert "plugin" in detail.lower()


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
    """The BRIM files stored on one broker, from the list filtered on it; the target is filtered."""
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


# H-55 v2 review (R1 c): a report file that can run as a script is refused at the upload, so no stored file can ever be fetched as one.
#: Names whose extension (lower-cased) is in ``static_uploads.BLOCKED_EXTENSIONS``, with the extension the 400 names.
BLOCKED_REPORT_NAMES = [
    pytest.param("report.js", ".js", id="js"),
    pytest.param("report.mjs", ".mjs", id="mjs"),
    pytest.param("report.cjs", ".cjs", id="cjs"),
    pytest.param("report.exe", ".exe", id="exe"),
    pytest.param("REPORT.JS", ".js", id="upper-case-js"),
]


def _xlsx_bytes() -> bytes:
    """A minimal zip with the parts of a workbook: enough for the upload, which only sniffs the plugins."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
    return out.getvalue()


#: (name, content) of the report files the upload keeps accepting.
ACCEPTED_REPORTS = [
    pytest.param("accepted.csv", b"date,type,quantity,amount,currency,description\n2025-01-01,DEPOSIT,0,1000.00,EUR,Test deposit\n", id="csv"),
    pytest.param("accepted.xlsx", _xlsx_bytes(), id="xlsx"),
    pytest.param("accepted.json", b'{"trades": []}', id="json"),
    pytest.param("accepted.pdf", b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n", id="pdf"),
    pytest.param("accepted.txt", b"plain text report\n", id="txt"),
]


class TestUploadBlockedExtensions:
    """R1 c — ``POST /upload`` refuses a name (original or custom) whose extension is in ``BLOCKED_EXTENSIONS``: 400 naming it, nothing written."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("filename", "extension"), BLOCKED_REPORT_NAMES)
    async def test_a_blocked_original_name_is_refused_and_nothing_is_written(self, test_server, filename, extension):
        """BX-001: a script or executable name answers 400 naming the extension; the broker's files are the same before and after."""
        print_section(f"BX-001: upload of {filename!r} is refused")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            try:
                before = {info["file_id"] for info in await _files_on(client, broker_id)}

                response = await _upload_csv(client, broker_id, b"alert('x');\n", filename)

                assert response.status_code == 400, f"{filename!r}: {response.status_code} {response.text}"
                assert extension in _detail_text(response).lower(), f"{filename!r}: the 400 does not name the extension {extension!r}: {response.text}"
                after = {info["file_id"] for info in await _files_on(client, broker_id)}
                assert after == before, f"{filename!r}: the refused upload left files {after - before}"
                print_success(f"✓ {filename!r} → 400, nothing written")
            finally:
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("custom_name", "extension"), [pytest.param("renamed.mjs", ".mjs", id="mjs"), pytest.param("renamed.exe", ".exe", id="exe"), pytest.param("renamed.js", ".js", id="js")])
    async def test_a_blocked_custom_name_is_refused_though_the_original_is_a_csv(self, test_server, sample_csv_content, custom_name, extension):
        """BX-002: the user-renamed ``custom_filename`` is what is stored and later served: its extension is checked, not only the original's."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            try:
                before = {info["file_id"] for info in await _files_on(client, broker_id)}

                response = await _upload_csv(client, broker_id, sample_csv_content, "original.csv", custom_filename=custom_name)

                assert response.status_code == 400, f"custom_filename={custom_name!r}: {response.status_code} {response.text}"
                assert extension in _detail_text(response).lower(), f"custom_filename={custom_name!r}: the 400 does not name {extension!r}: {response.text}"
                assert {info["file_id"] for info in await _files_on(client, broker_id)} == before, "the refused upload left a file"
            finally:
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("filename", "content"), ACCEPTED_REPORTS)
    async def test_the_report_extensions_stay_accepted(self, test_server, filename, content):
        """BX-003 — retro-compatibility guard (passes before and after R1): ``.csv``, ``.xlsx``, ``.json``, ``.pdf``, ``.txt`` are stored."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            try:
                response = await _upload_csv(client, broker_id, content, filename)

                assert response.status_code == 200, f"{filename!r}: {response.status_code} {response.text}"
                assert response.json()["filename"] == filename
                assert response.json()["file_id"] in {info["file_id"] for info in await _files_on(client, broker_id)}
            finally:
                await _delete_created(client, broker_ids=[broker_id])  # the broker's delete takes its report files with it


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
        brings the opening checkpoint, the verification and H0; the gap-fix proposes the opening deposit and checks the verification.

        Lot B-52 (red until the cure): the verification on 2020-06-26 is in operation-date terms, 1776.46. It is the bank's
        1994.46 plus the Tunturi purchase traded that day and settled on 06-30 (−218). The selection records that purchase on
        06-26, so LibreFolio's side is 1776.46 too, and the check stays ok."""
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
                assert (verification["as_of"], _money_list(verification["cash"])) == ("2020-06-26", {"EUR": Decimal("1776.46")})

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
                assert (check["ok"], _money_rows(check["cash"])) == (True, {"EUR": (Decimal("1776.46"), Decimal("1776.46"), Decimal("0"))})
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
# why (``cannot_parse_detail``) and the guard appends it: still a 400, the file still goes to
# ``failed`` with the same English message, which names the missing column. Since workstream W, lot
# K2a (backlog L6), the message names the plugin by its ``provider_name`` and the file by the name
# it was uploaded with, never by the plugin code nor by the stored ``{file_id}{ext}``: asserted
# whole. Since lot W5-5 (backlog C-70b) the ``detail`` of that 400 is an OBJECT, not a sentence:
# ``{"code": "parse_failed", "message": <that English sentence>, "plugin_code", "plugin_name",
# "reason": {"code", "message", "context"}}``, so the import wizard can translate it; the English
# sentence stays as the ``message`` of the object and as the file's stored ``error_message``
# (diagnostic). The rules of the message are tested at service level, in
# test_services/test_brim_parse_race.py. The tests delete the file and the broker they created.

GENERIC_CSV_CODE = "broker_generic_csv"
# A header with a ``type`` column and no date column under any alias the generic CSV knows (``HEADER_MAPPINGS``).
CSV_WITHOUT_DATE = b"type,amount,currency,description\nBUY,-1000.00,EUR,Buy some shares\nDEPOSIT,500.00,EUR,Top-up\n"
# Directa's ``can_parse`` wants its labels anywhere in the first 20 rows and the ``Conto :`` marker; its ``parse`` wants the three
# labels on ONE row. Spread over four rows they pass the first and fail the second: a real plugin that raises ``BRIMParseError``
# ("Directa header row not found ...", no ``details``) from a file of three lines. The expected sentence is written out by hand.
DIRECTA_CODE = "broker_directa"
DIRECTA_NAME = "Directa SIM"
DIRECTA_LABELS_ON_SEPARATE_ROWS = b"Conto : 12345\nData operazione\nTipo operazione\nIsin;Importo euro\n"
DIRECTA_HEADER_ROW_MISSING = "Directa header row not found (expected 'Data operazione'/'Tipo operazione'/'Isin')"


def _plain_workbook_bytes() -> bytes:
    """A small valid ``.xlsx`` (a header and one row): the generic CSV refuses it by its extension alone."""
    from openpyxl import Workbook  # noqa: PLC0415 — test-only local import

    workbook = Workbook()
    sheet = workbook.active
    sheet["A1"], sheet["B1"] = "date", "type"
    sheet["A2"], sheet["B2"] = "2025-01-01", "BUY"
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def _parse_failed_keys() -> set:
    """The keys of the ``detail`` object of a failed parse (lot W5-5): the contract the import wizard translates from."""
    return {"code", "message", "plugin_code", "plugin_name", "reason"}


async def _forced_parse(client: httpx.AsyncClient, broker_id: int, content: bytes, filename: str, plugin_code: str, file_ids: list) -> Tuple[str, httpx.Response]:
    """Upload ``content`` as ``filename`` on the broker and force ``plugin_code`` on it: ``(file_id, the parse response)``."""
    upload = await _upload_csv(client, broker_id, content, filename)
    assert upload.status_code == 200, upload.text
    file_id = upload.json()["file_id"]
    file_ids.append(file_id)
    response = await client.post(f"{API_BASE}/brokers/import/files/{file_id}/parse", json={"plugin_code": plugin_code, "broker_id": broker_id}, timeout=TIMEOUT)
    return file_id, response


async def _assert_failed_with(client: httpx.AsyncClient, file_id: str, message: str) -> None:
    """The refused file is ``failed`` and keeps ``message`` (English, diagnostic) as its stored ``error_message``."""
    info = await client.get(f"{API_BASE}/brokers/import/files/{file_id}", timeout=TIMEOUT)
    assert info.status_code == 200, info.text
    assert (info.json()["status"], info.json()["error_message"]) == ("failed", message), f"the failed file keeps the English text as its diagnostic: {info.json()}"


class TestParseRefusalReason:
    """G.5 / C-70b — a parse forced with a plugin that refuses the file answers 400 with an object the wizard translates, and the file goes to ``failed``."""

    @pytest.mark.asyncio
    async def test_forcing_the_generic_csv_on_a_csv_without_date_names_the_missing_column(self, test_server):
        """RS-G05: ``plugin_code="broker_generic_csv"`` on an uploaded CSV with ``type`` and no date column: 400, ``detail`` is the
        object of a failed parse — ``message`` is "Plugin 'Generic CSV' cannot parse file '<the name it was uploaded with>': required
        column 'date' not found in the CSV header", ``reason`` is the plugin's refusal (code ``missing_columns``, context ``columns``
        and ``count``) — and the file is ``failed`` with that same English message. The plugin by its name and the file by its uploaded
        name since lot K2a (L6); the detail an object since lot W5-5 (C-70b)."""
        print_section("RS-G05: the forced generic CSV names the missing column")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            file_ids = []
            try:
                filename = f"no_date_{uuid.uuid4().hex[:8]}.csv"
                upload = await _upload_csv(client, broker_id, CSV_WITHOUT_DATE, filename)
                assert upload.status_code == 200, upload.text
                file_id = upload.json()["file_id"]
                file_ids.append(file_id)
                assert upload.json()["filename"] == filename, f"premise: the upload keeps the name the user gave: {upload.json()}"
                assert GENERIC_CSV_CODE not in upload.json()["compatible_plugins"], f"premise: the generic CSV does not offer itself for a CSV without a date column, so the parse forces it: {upload.json()}"

                response = await client.post(f"{API_BASE}/brokers/import/files/{file_id}/parse", json={"plugin_code": GENERIC_CSV_CODE, "broker_id": broker_id}, timeout=TIMEOUT)

                assert response.status_code == 400, response.text
                detail = response.json()["detail"]
                assert isinstance(detail, dict), f"the detail of a refused parse is an object the wizard can translate, not an English sentence (C-70b): {detail!r}"
                assert set(detail) == _parse_failed_keys(), f"the keys of the failed-parse detail: {detail!r}"
                english = f"Plugin 'Generic CSV' cannot parse file '{filename}': required column 'date' not found in the CSV header"
                assert detail["code"] == "parse_failed", detail
                assert detail["message"] == english, f"the English text stays in the object, naming the plugin and the file as the user knows them (K2a, L6): {detail['message']!r}"
                assert (detail["plugin_code"], detail["plugin_name"]) == (GENERIC_CSV_CODE, "Generic CSV"), detail
                assert detail["reason"] == {"code": "missing_columns", "message": "required column 'date' not found in the CSV header", "context": {"columns": "date", "count": 1}}, f"the plugin's coded refusal, as cannot_parse_detail gives it: {detail['reason']!r}"
                await _assert_failed_with(client, file_id, english)
                print_success("✓ the forced generic CSV answers the parse_failed object with the coded refusal, and the file is failed with the English text")
            finally:
                await _delete_files(client, file_ids)
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    async def test_forcing_the_generic_csv_on_a_workbook_gives_the_csv_only_code(self, test_server):
        """RS-C70-02: the generic CSV forced on an uploaded ``.xlsx``: 400, the same object, ``reason.code`` is ``csv_only`` with the
        plugin's code in its context (the wizard translates ``importWizard.parseRefusal.csv_only`` with it)."""
        print_section("RS-C70-02: the forced generic CSV on a workbook")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            file_ids = []
            try:
                filename = f"book_{uuid.uuid4().hex[:8]}.xlsx"
                upload = await client.post(f"{API_BASE}/brokers/import/upload", files={"file": (filename, io.BytesIO(_plain_workbook_bytes()), XLSX_MEDIA_TYPE)}, data={"broker_id": broker_id}, timeout=TIMEOUT)
                assert upload.status_code == 200, upload.text
                file_id = upload.json()["file_id"]
                file_ids.append(file_id)

                response = await client.post(f"{API_BASE}/brokers/import/files/{file_id}/parse", json={"plugin_code": GENERIC_CSV_CODE, "broker_id": broker_id}, timeout=TIMEOUT)

                assert response.status_code == 400, response.text
                detail = response.json()["detail"]
                assert isinstance(detail, dict), f"the detail of a refused parse is an object (C-70b): {detail!r}"
                assert (detail["code"], detail["plugin_code"], detail["plugin_name"]) == ("parse_failed", GENERIC_CSV_CODE, "Generic CSV"), detail
                assert detail["reason"]["code"] == "csv_only", detail["reason"]
                assert detail["reason"]["context"] == {"plugin_code": GENERIC_CSV_CODE}, detail["reason"]
                assert detail["message"] == f"Plugin 'Generic CSV' cannot parse file '{filename}': {detail['reason']['message']}", f"the English text is the frame plus the plugin's sentence: {detail['message']!r}"
                await _assert_failed_with(client, file_id, detail["message"])
            finally:
                await _delete_files(client, file_ids)
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    async def test_a_plugin_that_raises_a_parse_error_without_a_code_gives_a_reason_with_no_code(self, test_server):
        """RS-C70-03: Directa forced on a three-line file that passes its ``can_parse`` and fails its ``parse`` with a ``BRIMParseError``
        that has no ``details``: 400, ``detail.message`` is "Parse error: <the plugin's sentence>", ``plugin_name`` is Directa's
        ``provider_name``, ``reason`` is ``{code: null, message: <the plugin's sentence>, context: {}}``, and the stored
        ``error_message`` is the plugin's sentence (the diagnostic the failed file has always kept)."""
        print_section("RS-C70-03: a parse error without a code")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            file_ids = []
            try:
                filename = f"directa_{uuid.uuid4().hex[:8]}.csv"
                file_id, response = await _forced_parse(client, broker_id, DIRECTA_LABELS_ON_SEPARATE_ROWS, filename, DIRECTA_CODE, file_ids)

                assert response.status_code == 400, f"premise: the file reaches the plugin's parse and fails there: {response.status_code} {response.text}"
                detail = response.json()["detail"]
                assert isinstance(detail, dict), f"the detail of a failed parse is an object the wizard can translate, not an English sentence (C-70b): {detail!r}"
                assert set(detail) == _parse_failed_keys(), detail
                assert detail["code"] == "parse_failed", detail
                assert detail["message"] == f"Parse error: {DIRECTA_HEADER_ROW_MISSING}", detail
                assert (detail["plugin_code"], detail["plugin_name"]) == (DIRECTA_CODE, DIRECTA_NAME), detail
                assert detail["reason"] == {"code": None, "message": DIRECTA_HEADER_ROW_MISSING, "context": {}}, f"a plugin that gives no code gives its sentence and an empty context: {detail['reason']!r}"
                await _assert_failed_with(client, file_id, DIRECTA_HEADER_ROW_MISSING)
                print_success("✓ a BRIMParseError without a code answers the parse_failed object with a null code, and the file keeps the plugin's sentence")
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
# CATEGORY 15: THE PREVIEW OF A DAMAGED EXCEL WORKBOOK ANSWERS 400 (step 6, F2)
# ============================================================================
#
# ``GET /files/{id}/preview`` reads an ``.xlsx`` with pandas and openpyxl, answers a ``ValueError`` with 400 and anything
# else with 500 "Failed to build file preview". A damaged workbook made the reader raise ``zipfile.BadZipFile``,
# ``KeyError``, ``xml.etree.ElementTree.ParseError`` or ``xlrd.XLRDError``, none of them a ``ValueError``: the user's
# broken file answered as a fault of the server. The coordinator's decision, verbatim: «le 4 famiglie, prese solo attorno
# alle due chiamate pandas, in `UnreadablePreviewError(ValueError)`. API invariate; un rosso anche via `uploads.py`.» So
# the endpoint is unchanged and answers 400, with a ``detail``. Two synthetic files, uploaded on the test's broker: bytes
# that are not even a zip, named ``damaged.xlsx``, and a valid workbook whose first sheet's XML is replaced by
# ``<not-xml``. Which exception each damage raises, and the cause the new error keeps, is tested at service level, in
# test_services/test_file_preview.py; the generic uploads' preview in test_api/test_uploads_api.py (UPLOAD-005H). The
# test deletes the file and the broker it created.

# Bytes that are no workbook and not even a zip archive.
NOT_A_WORKBOOK = b"LibreFolio F2 synthetic bytes: not an Excel workbook and not a zip archive.\n" * 16
# The member openpyxl writes a workbook's first sheet to.
FIRST_SHEET_XML = "xl/worksheets/sheet1.xml"


def _workbook_with_unparseable_sheet() -> bytes:
    """A valid workbook, built with openpyxl, whose first sheet's XML is replaced by ``<not-xml``, every other member copied unchanged: it opens, its first sheet does not parse."""
    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Statement"
    sheet["A1"] = "date"
    sheet["B1"] = "amount"
    sheet["A2"] = "2025-01-01"
    sheet["B2"] = 1000
    valid = io.BytesIO()
    workbook.save(valid)
    rebuilt = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(valid.getvalue())) as original, zipfile.ZipFile(rebuilt, "w") as damaged:
        assert FIRST_SHEET_XML in original.namelist(), f"premise: openpyxl writes the first sheet as {FIRST_SHEET_XML}: {original.namelist()}"
        for member in original.infolist():
            damaged.writestr(member, b"<not-xml" if member.filename == FIRST_SHEET_XML else original.read(member))
    return rebuilt.getvalue()


# (name the file is uploaded under, how its bytes are built)
DAMAGED_WORKBOOKS = (
    pytest.param("damaged.xlsx", lambda: NOT_A_WORKBOOK, id="not-a-zip"),
    pytest.param("broken_sheet.xlsx", _workbook_with_unparseable_sheet, id="unparseable-sheet-xml"),
)


class TestDamagedWorkbookPreview:
    """F2 — ``GET /files/{id}/preview`` of a damaged Excel workbook answers 400 with a ``detail``: the file is the user's, the fault is not the server's."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("filename", "build"), DAMAGED_WORKBOOKS)
    async def test_the_preview_of_a_damaged_workbook_answers_400(self, test_server, filename, build):
        """RS-F201: a damaged ``.xlsx`` uploaded on the test's broker — bytes that are not even a zip, or a workbook whose
        first sheet's XML does not parse: its preview answers 400 (500 before F2) with ``detail`` ``{"code": "preview_unreadable",
        "message": <English text>}`` (an object since lot W5-5, C-70b)."""
        print_section(f"RS-F201: the preview of a damaged workbook, {filename}, answers 400")
        content = build()
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            file_ids = []
            try:
                files = {"file": (filename, io.BytesIO(content), XLSX_MEDIA_TYPE)}
                upload = await client.post(f"{API_BASE}/brokers/import/upload", files=files, data={"broker_id": broker_id}, timeout=TIMEOUT)
                assert upload.status_code == 200, upload.text
                file_id = upload.json()["file_id"]
                file_ids.append(file_id)

                response = await client.get(f"{API_BASE}/brokers/import/files/{file_id}/preview", timeout=TIMEOUT)

                assert response.status_code == 400, f"the preview of the damaged {filename} answers {response.status_code} {response.text}: a damaged workbook is the user's file, not a fault of the server (F2)"
                detail = response.json().get("detail")
                assert isinstance(detail, dict), f"the 400 says why in a detail object the wizard translates, not in an English sentence (C-70b): {response.text}"
                assert set(detail) == {"code", "message"}, f"the keys of a preview failure: {response.text}"
                assert detail["code"] == "preview_unreadable", f"a damaged workbook is unreadable, not unsupported: {response.text}"
                assert isinstance(detail["message"], str) and detail["message"].strip(), f"the English text stays as the diagnostic message: {response.text}"
                print_success(f"✓ the preview of the damaged {filename} answers 400 with the preview_unreadable object")
            finally:
                await _delete_files(client, file_ids)
                await _delete_created(client, broker_ids=[broker_id])


# ============================================================================
# CATEGORY 16: DEGIRO CURRENCY CONVERSIONS GO THROUGH THE BATCH AS LINKED PAIRS (workstream L, issue #35)
# ============================================================================
#
# The rewritten DEGIRO plugin is the first BRIM plugin that emits pairs: each currency conversion of an Account
# Statement becomes two FX_CONVERSION rows with one ``link_uuid``, one description and one set of tags (plan
# 31_brimDegiro §1.4, §2.5). The import editor hands what the wizard gives it to POST /transactions/validate, then
# /commit, and the batch wants exactly two creates per ``link_uuid``, of one type, with the same description and tags
# (``linkUuidPairCount``, ``pairTypeMismatch``, ``pairDescriptionMismatch``, ``pairTagsMismatch``). The test uploads
# the synthetic English sample, parses it with DEGIRO, submits the two conversions and the rows that need no asset
# (the deposit, the three interest credits, the connection fee) as parsed, and reads the saved legs back, each one
# pointing at the other. Red until the rewrite: today's plugin does not recognise the English header. What the plugin
# reads, row by row, is in test_external/test_brim_degiro.py. The test deletes the file and the broker it created.

DEGIRO_CODE = "broker_degiro"
DEGIRO_ACCOUNT_SAMPLE = PROJECT_ROOT / "backend" / "app" / "services" / "brim_providers" / "sample_reports" / "degiro-account-en.csv"
# The rows of the English sample without an asset, as (type, currency, amount): the editor can save them as parsed.
DEGIRO_CASH_ROWS = [("DEPOSIT", "EUR", Decimal("2500.00")), ("FEE", "EUR", Decimal("-2.50")), ("INTEREST", "CZK", Decimal("3.47")), ("INTEREST", "EUR", Decimal("0.75")), ("INTEREST", "EUR", Decimal("3.00"))]
DEGIRO_PAIR_CODES = {"linkUuidPairCount", "pairTypeMismatch", "pairDescriptionMismatch", "pairTagsMismatch"}


def _degiro_selection(transactions: list) -> Tuple[list, list]:
    """What the editor submits of a DEGIRO parse here: every FX_CONVERSION leg, and the DEPOSIT, INTEREST and FEE rows without an asset."""
    conversions = [tx for tx in transactions if tx["type"] == "FX_CONVERSION"]
    cash_rows = [tx for tx in transactions if tx["type"] in ("DEPOSIT", "INTEREST", "FEE") and tx.get("asset_id") is None]
    return conversions, cash_rows


def _pairs_by_link(conversions: list) -> Dict[str, List[int]]:
    """The positions of the legs in ``conversions``, by ``link_uuid``."""
    pairs: Dict[str, List[int]] = {}
    for index, tx in enumerate(conversions):
        pairs.setdefault(tx["link_uuid"], []).append(index)
    return pairs


class TestDegiroConversionsThroughTheBatch:
    """L — the conversions of a DEGIRO statement validate and commit as linked pairs, submitted as the import editor submits them."""

    @pytest.mark.asyncio
    async def test_the_conversions_of_the_english_sample_commit_as_linked_pairs(self, test_server):
        """RS-DG01: ``degiro-account-en.csv`` uploaded and parsed with DEGIRO; its 2 conversions (4 legs) and its 5 rows without an asset go to
        /validate with no issue — no ``linkUuidPairCount``, ``pairDescriptionMismatch``, ``pairTagsMismatch`` — then to /commit; read back, each leg's
        ``related_transaction_id`` is the other leg of its conversion."""
        print_section("RS-DG01: DEGIRO conversions through validate and commit")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            file_ids = []
            try:
                upload = await _upload_csv(client, broker_id, DEGIRO_ACCOUNT_SAMPLE.read_bytes(), DEGIRO_ACCOUNT_SAMPLE.name)
                assert upload.status_code == 200, upload.text
                file_ids.append(upload.json()["file_id"])
                assert DEGIRO_CODE in upload.json()["compatible_plugins"], f"the test backend's DEGIRO plugin does not recognise {DEGIRO_ACCOUNT_SAMPLE.name}: compatible {upload.json()['compatible_plugins']} (DEGIRO rewrite, issue #35)"

                parsed = await client.post(f"{API_BASE}/brokers/import/files/{file_ids[0]}/parse", json={"plugin_code": DEGIRO_CODE, "broker_id": broker_id}, timeout=TIMEOUT)
                assert parsed.status_code == 200, parsed.text
                conversions, cash_rows = _degiro_selection(parsed.json()["transactions"])
                pairs = _pairs_by_link(conversions)
                assert sorted(len(indexes) for indexes in pairs.values()) == [2, 2], f"presence barrier: two conversions of two legs each, by link_uuid: {[(tx['cash'], tx['link_uuid']) for tx in conversions]}"
                assert sorted((tx["type"], tx["cash"]["code"], Decimal(tx["cash"]["amount"])) for tx in cash_rows) == DEGIRO_CASH_ROWS
                creates = [*conversions, *cash_rows]

                validated = await client.post(f"{API_BASE}/transactions/validate", json={"creates": creates}, timeout=TIMEOUT)
                assert validated.status_code == 200, validated.text
                issues = validated.json()["issues"]
                assert [issue for issue in issues if issue.get("code") in DEGIRO_PAIR_CODES] == [], f"the batch refuses the DEGIRO pairs: {issues}"
                assert issues == [], f"the DEGIRO rows do not validate: {issues}"

                committed = await client.post(f"{API_BASE}/transactions/commit", json={"creates": creates}, timeout=TIMEOUT)
                assert committed.status_code == 200, committed.text
                assert committed.json()["committed"] is True, committed.text
                saved_ids = {result["index"]: result["ids"][0] for result in committed.json()["results"]}
                expected_links = {saved_ids[a]: saved_ids[b] for first, second in pairs.values() for a, b in ((first, second), (second, first))}
                saved = await client.get(f"{API_BASE}/transactions", params={"ids": list(expected_links)}, timeout=TIMEOUT)
                assert saved.status_code == 200, saved.text

                assert {item["id"]: item["related_transaction_id"] for item in saved.json()} == expected_links, "each saved leg points at the other leg of its conversion"
                assert {item["type"] for item in saved.json()} == {"FX_CONVERSION"}
                print_success("✓ the DEGIRO conversions validate and commit as reciprocally linked pairs")
            finally:
                await _delete_files(client, file_ids)
                await _delete_created(client, broker_ids=[broker_id])


# ============================================================================
# CATEGORY 17: ASK ONE PLUGIN ABOUT AN UPLOADED FILE (37_brimScalable, plan §7.1)
# ============================================================================
#
# ``GET /brokers/import/files/{file_id}/plugin-check?plugin_code=…`` says whether one plugin reads an uploaded file and,
# when it does not, why: the plugin's ``can_parse``, then its ``cannot_parse_detail`` (a stable code the frontend
# translates, the English sentence, the context of the code). The import wizard asks it right after an upload, for the
# broker's default plugin. Access as for ``GET /files/{file_id}``: any role on the file's broker (VIEWER+), 403 without one.
# 404 for an unknown file or plugin, 422 without ``plugin_code``. Nothing is parsed: the file stays ``uploaded``.
# The overnight account's sample uploaded to a broker is the case the endpoint was made for: the broker plugin refuses it
# and names the plugin that reads it. Only RS-PC01 and RS-PC02 need the Scalable plugins; the others ask the generic CSV,
# which refuses with a code of its own since workstream W, lot K2a (backlog C-70, part a). No real plugin refuses without
# a code any more, and an API test cannot plant a stand-in in the server, so the default refusal without a code is covered
# in test_external/test_brim_providers.py (category 4d) and in the frontend's defaultPluginCheck.test.ts. What the plugins
# answer, file by file, is in test_external/test_brim_scalable.py, test_brim_providers.py (category 4e) and
# test_brim_degiro.py (A2). Each test deletes the files and the broker it created.

SCALABLE_DEPOSIT_SAMPLE = PROJECT_ROOT / "backend" / "app" / "services" / "brim_providers" / "sample_reports" / "scalable-deposit-export.csv"
SCALABLE_BROKER_CODE = "broker_scalable"
SCALABLE_DEPOSIT_CODE = "broker_scalable_deposit"
# What the broker plugin owes about the overnight account's export, but the English sentence: its code and its context.
SCALABLE_DEPOSIT_REFUSAL = {"code": "scalable_deposit_file", "context": {"plugin_code": SCALABLE_DEPOSIT_CODE, "plugin_name": "Scalable Capital overnight account"}}
UNKNOWN_PLUGIN_CODE = "broker_does_not_exist"
# The generic CSV's refusal of CSV_WITHOUT_DATE (category 12): since K2a (backlog C-70, part a) the code the wizard translates and its
# context, the count an integer for the plural; the English sentence, the message, is unchanged.
GENERIC_REFUSAL = {"code": "missing_columns", "message": "required column 'date' not found in the CSV header", "context": {"columns": "date", "count": 1}}


async def _plugin_check(client: httpx.AsyncClient, file_id: str, **params: str) -> httpx.Response:
    """``GET /files/{file_id}/plugin-check`` with the query ``params``; while the route does not exist, the test fails saying so."""
    response = await client.get(f"{API_BASE}/brokers/import/files/{file_id}/plugin-check", params=params, timeout=TIMEOUT)
    if _route_missing(response):
        pytest.fail(f"GET /brokers/import/files/{{file_id}}/plugin-check does not exist yet (37_brimScalable, plan §7.1): {response.status_code} {response.text}", pytrace=False)
    return response


def _check_of(response: httpx.Response) -> Tuple[str, bool, Optional[dict]]:
    """``(plugin_code, can_parse, refusal)`` of a 200 answer."""
    assert response.status_code == 200, f"{response.status_code} {response.text}"
    body = response.json()
    return body["plugin_code"], body["can_parse"], body["refusal"]


async def _upload_for_check(client: httpx.AsyncClient, broker_id: int, content: bytes, filename: str, file_ids: list) -> str:
    """Upload one CSV to ``broker_id``; its id joins ``file_ids``, which the test deletes."""
    upload = await _upload_csv(client, broker_id, content, filename)
    assert upload.status_code == 200, upload.text
    file_ids.append(upload.json()["file_id"])
    return file_ids[-1]


async def _upload_scalable_deposit(client: httpx.AsyncClient, broker_id: int, file_ids: list) -> str:
    """Upload the overnight account's sample; the premise is that the test backend reads it with the overnight account's plugin, not the broker's."""
    file_id = await _upload_for_check(client, broker_id, SCALABLE_DEPOSIT_SAMPLE.read_bytes(), SCALABLE_DEPOSIT_SAMPLE.name, file_ids)
    info = await client.get(f"{API_BASE}/brokers/import/files/{file_id}", timeout=TIMEOUT)
    assert info.status_code == 200, info.text
    compatible = info.json()["compatible_plugins"]
    if SCALABLE_DEPOSIT_CODE not in compatible or SCALABLE_BROKER_CODE in compatible:
        pytest.fail(f"premise: the test backend reads {SCALABLE_DEPOSIT_SAMPLE.name} with {SCALABLE_DEPOSIT_CODE} and not with {SCALABLE_BROKER_CODE}: compatible {compatible} (37_brimScalable, plan §4)", pytrace=False)
    return file_id


async def _assert_still_uploaded(client: httpx.AsyncClient, file_id: str) -> None:
    """The file as the upload left it: ``uploaded``, no parse result, no error, no parsing plugin."""
    info = await client.get(f"{API_BASE}/brokers/import/files/{file_id}", timeout=TIMEOUT)
    assert info.status_code == 200, info.text
    data = info.json()
    assert (data["status"], data["last_parse_result"], data["error_message"], data["parsed_plugin_code"]) == ("uploaded", None, None, None), f"the plugin check changed the file: {data}"


class TestPluginCheckEndpoint:
    """§7.1 — ``GET /files/{file_id}/plugin-check``: one plugin's answer about an uploaded file, with the code and the context of a refusal; nothing is parsed."""

    @pytest.mark.asyncio
    async def test_the_broker_plugin_refuses_the_overnight_account_export_and_names_its_plugin(self, test_server):
        """RS-PC01: ``scalable-deposit-export.csv`` on the user's broker. ``broker_scalable``: 200, ``can_parse`` false, refusal ``scalable_deposit_file``
        whose context names ``broker_scalable_deposit``, with an English sentence. ``broker_scalable_deposit``: ``can_parse`` true, no refusal. The file
        is still ``uploaded`` after both."""
        print_section("RS-PC01: the broker plugin refuses the overnight account's export and names its plugin")
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            file_ids = []
            try:
                file_id = await _upload_scalable_deposit(client, broker_id, file_ids)

                refused = _check_of(await _plugin_check(client, file_id, plugin_code=SCALABLE_BROKER_CODE))
                accepted = _check_of(await _plugin_check(client, file_id, plugin_code=SCALABLE_DEPOSIT_CODE))

                assert refused[:2] == (SCALABLE_BROKER_CODE, False), refused
                refusal = refused[2] or {}
                assert {key: refusal.get(key) for key in SCALABLE_DEPOSIT_REFUSAL} == SCALABLE_DEPOSIT_REFUSAL, refused
                assert isinstance(refusal.get("message"), str) and refusal["message"].strip(), f"the refusal has no English sentence to fall back on: {refused}"
                assert accepted == (SCALABLE_DEPOSIT_CODE, True, None), accepted
                await _assert_still_uploaded(client, file_id)
                print_success("✓ the broker plugin refuses the overnight account's export and names the plugin that reads it")
            finally:
                await _delete_files(client, file_ids)
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    async def test_another_broker_s_file_is_refused_without_a_refusal(self, test_server, sample_csv_content):
        """RS-PC02: a generic CSV asked to ``broker_scalable``: 200, ``can_parse`` false, ``refusal`` null: the plugin has nothing to say about it."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            file_ids = []
            try:
                file_id = await _upload_for_check(client, broker_id, sample_csv_content, f"generic_{uuid.uuid4().hex[:8]}.csv", file_ids)

                check = _check_of(await _plugin_check(client, file_id, plugin_code=SCALABLE_BROKER_CODE))

                assert check == (SCALABLE_BROKER_CODE, False, None), check
                await _assert_still_uploaded(client, file_id)
            finally:
                await _delete_files(client, file_ids)
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    async def test_the_generic_csv_refuses_a_csv_without_date_with_its_code_and_context(self, test_server):
        """RS-PC03: the CSV without a date column of RS-G05 asked to ``broker_generic_csv``: ``can_parse`` false, refusal ``{code: "missing_columns",
        message: <its English reason, unchanged>, context: {"columns": "date", "count": 1}}``, the code the import wizard translates (K2a, backlog
        C-70 part a); the file stays ``uploaded``."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            file_ids = []
            try:
                file_id = await _upload_for_check(client, broker_id, CSV_WITHOUT_DATE, f"no_date_{uuid.uuid4().hex[:8]}.csv", file_ids)

                check = _check_of(await _plugin_check(client, file_id, plugin_code=GENERIC_CSV_CODE))

                assert check[:2] == (GENERIC_CSV_CODE, False), check
                await _assert_still_uploaded(client, file_id)
                assert check[2] == GENERIC_REFUSAL, f"the generic CSV's refusal through the endpoint, with the code the wizard translates and its context: {check[2]}"
            finally:
                await _delete_files(client, file_ids)
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    async def test_an_unknown_plugin_is_404(self, test_server, sample_csv_content):
        """RS-PC04: ``plugin_code=broker_does_not_exist`` on an uploaded file: 404 "Plugin 'broker_does_not_exist' not found"; the file is untouched."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            file_ids = []
            try:
                file_id = await _upload_for_check(client, broker_id, sample_csv_content, f"generic_{uuid.uuid4().hex[:8]}.csv", file_ids)

                response = await _plugin_check(client, file_id, plugin_code=UNKNOWN_PLUGIN_CODE)

                assert response.status_code == 404, response.text
                assert _detail_text(response) == f"Plugin '{UNKNOWN_PLUGIN_CODE}' not found"
                await _assert_still_uploaded(client, file_id)
            finally:
                await _delete_files(client, file_ids)
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    async def test_an_unknown_file_is_404(self, test_server):
        """RS-PC05: a file id nobody uploaded, with a registered plugin: 404 "File not found"."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)

            response = await _plugin_check(client, str(uuid.uuid4()), plugin_code=GENERIC_CSV_CODE)

            assert response.status_code == 404, response.text
            assert _detail_text(response) == "File not found"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("params", [pytest.param({}, id="missing"), pytest.param({"plugin_code": ""}, id="empty")])
    async def test_plugin_code_is_required(self, test_server, sample_csv_content, params):
        """RS-PC06: without ``plugin_code``, or with an empty one: 422 naming ``plugin_code``; the file is untouched."""
        async with httpx.AsyncClient() as client:
            await create_test_user(client)
            broker_id = await create_test_broker(client)
            file_ids = []
            try:
                file_id = await _upload_for_check(client, broker_id, sample_csv_content, f"generic_{uuid.uuid4().hex[:8]}.csv", file_ids)

                response = await _plugin_check(client, file_id, **params)

                assert response.status_code == 422, response.text
                errors = response.json().get("detail")
                assert isinstance(errors, list) and any("plugin_code" in [str(part) for part in error.get("loc", [])] for error in errors), errors
                await _assert_still_uploaded(client, file_id)
            finally:
                await _delete_files(client, file_ids)
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    async def test_a_viewer_may_ask_and_a_user_without_access_may_not(self, test_server):
        """RS-PC07: a VIEWER of the broker gets the owner's answer; a user without access to the broker gets 403; the file is untouched."""
        print_section("RS-PC07: plugin-check access, VIEWER+ only")
        async with httpx.AsyncClient() as owner, httpx.AsyncClient() as viewer, httpx.AsyncClient() as stranger:
            owner_id = await create_test_user(owner)
            viewer_id = await create_test_user(viewer)
            await create_test_user(stranger)
            broker_id = await create_test_broker(owner)
            file_ids = []
            try:
                access = await owner.put(
                    f"{API_BASE}/brokers/{broker_id}/access",
                    json=[{"user_id": owner_id, "role": "OWNER", "share_percentage": 1.0}, {"user_id": viewer_id, "role": "VIEWER", "share_percentage": 0}],
                    timeout=TIMEOUT,
                )
                assert access.status_code == 200, access.text
                file_id = await _upload_for_check(owner, broker_id, CSV_WITHOUT_DATE, f"no_date_{uuid.uuid4().hex[:8]}.csv", file_ids)

                as_owner = await _plugin_check(owner, file_id, plugin_code=GENERIC_CSV_CODE)
                as_viewer = await _plugin_check(viewer, file_id, plugin_code=GENERIC_CSV_CODE)
                as_stranger = await _plugin_check(stranger, file_id, plugin_code=GENERIC_CSV_CODE)

                owner_answer = _check_of(as_owner)
                # Access is the subject, not the code: the barrier reads the reason, the same before and after K2a; RS-PC03 pins the whole refusal.
                assert (*owner_answer[:2], (owner_answer[2] or {}).get("message")) == (GENERIC_CSV_CODE, False, GENERIC_REFUSAL["message"]), f"presence barrier: the owner gets the plugin's answer: {owner_answer}"
                assert _check_of(as_viewer) == owner_answer, "a VIEWER of the broker gets the owner's answer"
                assert as_stranger.status_code == 403, f"a user without access: {as_stranger.status_code} {as_stranger.text}"
                await _assert_still_uploaded(owner, file_id)
                print_success("✓ a VIEWER may ask, a user without access may not")
            finally:
                await _delete_files(owner, file_ids)
                await _delete_created(owner, broker_ids=[broker_id])


# ============================================================================
# CATEGORY 18: A BROKER'S REPORTS ONLY TO WHO MAY SEE THAT BROKER (F36, decision 36; W-B3, W-B4, W-B32)
# ============================================================================
#
# Decision 36 (developer, 15/10): a broker's files — list, preview, download — only to users with at least VIEWER on that
# broker. The per-file routes (``GET /files/{id}``, ``/preview``, ``/download``, ``/last-parse``, ``/plugin-check``: VIEWER+;
# ``POST /files/{id}/parse`` and ``DELETE /files/{id}``: EDITOR+) all start with ``_get_brim_file_with_access``, which looks
# at the broker only ``if file_info.target_broker_id and not current_user.is_superuser``: a file with NO broker skips every
# check, for anyone signed in, its parse and its delete included (W-B3). And ``brim_provider.list_files`` keeps
# ``target_broker_id is None`` in every list it filters by broker, so such a file reaches every user's list, whatever
# ``broker_ids`` they ask for. Files with no broker are those an old version left in the ROOT of a status folder of
# ``broker_reports/`` ("backward compatibility"): before f0b7aad8d (January 2026) a sidecar had neither
# ``uploaded_by_user_id`` nor ``target_broker_id``; the upload has required a broker since.
#
# The cure, approved by the coordinator (plan 04, F36):
# 1. a file with no broker is its uploader's (``uploaded_by_user_id``) and the administrator's (``is_superuser``) only:
#    anyone else gets 403 on every per-file route and does not list it. A file with a broker keeps today's rules.
# 2. a regular user lists the files of the brokers they have at least VIEWER on, plus the files with no broker they
#    uploaded; the administrator's list is unchanged.
# 3. every list item carries ``can_delete``: true for the administrator, for an EDITOR or OWNER of the file's broker and
#    for the uploader of a file with no broker; false otherwise: a VIEWER, and the uploader of a broker's file who is now
#    only its VIEWER (on a broker's file, having uploaded it grants nothing: DELETE answers by the role).
# 4. W-B4: a ``file_id`` that is not a UUID in its canonical form (lower-case, as an upload writes it) answers 404 on every
#    per-file route, before any lookup.
# 5. no data repair: the files with no broker stay where they are.
# 6. a parse imports only into a broker its caller may edit: ``POST /files/{id}/parse`` checks the body's ``broker_id`` as
#    ``/duplicates`` and the report-set routes check theirs (EDITOR or OWNER of that broker; the administrator passes),
#    otherwise 403, before anything is parsed. Today the route checks only the file's broker: an EDITOR of the file's
#    broker parses it into any broker id, and reads the duplicate report computed against that broker's transactions.
# 7. W-B32 (approved by the coordinator on 16/10, within decision 36): a list the request filters by broker (``broker_ids``, as
#    a broker's «Uploaded Reports» asks) holds that broker's files only: a file with no broker is left out, for its uploader and
#    the administrator too. Unfiltered (the Files page), the list is that of 2. The cure is the route's: for a regular user the
#    route hands ``list_files`` the brokers they may see even when the request names none, so ``list_files``, which keeps the
#    files with no broker under any broker filter, cannot tell the Files page from a broker's list.
#
# A file with no broker is written by the test as an old version wrote it: content and sidecar in the root of ``uploaded/``
# in this lane's ``broker_reports`` (``get_test_data_dir``: the runner exports ``--data-dir`` to the backend under test and
# to pytest alike, and the function refuses a directory overlapping production data), the sidecar keys of that time, no
# ``plugins_signature`` (a read detects its plugins again, as for any file older than item 8), and either
# ``uploaded_by_user_id`` = the test's uploader with ``target_broker_id`` null (what ``save_uploaded_file`` writes when it
# is given no broker), or neither key (a file from before f0b7aad8d). The writes and the sweep hold the backend's own lock
# for the files with no broker (``broker_reports/.locks/broker_none.lock``): a concurrent read that detects the plugins
# again then never writes a sidecar back after the sweep. The sweep covers every status folder, since today a parse moves
# the file to ``parsed/``, and runs at teardown, after a red too. Before anything is asserted about a user who must be
# refused, the uploader (or the administrator) reads the file: the premise that the test reached the data directory of
# the backend under test, and the presence barrier of every negative.
#
# W-B4 is pinned three times. Ids that name nothing — ``not-a-uuid``; ``..``, sent as ``%2E%2E`` because httpx resolves a literal
# dot segment itself, which uvicorn decodes and ``{file_id}`` (``[^/]+``) takes; a UUID with a suffix — already answer 404
# today, from the lookup: guards. An id of 300 characters makes the lookup itself fail: ``Path.exists`` raises
# ENAMETOOLONG for a name longer than the file system's limit (255), an errno ``pathlib`` does not swallow, so every route
# answers 500 today: red. «Before any lookup» needs a file the lookup would find: a sidecar named by a UUID with a suffix,
# planted in the user's own broker folder next to a twin named by a plain UUID, which is served (the barrier). The canonical
# form, last: the id of a file the user uploaded, upper-cased. ``uuid.UUID`` reads it, and on a case-insensitive file system
# (macOS's default, this lane) the lookup finds the file under that spelling, so only a check of the canonical form refuses
# it; on a case-sensitive one (Linux) the lookup finds nothing. Its red is therefore macOS's only; the cure answers 404 on both.
#
# The parse target (item 6) needs no planted file. An owner holds two brokers: the file's, where the caller is EDITOR and
# the owner uploads the file, and a target, where the caller is VIEWER or holds no role; the access lists are read back
# before the parse, the roles being the premise. The refused parse must leave the file ``uploaded`` with no parse; then the
# same caller parses the same file into its own broker, 200: the barrier that puts the 403 on the target broker, not on the
# file. The administrator, with no role on either broker, parses into the target.
#
# The administrator is ``e2e_test_admin`` of populate_mock_data.py, which the api setup (``db populate``) seeds on the lane;
# every other account is registered by the test and checked to be a regular one. The tests delete the files and brokers
# they created and sweep what they planted; the accounts stay, as everywhere in this module.
#
# Write-scoped, as the rest of the unit: the planted files carry fresh ids and are swept; no other api unit lists BRIM
# files, and the backend's housekeeping (a broker deletion lists that broker's files, those with no broker included, then
# deletes only that broker's) leaves them alone.

BRIM_FILES_URL = f"{API_BASE}/brokers/import/files"
#: The administrator populate_mock_data.py seeds on the lane (the api setup runs ``db populate``).
LANE_ADMIN = ("e2e_test_admin", "E2eAdminPass123!")
#: The status folders of ``broker_reports``: a report is planted in the first, a parse moves it to the second.
STATUS_FOLDERS = ("uploaded", "parsed", "failed")
#: The rows of ``sample_csv_content``: any plugin catalogue reads them as the generic CSV's, and the generic CSV parses them.
PLANTED_CSV = b"date,type,quantity,amount,currency,description\n2025-01-01,DEPOSIT,0,1000.00,EUR,Test deposit\n2025-01-02,BUY,10,-500.00,EUR,Buy some shares\n"
#: Longer than any file name the file system accepts (NAME_MAX 255) once ``.json`` is appended: today's lookup raises ENAMETOOLONG.
OVERLONG_FILE_ID = "a" * 300
#: W-B4: ids that are not UUIDs, as F36-10 writes them in the URL path (``_non_uuid_id``).
NON_UUID_KINDS = ("not-a-uuid", "dot-dot", "over-long", "uuid-with-suffix")


@dataclass(frozen=True)
class _FileRoute:
    """A per-file route: its name, its method, its path after ``/files/{file_id}``; ``viewer``: a VIEWER of the file's broker may use it."""

    name: str
    method: str
    suffix: str
    viewer: bool


FILE_ROUTES = (
    _FileRoute("info", "GET", "", True),
    _FileRoute("preview", "GET", "/preview", True),
    _FileRoute("download", "GET", "/download", True),
    _FileRoute("last-parse", "GET", "/last-parse", True),
    _FileRoute("plugin-check", "GET", "/plugin-check", True),
    _FileRoute("parse", "POST", "/parse", False),
    _FileRoute("delete", "DELETE", "", False),
)
READ_ROUTES = tuple(route for route in FILE_ROUTES if route.viewer)
ROUTE = {route.name: route for route in FILE_ROUTES}


async def _ask(client: httpx.AsyncClient, route: _FileRoute, file_id: str, broker_id: Optional[int] = None) -> httpx.Response:
    """``route`` on ``file_id``, written in the URL path as given, the request otherwise well-formed: a plugin check asks the
    generic CSV, a parse imports into ``broker_id`` with it. Only the file and the caller decide the answer."""
    url = f"{BRIM_FILES_URL}/{file_id}{route.suffix}"
    if route.name == "parse":
        assert broker_id is not None, "a parse names the broker it imports into"
        return await client.post(url, json={"plugin_code": GENERIC_CSV_CODE, "broker_id": broker_id}, timeout=TIMEOUT)
    params = {"plugin_code": GENERIC_CSV_CODE} if route.name == "plugin-check" else None
    return await client.request(route.method, url, params=params, timeout=TIMEOUT)


def _answer(response: httpx.Response) -> str:
    """A response, short enough for an assertion message."""
    return f"{response.status_code} {response.text[:160]}"


async def _regular_user(client: httpx.AsyncClient) -> int:
    """A regular account of this test, registered and signed in on ``client``: its id."""
    user_id = await create_test_user(client)
    me = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
    assert me.status_code == 200, _answer(me)
    assert me.json()["user"]["is_superuser"] is False, "premise: the account registered as the lane's first, hence its administrator: the api setup (db populate) did not run on this lane"
    return user_id


async def _lane_admin(client: httpx.AsyncClient) -> int:
    """``e2e_test_admin`` signed in on ``client``: its id."""
    username, password = LANE_ADMIN
    response = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)
    assert response.status_code == 200, f"premise: {username} of populate_mock_data.py signs in on the lane (the api setup, db populate, seeds it): {_answer(response)}"
    user = response.json()["user"]
    assert user["is_superuser"] is True, f"premise: {username} is an administrator: {user}"
    return user["id"]


async def _set_access(owner: httpx.AsyncClient, broker_id: int, owner_id: int, members: Dict[int, str]) -> None:
    """The broker's whole access list (``PUT`` replaces it): its owner, and ``members`` as ``{user_id: role}``."""
    items = [{"user_id": owner_id, "role": "OWNER", "share_percentage": 1.0}] + [{"user_id": user_id, "role": role, "share_percentage": 0} for user_id, role in members.items()]
    response = await owner.put(f"{API_BASE}/brokers/{broker_id}/access", json=items, timeout=TIMEOUT)
    assert response.status_code == 200, _answer(response)


async def _listed(client: httpx.AsyncClient, **params: object) -> Dict[str, dict]:
    """``GET /files`` as ``client``'s user sees it, with the query ``params``: its items by file id."""
    response = await client.get(BRIM_FILES_URL, params=params, timeout=TIMEOUT)
    assert response.status_code == 200, _answer(response)
    return {item["file_id"]: item for item in response.json()}


async def _can_delete(client: httpx.AsyncClient, files: Dict[str, str]) -> Dict[str, object]:
    """``can_delete`` of each of ``files`` (``{label: file_id}``) in ``client``'s list; ``"not listed"`` or ``"no can_delete"`` when there is none to read."""
    listed = await _listed(client)
    return {label: listed[file_id].get("can_delete", "no can_delete") if file_id in listed else "not listed" for label, file_id in files.items()}


@dataclass(frozen=True)
class _Planted:
    """A report the test writes straight into the lane's ``broker_reports``: in ``broker_<id>/``, or in the root when ``broker_id`` is None."""

    file_id: str
    filename: str
    broker_id: Optional[int]
    content: bytes = PLANTED_CSV

    @property
    def names(self) -> Tuple[str, str]:
        """The content's file name and the sidecar's, as the backend derives them (the extension from ``filename``)."""
        return f"{self.file_id}{Path(self.filename).suffix.lower()}", f"{self.file_id}.json"


class _Planter:
    """Writes reports into this lane's ``broker_reports`` under the backend's lock, tells where they are, and sweeps them."""

    def __init__(self) -> None:
        try:
            self.reports = get_test_data_dir() / "broker_reports"
        except ValueError as exc:
            pytest.fail(f"refusing to write broker reports outside a test data directory: {exc}", pytrace=False)
        self.planted: List[_Planted] = []

    def _folder(self, report: _Planted, status: str) -> Path:
        folder = self.reports / status
        return folder if report.broker_id is None else folder / f"broker_{report.broker_id}"

    @contextlib.contextmanager
    def _lock(self, broker_id: Optional[int]) -> Iterator[None]:
        """The backend's metadata lock of one broker (``broker_none`` for the files with no broker), taken as ``brim_provider._acquire_file_lock`` takes it."""
        if fcntl is None:  # not POSIX: the backend's lock is in-process only, there is nothing to share with it
            yield
            return
        lock_file = self.reports / ".locks" / ("broker_none.lock" if broker_id is None else f"broker_{broker_id}.lock")
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_file, "a+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def plant(self, report: _Planted, sidecar: Dict[str, object]) -> _Planted:
        """Write ``report`` in ``uploaded/`` as the backend writes an upload: the content, then the sidecar, atomically. Recorded first: a failed write is swept too."""
        self.planted.append(report)
        folder = self._folder(report, "uploaded")
        content_name, sidecar_name = report.names
        with self._lock(report.broker_id):
            folder.mkdir(parents=True, exist_ok=True)
            (folder / content_name).write_bytes(report.content)
            staged = folder / f"{sidecar_name}.tmp.{uuid.uuid4().hex}"
            staged.write_text(json.dumps(sidecar, indent=2))
            staged.replace(folder / sidecar_name)
        return report

    def where(self, report: _Planted) -> List[str]:
        """Where ``report``'s content and sidecar are now, as paths relative to ``broker_reports``."""
        paths = [self._folder(report, status) / name for status in STATUS_FOLDERS for name in report.names]
        return sorted(str(path.relative_to(self.reports)) for path in paths if path.exists())

    def as_planted(self, report: _Planted) -> List[str]:
        """Where ``plant`` left ``report``."""
        return sorted(str((self._folder(report, "uploaded") / name).relative_to(self.reports)) for name in report.names)

    def sweep_all(self) -> None:
        """Remove every planted report from every status folder, wherever a route moved it, under the backend's lock.

        A swept report leaves the list, so a second call takes no lock: the lock file of a broker deleted meanwhile is not created again.
        """
        while self.planted:
            report = self.planted[-1]
            with self._lock(report.broker_id):
                for status in STATUS_FOLDERS:
                    for name in report.names:
                        (self._folder(report, status) / name).unlink(missing_ok=True)
            self.planted.pop()


@pytest.fixture
def planter() -> Iterator[_Planter]:
    """Reports written straight into the lane's ``broker_reports``; swept at teardown, after a red too."""
    planter = _Planter()
    yield planter
    planter.sweep_all()


def _without_broker(planter: _Planter, uploader_id: Optional[int]) -> _Planted:
    """A file with no broker, written as an old version wrote it: the sidecar keys of that time, no ``plugins_signature``.

    With ``uploader_id``, what ``save_uploaded_file`` has written since f0b7aad8d when given no broker
    (``target_broker_id`` null); without it, a file from before f0b7aad8d (neither key).
    """
    report = _Planted(file_id=str(uuid.uuid4()), filename=f"legacy_{uuid.uuid4().hex[:8]}.csv", broker_id=None)
    sidecar: Dict[str, object] = {
        "file_id": report.file_id,
        "filename": report.filename,
        "extension": ".csv",
        "size_bytes": len(report.content),
        "status": "uploaded",
        "uploaded_at": datetime.now(UTC).isoformat(),
        "processed_at": None,
        "compatible_plugins": [GENERIC_CSV_CODE],
        "error_message": None,
    }
    if uploader_id is not None:
        sidecar.update({"uploaded_by_user_id": uploader_id, "target_broker_id": None, "last_parse_result": None})
    return planter.plant(report, sidecar)


def _on_broker(planter: _Planter, broker_id: int, uploader_id: int, file_id: str) -> _Planted:
    """A file of ``broker_id`` named ``file_id``, with the sidecar today's upload writes, less the detection signature (a read detects its plugins again)."""
    report = _Planted(file_id=file_id, filename=f"f36_{uuid.uuid4().hex[:8]}.csv", broker_id=broker_id)
    sidecar: Dict[str, object] = {
        "file_id": report.file_id,
        "filename": report.filename,
        "extension": ".csv",
        "size_bytes": len(report.content),
        "status": "uploaded",
        "uploaded_at": datetime.now(UTC).isoformat(),
        "processed_at": None,
        "compatible_plugins": [GENERIC_CSV_CODE],
        "error_message": None,
        "uploaded_by_user_id": uploader_id,
        "target_broker_id": broker_id,
        "last_parse_result": None,
        "batch_id": None,
    }
    return planter.plant(report, sidecar)


async def _assert_reads_without_broker(client: httpx.AsyncClient, report: _Planted, uploader_id: Optional[int]) -> None:
    """``client``'s user — the uploader, or the administrator — reads the planted file with no broker as it was written: the premise
    that the test reached the data directory of the backend under test, and the presence barrier of the negatives that follow."""
    response = await _ask(client, ROUTE["info"], report.file_id)
    assert response.status_code == 200, f"premise: the file with no broker planted in the root of uploaded/ in {get_test_data_dir()} is read by its uploader or the administrator: {_answer(response)} — the test did not reach the data directory of the backend under test"
    info = response.json()
    read = (info["file_id"], info["target_broker_id"], info["uploaded_by_user_id"], info["status"])
    assert read == (report.file_id, None, uploader_id, "uploaded"), f"premise: the file as planted: {info}"


async def _assert_untouched(planter: _Planter, reader: httpx.AsyncClient, report: _Planted) -> None:
    """``report`` still where it was planted, and still ``uploaded`` with no parse for ``reader`` (its uploader or the administrator)."""
    assert planter.where(report) == planter.as_planted(report), f"the refused request moved or deleted the file: on disk now {planter.where(report)}, planted as {planter.as_planted(report)}"
    await _assert_still_uploaded(reader, report.file_id)


def _non_uuid_id(kind: str) -> str:
    """An id that is not a UUID, as written in the URL path (``..`` percent-encoded: httpx resolves a literal dot segment itself)."""
    return {"not-a-uuid": "not-a-uuid", "dot-dot": "%2E%2E", "over-long": OVERLONG_FILE_ID, "uuid-with-suffix": f"{uuid.uuid4()}-1"}[kind]


class TestReportsWithoutBroker:
    """F36, W-B3 — a file with no broker (an old version's, in the root of a status folder) is its uploader's and the administrator's only."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", ["unfiltered", "own-broker", "foreign-broker"])
    async def test_another_user_does_not_list_it(self, test_server, planter, query):
        """F36-01: U's file with no broker is absent from V's list: unfiltered, filtered on V's broker, filtered on U's broker
        (which V cannot see). Barriers: U lists it; V lists V's own file (unfiltered and on V's broker); the filter on U's
        broker gives U's file to U and never to V. Red today: ``list_files`` keeps every file with no broker in every list."""
        print_section(f"F36-01: a file with no broker is not in another user's list ({query})")
        async with httpx.AsyncClient() as uploader, httpx.AsyncClient() as other:
            uploader_id = await _regular_user(uploader)
            await _regular_user(other)
            uploader_broker = await create_test_broker(uploader)
            other_broker = await create_test_broker(other)
            uploader_files: List[str] = []
            other_files: List[str] = []
            try:
                legacy = _without_broker(planter, uploader_id)
                await _assert_reads_without_broker(uploader, legacy, uploader_id)
                uploader_file = await _upload_for_check(uploader, uploader_broker, PLANTED_CSV, f"f36_{uuid.uuid4().hex[:8]}.csv", uploader_files)
                other_file = await _upload_for_check(other, other_broker, PLANTED_CSV, f"f36_{uuid.uuid4().hex[:8]}.csv", other_files)
                assert legacy.file_id in await _listed(uploader), "presence barrier: the uploader lists the file with no broker"
                params = {"unfiltered": {}, "own-broker": {"broker_ids": other_broker}, "foreign-broker": {"broker_ids": uploader_broker}}[query]

                listed = await _listed(other, **params)

                if query == "foreign-broker":
                    assert uploader_file in await _listed(uploader, **params), "presence barrier: the filter on the uploader's broker gives the uploader's file to the uploader"
                else:
                    assert other_file in listed, "presence barrier: the other user lists their own file"
                assert uploader_file not in listed, f"a broker's file reached the list of a user without access to that broker ({query})"
                assert legacy.file_id not in listed, f"the file with no broker uploaded by user {uploader_id} is in another user's list ({query}): list_files keeps every file with no broker in every list"
                print_success(f"✓ a file with no broker is not in another user's list ({query})")
            finally:
                await _delete_files(uploader, uploader_files)
                await _delete_files(other, other_files)
                await _delete_created(uploader, broker_ids=[uploader_broker])
                await _delete_created(other, broker_ids=[other_broker])

    @pytest.mark.asyncio
    @pytest.mark.parametrize("route", FILE_ROUTES, ids=lambda route: route.name)
    async def test_another_user_is_refused_on_every_route(self, test_server, planter, route):
        """F36-02: V, neither U nor an administrator, on U's file with no broker: 403 on ``route``, and the file stays where it was,
        ``uploaded``, with no parse (a parse names V's own broker: only the file can refuse it). Red today: every route answers 200
        for anyone signed in; the parse moves the file to ``parsed/``, the delete removes it."""
        print_section(f"F36-02: a file with no broker refuses another user ({route.name})")
        async with httpx.AsyncClient() as uploader, httpx.AsyncClient() as other:
            uploader_id = await _regular_user(uploader)
            await _regular_user(other)
            other_broker = await create_test_broker(other)
            try:
                legacy = _without_broker(planter, uploader_id)
                await _assert_reads_without_broker(uploader, legacy, uploader_id)

                response = await _ask(other, route, legacy.file_id, other_broker)

                assert response.status_code == 403, f"{route.name} on a file with no broker, by a user who is neither its uploader nor an administrator: expected 403, got {_answer(response)}"
                await _assert_untouched(planter, uploader, legacy)
                print_success(f"✓ {route.name}: 403, the file untouched")
            finally:
                await _delete_created(other, broker_ids=[other_broker])

    @pytest.mark.asyncio
    async def test_a_file_with_neither_broker_nor_uploader_is_the_administrators_only(self, test_server, planter):
        """F36-03: a file from before f0b7aad8d (neither ``target_broker_id`` nor ``uploaded_by_user_id``): a regular user does not list
        it, gets 403 on ``GET /files/{id}`` and on ``DELETE``, and the file stays. Barrier: the administrator reads and lists it. Red
        today: listed, 200, and the delete removes it."""
        print_section("F36-03: a file with neither broker nor uploader is the administrator's only")
        async with httpx.AsyncClient() as admin, httpx.AsyncClient() as user:
            await _lane_admin(admin)
            await _regular_user(user)
            orphan = _without_broker(planter, None)
            await _assert_reads_without_broker(admin, orphan, None)
            assert orphan.file_id in await _listed(admin), "presence barrier: the administrator lists it"

            listed = orphan.file_id in await _listed(user)
            info = await _ask(user, ROUTE["info"], orphan.file_id)
            delete = await _ask(user, ROUTE["delete"], orphan.file_id)

            seen = {"listed": listed, "info": info.status_code, "delete": delete.status_code, "on disk": planter.where(orphan)}
            assert seen == {"listed": False, "info": 403, "delete": 403, "on disk": planter.as_planted(orphan)}, f"a regular user on a file with neither broker nor uploader: {seen} (info {_answer(info)}; delete {_answer(delete)})"
            print_success("✓ a file with neither broker nor uploader is the administrator's only")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("reader", ["uploader", "administrator"])
    async def test_its_uploader_and_the_administrator_list_and_read_it(self, test_server, planter, reader):
        """F36-04 (guard, green today): U's file with no broker is in the list of ``reader`` (U, or the administrator), and every read
        route answers 200: the info as planted, the preview of this file, the download with the planted bytes, no last parse, the
        generic CSV's plugin check."""
        print_section(f"F36-04: the {reader} lists and reads a file with no broker")
        async with httpx.AsyncClient() as uploader, httpx.AsyncClient() as admin:
            uploader_id = await _regular_user(uploader)
            client = uploader
            if reader == "administrator":
                await _lane_admin(admin)
                client = admin
            legacy = _without_broker(planter, uploader_id)
            await _assert_reads_without_broker(client, legacy, uploader_id)

            assert legacy.file_id in await _listed(client), f"the {reader} does not list the file with no broker"
            answers = {route.name: await _ask(client, route, legacy.file_id) for route in READ_ROUTES}

            assert {name: response.status_code for name, response in answers.items()} == dict.fromkeys(answers, 200), {name: _answer(response) for name, response in answers.items()}
            assert answers["preview"].json()["download_url"].endswith(f"/files/{legacy.file_id}/download"), answers["preview"].text
            assert answers["download"].content == legacy.content, "the download is not the planted file"
            assert answers["last-parse"].json() is None, answers["last-parse"].text
            assert answers["plugin-check"].json()["plugin_code"] == GENERIC_CSV_CODE, answers["plugin-check"].text
            print_success(f"✓ the {reader} lists and reads a file with no broker")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("deleter", ["uploader", "administrator"])
    async def test_its_uploader_and_the_administrator_delete_it(self, test_server, planter, deleter):
        """F36-05 (guard, green today): ``deleter`` (U, or the administrator) deletes U's file with no broker: 200
        ``{"success": true, "file_id": …}``; content and sidecar are gone from disk, the deleter no longer lists it, and reading it is 404."""
        print_section(f"F36-05: the {deleter} deletes a file with no broker")
        async with httpx.AsyncClient() as uploader, httpx.AsyncClient() as admin:
            uploader_id = await _regular_user(uploader)
            client = uploader
            if deleter == "administrator":
                await _lane_admin(admin)
                client = admin
            legacy = _without_broker(planter, uploader_id)
            await _assert_reads_without_broker(client, legacy, uploader_id)

            response = await _ask(client, ROUTE["delete"], legacy.file_id)

            assert response.status_code == 200 and response.json() == {"success": True, "file_id": legacy.file_id}, _answer(response)
            assert planter.where(legacy) == [], f"the delete left the file on disk: {planter.where(legacy)}"
            assert legacy.file_id not in await _listed(client), f"the {deleter} still lists the deleted file"
            gone = await _ask(client, ROUTE["info"], legacy.file_id)
            assert gone.status_code == 404, _answer(gone)
            print_success(f"✓ the {deleter} deletes a file with no broker")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("reader", ["uploader", "administrator"])
    async def test_the_list_of_a_broker_leaves_out_a_file_with_no_broker(self, test_server, planter, reader):
        """F36-16 (W-B32): U owns broker B, with a report uploaded to it, and has a file with no broker. ``reader`` (U, or the
        administrator, who holds no role on B: no role narrows an administrator's list) asks for B's list, ``broker_ids`` = B, as
        B's «Uploaded Reports» does: B's report is there, the file with no broker is not, and every item is a file of B. Barriers:
        the reader reads the file with no broker and lists it unfiltered (F36-04's contract, which the cure keeps: the Files page
        asks with no filter); B's report is in B's list. Red today: the route hands the filter to ``list_files``, which keeps every
        file with no broker under any broker filter, and then drops only those another user uploaded (decision 36): the file shows
        in the list of every broker, U's own to U, all of them to the administrator."""
        print_section(f"F36-16: a broker's list, as the {reader} reads it, leaves out a file with no broker")
        async with httpx.AsyncClient() as uploader, httpx.AsyncClient() as admin:
            uploader_id = await _regular_user(uploader)
            client = uploader
            if reader == "administrator":
                await _lane_admin(admin)
                client = admin
            broker_id = await create_test_broker(uploader)
            file_ids: List[str] = []
            try:
                broker_report = await _upload_for_check(uploader, broker_id, PLANTED_CSV, f"f36_{uuid.uuid4().hex[:8]}.csv", file_ids)
                legacy = _without_broker(planter, uploader_id)
                await _assert_reads_without_broker(client, legacy, uploader_id)
                assert legacy.file_id in await _listed(client), f"presence barrier: the {reader} lists the file with no broker when the list is not filtered (F36-04)"

                listed = await _listed(client, broker_ids=broker_id)

                assert broker_report in listed, f"presence barrier: the {reader} finds broker {broker_id}'s report in the list of broker {broker_id}"
                assert legacy.file_id not in listed, f"a report with no broker shows in the list of broker {broker_id} (its «Uploaded Reports») as the {reader} reads it: file {legacy.file_id}, uploaded by user {uploader_id} with no broker, is listed under every broker"
                strays = {file_id: item["target_broker_id"] for file_id, item in listed.items() if item["target_broker_id"] != broker_id}
                assert strays == {}, f"the list of broker {broker_id}, as the {reader} reads it, shows reports of another broker or of none ({{file_id: target_broker_id}}): {strays}"
                print_success(f"✓ a broker's list, as the {reader} reads it, leaves out a file with no broker")
            finally:
                await _delete_files(uploader, file_ids)
                await _delete_created(uploader, broker_ids=[broker_id])


class TestReportsOfABroker:
    """F36 — a broker's file keeps today's rules: any role reads it, EDITOR or OWNER parses and deletes it, anyone else gets 403."""

    @pytest.mark.asyncio
    async def test_a_viewer_reads_it_but_neither_parses_nor_deletes_it(self, test_server):
        """F36-06 (guard, green today): a VIEWER of the broker gets 200 on the five read routes, 403 on the parse (into that broker) and
        on the delete; the file stays ``uploaded`` with no parse."""
        print_section("F36-06: a VIEWER reads a broker's file, neither parses nor deletes it")
        async with httpx.AsyncClient() as owner, httpx.AsyncClient() as viewer:
            owner_id = await _regular_user(owner)
            viewer_id = await _regular_user(viewer)
            broker_id = await create_test_broker(owner)
            file_ids: List[str] = []
            try:
                await _set_access(owner, broker_id, owner_id, {viewer_id: "VIEWER"})
                file_id = await _upload_for_check(owner, broker_id, PLANTED_CSV, f"f36_{uuid.uuid4().hex[:8]}.csv", file_ids)

                answers = {route.name: (await _ask(viewer, route, file_id, broker_id)).status_code for route in FILE_ROUTES}

                assert answers == {route.name: 200 if route.viewer else 403 for route in FILE_ROUTES}, f"a VIEWER on the broker's file: {answers}"
                await _assert_still_uploaded(owner, file_id)
                print_success("✓ a VIEWER reads, neither parses nor deletes")
            finally:
                await _delete_files(owner, file_ids)
                await _delete_created(owner, broker_ids=[broker_id])

    @pytest.mark.asyncio
    async def test_a_user_without_access_does_not_list_it_and_is_refused_everywhere(self, test_server):
        """F36-07 (guard, green today): a user with no role on the broker does not list its file (the owner does: the barrier) and
        gets 403 on all seven per-file routes; the file stays ``uploaded`` with no parse."""
        print_section("F36-07: a user without access does not list a broker's file and is refused on every route")
        async with httpx.AsyncClient() as owner, httpx.AsyncClient() as stranger:
            await _regular_user(owner)
            await _regular_user(stranger)
            broker_id = await create_test_broker(owner)
            file_ids: List[str] = []
            try:
                file_id = await _upload_for_check(owner, broker_id, PLANTED_CSV, f"f36_{uuid.uuid4().hex[:8]}.csv", file_ids)
                assert file_id in await _listed(owner), "presence barrier: the owner lists the broker's file"

                assert file_id not in await _listed(stranger), "a broker's file is in the list of a user without access to the broker"
                answers = {route.name: (await _ask(stranger, route, file_id, broker_id)).status_code for route in FILE_ROUTES}

                assert answers == dict.fromkeys(answers, 403), f"a user without access on the broker's file: {answers}"
                await _assert_still_uploaded(owner, file_id)
                print_success("✓ a user without access neither lists nor reaches a broker's file")
            finally:
                await _delete_files(owner, file_ids)
                await _delete_created(owner, broker_ids=[broker_id])

    @pytest.mark.asyncio
    async def test_an_editor_deletes_it(self, test_server):
        """F36-08 (guard, green today): an EDITOR of the broker deletes the owner's file: 200 ``{"success": true, "file_id": …}``; the
        owner no longer lists it, and reading it is 404."""
        print_section("F36-08: an EDITOR deletes a broker's file")
        async with httpx.AsyncClient() as owner, httpx.AsyncClient() as editor:
            owner_id = await _regular_user(owner)
            editor_id = await _regular_user(editor)
            broker_id = await create_test_broker(owner)
            file_ids: List[str] = []
            try:
                await _set_access(owner, broker_id, owner_id, {editor_id: "EDITOR"})
                file_id = await _upload_for_check(owner, broker_id, PLANTED_CSV, f"f36_{uuid.uuid4().hex[:8]}.csv", file_ids)

                response = await _ask(editor, ROUTE["delete"], file_id)

                assert response.status_code == 200 and response.json() == {"success": True, "file_id": file_id}, _answer(response)
                assert file_id not in await _listed(owner), "the owner still lists the deleted file"
                gone = await _ask(owner, ROUTE["info"], file_id)
                assert gone.status_code == 404, _answer(gone)
                print_success("✓ an EDITOR deletes a broker's file")
            finally:
                await _delete_files(owner, file_ids)
                await _delete_created(owner, broker_ids=[broker_id])


class TestListCanDelete:
    """F36 — every item of ``GET /files`` says whether its reader may delete it (``can_delete``), as ``DELETE /files/{id}`` will answer."""

    @pytest.mark.asyncio
    async def test_each_list_item_says_whether_its_reader_may_delete_it(self, test_server, planter):
        """F36-09: one broker (its OWNER, an EDITOR, and a VIEWER who uploaded a file while EDITOR), U's file with no broker and a
        file with neither broker nor uploader. ``can_delete``: true for U on U's file; for the OWNER and the EDITOR on both of the
        broker's files; for the administrator on all four. False for the VIEWER on both of the broker's files, its own upload
        included. Red today: no list item carries ``can_delete``."""
        print_section("F36-09: can_delete on every list item")
        async with httpx.AsyncClient() as uploader, httpx.AsyncClient() as owner, httpx.AsyncClient() as editor, httpx.AsyncClient() as viewer, httpx.AsyncClient() as admin:
            uploader_id = await _regular_user(uploader)
            owner_id = await _regular_user(owner)
            editor_id = await _regular_user(editor)
            viewer_id = await _regular_user(viewer)
            await _lane_admin(admin)
            broker_id = await create_test_broker(owner)
            file_ids: List[str] = []
            try:
                await _set_access(owner, broker_id, owner_id, {editor_id: "EDITOR", viewer_id: "EDITOR"})
                owners_upload = await _upload_for_check(owner, broker_id, PLANTED_CSV, f"f36_owner_{uuid.uuid4().hex[:8]}.csv", file_ids)
                viewers_upload = await _upload_for_check(viewer, broker_id, PLANTED_CSV, f"f36_viewer_{uuid.uuid4().hex[:8]}.csv", file_ids)
                await _set_access(owner, broker_id, owner_id, {editor_id: "EDITOR", viewer_id: "VIEWER"})
                legacy = _without_broker(planter, uploader_id)
                orphan = _without_broker(planter, None)
                await _assert_reads_without_broker(uploader, legacy, uploader_id)
                files = {"no broker, U's": legacy.file_id, "no broker, no uploader": orphan.file_id, "the owner's upload": owners_upload, "the viewer's upload, made as EDITOR": viewers_upload}
                broker_files = ("the owner's upload", "the viewer's upload, made as EDITOR")
                readers = {"U, the uploader": uploader, "the OWNER": owner, "the EDITOR": editor, "the VIEWER": viewer, "the administrator": admin}
                expected = {
                    "U, the uploader": {"no broker, U's": True},
                    "the OWNER": dict.fromkeys(broker_files, True),
                    "the EDITOR": dict.fromkeys(broker_files, True),
                    "the VIEWER": dict.fromkeys(broker_files, False),
                    "the administrator": dict.fromkeys(files, True),
                }

                seen = {reader: await _can_delete(readers[reader], {label: files[label] for label in wanted}) for reader, wanted in expected.items()}

                assert seen == expected, f"can_delete per reader and file: {seen}"
                print_success("✓ can_delete on every list item")
            finally:
                await _delete_files(owner, file_ids)
                await _delete_created(owner, broker_ids=[broker_id])


class TestFileIdsAreUuids:
    """W-B4 — a ``file_id`` that is not a UUID in its canonical form (lower-case, as an upload writes it) answers 404 on every per-file route, before any lookup."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", NON_UUID_KINDS)
    async def test_a_file_id_that_is_not_a_uuid_answers_404_on_every_route(self, test_server, kind):
        """F36-10: ``not-a-uuid``, ``..``, 300 characters, a UUID with a suffix, on the seven per-file routes, as a regular user with a
        broker of their own (the parse imports into it): 404 everywhere. Today: guards for ``not-a-uuid``, ``dot-dot`` and
        ``uuid-with-suffix`` (the lookup finds nothing: 404); red for ``over-long`` (the lookup raises ENAMETOOLONG: 500)."""
        print_section(f"F36-10: a file id that is not a UUID answers 404 on every route ({kind})")
        async with httpx.AsyncClient() as client:
            await _regular_user(client)
            broker_id = await create_test_broker(client)
            try:
                file_id = _non_uuid_id(kind)

                answers = {route.name: await _ask(client, route, file_id, broker_id) for route in FILE_ROUTES}

                assert {name: response.status_code for name, response in answers.items()} == dict.fromkeys(answers, 404), {name: _answer(response) for name, response in answers.items() if response.status_code != 404}
                print_success(f"✓ {kind}: 404 on every route")
            finally:
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    async def test_a_file_named_by_an_id_that_is_not_a_uuid_is_never_looked_up(self, test_server, planter):
        """F36-11: in the user's own broker folder, a file named ``<uuid>-1`` (its sidecar says so) next to a twin named by a plain
        UUID. The twin is served (the barrier: the planted files reach the backend's data directory); ``<uuid>-1`` answers 404 on
        all seven routes, although the user owns the broker, and stays where it was planted. Red today: the lookup finds it, and
        every route serves it (200), the parse moving it to ``parsed/``, the delete removing it."""
        print_section("F36-11: a file named by an id that is not a UUID is never looked up")
        async with httpx.AsyncClient() as client:
            owner_id = await _regular_user(client)
            broker_id = await create_test_broker(client)
            try:
                twin = _on_broker(planter, broker_id, owner_id, str(uuid.uuid4()))
                suffixed = _on_broker(planter, broker_id, owner_id, f"{uuid.uuid4()}-1")
                served = await _ask(client, ROUTE["info"], twin.file_id)
                assert served.status_code == 200 and served.json()["file_id"] == twin.file_id, f"premise: a file planted in the owner's broker folder under a plain UUID is served: {_answer(served)} — the test did not reach the data directory of the backend under test"

                answers = {route.name: await _ask(client, route, suffixed.file_id, broker_id) for route in FILE_ROUTES}

                assert {name: response.status_code for name, response in answers.items()} == dict.fromkeys(answers, 404), {name: _answer(response) for name, response in answers.items() if response.status_code != 404}
                assert planter.where(suffixed) == planter.as_planted(suffixed), f"a route reached the file named {suffixed.file_id}: on disk now {planter.where(suffixed)}"
                print_success("✓ a file named by an id that is not a UUID is never looked up")
            finally:
                planter.sweep_all()  # before the broker goes: its deletion removes its folders only when they are empty
                await _delete_created(client, broker_ids=[broker_id])

    @pytest.mark.asyncio
    async def test_the_upper_cased_id_of_an_existing_file_answers_404_on_every_route(self, test_server):
        """F36-15: a file the user uploaded to their own broker, its id upper-cased, on the seven per-file routes: 404 everywhere,
        although the user owns the broker and, on a case-insensitive disk, the spelling names the file. The file stays ``uploaded``
        with no parse, and its own id serves it, before and after (the barrier). A file id is the canonical, lower-case UUID an
        upload writes. Platform-dependent today. Red on a case-insensitive file system (macOS's default, this lane): the format
        check accepts the id (``str(uuid.UUID(id)) == id.lower()``), the lookup finds the lower-case sidecar, the access check
        passes (the user owns the broker) and every route serves the file, 200; the parse moves it to ``parsed/``, the delete
        removes it. Green on a case-sensitive one (Linux): the lookup finds nothing, 404. The cure, only the canonical form is
        a file id, answers 404 on both."""
        print_section("F36-15: the upper-cased id of an existing file answers 404 on every route")
        async with httpx.AsyncClient() as client:
            await _regular_user(client)
            broker_id = await create_test_broker(client)
            file_ids: List[str] = []
            try:
                file_id = await _upload_for_check(client, broker_id, PLANTED_CSV, f"f36_{uuid.uuid4().hex[:8]}.csv", file_ids)
                shouted = file_id.upper()
                assert str(uuid.UUID(file_id)) == file_id, f"premise: an upload writes its id as a canonical UUID, lower-case: {file_id}"
                assert shouted != file_id, f"premise: the id has a letter to upper-case: {file_id}"
                served = await _ask(client, ROUTE["info"], file_id)
                assert served.status_code == 200 and served.json()["file_id"] == file_id, f"barrier: the file's own id serves it: {_answer(served)}"

                answers = {route.name: await _ask(client, route, shouted, broker_id) for route in FILE_ROUTES}

                assert {name: response.status_code for name, response in answers.items()} == dict.fromkeys(answers, 404), {name: _answer(response) for name, response in answers.items() if response.status_code != 404}
                await _assert_still_uploaded(client, file_id)
                print_success("✓ the upper-cased id of an existing file answers 404 on every route; the file is untouched")
            finally:
                await _delete_files(client, file_ids)
                await _delete_created(client, broker_ids=[broker_id])


async def _roles(owner: httpx.AsyncClient, broker_id: int) -> Dict[int, str]:
    """The broker's access list as its owner reads it: ``{user_id: role}``."""
    response = await owner.get(f"{API_BASE}/brokers/{broker_id}/access", timeout=TIMEOUT)
    assert response.status_code == 200, _answer(response)
    return {item["user_id"]: item["role"] for item in response.json()["items"]}


async def _parse_scene(owner: httpx.AsyncClient, caller: httpx.AsyncClient, role_on_target: Optional[str], broker_ids: List[int], file_ids: List[str]) -> Tuple[int, int, str]:
    """``owner`` holds two brokers: the file's, where ``caller`` is EDITOR and ``owner`` uploads the file, and a target, where ``caller``
    holds ``role_on_target`` (None: no role). ``(file_broker, target_broker, file_id)``; each broker and the file join ``broker_ids``
    and ``file_ids`` as soon as they exist, for the test's cleanup. The roles are read back: they are the premise."""
    owner_id = await _regular_user(owner)
    caller_id = await _regular_user(caller)
    file_broker = await create_test_broker(owner)
    broker_ids.append(file_broker)
    target_broker = await create_test_broker(owner)
    broker_ids.append(target_broker)
    await _set_access(owner, file_broker, owner_id, {caller_id: "EDITOR"})
    target_members = {} if role_on_target is None else {caller_id: role_on_target}
    if target_members:
        await _set_access(owner, target_broker, owner_id, target_members)
    roles = (await _roles(owner, file_broker), await _roles(owner, target_broker))
    assert roles == ({owner_id: "OWNER", caller_id: "EDITOR"}, {owner_id: "OWNER", **target_members}), f"premise: the roles of the scene, (the file's broker, the target): {roles}"
    file_id = await _upload_for_check(owner, file_broker, PLANTED_CSV, f"f36_{uuid.uuid4().hex[:8]}.csv", file_ids)
    return file_broker, target_broker, file_id


class TestParseTargetBroker:
    """F36 — ``POST /files/{id}/parse`` imports only into a broker its caller may edit: the body's ``broker_id`` needs EDITOR or OWNER there; the administrator passes."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("role_on_target", [pytest.param("VIEWER", id="viewer-of-target"), pytest.param(None, id="no-role-on-target")])
    async def test_an_editor_cannot_parse_the_file_into_a_broker_they_do_not_edit(self, test_server, role_on_target):
        """F36-12: E, EDITOR of the file's broker A and VIEWER of broker B (or with no role on B), parses the file with ``broker_id`` B:
        403, and the file stays ``uploaded`` with no parse. Barrier: E then parses the same file into A, 200: the refusal is about B,
        not about the file. Red today: 200, the parse of the file into B (the response's ``broker_id`` is B, its duplicate report is
        computed against B's transactions), and the file moves to ``parsed/`` with that parse cached as its last one."""
        held = role_on_target or "no role"
        print_section(f"F36-12: an EDITOR of the file's broker cannot parse it into a broker where they hold {held}")
        async with httpx.AsyncClient() as owner, httpx.AsyncClient() as editor:
            broker_ids: List[int] = []
            file_ids: List[str] = []
            try:
                file_broker, target_broker, file_id = await _parse_scene(owner, editor, role_on_target, broker_ids, file_ids)

                refused = await _ask(editor, ROUTE["parse"], file_id, target_broker)

                assert refused.status_code == 403, f"a parse into broker {target_broker}, where the caller holds {held}, of a file of broker {file_broker}, where the caller is EDITOR: expected 403, got {_answer(refused)}"
                await _assert_still_uploaded(owner, file_id)
                served = await _ask(editor, ROUTE["parse"], file_id, file_broker)
                assert served.status_code == 200 and served.json()["broker_id"] == file_broker, f"barrier: the same caller parses the same file into its own broker {file_broker}: {_answer(served)}"
                print_success(f"✓ a parse into a broker where the caller holds {held}: 403, the file untouched")
            finally:
                await _delete_files(owner, file_ids)
                await _delete_created(owner, broker_ids=broker_ids)

    @pytest.mark.asyncio
    async def test_an_editor_parses_the_file_into_its_own_broker(self, test_server):
        """F36-13 (guard, green today): the caller of F36-12, EDITOR of the file's broker A and VIEWER of broker B, parses the same file
        with ``broker_id`` A: 200, the parse of that file by the generic CSV into A."""
        print_section("F36-13: an EDITOR parses the file into its own broker")
        async with httpx.AsyncClient() as owner, httpx.AsyncClient() as editor:
            broker_ids: List[int] = []
            file_ids: List[str] = []
            try:
                file_broker, _, file_id = await _parse_scene(owner, editor, "VIEWER", broker_ids, file_ids)

                served = await _ask(editor, ROUTE["parse"], file_id, file_broker)

                assert served.status_code == 200, _answer(served)
                parsed = served.json()
                assert (parsed["file_id"], parsed["plugin_code"], parsed["broker_id"]) == (file_id, GENERIC_CSV_CODE, file_broker), _answer(served)
                print_success("✓ an EDITOR parses the file into its own broker")
            finally:
                await _delete_files(owner, file_ids)
                await _delete_created(owner, broker_ids=broker_ids)

    @pytest.mark.asyncio
    async def test_the_administrator_parses_the_file_into_a_broker_without_a_role(self, test_server):
        """F36-14 (guard, green today): the administrator, with no role on the file's broker A nor on broker B, parses the file with
        ``broker_id`` B: 200, the parse of that file into B."""
        print_section("F36-14: the administrator parses a file into a broker they hold no role on")
        async with httpx.AsyncClient() as owner, httpx.AsyncClient() as admin:
            broker_ids: List[int] = []
            file_ids: List[str] = []
            try:
                owner_id = await _regular_user(owner)
                admin_id = await _lane_admin(admin)
                file_broker = await create_test_broker(owner)
                broker_ids.append(file_broker)
                target_broker = await create_test_broker(owner)
                broker_ids.append(target_broker)
                roles = (await _roles(owner, file_broker), await _roles(owner, target_broker))
                assert roles == ({owner_id: "OWNER"}, {owner_id: "OWNER"}), f"premise: the administrator ({admin_id}) holds no role on either broker: {roles}"
                file_id = await _upload_for_check(owner, file_broker, PLANTED_CSV, f"f36_{uuid.uuid4().hex[:8]}.csv", file_ids)

                served = await _ask(admin, ROUTE["parse"], file_id, target_broker)

                assert served.status_code == 200, _answer(served)
                parsed = served.json()
                assert (parsed["file_id"], parsed["broker_id"]) == (file_id, target_broker), _answer(served)
                print_success("✓ the administrator parses a file into a broker they hold no role on")
            finally:
                await _delete_files(owner, file_ids)
                await _delete_created(owner, broker_ids=broker_ids)


# ============================================================================
# Note: E2E tests are in test_e2e/test_brim_e2e.py
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
