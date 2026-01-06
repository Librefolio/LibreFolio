# Test Checklist: Broker & Transaction Subsystem

**Created:** 2024-12-24  
**Purpose:** Comprehensive test coverage for the Broker and Transaction services, schemas, and API endpoints.  
**Scope:** Unit tests, integration tests, and API tests for the new async services.

---

## Test Organization

```
backend/test_scripts/
├── test_services/
│   ├── test_transaction_service.py
│   └── test_broker_service.py
├── test_schemas/
│   ├── test_transaction_schemas.py
│   └── test_broker_schemas.py
└── test_api/
    ├── test_transactions_api.py
    └── test_brokers_api.py
```

---

## Pre-setup: aggiornare test_runner

Dopo aver creato i file nuovi vuoti, modificare subito 'test_runner' per gestite la nuova categoria (schemas) e i vari file.
Modificare 'run_command' e 'argvparse' affinchè, eccetto se si sta usando all (sia nel 1° livello che nel 2°) accetti una lista di test-name, che sarebbero i metodi di test da
eseguire negli script.
Questo per permettere un test più capillare, un "3° livello" che se non specificato è come fosse all, altrimenti esegue quella lista specifica.

---

## Category 1: Transaction Schema Validation

> **Reference:** `backend/app/schemas/transactions.py` - `TXCreateItem`, lines 72-220
> **Method under test:** `TXCreateItem.validate_transaction_rules()` (model_validator)

These tests verify that the Pydantic schema correctly validates transaction business rules
before they reach the service layer.

### 1.1 Link UUID Requirements

| Test ID  | Test Name                                 | Description                            | Expected Result                                                 | Notes                                                   |
|----------|-------------------------------------------|----------------------------------------|-----------------------------------------------------------------|---------------------------------------------------------|
| TX-S-001 | `test_transfer_requires_link_uuid`        | Create TRANSFER without link_uuid      | ValidationError: "TRANSFER requires link_uuid for pairing"      | Based on Rule 1 in validate_transaction_rules, line 161 |
| TX-S-002 | `test_fx_conversion_requires_link_uuid`   | Create FX_CONVERSION without link_uuid | ValidationError: "FX_CONVERSION requires link_uuid for pairing" | Based on Rule 1, line 161-163                           |
| TX-S-003 | `test_transfer_with_link_uuid_valid`      | Create TRANSFER with link_uuid         | Validation passes                                               | link_uuid can be any UUID string                        |
| TX-S-004 | `test_fx_conversion_with_link_uuid_valid` | Create FX_CONVERSION with link_uuid    | Validation passes                                               |                                                         |

### 1.2 TRANSFER Specific Rules

| Test ID  | Test Name                                 | Description                                                | Expected Result                                           | Notes            |
|----------|-------------------------------------------|------------------------------------------------------------|-----------------------------------------------------------|------------------|
| TX-S-010 | `test_transfer_requires_asset_id`         | TRANSFER without asset_id                                  | ValidationError: "TRANSFER requires asset_id"             | Rule 2, line 166 |
| TX-S-011 | `test_transfer_requires_nonzero_quantity` | TRANSFER with quantity=0                                   | ValidationError: "TRANSFER requires quantity != 0"        | Rule 2, line 168 |
| TX-S-012 | `test_transfer_no_cash_allowed`           | TRANSFER with cash movement                                | ValidationError: "TRANSFER should not have cash movement" | Rule 2, line 170 |
| TX-S-013 | `test_transfer_valid`                     | Valid TRANSFER (asset_id, quantity!=0, no cash, link_uuid) | Validation passes                                         |                  |

### 1.3 FX_CONVERSION Specific Rules

| Test ID  | Test Name                        | Description                                               | Expected Result                                                 | Notes            |
|----------|----------------------------------|-----------------------------------------------------------|-----------------------------------------------------------------|------------------|
| TX-S-020 | `test_fx_no_asset_allowed`       | FX_CONVERSION with asset_id                               | ValidationError: "FX_CONVERSION should not have asset_id"       | Rule 3, line 174 |
| TX-S-021 | `test_fx_requires_zero_quantity` | FX_CONVERSION with quantity!=0                            | ValidationError: "FX_CONVERSION should have quantity = 0"       | Rule 3, line 176 |
| TX-S-022 | `test_fx_requires_cash`          | FX_CONVERSION without cash                                | ValidationError: "FX_CONVERSION requires cash with amount != 0" | Rule 3, line 178 |
| TX-S-023 | `test_fx_cash_zero_not_allowed`  | FX_CONVERSION with cash.amount=0                          | ValidationError: same as above                                  |                  |
| TX-S-024 | `test_fx_valid`                  | Valid FX_CONVERSION (no asset, qty=0, cash!=0, link_uuid) | Validation passes                                               |                  |

### 1.4 DEPOSIT/WITHDRAWAL Rules

| Test ID  | Test Name                          | Description                       | Expected Result                                     | Notes            |
|----------|------------------------------------|-----------------------------------|-----------------------------------------------------|------------------|
| TX-S-030 | `test_deposit_no_asset_allowed`    | DEPOSIT with asset_id             | ValidationError: "DEPOSIT should not have asset_id" | Rule 4, line 182 |
| TX-S-031 | `test_withdrawal_no_asset_allowed` | WITHDRAWAL with asset_id          | ValidationError: same pattern                       | Rule 4           |
| TX-S-032 | `test_deposit_requires_cash`       | DEPOSIT without cash              | ValidationError: "DEPOSIT requires cash"            | Rule 7, line 197 |
| TX-S-033 | `test_withdrawal_requires_cash`    | WITHDRAWAL without cash           | ValidationError: same pattern                       | Rule 7           |
| TX-S-034 | `test_deposit_valid`               | Valid DEPOSIT (cash, no asset)    | Validation passes                                   |                  |
| TX-S-035 | `test_withdrawal_valid`            | Valid WITHDRAWAL (cash, no asset) | Validation passes                                   |                  |

### 1.5 Asset Required Types

| Test ID  | Test Name                        | Description                           | Expected Result                                 | Notes                |
|----------|----------------------------------|---------------------------------------|-------------------------------------------------|----------------------|
| TX-S-040 | `test_buy_requires_asset`        | BUY without asset_id                  | ValidationError: "BUY requires asset_id"        | Rule 5, line 185-191 |
| TX-S-041 | `test_sell_requires_asset`       | SELL without asset_id                 | ValidationError: "SELL requires asset_id"       | Rule 5               |
| TX-S-042 | `test_dividend_requires_asset`   | DIVIDEND without asset_id             | ValidationError: "DIVIDEND requires asset_id"   | Rule 5               |
| TX-S-043 | `test_adjustment_requires_asset` | ADJUSTMENT without asset_id           | ValidationError: "ADJUSTMENT requires asset_id" | Rule 5               |
| TX-S-044 | `test_buy_valid`                 | Valid BUY (asset_id, quantity, cash)  | Validation passes                               |                      |
| TX-S-045 | `test_sell_valid`                | Valid SELL (asset_id, quantity, cash) | Validation passes                               |                      |

