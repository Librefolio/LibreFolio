# BRIM Test Plan

**Document:** 01_test_brim_plan.md  
**Created:** 2026-01-03  
**Updated:** 2026-01-06
**Status:** ✅ PARTIALLY IMPLEMENTED

---

## Implementation Progress

| Category                        | Status  | Tests | File                     |
|---------------------------------|---------|-------|--------------------------|
| Category 1: Plugin Discovery    | ✅ Done  | 5/5   | `test_brim_providers.py` |
| Category 2: File Parsing        | ✅ Done  | 8/8   | `test_brim_providers.py` |
| Category 2B: Auto-Detection     | ✅ Done  | 14/14 | `test_brim_providers.py` |
| Category 3: Asset Search        | ✅ Done  | 6/6   | `test_brim_db.py`        |
| Category 4: Duplicate Detection | ✅ Done  | 5/5   | `test_brim_db.py`        |
| Category 5: File Storage        | 📋 TODO | 0/5   | `test_brim_api.py`       |
| Category 6: API Endpoints       | 📋 TODO | 0/8   | `test_brim_api.py`       |
| Category 7: E2E Import          | 📋 TODO | 0/4   | `test_brim_api.py`       |

**Total: 38/55 tests implemented**

---

## Overview

This document defines the test strategy for the Broker Report Import Manager (BRIM) system.

**Key Principle:** Tests must be idempotent and repeatable. Since parsing the same file multiple
times would create duplicate transactions, we need a cleanup mechanism before each test run.

---

## Test Structure

```
backend/test_scripts/
├── test_services/
│   └── test_brim_providers.py     # Plugin parsing tests (no DB)
├── test_api/
│   └── test_brim_api.py           # API endpoint tests (with DB)
└── conftest.py                    # Shared fixtures including cleanup
```

---

## Test Categories

### Category 1: Plugin Discovery & Registration

**File:** `test_brim_providers.py`  
**Requires DB:** No

| Test ID | Test Name                                   | Objective                   | Expected Result                          |
|---------|---------------------------------------------|-----------------------------|------------------------------------------|
| PD-001  | `test_registry_discovers_plugins`           | Verify auto-discovery works | At least 1 plugin registered             |
| PD-002  | `test_all_plugins_have_required_properties` | Verify plugin interface     | All plugins have code, name, description |
| PD-003  | `test_plugin_codes_are_unique`              | Verify no duplicate codes   | No duplicate provider_code values        |
| PD-004  | `test_get_provider_instance`                | Verify instance creation    | Returns valid plugin instance            |
| PD-005  | `test_get_nonexistent_provider`             | Verify error handling       | Returns None for unknown code            |

---

### Category 2: File Parsing (Plugin Layer)

**File:** `test_brim_providers.py`  
**Requires DB:** No

| Test ID | Test Name                              | Objective                   | Expected Result                              |
|---------|----------------------------------------|-----------------------------|----------------------------------------------|
| FP-001  | `test_parse_generic_simple_csv`        | Basic CSV parsing           | All rows parsed, no warnings                 |
| FP-002  | `test_parse_generic_dates_csv`         | Multiple date formats       | All dates parsed correctly                   |
| FP-003  | `test_parse_generic_types_csv`         | All transaction types       | All types mapped to enum                     |
| FP-004  | `test_parse_generic_multilang_csv`     | Multi-language headers      | Headers auto-detected                        |
| FP-005  | `test_parse_generic_with_warnings_csv` | Invalid rows handling       | Valid rows parsed, warnings list populated   |
| FP-006  | `test_parse_generic_with_assets_csv`   | Asset identifier extraction | Fake IDs assigned, asset info extracted      |
| FP-007  | `test_same_asset_gets_same_fake_id`    | Fake ID consistency         | Same symbol → same fake ID                   |
| FP-008  | `test_isin_classified_correctly`       | ISIN detection              | 12-char ISIN → extracted_isin populated      |
| FP-009  | `test_symbol_classified_correctly`     | Symbol detection            | Short alphanumeric → extracted_symbol        |
| FP-010  | `test_name_classified_correctly`       | Name fallback               | Long string → extracted_name                 |
| FP-011  | `test_every_sample_file_is_processed`  | Coverage check              | All sample files parsed by at least 1 plugin |
| FP-012  | `test_unsupported_file_rejected`       | Negative test               | .xlsx rejected by CSV plugin                 |

