[REVIEWED 2026-04-24]

# Sub-Plan: Phase 7 Part 3 Closure_2 — Blocco G test coverage

Parent: plan-phase07-transaction-Part3_1_Closure_2.prompt.md (Blocco G)
Data: 24 Aprile 2026 - Stato: IN CORSO
Effort riveduto: ~8h (dopo audit coverage reale 2026-04-24)

## Revisione scope (post-audit 2026-04-24)

Audit (`/tmp/libreFolio_coverage_audit.sh`): ~85% della coverage pianificata
per G.1/G.2 e gia presente in `test_transaction_service.py` (~50 test: Blocco
A atomic + H pairing/promote) e `test_transactions_api.py` (18 test Blocco
B). Anche E.8, I-bis #26/#R6-2, FAProviderKind sono gia coperti altrove.

Conseguenze:

- G.1/G.2 declassati da "scrittura da zero" a "audit + gap-fill".
- Scoperti 3 gap dimenticati nel plan originale -> aggiunti G.6c, G.12, G.13.
- Confermati 5 gap reali -> G.3, G.4, G.5, G.10, G.11 restano P1.

## Scope riveduto

| ID | File target | Area Part3 | Stato | Effort |
|----|-------------|------------|:-----:|:------:|
| G.6 | `test_ohlc_sentinel.py` (nuovo) | F.4 sentinel | DONE 7/7 (2026-04-24) | - |
| G.6b | `test_current_price_bootstrap.py` (services) | F.2/F.3 unit `_extend_ohlc_bounds` | DONE 8/8 (2026-04-24) | - |
| G.6c (NEW) | `test_current_price_persistence.py` (api) | F.2/F.3 side-effect /current | DONE 5/5 (2026-04-24) | - |
| G.11 | `test_asset_prices_export.py` (nuovo) | I.4 export + I-bis #5 round-trip | DONE 5/5 (2026-04-24) | - |
| G.5 | `test_prices_currency_coherence.py` (nuovo) | I.2 hard-reject mismatch | DONE 5/5 (2026-04-24) | - |
| G.10 | `test_asset_currency_change.py` (nuovo) | I.3 PATCH + I-bis #7 HTTP 409 | DONE 4/4 (2026-04-24) | - |
| G.12 (NEW) | `test_prices_sync_delta.py` (nuovo) | I-bis #24 changed_points + cap 500 | DONE 5/5 (2026-04-24) | - |
| G.3 | `test_transactions_validate.py` (nuovo) | Blocco C.1 dry-run | DONE 6/6 (2026-04-24) | - |
| G.4 | `test_events_suggest.py` (nuovo) | Blocco C.2 | DONE 7/7 (2026-04-24) | - |
| G.13 (NEW) | `test_scheduled_investment_param_change.py` (services) | #R6-4 event wipe + tx disconnect | DONE 3/3 (2026-04-24) | - |
| G.1 | `test_transaction_service.py` (audit) | Blocco A/H gap-fill | DONE audit — no gap (2026-04-24) | - |
| G.2 | `test_broker_multiuser_api.py` (+2 test) | Blocco B access matrix gap-fill | DONE 2/2 (2026-04-24) | - |
| G.7 | `scripts/test_runner.py` | tooling | DONE (2026-04-24) — 10/10 entries wired | - |
| G.8/G.9 | meta | coverage report + `./dev.py test all-backend` | DONE (2026-04-24) — 7/7 groups green, 76.05% cov | - |

Totale: ~8h.

## Ordine di esecuzione

| Batch | Contenuto | Effort | Razionale |
|-------|-----------|:------:|-----------|
| G-batch1 | G.6b + G.6c + G.11 | ~2h | F.2/F.3 + export/round-trip - bassa complessita, alto valore — **DONE 2026-04-24 (25/25 test PASS)** |
| G-batch2 | G.5 + G.10 + G.12 | ~2.5h | Currency coherence + change flow + I-bis #24 delta - P1 tutti — **DONE 2026-04-24 (14/14 test PASS)** |
| G-batch3 | G.3 + G.4 | ~1.75h | Blocco C endpoints dry-run + events/suggest — **DONE 2026-04-24 (13/13 test PASS)** |
| G-batch4 | G.13 + G.1/G.2 audit | ~1.5h | #R6-4 scheduled + gap-fill residuo — **DONE 2026-04-24 (5/5 new test PASS + G.1 no-gap)** |
| G-batch5 | G.7 + G.8 + G.9 | ~45min | Test-runner + validazione finale — **DONE 2026-04-24 (7/7 groups green, 32/32 api, 19/19 services, 76.05% backend cov)** |

## Commit strategy (1 per batch)

