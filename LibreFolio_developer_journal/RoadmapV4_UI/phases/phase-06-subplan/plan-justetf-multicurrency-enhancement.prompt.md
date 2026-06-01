# Plan: JustETF Multi-Currency Enhancement

## Problem

JustETF provider currently hardcodes EUR for all operations. The user wants:
1. Provider to support currency selection (EUR/USD/CHF/GBP) via `params_schema`
2. Search results show all 4 currency variants per ETF, with flag emoji + 👑 for fund currency
3. `get_current_value()` only available for EUR (gettex limitation) — graceful degradation for other currencies
4. Document the currency limitation in user docs (EN only)

## Approach

Use `params_schema` to add a `currency` select field. When currency ≠ EUR, `get_current_value()` raises a clear error (system handles gracefully → "current value unavailable", history still works). Search emits 4 results per match with flag + 👑 annotation.

## Todos

### 1. `justetf-currency-param` — Add currency `params_schema` to JustETF provider
- Add `params_schema` property returning a `currency` select field (EUR/USD/CHF/GBP, default EUR)
- Update `validate_params()` to accept and validate the currency field

### 2. `justetf-history-currency` — Use `provider_params["currency"]` in `get_history_value()`
- Read currency from `provider_params` (fallback EUR)
- Pass to `load_chart(isin, currency, add_current)` — but `add_current` must be False when currency ≠ EUR (gettex only gives EUR quotes)
- Update cache key to include currency

### 3. `justetf-current-eur-only` — Limit `get_current_value()` to EUR
- If `provider_params["currency"]` ≠ EUR → raise `AssetSourceError("NOT_SUPPORTED", "Current value only available in EUR...")`
- Gettex WebSocket only provides EUR quotes, this is a hard limitation

### 4. `justetf-search-multicurrency` — Emit multi-currency search results
- For each ETF match, emit 4 results (one per supported currency)
- `display_name` format: `"🇪🇺 ETF Name"` / `"🇺🇸 ETF Name"` / `"🇨🇭 ETF Name"` / `"🇬🇧 ETF Name"`
- Fund currency result gets additional 👑: `"🇺🇸👑 ETF Name"` (if fund currency matches one of the 4)
- `currency` field = the selected currency variant
- Need `provider_params` in the search result — check if schema supports it or if currency in display_name is enough

### 5. `justetf-metadata-currency` — Update `fetch_asset_metadata()` to return correct currency
- Return the currency from `provider_params` instead of hardcoded EUR
- Fund's native `fundCurrency` from overview is used as a display hint, not as the stored currency

### 6. `justetf-docs-limitation` — Document currency limitation in mkdocs (EN)
- Update `mkdocs_src/docs/user/assets/providers/justetf.en.md` with:
  - Currency selection feature explanation
  - Limitation: current price only available in EUR (gettex)
  - For non-EUR currencies: only historical data available (JustETF converts at their rates)
  - Flag emoji legend (🇪🇺/🇺🇸/🇨🇭/🇬🇧 + 👑 = fund native currency)
- Update `mkdocs_src/docs/developer/backend/assets/provider_justetf.md` with technical details
- Update provider comparison table in `index.en.md` (search: ✅ not ❌, add currency note)

### 7. `justetf-tests` — Update/verify provider tests
- Run existing `test_asset_providers.py` against JustETF → verify backward compat (currency=EUR default)
- Add JustETF-specific test cases in `test_cases` property for ALL 4 currencies:
  - EUR: current ✅ + history ✅ (existing behavior)
  - USD: current → NOT_SUPPORTED ✅ + history ✅ (converted by JustETF)
  - CHF: current → NOT_SUPPORTED ✅ + history ✅
  - GBP: current → NOT_SUPPORTED ✅ + history ✅
- Verify search returns 4× results per ETF match
- Run full provider test suite: `./dev.py test external --providers justetf`
- Run all provider tests to check no regressions: `./dev.py test external`

## Execution Tracking

### Progress
- ✅ `justetf-currency-param` — params_schema + validate_params + _get_currency helper
- ✅ `justetf-history-currency` — load_chart uses provider_params currency, add_current=False for non-EUR, cache key updated
- ✅ `justetf-current-eur-only` — raises NOT_SUPPORTED with clear message for non-EUR
- ✅ `justetf-search-multicurrency` — 4 results per match with flag emojis + 👑 for fundCurrency
- ✅ `justetf-metadata-currency` — returns currency from provider_params
- ✅ `justetf-docs-limitation` — user docs (justetf.en.md), developer docs (provider_justetf.md), index table
- ✅ `justetf-tests` — 11/11 multi-currency tests pass, 27/27 generic provider tests pass (0 regressions)
- ✅ Frontend: AssetModal auto-fills providerParams.currency from search result
- ✅ Frontend: DateRangePicker badge highlighting via effectivePreset (auto-detect matching preset from dates)
- ✅ Frontend: goBack fixed — list pages use goto(replaceState) instead of native history.replaceState
- ✅ Frontend: ProviderAssignmentSection currency dropdown shows flag + symbol
- ✅ Frontend: Test tooltips format currency with flag + symbol
- ✅ Frontend: Test inline summary shows formatted currency (flag + code + symbol) for both current price and history
- ✅ Frontend: Global dateRangeStore — date range persists across pages (goBack shows latest range, not stale URL)
- ✅ Frontend: URL paste/bookmark priority — `resolveInitialRange()` reads `window.location.search` at module-load time (before page mount)
- ✅ Mock data: added USD JustETF asset (`IE00B4L5Y983`) in `populate_mock_data.py` with `provider_params: {"currency": "USD"}` — exercises non-default currency flow

### Deviations Log
- **test_cases limitation**: Generic test framework iterates ALL test_cases for get_current_value. Non-EUR cases would fail (NOT_SUPPORTED). Solution: kept only EUR in test_cases, created dedicated `test_justetf_multicurrency.py` for full 4-currency validation.
- **Reactivity bug**: `getCurrencyInfo()` in ProviderAssignmentSection was called without reactive dependency on `currencyStoreVersion`. At first render, currency store not yet loaded → fallback values (raw code). Fix: converted to `$derived.by` with `void $currencyStoreVersion`, added `ensureCurrenciesLoaded` on mount.
- **Date range goBack**: Original fix used `goto(replaceState)` to update navigationStore. This kept the stale URL in the stack. Evolved to a global store (`dateRangeStore.svelte.ts`) as single source of truth. Pages read from store on mount, ignoring URL params from nav stack. URL params only win on full page load (module init reads `window.location.search` before any component mounts).

## Notes

- `Currency = Literal["EUR", "USD", "CHF", "GBP"]` — only these 4 are supported by JustETF chart API
- `add_current` in `load_chart` appends today's gettex quote → only valid for EUR
- The search result schema `FAProviderSearchResultItem` has no `provider_params` field — currency choice is communicated via the `currency` field in the result, and the user selects which variant to add
- For currencies not in the 4 supported (JPY, SEK, etc.) — user relies on LibreFolio's own FX conversion from the 4 base currencies
- The index.en.md says search is ❌ — this is outdated, search works. Fix this too.

## Dependencies

- `justetf-history-currency` depends on `justetf-currency-param`
- `justetf-current-eur-only` depends on `justetf-currency-param`
- `justetf-metadata-currency` depends on `justetf-currency-param`
- `justetf-search-multicurrency` depends on `justetf-currency-param`
- `justetf-tests` depends on all others
- `justetf-docs-limitation` is independent