---

### Category 2B: Auto-Detection & Sample File Coverage

**File:** `test_brim_providers.py`  
**Requires DB:** No

**Key Test Principle:** Iterate over ALL sample files in `sample_reports/` directory and verify:

1. Each file is successfully auto-detected
2. Each file is successfully parsed (no exceptions)
3. Each registered plugin is used at least once across all samples

| Test ID | Test Name                             | Objective            | Expected Result                               |
|---------|---------------------------------------|----------------------|-----------------------------------------------|
| AD-001  | `test_iterate_all_sample_files`       | Parse all samples    | All files parse without exception             |
| AD-002  | `test_auto_detect_each_sample`        | Auto-detection works | Each file auto-detects correct plugin         |
| AD-003  | `test_all_plugins_used_at_least_once` | Plugin coverage      | Every registered plugin parses ≥1 file        |
| AD-004  | `test_directa_auto_detected`          | Directa detection    | `directa-export.csv` → `broker_directa`       |
| AD-005  | `test_degiro_auto_detected`           | DEGIRO detection     | `degiro-export.csv` → `broker_degiro`         |
| AD-006  | `test_trading212_auto_detected`       | Trading212 detection | `trading212-export.csv` → `broker_trading212` |
| AD-007  | `test_ibkr_auto_detected`             | IBKR detection       | `ibkr-trades-export.csv` → `broker_ibkr`      |
| AD-008  | `test_etoro_auto_detected`            | eToro detection      | `etoro-export.csv` → `broker_etoro`           |
| AD-009  | `test_generic_files_fallback`         | Generic fallback     | `generic_*.csv` → `broker_generic_csv`        |

---

### Category 2C: Parametrized Plugin Tests (TODO)

**File:** `test_brim_providers.py`  
**Requires DB:** No  
**Status:** 📋 TO IMPLEMENT

**Concept:** Each plugin should provide TEST_DATA in the class (like asset/forex providers).
Tests are parametrized to run the same assertions against ALL plugins automatically.

**Plugin Test Data Structure:**

```python
class DirectaBrokerProvider(BRIMProvider):
    # ...existing code...

    TEST_SAMPLES = [
        {
            "filename": "directa-export.csv",
            "expected_tx_count": 23,
            "expected_asset_count": 14,
            "expected_warnings": 2,
            "contains_types": [TransactionType.BUY, TransactionType.SELL, TransactionType.DIVIDEND],
            }
        ]
```

**Parametrized Test Implementation:**

```python
def get_all_plugins_with_test_data():
    """Collect all plugins that have TEST_SAMPLES defined."""
    plugins = []
    for info in BRIMProviderRegistry.list_plugin_info():
        instance = BRIMProviderRegistry.get_provider_instance(info.code)
        if hasattr(instance, 'TEST_SAMPLES') and instance.TEST_SAMPLES:
            for sample in instance.TEST_SAMPLES:
                plugins.append((info.code, sample))
    return plugins


@pytest.mark.parametrize("plugin_code,sample_data", get_all_plugins_with_test_data())
def test_plugin_parses_sample(plugin_code, sample_data):
    """Test each plugin against its declared sample files."""
    sample_dir = Path("backend/app/services/brim_providers/sample_reports")
    file_path = sample_dir / sample_data["filename"]

    assert file_path.exists(), f"Sample file not found: {file_path}"

    plugin = BRIMProviderRegistry.get_provider_instance(plugin_code)
    txs, warnings, assets = plugin.parse(file_path, broker_id=1)

    # Assertions from sample_data
    if "expected_tx_count" in sample_data:
        assert len(txs) == sample_data["expected_tx_count"]
    if "expected_asset_count" in sample_data:
        assert len(assets) == sample_data["expected_asset_count"]
    if "expected_warnings" in sample_data:
        assert len(warnings) == sample_data["expected_warnings"]
    if "contains_types" in sample_data:
        found_types = {tx.type for tx in txs}
        for expected_type in sample_data["contains_types"]:
            assert expected_type in found_types
```