- `test(phase07-G1): OHLC sentinel + F.2/F.3 + prices export round-trip` (G.6 + G.6b + G.6c + G.11)
- `test(phase07-G2): currency coherence + asset currency change + sync delta` (G.5 + G.10 + G.12)
- `test(phase07-G3): transactions validate + events suggest` (G.3 + G.4)
- `test(phase07-G4): scheduled_investment param-change + existing-coverage gap-fill` (G.13 + G.1 + G.2)
- `test(phase07-G5): test runner groups + coverage validation` (G.7 + G.8 + G.9)

## Gap rilevati nell'audit (3 dimenticati)

1. **I-bis #24 FARefreshResult.changed_points**: nessun test esistente.
   Contratto: (a) campo popolato con delta real (new+changed, non fetched
   identici), (b) None quando oltre `CHANGED_POINTS_PAYLOAD_CAP=500`,
   (c) idempotent no-op sync -> `changed_points=[]`. -> G.12.

2. **F.2/F.3 side-effect persistente di /current**: documentato in
   `wiki/concepts/prices-current-side-effect.md` ma mai testato end-to-end.
   -> G.6c.

3. **#R6-4 scheduled_investment param-change**: retest manuale passato ma
   nessuna protezione di regressione. -> G.13.

## Copertura preesistente confermata (no-op)

- Blocco A atomic + Blocco H pairing/promote: ~50 test in `test_transaction_service.py`.
- Blocco B api: 18 test in `test_transactions_api.py`.
- E.8 target_currency: 7 test in `test_events_target_currency.py`.
- I-bis #26 + #R6-2: 15+ test in `test_synthetic_yield_integration.py`.
- FAProviderKind (Batch 2 part4b): 20 test in `test_provider_core_cache.py`.
- Blocco H api: `test_transfer_promotion.py` (3 test).

## Cross-link

- Parent: plan-phase07-transaction-Part3_1_Closure_2.prompt.md
- devWiki: `wiki/concepts/prices-current-side-effect.md`
- Audit log: `/tmp/libreFolio_coverage_audit.log`

---

## G-batch6 — Post-G coverage gap-fill (2026-04-25)

**Trigger**: full coverage run after G-batch5 closed showed:
- Backend: 85.34%, Combined (BE+FE): 85.97%, Frontend E2E → BE: 45.93%
- 8 production functions still at **0% coverage** despite contracts shipped
  in Part 3 phases.

### G-batch6 deliverables — DONE 2026-04-25 (17/17 test PASS + 1 prod bug fixed)

| ID | Target | New tests | Status |
|----|--------|-----------|:------:|
| G-batch6.1–5 | `backend/test_scripts/test_api/test_market_data_wipe.py` | 5 (summary empty/populated, wipe destructive+idempotent, 404, dry-run non-mutation) | ✅ |
| G-batch6.6–13 | `backend/test_scripts/test_api/test_backup_export_extras.py` | 8 (events CSV/JSON/404/empty, FX CSV/JSON inverted/400/empty) | ✅ |
| G-batch6.14–17 | `backend/test_scripts/test_services/test_brim_provider_base.py` | 4 (`docs_url`, `icon_url`, `plugin_version`, `to_plugin_info`) | ✅ |

**Coverage delta**:

| File / function | Before | After |
|-----------------|:------:|:-----:|
| `api/v1/assets.py::market_data_summary` | 0% | ~100% |
| `api/v1/assets.py::wipe_market_data` | 0% | ~100% |
| `services/asset_source.py::wipe_market_data_for_currency_change` | 0% | ~95% (cache-invalidation `except Exception` excluded) |
| `api/v1/backup.py::backup_asset_events` | 0% | ~100% |
| `api/v1/backup.py::backup_fx_rates` | 0% | ~95% (inverted+400+normalisation paths) |
| `services/brim_provider.py::BRIMProvider.docs_url` | 0% | 100% |

**Production bug discovered & fixed**:

- `backend/app/api/v1/assets.py` — handlers `market_data_summary` and
  `wipe_market_data` referenced `e.code` on `AssetSourceError`, but the
  exception class only exposes `error_code`. Result: `AssetSourceError`
  raised by the service was being re-raised by the bare `except Exception`
  branch as **HTTP 500** instead of the documented **404 ASSET_NOT_FOUND**.
  Fix: `e.code` → `e.error_code` (2 occurrences). Test
  `test_wipe_unknown_asset_returns_404` now passes 404 for both endpoints.

### Test runner registrations

Added in `scripts/test_runner.py`:

- `services brim-provider-base` → `services_brim_provider_base()`
- `api market-data-wipe` → `api_market_data_wipe()`
- `api backup-export-extras` → `api_backup_export_extras()`

