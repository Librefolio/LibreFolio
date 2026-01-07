"""
BRIM End-to-End Tests.

Complete import flow tests:
- E2E-001: Full import flow (deposits only)
- E2E-002: Full import flow with assets
- E2E-003: User can filter duplicates before import
- E2E-004: Re-import detects duplicates

These tests require:
- Database connection
- Test server running
- File system access

See checklist: 01_test_brim_plan.md - Category 7
"""
import io
import uuid

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


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
            unique_name = f"BRIM_E2E_Test_Broker_{uuid.uuid4().hex[:8]}"
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


# ============================================================================
# E2E IMPORT TESTS
# ============================================================================

class TestBRIME2EImport:
    """End-to-end import flow tests."""

    @pytest.mark.asyncio
    async def test_full_import_flow_deposits_only(self, test_server, test_broker_id):
        """
        E2E-001: Full import flow for deposit-only file (no assets).

        Flow:
        1. Upload CSV with deposits/withdrawals
        2. Parse file
        3. Import transactions via POST /transactions
        4. Verify transactions created
        """
        async with httpx.AsyncClient() as client:
            # Create CSV with only deposits/withdrawals (no assets)
            csv_content = b"""date,type,quantity,amount,currency,description
2025-01-10,DEPOSIT,0,10000.00,EUR,Initial deposit for E2E test
2025-01-11,WITHDRAWAL,0,-500.00,EUR,Test withdrawal
"""

            # Step 1: Upload
            files = {"file": ("e2e_deposits.csv", io.BytesIO(csv_content), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                timeout=TIMEOUT,
                )
            assert upload_response.status_code == 200
            file_id = upload_response.json()["file_id"]

            # Step 2: Parse
            parse_response = await client.post(
                f"{API_BASE}/brokers/import/files/{file_id}/parse",
                json={
                    "plugin_code": "broker_generic_csv",
                    "broker_id": test_broker_id,
                    },
                timeout=TIMEOUT,
                )
            assert parse_response.status_code == 200
            parse_data = parse_response.json()

            transactions = parse_data["transactions"]
            assert len(transactions) == 2

            # All transactions should be unique (first import)
            assert len(parse_data["duplicates"]["tx_unique_indices"]) == 2

            # Step 3: Import via transactions endpoint
            import_response = await client.post(
                f"{API_BASE}/transactions",
                json=transactions,
                timeout=TIMEOUT,
                )

            # Transactions endpoint returns 200 with success_count
            assert import_response.status_code == 200, f"Import failed: {import_response.text}"
            import_data = import_response.json()
            assert import_data["success_count"] == 2

    @pytest.mark.asyncio
    async def test_full_import_flow_with_assets(self, test_server, test_broker_id):
        """
        E2E-002: Full import flow with asset transactions.

        Uses generic CSV format with asset identifiers. Tests:
        1. Upload file with asset identifiers
        2. Parse and get asset_mappings
        3. Verify fake_asset_ids are assigned
        4. Verify asset mappings structure
        """
        async with httpx.AsyncClient() as client:
            # CSV with asset identifiers
            csv_content = b"""date,type,quantity,amount,currency,asset,description
2025-02-01,DEPOSIT,0,10000.00,EUR,,Initial deposit
2025-02-02,BUY,10,-1000.00,EUR,TESTASSET1,Buy test asset 1
2025-02-03,BUY,5,-500.00,EUR,TESTASSET1,Buy more test asset 1
2025-02-04,BUY,20,-2000.00,EUR,TESTASSET2,Buy test asset 2
"""

            # Step 1: Upload
            files = {"file": ("e2e_with_assets.csv", io.BytesIO(csv_content), "text/csv")}
            upload_response = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files,
                timeout=TIMEOUT,
                )
            assert upload_response.status_code == 200
            file_id = upload_response.json()["file_id"]

            # Step 2: Parse
            parse_response = await client.post(
                f"{API_BASE}/brokers/import/files/{file_id}/parse",
                json={
                    "plugin_code": "broker_generic_csv",
                    "broker_id": test_broker_id,
                    },
                timeout=TIMEOUT,
                )
            assert parse_response.status_code == 200, f"Parse failed: {parse_response.text}"
            parse_data = parse_response.json()

            transactions = parse_data["transactions"]
            asset_mappings = parse_data["asset_mappings"]

            # Should have 4 transactions
            assert len(transactions) == 4, f"Expected 4 transactions, got {len(transactions)}"

            # Should have 2 unique asset mappings (TESTASSET1 and TESTASSET2)
            assert len(asset_mappings) == 2, f"Expected 2 asset mappings, got {len(asset_mappings)}"

            # Verify asset mapping structure
            for mapping in asset_mappings:
                assert "fake_asset_id" in mapping
                assert "candidates" in mapping
                # Since these are test assets, candidates should be empty
                # (no matching assets in DB)

            # Transactions with assets should have fake_asset_id
            asset_txs = [tx for tx in transactions if tx.get("asset_id") is not None]
            assert len(asset_txs) == 3, "3 transactions should have asset_id"

            # Deposit should have no asset_id
            deposit_txs = [tx for tx in transactions if tx.get("type") == "DEPOSIT"]
            assert len(deposit_txs) == 1
            assert deposit_txs[0].get("asset_id") is None

    @pytest.mark.asyncio
    async def test_import_user_can_filter_duplicates(self, test_server, test_broker_id):
        """
        E2E-003: User can choose to skip duplicates during import.

        Flow:
        1. Import transactions
        2. Parse same file again
        3. Parse response shows duplicates
        4. User filters tx_unique_indices before import
        5. Only unique transactions are imported
        """
        async with httpx.AsyncClient() as client:
            # Create unique CSV
            unique_id = uuid.uuid4().hex[:8]
            csv_content = f"""date,type,quantity,amount,currency,description
2025-03-01,DEPOSIT,0,5000.00,EUR,First deposit {unique_id}
2025-03-02,DEPOSIT,0,3000.00,EUR,Second deposit {unique_id}
""".encode()

            # First import - both transactions
            files1 = {"file": (f"filter_test_{unique_id}.csv", io.BytesIO(csv_content), "text/csv")}
            upload1 = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files1,
                timeout=TIMEOUT,
                )
            file_id1 = upload1.json()["file_id"]

            parse1 = await client.post(
                f"{API_BASE}/brokers/import/files/{file_id1}/parse",
                json={"plugin_code": "broker_generic_csv", "broker_id": test_broker_id},
                timeout=TIMEOUT,
                )
            tx1 = parse1.json()["transactions"]

            # Import both
            import1 = await client.post(f"{API_BASE}/transactions", json=tx1, timeout=TIMEOUT)
            assert import1.status_code == 200

            # Second upload with one new, one duplicate
            csv_content2 = f"""date,type,quantity,amount,currency,description
2025-03-01,DEPOSIT,0,5000.00,EUR,First deposit {unique_id}
2025-03-03,DEPOSIT,0,2000.00,EUR,Third deposit {unique_id}
""".encode()

            files2 = {"file": (f"filter_test2_{unique_id}.csv", io.BytesIO(csv_content2), "text/csv")}
            upload2 = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files2,
                timeout=TIMEOUT,
                )
            file_id2 = upload2.json()["file_id"]

            parse2 = await client.post(
                f"{API_BASE}/brokers/import/files/{file_id2}/parse",
                json={"plugin_code": "broker_generic_csv", "broker_id": test_broker_id},
                timeout=TIMEOUT,
                )
            parse2_data = parse2.json()

            # Should have 1 unique (new deposit) and 1 duplicate
            unique_indices = parse2_data["duplicates"]["tx_unique_indices"]

            # User selects only unique transactions for import
            transactions_to_import = [
                parse2_data["transactions"][i] for i in unique_indices
                ]

            # Import only unique
            if transactions_to_import:
                import2 = await client.post(
                    f"{API_BASE}/transactions",
                    json=transactions_to_import,
                    timeout=TIMEOUT,
                    )
                assert import2.status_code == 200
                # Should import only the new one
                assert import2.json()["success_count"] == len(unique_indices)

    @pytest.mark.asyncio
    async def test_reimport_detects_duplicates(self, test_server, test_broker_id):
        """
        E2E-004: Re-importing same file shows transactions as duplicates.

        Flow:
        1. Upload and import a file
        2. Upload same content again
        3. Parse should detect all as duplicates
        """
        async with httpx.AsyncClient() as client:
            # Create unique CSV
            unique_id = uuid.uuid4().hex[:8]
            csv_content = f"""date,type,quantity,amount,currency,description
2025-01-20,DEPOSIT,0,7777.00,EUR,Unique deposit {unique_id}
""".encode()

            # First import
            files1 = {"file": (f"dup_test_{unique_id}.csv", io.BytesIO(csv_content), "text/csv")}
            upload1 = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files1,
                timeout=TIMEOUT,
                )
            file_id1 = upload1.json()["file_id"]

            parse1 = await client.post(
                f"{API_BASE}/brokers/import/files/{file_id1}/parse",
                json={"plugin_code": "broker_generic_csv", "broker_id": test_broker_id},
                timeout=TIMEOUT,
                )
            tx1 = parse1.json()["transactions"]

            # Import first time
            await client.post(f"{API_BASE}/transactions", json=tx1, timeout=TIMEOUT)

            # Second upload of same content
            files2 = {"file": (f"dup_test_{unique_id}_2.csv", io.BytesIO(csv_content), "text/csv")}
            upload2 = await client.post(
                f"{API_BASE}/brokers/import/upload",
                files=files2,
                timeout=TIMEOUT,
                )
            file_id2 = upload2.json()["file_id"]

            # Parse again - should detect duplicate
            parse2 = await client.post(
                f"{API_BASE}/brokers/import/files/{file_id2}/parse",
                json={"plugin_code": "broker_generic_csv", "broker_id": test_broker_id},
                timeout=TIMEOUT,
                )

            duplicates = parse2.json()["duplicates"]

            # Should have duplicates detected
            total_duplicates = (
                len(duplicates.get("tx_possible_duplicates", [])) +
                len(duplicates.get("tx_likely_duplicates", []))
            )
            assert total_duplicates >= 1, "Should detect duplicate transaction"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