| Test ID | Test Name                         | Objective               | Expected Result                        |
|---------|-----------------------------------|-------------------------|----------------------------------------|
| PP-001  | `test_plugin_parses_sample`       | Parametrized parse test | Each plugin passes for its samples     |
| PP-002  | `test_all_plugins_have_test_data` | Coverage                | Every plugin has TEST_SAMPLES          |
| PP-003  | `test_sample_files_all_covered`   | No orphan files         | Every sample has a plugin that uses it |

---

**Implementation Notes:**

```python
def test_iterate_all_sample_files():
    """Every sample file in sample_reports/ must parse successfully."""
    sample_dir = Path("backend/app/services/brim_providers/sample_reports")
    parsed_by_plugin = {}

    for csv_file in sample_dir.glob("*.csv"):
        plugin_code = BRIMProviderRegistry.auto_detect_plugin(csv_file)
        assert plugin_code is not None, f"No plugin detected for {csv_file.name}"

        plugin = BRIMProviderRegistry.get_provider_instance(plugin_code)
        txs, warnings, assets = plugin.parse(csv_file, broker_id=1)

        assert len(txs) > 0, f"No transactions parsed from {csv_file.name}"

        parsed_by_plugin.setdefault(plugin_code, []).append(csv_file.name)

    # Verify each plugin was used at least once
    registered = set(BRIMProviderRegistry._providers.keys())
    used = set(parsed_by_plugin.keys())
    unused = registered - used
    assert not unused, f"Plugins never used: {unused}"
```

---

### Category 3: Asset Candidate Search (Core Layer)

**File:** `test_brim_providers.py`  
**Requires DB:** Yes (needs assets in DB)

| Test ID | Test Name                                 | Objective             | Expected Result                     |
|---------|-------------------------------------------|-----------------------|-------------------------------------|
| AC-001  | `test_search_by_isin_exact_match`         | ISIN search           | EXACT confidence, 1 candidate       |
| AC-002  | `test_search_by_symbol_exact_match`       | Symbol search         | MEDIUM confidence                   |
| AC-003  | `test_search_by_name_partial_match`       | Name search           | LOW confidence                      |
| AC-004  | `test_search_no_match`                    | No results            | Empty candidates list               |
| AC-005  | `test_search_multiple_matches`            | Multiple assets match | Multiple candidates, no auto-select |
| AC-006  | `test_auto_select_single_candidate`       | Single match          | selected_asset_id populated         |
| AC-007  | `test_no_auto_select_multiple_candidates` | Multiple matches      | selected_asset_id is None           |

**Fixtures Required:**

- Create test assets with known ISIN, symbols, names before tests
- Clean up after tests

---

### Category 4: Duplicate Detection (Core Layer)

**File:** `test_brim_providers.py`  
**Requires DB:** Yes (needs transactions in DB)

**Logic:**

- If asset is auto-resolved (1 candidate found), filter DB query by asset_id
- Use `*_WITH_ASSET` levels for higher confidence
- If asset not resolved, use base `POSSIBLE`/`LIKELY` levels

| Test ID | Test Name                             | Objective                            | Expected Result                              |
|---------|---------------------------------------|--------------------------------------|----------------------------------------------|
| DD-001  | `test_detect_no_duplicates`           | Fresh transactions                   | All in tx_unique_indices                     |
| DD-002  | `test_detect_possible_duplicate`      | Same type/date/qty/cash, no asset    | In tx_possible_duplicates with POSSIBLE      |
| DD-003  | `test_detect_likely_duplicate`        | Same + description, no asset         | In tx_likely_duplicates with LIKELY          |
| DD-004  | `test_different_broker_not_duplicate` | Same data, different broker          | Not flagged as duplicate                     |
| DD-005  | `test_quantity_tolerance`             | Small quantity difference            | Within tolerance = match                     |
| DD-006  | `test_amount_tolerance`               | Small amount difference              | Within tolerance = match                     |
| DD-007  | `test_empty_description_not_likely`   | One desc empty                       | POSSIBLE not LIKELY                          |
| DD-008  | `test_possible_with_asset`            | Single asset candidate auto-resolved | POSSIBLE_WITH_ASSET level, filtered by asset |
| DD-009  | `test_likely_with_asset`              | Auto-resolved + same description     | LIKELY_WITH_ASSET level                      |
| DD-010  | `test_asset_filter_excludes_others`   | Asset resolved, other assets exist   | Only matches same asset_id                   |