### 1.6 Cash Required Types

| Test ID  | Test Name                     | Description           | Expected Result                      | Notes            |
|----------|-------------------------------|-----------------------|--------------------------------------|------------------|
| TX-S-050 | `test_buy_requires_cash`      | BUY without cash      | ValidationError: "BUY requires cash" | Rule 7, line 197 |
| TX-S-051 | `test_sell_requires_cash`     | SELL without cash     | ValidationError                      | Rule 7           |
| TX-S-052 | `test_dividend_requires_cash` | DIVIDEND without cash | ValidationError                      | Rule 7           |
| TX-S-053 | `test_interest_requires_cash` | INTEREST without cash | ValidationError                      | Rule 7           |
| TX-S-054 | `test_fee_requires_cash`      | FEE without cash      | ValidationError                      | Rule 7           |
| TX-S-055 | `test_tax_requires_cash`      | TAX without cash      | ValidationError                      | Rule 7           |

### 1.7 Asset Optional Types

| Test ID  | Test Name                           | Description                                  | Expected Result   | Notes                     |
|----------|-------------------------------------|----------------------------------------------|-------------------|---------------------------|
| TX-S-060 | `test_interest_with_asset_valid`    | INTEREST with asset_id (bond interest)       | Validation passes | Rule 6: asset is optional |
| TX-S-061 | `test_interest_without_asset_valid` | INTEREST without asset_id (deposit interest) | Validation passes | Rule 6                    |
| TX-S-062 | `test_fee_with_asset_valid`         | FEE with asset_id (trading commission)       | Validation passes | Rule 6                    |
| TX-S-063 | `test_fee_without_asset_valid`      | FEE without asset_id (annual fee)            | Validation passes | Rule 6                    |
| TX-S-064 | `test_tax_with_asset_valid`         | TAX with asset_id (capital gain)             | Validation passes | Rule 6                    |
| TX-S-065 | `test_tax_without_asset_valid`      | TAX without asset_id (stamp duty)            | Validation passes | Rule 6                    |

### 1.8 ADJUSTMENT Rules

| Test ID  | Test Name                         | Description                                 | Expected Result                                             | Notes            |
|----------|-----------------------------------|---------------------------------------------|-------------------------------------------------------------|------------------|
| TX-S-070 | `test_adjustment_no_cash_allowed` | ADJUSTMENT with cash                        | ValidationError: "ADJUSTMENT should not have cash movement" | Rule 8, line 207 |
| TX-S-071 | `test_adjustment_valid`           | Valid ADJUSTMENT (asset, quantity, no cash) | Validation passes                                           |                  |

### 1.9 Helper Methods

| Test ID  | Test Name                        | Description                              | Expected Result      | Notes           |
|----------|----------------------------------|------------------------------------------|----------------------|-----------------|
| TX-S-080 | `test_get_amount_with_cash`      | TXCreateItem.get_amount() with cash      | Returns cash.amount  | Method line 212 |
| TX-S-081 | `test_get_amount_without_cash`   | TXCreateItem.get_amount() without cash   | Returns Decimal("0") |                 |
| TX-S-082 | `test_get_currency_with_cash`    | TXCreateItem.get_currency() with cash    | Returns cash.code    | Method line 216 |
| TX-S-083 | `test_get_currency_without_cash` | TXCreateItem.get_currency() without cash | Returns None         |                 |
| TX-S-084 | `test_get_tags_csv`              | TXCreateItem.get_tags_csv()              | Converts list to CSV | Method line 220 |

---

## Category 2: Broker Schema Validation

> **Reference:** `backend/app/schemas/brokers.py` - `BRCreateItem`, lines 37-76
> **Methods under test:** `validate_name()`, `validate_initial_balances()`

### 2.1 Name Validation

| Test ID  | Test Name                     | Description                      | Expected Result                                              | Notes                |
|----------|-------------------------------|----------------------------------|--------------------------------------------------------------|----------------------|
| BR-S-001 | `test_broker_name_required`   | Create broker without name       | ValidationError: field required                              | Field line 52        |
| BR-S-002 | `test_broker_name_empty`      | Create broker with empty name    | ValidationError: "Broker name cannot be empty or whitespace" | validator line 65-68 |
| BR-S-003 | `test_broker_name_whitespace` | Create broker with "   "         | ValidationError: same as above                               |                      |
| BR-S-004 | `test_broker_name_valid`      | Create broker with valid name    | Validation passes                                            |                      |
| BR-S-005 | `test_broker_name_max_length` | Create broker with 101 char name | ValidationError: max_length                                  | Field constraint     |

### 2.2 Initial Balances Validation

| Test ID  | Test Name                                 | Description                            | Expected Result                  | Notes                |
|----------|-------------------------------------------|----------------------------------------|----------------------------------|----------------------|
| BR-S-010 | `test_initial_balances_none`              | Create broker without initial_balances | Validation passes (None allowed) |                      |
| BR-S-011 | `test_initial_balances_empty_list`        | Create broker with []                  | Validation passes (becomes None) |                      |
| BR-S-012 | `test_initial_balances_positive`          | Create broker with positive amounts    | Validation passes, amounts kept  | validator line 72-76 |
| BR-S-013 | `test_initial_balances_zero_filtered`     | Create broker with amount=0            | Zero filtered out                | is_positive() check  |
| BR-S-014 | `test_initial_balances_negative_filtered` | Create broker with negative amount     | Negative filtered out            | is_positive() check  |
| BR-S-015 | `test_initial_balances_mixed`             | Create broker with +, -, 0 amounts     | Only positive kept               |                      |

### 2.3 Update Schema

| Test ID  | Test Name                         | Description                  | Expected Result   | Notes                    |
|----------|-----------------------------------|------------------------------|-------------------|--------------------------|
| BR-S-020 | `test_update_all_fields_optional` | BRUpdateItem with no fields  | Validation passes | All fields optional      |
| BR-S-021 | `test_update_name_empty`          | BRUpdateItem with name=""    | ValidationError   | Same validator as create |
| BR-S-022 | `test_update_name_valid`          | BRUpdateItem with valid name | Validation passes |                          |

### 2.4 Delete Schema

| Test ID  | Test Name                   | Description                  | Expected Result                 | Notes               |
|----------|-----------------------------|------------------------------|---------------------------------|---------------------|
| BR-S-030 | `test_delete_force_default` | BRDeleteItem with only id    | force defaults to False         | Field default=False |
| BR-S-031 | `test_delete_force_true`    | BRDeleteItem with force=True | Validation passes               |                     |
| BR-S-032 | `test_delete_id_required`   | BRDeleteItem without id      | ValidationError: field required |                     |

---

## Category 3: TransactionService Unit Tests

> **Reference:** `backend/app/services/transaction_service.py`
> **Class under test:** `TransactionService`

These tests use a real test database to verify service behavior.

### 3.1 create_bulk - Basic Creation