### Commit suggestion

```
test(phase07-G6): cover 0%-functions market_data_wipe + backup events/fx + BRIM defaults

- New test_market_data_wipe.py (5 tests): GET /summary + POST /wipe
  exercise the Policy D wipe end-to-end.
- New test_backup_export_extras.py (8 tests): events CSV/JSON + FX rates
  CSV/JSON with inverted-pair handling.
- New test_brim_provider_base.py (4 tests): default docs_url/icon_url/
  plugin_version inherited by all BRIM provider subclasses.
- Fix: assets.py wipe handlers used e.code (non-existent attribute) on
  AssetSourceError, causing 500 instead of 404. Now correctly maps
  ASSET_NOT_FOUND to HTTP 404.
- test_runner.py: 3 new entries (services brim-provider-base,
  api market-data-wipe, api backup-export-extras).
```

---

## G-batch7 — Audit coverage parziale (2026-04-25)

**Goal**: classify the partially-covered functions reported by the user as
either (A) needing more tests, (B) defensive-only branches not worth
testing, or (C) mixed (needs *some* targeted additions).

Methodology: read each function's source, identify the structural shape
of the missing branches, and judge them against the contract surface.

### Verdict table

Legend: 🟢 = needs new tests (worthwhile);
🟡 = mixed — small targeted additions only;
🔴 = mostly defensive / external-dependent — not worth chasing.

| Function | Loc / Miss | Verdict | Rationale |
|----------|:---------:|:------:|-----------|
| `services/fx.py::sync_pairs_bulk._process_route` | 104 / 54 (48%) | 🟡 | Missing branches are: (a) **multi-step CHAIN** path (lines 1033–1130) — currently no test feeds a 2-leg chain mockprov scenario; (b) **timeout** branch (`asyncio.wait_for` line 955); (c) **leg failure** propagation (line 962). Worth adding *one* multi-step CHAIN test (mockprov A→B→C) — covers ~25 of the 54 missing lines. Timeout/leg-failure are pure error guards, leave at 🔴. |
| `api/v1/uploads.py::serve_file` | 60 / 52 (13%) | 🟢 | This is **business logic**, not error handling. Missing: text preview window, image preview/resize (Pillow path), download-with-original-filename, MIME detection branches. The 13% coverage means only the "404 not found" guard is tested. Worth a dedicated suite (`test_uploads_serve_file.py`) with ~6 tests: text preview, image preview, download flag, 400 wrong-MIME, attachment header, plain serve. |
| `services/asset_source.py::wipe_market_data_for_currency_change` | 43 / 43 (0%) | ✅ DONE in G-batch6 | Now covered. |
| `services/asset_source_providers/justetf.py::fetch_asset_metadata` | 72 / 42 (41%) | 🔴 | Missing branches are almost all guarded by `try/except Exception` for `get_etf_overview` failures, plus the rich-metadata path (countries→geographic_area, sectors→sector_area normalization). The latter requires a fixture with realistic JustETF response which is **external-dependent**. The unit-testable parts (renormalization math, `_country_name_to_iso3`) are tiny. Recommendation: leave to external provider tests (which run live + are slow). |
| `services/transaction_service.py::validate_batch` | 111 / 37 (66%) | 🟡 | Already 67% covered by `test_transactions_validate.py` (G.3). Missing branches: (a) update path with `tx.asset_id is None` raising ValueError on `asset_event_id`; (b) bare-except wrappers around per-item delete/update (lines 614, 649). Add 2 targeted tests in `test_transactions_validate.py`: "update sets asset_event_id without asset_id → issue logged not raised" and "delete with cascade-fail → issue logged". |
| `services/asset_source.py::get_prices_bulk` | 108 / 29 (73%) | 🔴 | 73% coverage; missing 29 lines are scattered defensive branches: provider exceptions, identifier-type fallbacks, FX-conversion fallback when `target_currency` rate is missing. These are exercised in production by happy paths and would require fragile mocks of provider failures. Diminishing returns — leave at current level. |
| `utils/currency_utils.py::normalize_currency` | 34 / 27 (20%) | 🟢 | 20% is **dramatic underexposure** for a deterministic utility. Missing: symbol match (`SYMBOL_TO_ISO`), name-search loop (lines 224–248), multi-match return shape, error-message branches. Pure unit tests, fast (<1s) — worth a dedicated `test_currency_utils_normalize.py` with ~8 cases (ISO direct, symbol unique `€`, symbol ambiguous `$`, name `Dollar`, multi-match `Pound`, empty input, unknown garbage, locale switch IT/FR). |
| `services/fx_providers/snb.py::_parse_json` | 38 / 26 (31%) | 🔴 | The 26 uncovered lines are SNB-specific JSON-shape edge cases (D1 ID extraction fallback to header, malformed dates, zero-rate skip, multi-unit divisor). All exercised by the live SNB provider test in `test_fx_providers.py`. Synthetic JSON fixtures would be brittle. Leave to external suite. |
| `services/asset_source.py::bulk_refresh_prices._persist_single` | 88 / 24 (73%) | 🔴 | Missing 24 lines are: (a) MANUAL provider skip; (b) deprecated provider skip; (c) per-asset failure → continue. All defensive guards exercised by the orchestration test. Adding mocks for each error path would be high-effort low-value. |
| `api/v1/fx.py::delete_rates_endpoint` | 51 / 23 (54%) | 🟡 | Already 46% covered. The missing 23 lines split between (a) `errors[]` collection in mixed-validity batch (worth 1 test), and (b) the `Exception` outer handler (defensive). Add 1 test: "DELETE /fx/rates with mixed valid+invalid pairs returns 200 with per-item errors". |
| `main.py::ensure_database_exists` | 40 / 22 (45%) | 🔴 | Startup-only function exercised by the `db create` test. Missing lines: (a) empty-file branch (manual creation rare); (b) `sqlite3` connect exception (file corruption); (c) non-SQLite URL fallback (Postgres future-proofing). All operational concerns — leave defensive. |
| `services/asset_source_providers/yahoo_finance.py::get_history_value` | 68 / 22 (67%) | 🔴 | yfinance-specific failure paths (rate-limit, ticker-not-found, empty DataFrame). Already 67% — additions would need yfinance mocks which are notoriously brittle (yfinance changes its internal DataFrame shape). Leave to external suite. |
| `services/transaction_service.py::delete_bulk` | 63 / 22 (65%) | 🟡 | Already exercises happy path + linked-pair pre-check. Missing: (a) BalanceValidationError post-flush (line 525-528) — actually triggerable by deleting a deposit that turns the balance negative; (b) bare-except on session.delete (line 512) — defensive. Add 1 test in `test_transaction_service.py`: "delete deposit → broker balance goes negative → rollback". |
| `services/brim_providers/broker_freetrade.py::parse` | 74 / 20 (72%) | 🔴 | Each BRIM parse() is at 70-78% with 16-20 missing lines. The missing lines are *broker-format edge cases* (corrupt rows, unknown transaction types, missing columns). Each broker has 1-2 official sample files in `samples/` covering the happy path. Synthetic edge-case fixtures would be high-effort and would not detect real-world format drifts (which the live sample updates catch). Leave at current level for **all** BRIM brokers (freetrade, trading212, ibkr, coinbase, directa, degiro). |
| `services/fx.py::ensure_rates_multi_source` | 102 / 20 (80%) | 🔴 | 80% covered. Missing 20 lines are: provider fallback failure cascade, MANUAL sentinel return, all-providers-failed terminal branch. Defensive priority cascade — leave. |