**Fixtures Required:**

- Create test broker and transactions before tests
- Clean up after tests

---

### Category 5: File Storage

**File:** `test_brim_api.py`  
**Requires DB:** No (file system only)

| Test ID | Test Name                   | Objective           | Expected Result                  |
|---------|-----------------------------|---------------------|----------------------------------|
| FS-001  | `test_save_uploaded_file`   | File save           | UUID returned, file exists       |
| FS-002  | `test_list_files`           | List all files      | Returns list of BRIMFileInfo     |
| FS-003  | `test_list_files_by_status` | Filter by status    | Only matching status returned    |
| FS-004  | `test_get_file_info`        | Get single file     | Returns BRIMFileInfo             |
| FS-005  | `test_get_file_path`        | Get filesystem path | Path exists and is readable      |
| FS-006  | `test_delete_file`          | Delete file         | File and metadata removed        |
| FS-007  | `test_move_to_imported`     | Status transition   | File in imported folder          |
| FS-008  | `test_move_to_failed`       | Status transition   | File in failed folder with error |

**Cleanup Required:**

- Delete all test files in all folders after test run

---

### Category 6: API Endpoints

**File:** `test_brim_api.py`  
**Requires DB:** Yes  
**Requires Server:** Yes (uses test client)

#### 6.1 File Management Endpoints

| Test ID | Test Name                 | Endpoint                | Expected Result            |
|---------|---------------------------|-------------------------|----------------------------|
| API-001 | `test_upload_file`        | POST /brim/upload       | 200, BRIMFileInfo returned |
| API-002 | `test_upload_empty_file`  | POST /brim/upload       | 400, error message         |
| API-003 | `test_upload_large_file`  | POST /brim/upload       | 413, file too large        |
| API-004 | `test_list_files`         | GET /brim/files         | 200, list returned         |
| API-005 | `test_get_file`           | GET /brim/files/{id}    | 200, BRIMFileInfo          |
| API-006 | `test_get_file_not_found` | GET /brim/files/{id}    | 404                        |
| API-007 | `test_delete_file`        | DELETE /brim/files/{id} | 200, success               |
| API-008 | `test_list_plugins`       | GET /brim/plugins       | 200, List[BRIMPluginInfo]  |

#### 6.2 Parse Endpoint

| Test ID | Test Name                            | Endpoint                      | Expected Result             |
|---------|--------------------------------------|-------------------------------|-----------------------------|
| API-009 | `test_parse_file`                    | POST /import/files/{id}/parse | 200, BRIMParseResponse      |
| API-010 | `test_parse_returns_asset_mappings`  | POST /parse                   | asset_mappings populated    |
| API-011 | `test_parse_returns_duplicates`      | POST /parse                   | duplicates report populated |
| API-012 | `test_parse_file_not_found`          | POST /parse                   | 404                         |
| API-013 | `test_parse_invalid_plugin`          | POST /parse                   | 400, plugin not found       |
| API-014 | `test_parse_plugin_cannot_parse`     | POST /parse                   | 400, cannot parse           |
| API-015 | `test_parse_success_moves_to_parsed` | POST /parse                   | File status = PARSED        |
| API-016 | `test_parse_failure_moves_to_failed` | POST /parse                   | File status = FAILED        |

**Note:** Transaction import uses standard `POST /transactions` endpoint, not a BRIM-specific endpoint.
File status is automatically managed by the parse endpoint (UPLOADED → PARSED or FAILED).

---

### Category 7: End-to-End Flow