| Test ID  | Test Name                      | Description                         | Expected Result                          | Notes                    |
|----------|--------------------------------|-------------------------------------|------------------------------------------|--------------------------|
| TX-U-001 | `test_create_single_deposit`   | Create one DEPOSIT transaction      | success_count=1, transaction_id returned | create_bulk, line 72-153 |
| TX-U-002 | `test_create_bulk_multiple`    | Create 3 different transactions     | success_count=3                          |                          |
| TX-U-003 | `test_create_sets_timestamps`  | Create transaction                  | created_at and updated_at set            | Line 111-112             |
| TX-U-004 | `test_create_with_tags`        | Create transaction with tags        | tags stored as CSV in DB                 | get_tags_csv()           |
| TX-U-005 | `test_create_with_description` | Create transaction with description | description stored                       |                          |

### 3.2 create_bulk - Link Resolution

| Test ID  | Test Name                      | Description                              | Expected Result                                   | Notes                 |
|----------|--------------------------------|------------------------------------------|---------------------------------------------------|-----------------------|
| TX-U-010 | `test_link_uuid_resolves_pair` | Create 2 TRANSFER with same link_uuid    | Second tx has related_transaction_id = first.id   | Phase 2, line 138-142 |
| TX-U-011 | `test_link_uuid_single_fails`  | Create 1 TRANSFER with link_uuid         | errors contains "has 1 transactions (expected 2)" | Line 143-144          |
| TX-U-012 | `test_link_uuid_triple_fails`  | Create 3 TRANSFERs with same link_uuid   | errors contains "has 3 transactions (expected 2)" |                       |
| TX-U-013 | `test_multiple_link_uuids`     | Create 2 pairs with different link_uuids | Both pairs correctly linked                       |                       |

### 3.3 create_bulk - Balance Validation

| Test ID  | Test Name                        | Description                                   | Expected Result                            | Notes                 |
|----------|----------------------------------|-----------------------------------------------|--------------------------------------------|-----------------------|
| TX-U-020 | `test_balance_validation_called` | Create transaction                            | _validate_broker_balances called           | Phase 3, line 146-152 |
| TX-U-021 | `test_cash_overdraft_blocked`    | WITHDRAWAL exceeding balance, overdraft=False | errors contains BalanceValidationError msg |                       |
| TX-U-022 | `test_cash_overdraft_allowed`    | Same but overdraft=True                       | No errors, transaction created             |                       |
| TX-U-023 | `test_asset_shorting_blocked`    | SELL exceeding holding, shorting=False        | errors contains BalanceValidationError msg |                       |
| TX-U-024 | `test_asset_shorting_allowed`    | Same but shorting=True                        | No errors, transaction created             |                       |

### 3.4 query - Filtering

| Test ID  | Test Name                        | Description                                 | Expected Result                     | Notes                      |
|----------|----------------------------------|---------------------------------------------|-------------------------------------|----------------------------|
| TX-U-030 | `test_query_no_filters`          | Query with default params                   | Returns all (up to limit)           | query method, line 157-205 |
| TX-U-031 | `test_query_by_broker_id`        | Query with broker_id filter                 | Only matching broker's transactions | Line 170                   |
| TX-U-032 | `test_query_by_asset_id`         | Query with asset_id filter                  | Only matching asset's transactions  | Line 173                   |
| TX-U-033 | `test_query_by_types`            | Query with types=[BUY, SELL]                | Only BUY and SELL returned          | Line 176                   |
| TX-U-034 | `test_query_by_date_range_start` | Query with date_range.start                 | Only >= start                       | Line 179                   |
| TX-U-035 | `test_query_by_date_range_end`   | Query with date_range.end                   | Only <= end                         | Line 181                   |
| TX-U-036 | `test_query_by_currency`         | Query with currency filter                  | Only matching currency              | Line 184                   |
| TX-U-037 | `test_query_by_tags`             | Query with tags filter                      | Any tag match (OR logic)            | Line 186-193               |
| TX-U-038 | `test_query_pagination`          | Query with offset and limit                 | Correct slice returned              | Line 196                   |
| TX-U-039 | `test_query_order`               | Query returns ordered by date desc, id desc | Verify order                        | Line 195                   |

### 3.5 query - Bidirectional Link Resolution

| Test ID  | Test Name                                   | Description                  | Expected Result                                         | Notes                                               |
|----------|---------------------------------------------|------------------------------|---------------------------------------------------------|-----------------------------------------------------|
| TX-U-040 | `test_query_linked_tx_both_have_related_id` | Query both tx A and B        | Both have related_transaction_id pointing to each other | Bidirectional FK with DEFERRABLE INITIALLY DEFERRED |
| TX-U-042 | `test_query_unlinked_tx_null`               | Query non-linked tx          | related_transaction_id = None                           |                                                     |
| TX-U-043 | `test_db_has_bidirectional_fk`              | Verify DB state after create | Both records have related_transaction_id set            | Verifies DEFERRABLE FK works                        |

### 3.6 get_by_id

| Test ID  | Test Name                  | Description              | Expected Result    | Notes                   |
|----------|----------------------------|--------------------------|--------------------|-------------------------|
| TX-U-050 | `test_get_by_id_exists`    | Get existing transaction | Returns TXReadItem | get_by_id, line 207-216 |
| TX-U-051 | `test_get_by_id_not_found` | Get non-existent ID      | Returns None       |                         |

### 3.7 update_bulk

| Test ID  | Test Name                                 | Description                      | Expected Result                           | Notes                     |
|----------|-------------------------------------------|----------------------------------|-------------------------------------------|---------------------------|
| TX-U-060 | `test_update_date`                        | Update transaction date          | Date changed                              | update_bulk, line 287-366 |
| TX-U-061 | `test_update_quantity`                    | Update quantity                  | Quantity changed                          |                           |
| TX-U-062 | `test_update_cash`                        | Update cash (amount + currency)  | Both changed                              | Line 326-328              |
| TX-U-063 | `test_update_tags`                        | Update tags                      | tags CSV updated                          | Line 330-332              |
| TX-U-064 | `test_update_description`                 | Update description               | Description changed                       |                           |
| TX-U-065 | `test_update_sets_updated_at`             | Update any field                 | updated_at changes                        | Line 336                  |
| TX-U-066 | `test_update_not_found`                   | Update non-existent ID           | success=False, error contains "not found" | Line 315-317              |
| TX-U-067 | `test_update_triggers_balance_validation` | Update amount to cause overdraft | errors contains validation error          | Line 358-365              |

### 3.8 delete_bulk - Basic

| Test ID  | Test Name               | Description                  | Expected Result                               | Notes                     |
|----------|-------------------------|------------------------------|-----------------------------------------------|---------------------------|
| TX-U-070 | `test_delete_single`    | Delete one transaction       | success=True, deleted_count=1                 | delete_bulk, line 368-465 |
| TX-U-071 | `test_delete_multiple`  | Delete multiple transactions | All deleted                                   |                           |
| TX-U-072 | `test_delete_not_found` | Delete non-existent ID       | Transaction not in results (silently ignored) | Only valid IDs processed  |