### Summary recommendations

**Worth implementing in G-batch7** (estimated ~3.5h, high value/cost ratio):

1. `test_currency_utils_normalize.py` — pure unit, ~8 tests, ~30 min. **🟢**
2. `test_uploads_serve_file.py` — API suite, ~6 tests (text preview / image preview / download), ~1.5h. **🟢**
3. Extend `test_fx_sync.py` (or new `test_fx_sync_chain.py`) with a 2-leg CHAIN sync test using mockprov, ~45 min. **🟡**
4. Append 2 tests to `test_transactions_validate.py` (asset_event_id without asset_id; delete with cascade error), ~30 min. **🟡**
5. Append 1 test to `test_fx_api.py` for mixed-validity DELETE, ~20 min. **🟡**
6. Append 1 test to `test_transaction_service.py` for `delete_bulk` balance violation, ~30 min. **🟡**

**Not worth chasing** (defensive / external-dependent — accept current %):

- All BRIM `parse()` methods (freetrade/trading212/ibkr/coinbase/directa/degiro)
- `justetf.fetch_asset_metadata` (external)
- `yahoo_finance.get_history_value` (external + yfinance internals)
- `snb._parse_json` (external + JSON shape edge cases)
- `asset_source.bulk_refresh_prices._persist_single` (defensive)
- `asset_source.get_prices_bulk` (defensive cascade)
- `main.ensure_database_exists` (startup operational guards)
- `fx.ensure_rates_multi_source` (provider fallback cascade)

Total *expected* backend coverage gain if **G-batch7 worthwhile items**
are implemented: ~+1.5–2 percentage points (from 85.34% to ~87%).