**File:** `test_brim_api.py`  
**Requires DB:** Yes  
**Requires Server:** Yes

**Flow:**

1. Upload file → `POST /import/upload` (status: UPLOADED)
2. Parse file → `POST /import/files/{id}/parse` (status: PARSED or FAILED)
3. Client resolves fake asset IDs to real asset IDs
4. Import transactions → `POST /transactions` (standard endpoint)

| Test ID | Test Name                                    | Objective                                  | Expected Result                       |
|---------|----------------------------------------------|--------------------------------------------|---------------------------------------|
| E2E-001 | `test_full_import_flow_no_assets`            | Upload → Parse → Import (deposits)         | Transactions created                  |
| E2E-002 | `test_full_import_flow_with_assets`          | Full flow with asset mapping               | Asset IDs resolved, TX created        |
| E2E-003 | `test_import_skips_duplicates`               | Parse → user deselects duplicates → Import | Only unique imported                  |
| E2E-004 | `test_reimport_same_file_creates_duplicates` | Import twice without cleanup               | Second import shows all as duplicates |
| E2E-005 | `test_full_flow_with_asset_creation`         | Full flow creating new assets              | Assets created, mapped, TX imported   |

#### E2E-005: Full Flow with Asset Creation (Detailed)

**Test File:** `generic_with_assets.csv`

```csv
date,type,quantity,amount,currency,asset,description
2025-01-02,BUY,10,-1000.00,EUR,AAPL,Buy Apple shares
2025-01-03,BUY,5,-500.00,EUR,AAPL,Buy more Apple
2025-01-04,BUY,20,-2000.00,EUR,MSFT,Buy Microsoft
2025-01-05,SELL,-5,550.00,EUR,AAPL,Sell Apple partial
2025-01-06,DIVIDEND,0,25.50,EUR,AAPL,Q4 dividend
2025-01-07,DEPOSIT,0,5000.00,EUR,,Cash deposit
2025-01-08,BUY,100,-1500.00,EUR,US0378331005,Buy via ISIN
```

**Test Steps:**