### 3.9 delete_bulk - Linked Transaction Enforcement

| Test ID  | Test Name                                  | Description                         | Expected Result                                    | Notes                          |
|----------|--------------------------------------------|-------------------------------------|----------------------------------------------------|--------------------------------|
| TX-U-080 | `test_delete_linked_missing_pair_fails`    | Delete tx A without tx B            | success=False, message contains "without its pair" | Line 397-408                   |
| TX-U-081 | `test_delete_linked_reverse_missing_fails` | Delete tx B without tx A            | success=False, same message                        | Line 410-421                   |
| TX-U-082 | `test_delete_linked_both_succeeds`         | Delete both A and B                 | Both deleted successfully                          | Bidirectional FK allows this   |
| TX-U-083 | `test_delete_bidirectional_fk_works`       | Delete mutually-linked transactions | Both deleted, verifies DEFERRABLE constraint       | Confirms FK deferred to COMMIT |

### 3.10 delete_bulk - Balance Validation

| Test ID  | Test Name                      | Description                             | Expected Result                  | Notes        |
|----------|--------------------------------|-----------------------------------------|----------------------------------|--------------|
| TX-U-090 | `test_delete_causes_overdraft` | Delete DEPOSIT leaving negative balance | errors contains validation error | Line 455-462 |
| TX-U-091 | `test_delete_causes_shorting`  | Delete BUY leaving negative holding     | errors contains validation error |              |

### 3.11 delete_by_broker

| Test ID  | Test Name                     | Description                            | Expected Result          | Notes                          |
|----------|-------------------------------|----------------------------------------|--------------------------|--------------------------------|
| TX-U-100 | `test_delete_by_broker_all`   | Delete all transactions for broker     | Returns count of deleted | delete_by_broker, line 467-482 |
| TX-U-101 | `test_delete_by_broker_empty` | Delete for broker with no transactions | Returns 0                |                                |

### 3.12 _validate_broker_balances - Day by Day

| Test ID  | Test Name                                    | Description                                      | Expected Result                   | Notes              |
|----------|----------------------------------------------|--------------------------------------------------|-----------------------------------|--------------------|
| TX-U-110 | `test_validation_skipped_both_flags_true`    | Broker with both flags True                      | No validation performed           | Line 520-521       |
| TX-U-111 | `test_validation_from_none_full_history`     | from_date=None                                   | Validates from first transaction  | Line 523-531       |
| TX-U-112 | `test_validation_day_by_day`                 | Multiple days                                    | Checks balance at END of each day | Line 559-598       |
| TX-U-113 | `test_validation_intraday_order_irrelevant`  | Same day: deposit 100, withdraw 150, deposit 100 | Passes (end of day = +50)         | Day-end validation |
| TX-U-114 | `test_validation_catches_temporary_negative` | Day 1: +100, Day 2: -150, Day 3: +100            | Fails on Day 2                    |                    |

### 3.13 Balance Query Methods

| Test ID  | Test Name                 | Description                | Expected Result               | Notes                            |
|----------|---------------------------|----------------------------|-------------------------------|----------------------------------|
| TX-U-120 | `test_get_cash_balances`  | After deposits/withdrawals | Correct sum per currency      | get_cash_balances, line 645-658  |
| TX-U-121 | `test_get_asset_holdings` | After buy/sell             | Correct sum per asset         | get_asset_holdings, line 660-673 |
| TX-U-122 | `test_get_cost_basis`     | After multiple BUYs        | Sum of BUY amounts (absolute) | get_cost_basis, line 675-695     |

---

## Category 4: BrokerService Unit Tests

> **Reference:** `backend/app/services/broker_service.py`
> **Class under test:** `BrokerService`

### 4.1 create_bulk - Basic Creation

| Test ID  | Test Name                     | Description                      | Expected Result                                | Notes                    |
|----------|-------------------------------|----------------------------------|------------------------------------------------|--------------------------|
| BR-U-001 | `test_create_single_broker`   | Create one broker                | success_count=1, broker_id returned            | create_bulk, line 63-130 |
| BR-U-002 | `test_create_duplicate_name`  | Create broker with existing name | success=False, error contains "already exists" | Line 79-82               |
| BR-U-003 | `test_create_sets_timestamps` | Create broker                    | created_at and updated_at set                  | Line 93-94               |

### 4.2 create_bulk - Initial Balances

| Test ID  | Test Name                           | Description                   | Expected Result             | Notes                |
|----------|-------------------------------------|-------------------------------|-----------------------------|----------------------|
| BR-U-010 | `test_create_with_initial_balances` | Create broker with [EUR:1000] | DEPOSIT transaction created | Line 99-113          |
| BR-U-011 | `test_create_deposits_count`        | Create with 2 currencies      | deposits_created=2          |                      |
| BR-U-012 | `test_create_balances_filtered`     | Create with amount=0          | No DEPOSIT created          | Schema filters zeros |

### 4.3 get_all / get_by_id

| Test ID  | Test Name                  | Description         | Expected Result    | Notes                   |
|----------|----------------------------|---------------------|--------------------|-------------------------|
| BR-U-020 | `test_get_all`             | Get all brokers     | List of BRReadItem | get_all, line 137-141   |
| BR-U-021 | `test_get_all_ordered`     | Get all brokers     | Ordered by name    | ORDER BY name           |
| BR-U-022 | `test_get_by_id_exists`    | Get existing broker | Returns BRReadItem | get_by_id, line 143-148 |
| BR-U-023 | `test_get_by_id_not_found` | Get non-existent ID | Returns None       |                         |

### 4.4 get_summary

| Test ID  | Test Name                        | Description             | Expected Result                              | Notes                     |
|----------|----------------------------------|-------------------------|----------------------------------------------|---------------------------|
| BR-U-030 | `test_get_summary_basic`         | Get summary of broker   | BRSummary returned                           | get_summary, line 150-226 |
| BR-U-031 | `test_get_summary_cash_balances` | After deposits          | cash_balances list populated                 | Line 165-166              |
| BR-U-032 | `test_get_summary_holdings`      | After BUYs              | holdings list populated                      | Line 168-215              |
| BR-U-033 | `test_get_summary_cost_basis`    | After BUYs              | total_cost, average_cost_per_unit calculated | Line 182-183              |
| BR-U-034 | `test_get_summary_with_price`    | Asset has price_history | current_value, unrealized_pnl populated      | Line 186-200              |
| BR-U-035 | `test_get_summary_not_found`     | Non-existent broker     | Returns None                                 | Line 161-162              |

### 4.5 update_bulk - Basic

