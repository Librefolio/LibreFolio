# 💱 FX Architecture

The Foreign Exchange (FX) system is responsible for fetching, storing, and providing exchange rates for currency conversion.

## 🔌 Multi-Provider Support

LibreFolio supports multiple FX rate providers (e.g., ECB, FED). This ensures redundancy and allows users to choose the source that best fits their needs (e.g., a US user might
prefer FED rates, while a European user prefers ECB).

### 📋 The `FXRateProvider` Interface

All providers must implement the `FXRateProvider` abstract base class:

```python
class FXRateProvider(ABC):
    @property
    def base_currency(self) -> str:
        """The provider's base currency (e.g., 'EUR' for ECB)."""
        pass

    async def fetch_rates(self, date_range, currencies) -> dict:
        """Fetch rates from the external API."""
        pass
```

## 📐 Normalization and Storage

Providers typically return rates relative to a specific base currency (e.g., ECB returns `1 EUR = X USD`).

To simplify storage and querying, LibreFolio normalizes all rates before saving them to the database. The rule is: **Base currency is always alphabetically smaller than Quote
currency.**

- **Input**: `EUR/USD` (EUR < USD) -> Stored as `base='EUR', quote='USD', rate=1.08`
- **Input**: `USD/GBP` (USD > GBP) -> Stored as `base='GBP', quote='USD', rate=1/0.78`

This ensures that we only need to store one rate per pair, and we can easily calculate the inverse if needed.

## 🔢 Priority System

When converting currency, the system needs to decide which rate to use if multiple providers have data for the same pair and date.

`fx_rates` holds **one rate per pair and date**, so the decision is taken when the rate is fetched, not
when it is read. Each pair has one or more **routes** in `fx_conversion_routes`, ranked by `priority`
(1 = primary). `sync_pairs_bulk()` — the live sync path, called by `POST /api/v1/fx/currencies/sync`
and by the scheduler's history-sync job — walks a pair's routes in priority order and falls back to the
next one when a route fails. See [FX Configuration & Routing](configuration.md) for routes, chains and
the `MANUAL` sentinel.

`ensure_rates_multi_source()` is an older single-provider orchestrator with no production caller: it is
kept, unwired, as the extension point for future multi-base providers.

### 🆕 A new pair syncs its full history

Saving a new pair does not sync it on the server: the frontend does it right after the save.
`finishFxPairCreation()` (`frontend/src/lib/services/fxCreationSync.ts`) calls
`POST /api/v1/fx/currencies/sync` with `start: "min"` and `end` = today when the new pair has a
non-`MANUAL` provider. `"min"` is the backend's sentinel for "everything the provider publishes": the
request's `start` is a `SyncStartDate` (`date | Literal["min"]`, `backend/app/schemas/refresh.py`), and
the sync passes it to the providers as an `FXProviderStartDate` (`backend/app/services/fx.py`). Asking
for the whole history, rather than the period of the page that opened the dialog, gives older
transactions a rate too. A full history can outlast the client's default timeout, so this request waits
up to 120 s (`FX_SYNC_TIMEOUT_MS`) — the same fixed limit `FxSyncModal` and `PageSyncModal` send.
Their **Timeout** field (`SyncModalBase`, default `max(20, item count)` s) drives only the countdown
and the timeout message, not the request.

The request carries the new pair and the intermediate pairs saved with
**Also create intermediate pairs**. A pair saved with no route (the `MANUAL` sentinel only) starts
no sync and gets a `Created` success toast instead; saving the routes of an existing pair (edit
mode) starts none either. After the sync, `classifyFxSyncOutcome()` grades the response:

| Outcome | When | Toast |
|:--------|:-----|:------|
| `failed` / `transport-error` | The request failed, a requested pair is missing from the response, the response has operation errors, or any pair is `failed` | error |
| `skipped` | Every pair is `skipped` | info |
| `partial` | Any pair is not `ok` | warning |
| `ok` | Every pair is `ok` | success |

A refresh callback that fails turns a success or info toast into a warning. Both toasts link the
pair name to its detail page (`fxPairHtml(…, {linkToDetail: true})`).

## 🔄 Conversion Logic

`convert_bulk()` (`backend/app/services/fx.py`) is the shared conversion function:
`POST /api/v1/fx/currencies/convert`, the portfolio engine and service, lots analysis, Yield on Cost,
asset price queries, risk eligibility and AI Export components call it with a list of
`(Currency, to_currency, date)` items. For each item:

1. **Identity**: same currency in and out — the amount is returned as is, with no lookup.
2. **Stored pair**: the pair is normalized alphabetically, the way rates are stored. The amount is
   multiplied by the rate when converting from the stored base, divided by it otherwise.
3. **Backward fill**: the rate is the latest one on or before the requested date, with no time limit.
   The result carries the rate's date and whether backward fill applied; the convert endpoint turns them
   into `backward_fill_info` (`actual_rate_date`, `days_back`).
4. **No rate**: when the pair has no rate on or before the date, the item fails —
   `RateNotFoundError` with `raise_on_error=True`, or a `None` result plus an error message otherwise.

There is no triangulation at conversion time. A pair that no provider quotes directly gets its rates at
sync time from a multi-step chain route, which stores the composite rate under the pair itself
(`source = "CHAIN:…"`) — see [Direct vs. Chain Routes](configuration.md#direct-vs-chain-routes).

### 🪟 Loading only the usable rate window {: #convert-bulk-window }

Portfolio reports call `convert_bulk()` with thousands of items: the engine preloads a rate for every
non-reporting currency and every day of the range. So the function reads only the rows the batch can
use, in one query for all pairs:

- for each pair it tracks the earliest (`min_date`) and latest (`max_date`) requested dates;
- it loads the rows from the **backward-fill anchor** — the last rate on or before `min_date`, a
  `MAX(date)` scalar subquery — up to `max_date`. The anchor keeps the unlimited backward fill exact:
  the earliest item still finds its rate, however old;
- it selects plain columns (`base`, `quote`, `date`, `rate`), not ORM objects;
- each item finds its rate with `bisect_right` over the pair's ascending dates.

Return values and errors are those of the full-history version this replaced, which loaded every pair's
whole history up to the latest requested date and scanned it linearly for each item (PR #30 by Martin
Sova, commit `5aa267f11`).

## 🧹 Rate writes clear the portfolio caches {: #portfolio-cache-invalidation }

Every write that changes stored rates drops the two portfolio cache layers, `portfolio_layer2` and
`portfolio_blob`, through `clear_cache()`, so the next report recomputes with the new rates:

| Write | Function | Clears when |
|-------|----------|-------------|
| Provider sync (`POST /api/v1/fx/currencies/sync`, scheduler) | `sync_pairs_bulk()` | At least one rate point changed |
| Manual rates (`POST /api/v1/fx/currencies/rate`) | `upsert_rates_bulk()` | After the commit (any non-empty batch) |
| Rate deletion (`DELETE /api/v1/fx/currencies/rate`) | `delete_rates_bulk()` | At least one row was deleted |

Both layers also key their entries on an FX fingerprint of the scope
(`compute_portfolio_fx_cache_identity()` in `portfolio_engine.py`); the explicit clear drops entries
right away instead of leaving them to their TTL. See [Cache Registry & Admin Endpoints](../../architecture/settings_cache.md)
for the caches themselves.