```python
@pytest.mark.asyncio
async def test_full_flow_with_asset_creation(
        client: AsyncClient,
        session: AsyncSession,
        clean_brim_test_data,
        clean_brim_files
        ):
    """
    Complete E2E test simulating real user workflow:
    1. Create test broker
    2. Upload CSV file
    3. Parse file (get fake asset IDs, asset mappings, duplicates)
    4. Create missing assets (simulating frontend flow)
    5. Replace fake IDs with real asset IDs
    6. Import transactions
    7. Verify transactions in DB
    8. Verify file moved to 'imported' folder
    """

    # =========================================================================
    # STEP 1: Setup - Create test broker
    # =========================================================================
    broker_response = await client.post("/api/v1/brokers", json=[
        {
            "name": "BRIM_TEST_BROKER",
            "description": "Test broker for E2E"
            }
        ])
    assert broker_response.status_code == 201
    broker_id = broker_response.json()["results"][0]["broker_id"]

    # =========================================================================
    # STEP 2: Upload CSV file
    # =========================================================================
    csv_path = Path("backend/app/services/brim_providers/sample_reports/generic_with_assets.csv")

    with open(csv_path, "rb") as f:
        upload_response = await client.post(
            "/api/v1/brim/upload",
            files={"file": ("generic_with_assets.csv", f, "text/csv")}
            )

    assert upload_response.status_code == 200
    file_info = upload_response.json()
    file_id = file_info["file_id"]
    assert file_info["status"] == "uploaded"
    assert "broker_generic_csv" in file_info["compatible_plugins"]

    # =========================================================================
    # STEP 3: Parse file (preview)
    # =========================================================================
    parse_response = await client.post(
        f"/api/v1/brim/files/{file_id}/parse",
        json={
            "plugin_code": "broker_generic_csv",
            "broker_id": broker_id
            }
        )

    assert parse_response.status_code == 200
    parse_result = parse_response.json()

    # Verify parse results
    transactions = parse_result["transactions"]
    asset_mappings = parse_result["asset_mappings"]
    duplicates = parse_result["duplicates"]

    assert len(transactions) == 7  # 7 rows in CSV
    assert len(asset_mappings) == 3  # AAPL, MSFT, US0378331005

    # Verify asset mappings have fake IDs
    fake_id_to_info = {m["fake_asset_id"]: m for m in asset_mappings}

    # All should be unresolved (no assets in DB yet)
    for mapping in asset_mappings:
        assert mapping["candidates"] == []  # No matches in DB
        assert mapping["selected_asset_id"] is None

    # Verify duplicates report (should be all unique, first import)
    assert len(duplicates["tx_unique_indices"]) == 7
    assert len(duplicates["tx_possible_duplicates"]) == 0
    assert len(duplicates["tx_certain_duplicates"]) == 0

    # =========================================================================
    # STEP 4: Create assets (simulating frontend creating missing assets)
    # =========================================================================

    # Find the mappings for each asset
    aapl_mapping = next(m for m in asset_mappings if m["extracted_symbol"] == "AAPL")
    msft_mapping = next(m for m in asset_mappings if m["extracted_symbol"] == "MSFT")
    isin_mapping = next(m for m in asset_mappings if m["extracted_isin"] == "US0378331005")

    # Create assets via API
    create_assets_response = await client.post("/api/v1/assets", json=[
        {
            "display_name": "BRIM_TEST_Apple Inc",
            "currency": "USD",
            "asset_type": "STOCK"
            },
        {
            "display_name": "BRIM_TEST_Microsoft Corp",
            "currency": "USD",
            "asset_type": "STOCK"
            },
        {
            "display_name": "BRIM_TEST_Unknown ISIN",
            "currency": "EUR",
            "asset_type": "STOCK"
            }
        ])

    assert create_assets_response.status_code == 201
    created_assets = create_assets_response.json()["results"]

    aapl_asset_id = created_assets[0]["asset_id"]
    msft_asset_id = created_assets[1]["asset_id"]
    isin_asset_id = created_assets[2]["asset_id"]

    # =========================================================================
    # STEP 5: Replace fake IDs with real asset IDs (simulating frontend)
    # =========================================================================

    # Build mapping: fake_id -> real_id
    fake_to_real = {
        aapl_mapping["fake_asset_id"]: aapl_asset_id,
        msft_mapping["fake_asset_id"]: msft_asset_id,
        isin_mapping["fake_asset_id"]: isin_asset_id,
        }

    # Replace fake IDs in transactions
    for tx in transactions:
        if tx["asset_id"] in fake_to_real:
            tx["asset_id"] = fake_to_real[tx["asset_id"]]
        # Add test tag for cleanup
        tx["tags"] = tx.get("tags", []) + ["brim_test"]

    # =========================================================================
    # STEP 6: Import transactions
    # =========================================================================
    import_response = await client.post(
        f"/api/v1/brim/files/{file_id}/import",
        json={
            "file_id": file_id,
            "transactions": transactions,
            "tags": ["e2e_test"]
            }
        )

    assert import_response.status_code == 200
    import_result = import_response.json()

    assert import_result["created_count"] == 7
    assert import_result["failed_count"] == 0

    # =========================================================================
    # STEP 7: Verify transactions in DB
    # =========================================================================
    from sqlalchemy import select
    from backend.app.db.models import Transaction

    stmt = select(Transaction).where(Transaction.broker_id == broker_id)
    result = await session.execute(stmt)
    db_transactions = result.scalars().all()

    assert len(db_transactions) == 7

    # Verify specific transactions
    buy_txs = [tx for tx in db_transactions if tx.type == TransactionType.BUY]
    assert len(buy_txs) == 4  # 3 BUY + 1 via ISIN

    deposit_tx = next(tx for tx in db_transactions if tx.type == TransactionType.DEPOSIT)
    assert deposit_tx.amount == Decimal("5000.00")
    assert deposit_tx.asset_id is None  # Deposit has no asset

    # =========================================================================
    # STEP 8: Verify file moved to 'imported' folder
    # =========================================================================
    file_info_response = await client.get(f"/api/v1/brim/files/{file_id}")
    assert file_info_response.status_code == 200
    assert file_info_response.json()["status"] == "imported"

    # =========================================================================
    # STEP 9: Re-parse same file to verify duplicate detection
    # =========================================================================
    # Upload same file again
    with open(csv_path, "rb") as f:
        upload2_response = await client.post(
            "/api/v1/brim/upload",
            files={"file": ("generic_with_assets.csv", f, "text/csv")}
            )

    file_id_2 = upload2_response.json()["file_id"]

    # Parse again
    parse2_response = await client.post(
        f"/api/v1/brim/files/{file_id_2}/parse",
        json={
            "plugin_code": "broker_generic_csv",
            "broker_id": broker_id
            }
        )

    parse2_result = parse2_response.json()
    duplicates2 = parse2_result["duplicates"]

    # All 7 transactions should now be flagged as duplicates
    total_duplicates = (
            len(duplicates2["tx_possible_duplicates"]) +
            len(duplicates2["tx_certain_duplicates"])
    )
    assert total_duplicates == 7, "All transactions should be detected as duplicates"
    assert len(duplicates2["tx_unique_indices"]) == 0
```