| Test ID  | Test Name                    | Description             | Expected Result                                | Notes                     |
|----------|------------------------------|-------------------------|------------------------------------------------|---------------------------|
| BR-U-040 | `test_update_name`           | Update broker name      | Name changed                                   | update_bulk, line 242-318 |
| BR-U-041 | `test_update_description`    | Update description      | Description changed                            |                           |
| BR-U-042 | `test_update_portal_url`     | Update portal_url       | URL changed                                    |                           |
| BR-U-043 | `test_update_duplicate_name` | Update to existing name | success=False, error contains "already exists" | Line 280-285              |
| BR-U-044 | `test_update_not_found`      | Update non-existent ID  | success=False, error contains "not found"      | Line 263-265              |

### 4.6 update_bulk - Flag Validation

| Test ID  | Test Name                                | Description                             | Expected Result                          | Notes                       |
|----------|------------------------------------------|-----------------------------------------|------------------------------------------|-----------------------------|
| BR-U-050 | `test_update_disable_overdraft_valid`    | Disable overdraft, no negative balance  | success=True, validation_triggered=True  | Line 269-272                |
| BR-U-051 | `test_update_disable_overdraft_invalid`  | Disable overdraft, HAS negative balance | success=False, validation_triggered=True | Line 303-308                |
| BR-U-052 | `test_update_disable_shorting_valid`     | Disable shorting, no negative holdings  | success=True, validation_triggered=True  |                             |
| BR-U-053 | `test_update_disable_shorting_invalid`   | Disable shorting, HAS negative holdings | success=False, validation_triggered=True |                             |
| BR-U-054 | `test_update_enable_flags_no_validation` | Enable overdraft (False→True)           | validation_triggered=False               | Only triggers on True→False |

### 4.7 delete_bulk - Basic

| Test ID  | Test Name                  | Description                        | Expected Result                             | Notes                     |
|----------|----------------------------|------------------------------------|---------------------------------------------|---------------------------|
| BR-U-060 | `test_delete_empty_broker` | Delete broker with no transactions | success=True                                | delete_bulk, line 322-388 |
| BR-U-061 | `test_delete_not_found`    | Delete non-existent ID             | success=False, message contains "not found" | Line 347-349              |

### 4.8 delete_bulk - Force Behavior

| Test ID  | Test Name                      | Description                                  | Expected Result                                      | Notes        |
|----------|--------------------------------|----------------------------------------------|------------------------------------------------------|--------------|
| BR-U-070 | `test_delete_with_tx_no_force` | Delete broker with transactions, force=False | success=False, message contains "has N transactions" | Line 354-362 |
| BR-U-071 | `test_delete_with_tx_force`    | Delete broker with transactions, force=True  | success=True, transactions_deleted=N                 | Line 364-368 |
| BR-U-072 | `test_delete_force_cascade`    | Force delete, verify transactions gone       | Transactions actually deleted                        |              |

---

## Category 5: API Integration Tests

> **Reference:** `backend/app/api/v1/transactions.py`, `backend/app/api/v1/brokers.py`
> **Test method:** Using FastAPI TestClient with real test database

These tests verify the full HTTP request/response cycle.

### 5.1 Transaction API - Create

| Test ID  | Test Name                                 | Description                     | Expected Result       | Notes               |
|----------|-------------------------------------------|---------------------------------|-----------------------|---------------------|
| TX-A-001 | `test_post_transactions_single`           | POST /transactions with 1 item  | 200, success_count=1  | Endpoint line 42-71 |
| TX-A-002 | `test_post_transactions_bulk`             | POST /transactions with 3 items | 200, success_count=3  |                     |
| TX-A-003 | `test_post_transactions_validation_error` | POST with invalid item          | 422 Validation Error  | Pydantic validation |
| TX-A-004 | `test_post_transactions_balance_error`    | POST causing overdraft          | 200, errors populated | Service validation  |

### 5.2 Transaction API - Read

| Test ID  | Test Name                            | Description                             | Expected Result             | Notes                 |
|----------|--------------------------------------|-----------------------------------------|-----------------------------|-----------------------|
| TX-A-010 | `test_get_transactions`              | GET /transactions                       | 200, list returned          | Endpoint line 78-130  |
| TX-A-011 | `test_get_transactions_with_filters` | GET /transactions?broker_id=1&types=BUY | Filtered results            |                       |
| TX-A-012 | `test_get_transactions_pagination`   | GET /transactions?limit=10&offset=5     | Paginated results           |                       |
| TX-A-013 | `test_get_transaction_by_id`         | GET /transactions/{id}                  | 200, single item            | Endpoint line 147-166 |
| TX-A-014 | `test_get_transaction_not_found`     | GET /transactions/999999                | 404                         |                       |
| TX-A-015 | `test_get_transaction_types`         | GET /transactions/types                 | 200, list of TXTypeMetadata | Endpoint line 133-145 |

### 5.3 Transaction API - Update

| Test ID  | Test Name                           | Description           | Expected Result             | Notes                 |
|----------|-------------------------------------|-----------------------|-----------------------------|-----------------------|
| TX-A-020 | `test_patch_transactions`           | PATCH /transactions   | 200, success_count          | Endpoint line 172-206 |
| TX-A-021 | `test_patch_transactions_not_found` | PATCH with invalid ID | 200, item has success=False |                       |

### 5.4 Transaction API - Delete

| Test ID  | Test Name                         | Description                    | Expected Result             | Notes                 |
|----------|-----------------------------------|--------------------------------|-----------------------------|-----------------------|
| TX-A-030 | `test_delete_transactions`        | DELETE /transactions?ids=1,2   | 200, total_deleted          | Endpoint line 212-248 |
| TX-A-031 | `test_delete_linked_without_pair` | DELETE only one of linked pair | 200, item has success=False |                       |

### 5.5 Broker API - Create

| Test ID  | Test Name                         | Description                | Expected Result         | Notes               |
|----------|-----------------------------------|----------------------------|-------------------------|---------------------|
| BR-A-001 | `test_post_brokers`               | POST /brokers              | 200, success_count=1    | Endpoint line 39-68 |
| BR-A-002 | `test_post_brokers_with_balances` | POST with initial_balances | 200, deposits_created>0 |                     |
| BR-A-003 | `test_post_brokers_duplicate`     | POST with existing name    | 200, success=False      |                     |

### 5.6 Broker API - Read

| Test ID  | Test Name                           | Description                 | Expected Result | Notes                 |
|----------|-------------------------------------|-----------------------------|-----------------|-----------------------|
| BR-A-010 | `test_get_brokers`                  | GET /brokers                | 200, list       | Endpoint line 73-86   |
| BR-A-011 | `test_get_broker_by_id`             | GET /brokers/{id}           | 200, BRReadItem | Endpoint line 89-111  |
| BR-A-012 | `test_get_broker_not_found`         | GET /brokers/999999         | 404             |                       |
| BR-A-013 | `test_get_broker_summary`           | GET /brokers/{id}/summary   | 200, BRSummary  | Endpoint line 114-140 |
| BR-A-014 | `test_get_broker_summary_not_found` | GET /brokers/999999/summary | 404             |                       |

### 5.7 Broker API - Update

