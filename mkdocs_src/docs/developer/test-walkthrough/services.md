# ⚙️ Backend Services Tests (`services`)

These tests verify the business logic encapsulated in the service layer. They typically mock external dependencies (like the database or APIs) to test logic in isolation.

## 🎯 Purpose

To ensure that complex business rules (e.g., BRIM parsing logic, asset metadata merging, scheduled investment calculations) are implemented correctly.

## 🔑 Key Tests

- **BRIM Providers**: Tests parsing of sample CSV files for each supported broker.
- **Asset Metadata**: Tests the logic for merging and patching asset metadata.
- **Asset Source**: Provider registration, assignment validation, price fetching.
- **Asset Source Refresh**: Sync pipeline, event upsert with `provider_assignment_id` filtering, idempotency.
- **Asset Sync Counts**: Verify `points_added`, `points_changed`, `points_unchanged` counters after sync operations.
- **Synthetic Yield**: Scheduled Investment engine — simple/compound interest, `generate_interest` auto-events, `MATURITY_SETTLEMENT`, late interest with grace period.
- **Synthetic Yield Integration**: Full integration tests with multi-period schedules, maturation frequencies, coupon resets, late interest compounding.

## 🚀 Running

```bash
./dev.py test services
```