**Expected Results:**

- 7 transactions created in DB
- File status changed to "imported"
- Re-parsing shows all 7 as duplicates
- Assets created with correct associations

---

## Test Fixtures & Cleanup

### Database Cleanup Fixture

```python
@pytest.fixture
async def clean_brim_test_data(session: AsyncSession):
    """
    Clean up BRIM test data before and after each test.
    
    This fixture:
    1. Deletes all transactions with tag 'brim_test'
    2. Deletes test broker 'BRIM_TEST_BROKER'
    3. Deletes test assets with name starting with 'BRIM_TEST_'
    4. Cleans up uploaded files in broker_reports folders
    
    Runs before and after each test to ensure clean state.
    """

    async def cleanup():
        # Delete test transactions
        await session.execute(
            delete(Transaction).where(
                Transaction.tags.contains('brim_test')
                )
            )

        # Delete test broker
        await session.execute(
            delete(Broker).where(Broker.name == 'BRIM_TEST_BROKER')
            )

        # Delete test assets
        await session.execute(
            delete(Asset).where(Asset.display_name.like('BRIM_TEST_%'))
            )

        await session.commit()

    # Cleanup before test
    await cleanup()

    yield

    # Cleanup after test
    await cleanup()
```

### File Cleanup Fixture

```python
@pytest.fixture
def clean_brim_files():
    """
    Clean up BRIM test files before and after each test.
    """
    import shutil
    from backend.app.services.brim_provider import BROKER_REPORTS_DIR

    def cleanup():
        for folder in ['uploaded', 'imported', 'failed']:
            folder_path = BROKER_REPORTS_DIR / folder
            if folder_path.exists():
                for f in folder_path.glob('*'):
                    if f.is_file():
                        f.unlink()

    cleanup()
    yield
    cleanup()
```

### Test Data Fixtures