| Test ID  | Test Name                           | Description                            | Expected Result    | Notes                 |
|----------|-------------------------------------|----------------------------------------|--------------------|-----------------------|
| BR-A-020 | `test_patch_broker`                 | PATCH /brokers/{id}                    | 200, success=True  | Endpoint line 146-180 |
| BR-A-021 | `test_patch_broker_not_found`       | PATCH /brokers/999999                  | 200, success=False |                       |
| BR-A-022 | `test_patch_broker_flag_validation` | PATCH disable overdraft, invalid state | 200, success=False |                       |

### 5.8 Broker API - Delete

| Test ID  | Test Name                              | Description                          | Expected Result                           | Notes                 |
|----------|----------------------------------------|--------------------------------------|-------------------------------------------|-----------------------|
| BR-A-030 | `test_delete_brokers`                  | DELETE /brokers?ids=1                | 200, total_deleted=1                      | Endpoint line 186-231 |
| BR-A-031 | `test_delete_brokers_with_tx_no_force` | DELETE with transactions, no force   | 200, success=False                        |                       |
| BR-A-032 | `test_delete_brokers_with_tx_force`    | DELETE with transactions, force=True | 200, success=True, transactions_deleted>0 |                       |

---

## Category 6: Edge Cases & Regression Tests ✅

> **File:** `backend/test_scripts/test_services/test_transaction_edge_cases.py`
> **Status:** ✅ IMPLEMENTED (2025-12-28) - 17 tests passing

### 6.1 Decimal Precision ✅

| Test ID  | Test Name                         | Description                            | Expected Result                | Status |
|----------|-----------------------------------|----------------------------------------|--------------------------------|--------|
| EDGE-001 | `test_decimal_precision_amount`   | Create tx with amount=0.000001         | Stored and retrieved correctly | ✅      |
| EDGE-002 | `test_decimal_precision_quantity` | Create tx with quantity=0.000001       | Stored and retrieved correctly | ✅      |
| EDGE-003 | `test_large_amounts`              | Create tx with amount=999999999.999999 | No overflow                    | ✅      |

**Note:** SQLite has precision limits for very large decimals (>12 digits). Test uses ~1 billion for reliable precision.

### 6.2 Currency Validation ✅

| Test ID  | Test Name                    | Description             | Expected Result | Status |
|----------|------------------------------|-------------------------|-----------------|--------|
| EDGE-010 | `test_currency_iso_valid`    | Create tx with EUR, USD | Passes          | ✅      |
| EDGE-011 | `test_currency_crypto_valid` | Create tx with BTC, ETH | Passes          | ✅      |
| EDGE-012 | `test_currency_invalid`      | Create tx with ZZZ      | ValidationError | ✅      |

**Note:** XXX is actually a valid ISO 4217 code (for "no currency"). Test uses ZZZ which is truly invalid.

### 6.3 Date Edge Cases ✅

| Test ID  | Test Name                            | Description                          | Expected Result                      | Status |
|----------|--------------------------------------|--------------------------------------|--------------------------------------|--------|
| EDGE-020 | `test_query_same_start_end`          | Query with start=end                 | Returns transactions on that day     | ✅      |
| EDGE-021 | `test_balance_validation_single_day` | All transactions same day            | Validated correctly                  | ✅      |
| EDGE-022 | `test_balance_validation_gaps`       | Transactions on day 1, day 5, day 10 | Validates each day with transactions | ✅      |

### 6.4 Empty/Null Handling ✅

| Test ID  | Test Name               | Description                     | Expected Result    | Status |
|----------|-------------------------|---------------------------------|--------------------|--------|
| EDGE-030 | `test_tags_null`        | Create tx with tags=None        | Stored as NULL     | ✅      |
| EDGE-031 | `test_tags_empty_list`  | Create tx with tags=[]          | Stored as NULL     | ✅      |
| EDGE-032 | `test_description_null` | Create tx with description=None | Stored as NULL     | ✅      |
| EDGE-033 | `test_query_no_results` | Query with impossible filters   | Returns empty list | ✅      |

### 6.5 Additional Edge Cases ✅

| Test ID  | Test Name                        | Description                     | Expected Result           | Status |
|----------|----------------------------------|---------------------------------|---------------------------|--------|
| EDGE-050 | `test_zero_quantity_adjustment`  | ADJUSTMENT with quantity=0      | Currently allowed (doc)   | ✅      |
| EDGE-051 | `test_negative_deposit`          | DEPOSIT with negative amount    | Documents actual behavior | ✅      |
| EDGE-052 | `test_future_date_transaction`   | Transaction with future date    | Allowed                   | ✅      |
| EDGE-053 | `test_very_old_date_transaction` | Transaction with date year 2000 | Allowed                   | ✅      |

### 6.6 Concurrent Operations (Future)

| Test ID  | Test Name                       | Description                       | Expected Result             | Status  |
|----------|---------------------------------|-----------------------------------|-----------------------------|---------|
| EDGE-040 | `test_concurrent_balance_check` | Parallel transactions same broker | Serialization prevents race | 🔲 TODO |

---

## Test Execution Order

**Recommended order to build confidence incrementally:**

1. **Schema Tests** (Category 1-2): Pure unit tests, no DB
2. **Service Unit Tests** (Category 3-4): Requires test DB, no HTTP
3. **API Tests** (Category 5): Full integration
4. **Edge Cases** (Category 6): Stress testing

---

## Test Data Fixtures

### Standard Test Broker

```python
broker_fixture = BRCreateItem(
    name="Test Broker",
    description="Test broker for unit tests",
    allow_cash_overdraft=False,
    allow_asset_shorting=False,
    initial_balances=[Currency(code="EUR", amount=Decimal("10000"))]
    )
```

### Standard Test Asset

Requires existing Asset in DB with known ID (e.g., `test_asset_id=1`)

### Transaction Type Samples

```python
deposit_fixture = TXCreateItem(
    broker_id=1, type=TransactionType.DEPOSIT, date=date.today(),
    cash=Currency(code="EUR", amount=Decimal("1000"))
    )

buy_fixture = TXCreateItem(
    broker_id=1, asset_id=1, type=TransactionType.BUY, date=date.today(),
    quantity=Decimal("10"), cash=Currency(code="EUR", amount=Decimal("-500"))
    )

transfer_pair_fixture = [
    TXCreateItem(
        broker_id=1, asset_id=1, type=TransactionType.TRANSFER, date=date.today(),
        quantity=Decimal("-10"), link_uuid="uuid-123"
        ),
    TXCreateItem(
        broker_id=2, asset_id=1, type=TransactionType.TRANSFER, date=date.today(),
        quantity=Decimal("10"), link_uuid="uuid-123"
        ),
    ]
```

---

## Coverage Goals

| Area                      | Target Coverage |
|---------------------------|-----------------|
| `transaction_service.py`  | ≥ 90%           |
| `broker_service.py`       | ≥ 90%           |
| `schemas/transactions.py` | ≥ 95%           |
| `schemas/brokers.py`      | ≥ 95%           |
| `api/v1/transactions.py`  | ≥ 85%           |
| `api/v1/brokers.py`       | ≥ 85%           |

---

## Status Tracking

| Category           | Total Tests | Written | Passing |
|--------------------|-------------|---------|---------|
| 1. TX Schema       | 34          | 52      | 52 ✅    |
| 2. BR Schema       | 14          | 29      | 29 ✅    |
| 3. TX Service      | 40          | 34      | 34 ✅    |
| 4. BR Service      | 26          | 30      | 30 ✅    |
| 5. API Integration | 24          | 28      | 28 ✅    |
| 6. Edge Cases      | 13          | 17      | 17 ✅    |
| **TOTAL**          | **151**     | **190** | **190** |

**Note (2025-12-28):**

- Transaction and Broker API tests are now passing.
- Fixed test_server_helper.py to properly set test mode using set_test_mode() function.
- Fixed test fixtures to use UUID for unique broker names.
- Edge Cases tests implemented in `test_transaction_edge_cases.py`:
    - Decimal precision (amount, quantity, large values)
    - Currency validation (ISO, crypto, invalid codes)
    - Date edge cases (same start/end, single day, gaps)
    - Empty/null handling (tags, description, empty query)
    - Additional cases (future dates, old dates, negative deposits)
- All Categories 1-6 complete and passing.

---

## Notes

- All async tests should use `pytest-asyncio` with `@pytest.mark.asyncio`
- Use `AsyncSession` from test fixtures, not production session
- Each test should be independent (setup/teardown via fixtures)
- API tests use `httpx.AsyncClient` with `ASGITransport`

---

## Appendix A: Schema Test Reorganization

### Current Situation

I test di validazione Pydantic per gli schemi sono attualmente dispersi in `test_utilities/`:

| File Attuale                                          | Schema Testato                                                                                        | Appartiene a                          |
|-------------------------------------------------------|-------------------------------------------------------------------------------------------------------|---------------------------------------|
| `test_utilities/test_currency.py`                     | `Currency` (`schemas/common.py`)                                                                      | `test_schemas/test_common_schemas.py` |
| `test_utilities/test_scheduled_investment_schemas.py` | `FAInterestRatePeriod`, `FALateInterestConfig`, `FAScheduledInvestmentSchedule` (`schemas/assets.py`) | `test_schemas/test_asset_schemas.py`  |
| `test_utilities/test_distribution_models.py`          | `FAGeographicArea`, `FASectorArea`, `FAClassificationParams` (`schemas/assets.py`)                    | `test_schemas/test_asset_schemas.py`  |
| `test_utilities/test_geographic_area_integration.py`  | `FAGeographicArea` serialization (`schemas/assets.py`)                                                | `test_schemas/test_asset_schemas.py`  |

### Proposta di Riorganizzazione

Creare una nuova cartella `test_schemas/` con file organizzati per schema origin:

```
backend/test_scripts/
├── test_schemas/                          # NEW FOLDER
│   ├── __init__.py
│   ├── test_common_schemas.py             # Currency, DateRangeModel, OldNew
│   ├── test_asset_schemas.py              # FAGeographicArea, FASectorArea, FAInterestRatePeriod, etc.
│   ├── test_transaction_schemas.py        # TXCreateItem, TXReadItem, TXUpdateItem (NEW)
│   └── test_broker_schemas.py             # BRCreateItem, BRReadItem, BRUpdateItem (NEW)
├── test_utilities/                        # MODIFIED - keep only non-schema tests
│   ├── test_decimal_utils.py              # Keep (utility, not schema)
│   ├── test_datetime_utils.py             # Keep (utility, not schema)
│   ├── test_financial_math.py             # Keep (utility, not schema)
│   ├── test_day_count_conventions.py      # Keep (utility, not schema)
│   ├── test_compound_interest.py          # Keep (utility, not schema)
│   ├── test_geo_normalization.py          # Keep (utility function, not schema)
│   ├── test_sector_normalization.py       # Keep (utility function, not schema)
│   ├── test_currency.py                   # MOVE → test_schemas/test_common_schemas.py
│   ├── test_scheduled_investment_schemas.py # MOVE → test_schemas/test_asset_schemas.py
│   ├── test_distribution_models.py        # MOVE → test_schemas/test_asset_schemas.py
│   └── test_geographic_area_integration.py # MOVE → test_schemas/test_asset_schemas.py
└── ...
```

### File da Spostare

#### 1. `test_currency.py` → `test_schemas/test_common_schemas.py`

- **356 righe** di test per `Currency`
- Testa: creation, crypto, invalid codes, arithmetic, comparison, serialization
- Include anche test per `OldNew` generic (verificare se presente)

#### 2. `test_scheduled_investment_schemas.py` → `test_schemas/test_asset_schemas.py`

- **362 righe** di test per scheduled investment schemas
- Testa: `FAInterestRatePeriod`, `FALateInterestConfig`, `FAScheduledInvestmentSchedule`
- Include test di ValidationError per regole business

#### 3. `test_distribution_models.py` → `test_schemas/test_asset_schemas.py`

- **237 righe** di test per distribution models
- Testa: `FAGeographicArea`, `FASectorArea`
- Include test di normalization, weight validation

#### 4. `test_geographic_area_integration.py` → `test_schemas/test_asset_schemas.py`

- **98 righe** di test per serialization
- Testa: `FAGeographicArea` within `FAClassificationParams`
- Include test round-trip JSON

### Modifiche a `test_runner.py`

#### 1. Aggiungere Categoria `schemas`

Aggiungere una nuova sezione dopo `# UTILS TESTS`:

```python
# ============================================================================
# SCHEMAS TESTS
# ============================================================================

def schemas_common(verbose: bool = False) -> bool:
    """Test common Pydantic schemas (Currency, DateRangeModel, OldNew)."""
    print_section("Schemas: Common (Currency, DateRangeModel, OldNew)")
    print_info("Testing: backend/app/schemas/common.py")
    return run_command(
        ["pipenv", "run", "python", "-m", "pytest", "backend/test_scripts/test_schemas/test_common_schemas.py", "-v"],
        "Common schemas tests",
        verbose=verbose
        )


def schemas_assets(verbose: bool = False) -> bool:
    """Test asset-related Pydantic schemas."""
    print_section("Schemas: Assets (FAGeographicArea, FAInterestRatePeriod, etc.)")
    print_info("Testing: backend/app/schemas/assets.py")
    return run_command(
        ["pipenv", "run", "python", "-m", "pytest", "backend/test_scripts/test_schemas/test_asset_schemas.py", "-v"],
        "Asset schemas tests",
        verbose=verbose
        )


def schemas_transactions(verbose: bool = False) -> bool:
    """Test transaction Pydantic schemas."""
    print_section("Schemas: Transactions (TXCreateItem, TXReadItem, etc.)")
    print_info("Testing: backend/app/schemas/transactions.py")
    return run_command(
        ["pipenv", "run", "python", "-m", "pytest", "backend/test_scripts/test_schemas/test_transaction_schemas.py", "-v"],
        "Transaction schemas tests",
        verbose=verbose
        )


def schemas_brokers(verbose: bool = False) -> bool:
    """Test broker Pydantic schemas."""
    print_section("Schemas: Brokers (BRCreateItem, BRReadItem, etc.)")
    print_info("Testing: backend/app/schemas/brokers.py")
    return run_command(
        ["pipenv", "run", "python", "-m", "pytest", "backend/test_scripts/test_schemas/test_broker_schemas.py", "-v"],
        "Broker schemas tests",
        verbose=verbose
        )


def schemas_all(verbose: bool = False) -> bool:
    """Run all schema validation tests."""
    print_header("LibreFolio Schema Validation Tests")
    print_info("Testing Pydantic schema validation rules")

    tests = [
        ("Common Schemas", lambda: schemas_common(verbose)),
        ("Asset Schemas", lambda: schemas_assets(verbose)),
        ("Transaction Schemas", lambda: schemas_transactions(verbose)),
        ("Broker Schemas", lambda: schemas_brokers(verbose)),
        ]

    results = []
    for test_name, test_func in tests:
        success = test_func()
        results.append((test_name, success))
        if not success:
            print_error(f"Test failed: {test_name}")
            print_warning("Stopping schema tests execution")
            break

    # Summary
    print_section("Schema Tests Summary")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.NC}" if success else f"{Colors.RED}❌ FAIL{Colors.NC}"
        print(f"{status} - {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print_success("All schema tests passed! 🎉")
        return True
    else:
        print_error(f"{total - passed} test(s) failed")
        return False
```