```python
@pytest.fixture
async def brim_test_broker(session: AsyncSession) -> Broker:
    """Create a test broker for BRIM tests."""
    broker = Broker(
        name="BRIM_TEST_BROKER",
        description="Test broker for BRIM tests"
        )
    session.add(broker)
    await session.commit()
    await session.refresh(broker)
    return broker


@pytest.fixture
async def brim_test_assets(session: AsyncSession) -> List[Asset]:
    """Create test assets with known identifiers for candidate search tests."""
    assets = [
        Asset(
            display_name="BRIM_TEST_APPLE",
            currency="USD",
            asset_type=AssetType.STOCK
            ),
        Asset(
            display_name="BRIM_TEST_MICROSOFT",
            currency="USD",
            asset_type=AssetType.STOCK
            ),
        ]

    for asset in assets:
        session.add(asset)
    await session.commit()

    # Add provider assignments with identifiers
    assignments = [
        AssetProviderAssignment(
            asset_id=assets[0].id,
            provider_code="yfinance",
            identifier="AAPL",
            identifier_type=IdentifierType.TICKER
            ),
        AssetProviderAssignment(
            asset_id=assets[1].id,
            provider_code="yfinance",
            identifier="US5949181045",  # MSFT ISIN
            identifier_type=IdentifierType.ISIN
            ),
        ]

    for assignment in assignments:
        session.add(assignment)
    await session.commit()

    return assets


@pytest.fixture
async def brim_test_transactions(
        session: AsyncSession,
        brim_test_broker: Broker
        ) -> List[Transaction]:
    """Create test transactions for duplicate detection tests."""
    from datetime import date
    from decimal import Decimal

    transactions = [
        Transaction(
            broker_id=brim_test_broker.id,
            type=TransactionType.DEPOSIT,
            date=date(2025, 1, 1),
            quantity=Decimal("0"),
            amount=Decimal("1000.00"),
            currency="EUR",
            description="Test deposit",
            tags="brim_test"
            ),
        Transaction(
            broker_id=brim_test_broker.id,
            type=TransactionType.BUY,
            date=date(2025, 1, 2),
            quantity=Decimal("10"),
            amount=Decimal("-500.00"),
            currency="EUR",
            description="Test buy",
            tags="brim_test"
            ),
        ]

    for tx in transactions:
        session.add(tx)
    await session.commit()

    return transactions
```

---

## Test Markers

```python
# In pytest.ini or conftest.py

pytest_plugins = ['pytest_asyncio']

# Custom markers
markers = [
    "brim: marks tests for BRIM system",
    "brim_no_db: BRIM tests that don't require database",
    "brim_db: BRIM tests that require database",
    "brim_api: BRIM API endpoint tests",
    "brim_e2e: BRIM end-to-end tests",
    ]
```

---

## Running Tests

```bash
# Run all BRIM tests
./dev.sh test brim

# Run only plugin tests (no DB)
./dev.sh test brim providers

# Run only API tests
./dev.sh test brim api

# Run with verbose output
./dev.sh test -v brim all
```

---

## Test Data Management

### Tagging Strategy

All test transactions should include the tag `brim_test` to enable easy cleanup:

```python
# When creating test transactions
tx = TXCreateItem(
    ...,
    tags=["brim_test", "import", "csv"]
    )
```

### Isolation Strategy

1. **Unique test broker:** Each test run uses `BRIM_TEST_BROKER`
2. **Unique test assets:** Names start with `BRIM_TEST_`
3. **Tagged transactions:** All have `brim_test` tag
4. **File cleanup:** All files in broker_reports deleted between tests

---

## Implementation Order

1. ⬜ Create `conftest.py` with cleanup fixtures (DB + files)
2. ⬜ Implement Category 1: Plugin Discovery tests (no DB)
3. ⬜ Implement Category 2: File Parsing tests (no DB)
4. ⬜ Implement Category 5: File Storage tests (no DB, filesystem only)
5. ⬜ Implement Category 3: Asset Candidate Search tests (needs fixtures)
6. ⬜ Implement Category 4: Duplicate Detection tests (needs fixtures)
7. ⬜ Implement Category 6: API Endpoint tests
8. ⬜ Implement Category 7: E2E tests (E2E-005 is the comprehensive test)

---

## Test File Dependencies

| Test Category          | Requires DB | Requires Server | Sample Files Used         |
|------------------------|-------------|-----------------|---------------------------|
| 1. Plugin Discovery    | No          | No              | None                      |
| 2. File Parsing        | No          | No              | All `generic_*.csv`       |
| 3. Asset Search        | Yes         | No              | None (uses fixtures)      |
| 4. Duplicate Detection | Yes         | No              | None (uses fixtures)      |
| 5. File Storage        | No          | No              | Creates temp files        |
| 6. API Endpoints       | Yes         | Yes             | `generic_simple.csv`      |
| 7. E2E Flow            | Yes         | Yes             | `generic_with_assets.csv` |

---

## Notes

- Tests should be run in isolation (each test is independent)
- Database tests use async fixtures with session scope
- API tests use the standard test client with server startup
- File tests clean the broker_reports folder before/after
- All test transactions tagged for easy cleanup
- E2E-005 is the most comprehensive test and exercises the full import flow