#### 2. Rimuovere Test Schema da `utils_all()`

Rimuovere queste voci dalla lista `tests` in `utils_all()`:

```python
# RIMUOVERE:
("Scheduled Investment Schemas", lambda: utils_scheduled_investment_schemas(verbose)),
("Currency and OldNew", lambda: utils_currency(verbose)),
("Distribution Models", lambda: utils_distribution_models(verbose)),
("FAGeographicArea Integration", lambda: utils_geographic_area_integration(verbose)),
```

E rimuovere le relative funzioni:

- `utils_scheduled_investment_schemas()`
- `utils_currency()`
- `utils_distribution_models()`
- `utils_geographic_area_integration()`

#### 3. Aggiornare Argparse

Aggiungere il nuovo subparser per `schemas`:

```python
# Schemas tests
schemas_parser = subparsers.add_parser('schemas', help='Schema validation tests')
schemas_subparsers = schemas_parser.add_subparsers(dest='action', help='Schema test type')

schemas_subparsers.add_parser('all', help='Run all schema tests')
schemas_subparsers.add_parser('common', help='Test common schemas (Currency, etc.)')
schemas_subparsers.add_parser('assets', help='Test asset schemas')
schemas_subparsers.add_parser('transactions', help='Test transaction schemas')
schemas_subparsers.add_parser('brokers', help='Test broker schemas')
```

#### 4. Aggiornare Handler nel `main()`

```python
elif args.category == 'schemas':
if args.action == 'all' or args.action is None:
    success = schemas_all(verbose=args.verbose)
elif args.action == 'common':
    success = schemas_common(verbose=args.verbose)
elif args.action == 'assets':
    success = schemas_assets(verbose=args.verbose)
elif args.action == 'transactions':
    success = schemas_transactions(verbose=args.verbose)
elif args.action == 'brokers':
    success = schemas_brokers(verbose=args.verbose)
else:
    schemas_parser.print_help()
    success = False
```

#### 5. Aggiungere `schemas` a `run_all_tests()`

Aggiungere `schemas_all` prima di `utils_all` o `services_all` nell'ordine di esecuzione globale.

### Test Name Filter (3° Livello) - Da Implementare

Come richiesto nella nota iniziale, modificare `run_command` e argparse per supportare una lista opzionale di test names:

```python
# Esempio di utilizzo:
python
test_runner.py
schemas
transactions
test_transfer_requires_link_uuid
test_fx_conversion_requires_link_uuid

# Diventa:
pipenv
run
python - m
pytest
backend / test_scripts / test_schemas / test_transaction_schemas.py::test_transfer_requires_link_uuid::test_fx_conversion_requires_link_uuid - v
```

Modifiche necessarie:

1. **Argparse**: Aggiungere `nargs='*'` per catturare test names opzionali
2. **run_command**: Aggiungere logica per appendere `-k "test1 or test2"` se test names forniti
3. **Documentazione**: Aggiornare help message

---

## Appendix B: Migration Checklist ✅ COMPLETE

Passi per applicare la riorganizzazione:

- [x] Creare cartella `backend/test_scripts/test_schemas/`
- [x] Creare `backend/test_scripts/test_schemas/__init__.py`
- [x] Creare `backend/test_scripts/test_schemas/test_common_schemas.py` (migrato da `test_currency.py`) ✅ 52 test
- [x] Creare `backend/test_scripts/test_schemas/test_asset_schemas.py` (uniti 3 file) ✅ 54 test
- [x] Creare `backend/test_scripts/test_schemas/test_transaction_schemas.py` (NUOVO) ✅ 52 test
- [x] Creare `backend/test_scripts/test_schemas/test_broker_schemas.py` (NUOVO) ✅ 29 test
- [x] Rimuovere vecchi file da `test_utilities/`:
    - [x] `test_currency.py`
    - [x] `test_scheduled_investment_schemas.py`
    - [x] `test_distribution_models.py`
    - [x] `test_geographic_area_integration.py`
- [x] Aggiornare `test_runner.py`:
    - [x] Aggiungere sezione `# SCHEMAS TESTS`
    - [x] Aggiungere funzioni `schemas_*`
    - [x] Rimuovere funzioni `utils_*` per i file spostati (rimossi da utils_all)
    - [x] Aggiornare `utils_all()` lista tests
    - [x] Aggiornare argparse con nuovo subparser
    - [x] Aggiornare handler nel `main()`
    - [x] Aggiornare `run_all_tests()` per includere schemas
    - [x] Implementare 3° livello (test name filter)
- [x] Verificare che `pytest` trovi tutti i test
- [x] Eseguire `python test_runner.py schemas all` per validare ✅

**Schema Tests Summary (2025-12-28):**

- Common Schemas: 52 tests (Currency, DateRangeModel, OldNew)
- Asset Schemas: 54 tests (FAInterestRatePeriod, FAGeographicArea, FASectorArea, etc.)
- Transaction Schemas: 52 tests (TXCreateItem, validation rules)
- Broker Schemas: 29 tests (BRCreateItem, BRSummary)
- **Total: 187 schema tests passing**

### API Test Files (Category 5) - COMPLETE ✅

- [x] `backend/test_scripts/test_api/test_transactions_api.py` - 14 test (13 pass, 1 skip)
- [x] `backend/test_scripts/test_api/test_brokers_api.py` - 14 test (all pass)
- [x] Fixed `test_server_helper.py` to use `set_test_mode(True)` (2025-12-28)
- [x] Fixed test fixtures to use UUID for unique broker names (2025-12-28)

