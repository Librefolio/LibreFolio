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
the sync passes it to the providers as an `FXProviderStartDate` (`backend/app/services/fx/base.py`). Asking
for the whole history, rather than the period of the page that opened the dialog, gives older
transactions a rate too. A full history can outlast the client's default timeout, so this request waits
up to 120 s (`FX_SYNC_TIMEOUT_MS`), like the Dashboard's rate sync. The sync windows (`FxSyncModal`,
`AssetSyncModal`, `PageSyncModal`) instead give each request the limit of their **Timeout** field
(`SyncModalBase`, default `max(20, item count)` s): `syncRequestTimeoutMs()`
(`frontend/src/lib/utils/sync/syncHelpers.ts`) returns `max(120 s, field + 5 s)`, so a larger field
lengthens the request and a smaller one keeps the 120 s floor.

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

`convert_bulk()` (`backend/app/services/fx/conversion.py`) is the shared conversion function:
`POST /api/v1/fx/currencies/convert`, the portfolio engine and service, lots analysis, Yield on Cost,
asset price queries, the [fixed-period changes](#fixed-period-changes) of the Assets and FX tables, risk eligibility
and AI Export components call it with a list of `(Currency, to_currency, date)` items. For each item:

1. **Identity**: same currency in and out — the amount is returned as is, with no lookup.
2. **Stored pair**: the pair is normalized alphabetically, the way rates are stored. The amount is
   multiplied by the rate when converting from the stored base, divided by it otherwise.
3. **Backward fill**: the rate is the latest usable one on or before the requested date, with no time
   limit. The result carries the rate's date and whether backward fill applied; the convert endpoint
   turns them into `backward_fill_info` (`actual_rate_date`, `days_back`).
4. **No rate**: when the pair has no usable rate on or before the date, the item fails —
   `RateNotFoundError` with `raise_on_error=True`, or a `None` result plus an error message otherwise
   (*No FX rate found for B/Q on or before D*).

A usable rate is one `fx_rates.rate` can keep (X-R38, see
[Chain Dates, Writes and Counters](configuration.md#chain-dates-writes-and-counters)). A row the
column cannot keep, written by an older release (an infinite rate, 0, 20 digits before the decimal
point), is a missing rate for its date: backward-filled from the latest usable rate before it, as a
date without a row would be, or the missing-rate error. A conversion never divides by zero nor
returns an infinite amount. Read through the model, such a row still gives `Decimal('Infinity')` for
a stored inf (see [Decimal Columns](../../architecture/database/index.md#decimal-columns)); the FX
writers no longer send one.

There is no triangulation at conversion time. A pair that no provider quotes directly gets its rates at
sync time from a multi-step chain route, which stores the composite rate under the pair itself
(`source = "CHAIN:…"`) — see [Direct vs. Chain Routes](configuration.md#direct-vs-chain-routes).

`POST /api/v1/fx/currencies/convert` expands each conversion's `date_range` into one `convert_bulk()`
item per day, both ends included; with signals, a second series of one-unit items runs from the start
of their warm-up to the same end. Both ends have a limit (X-R55, `backend/app/utils/date_range_limits.py`):
the end is cut at `latest_range_end()`, tomorrow in UTC (a day of margin for a user whose calendar is
ahead of UTC), and the start, the warm-up included, goes back at most `RANGE_SPAN_LIMIT_DAYS`
(36,525 days, 100 years) before that end (`range_span_floor()`, never before `date.min`). A conversion
that starts after the cut asks for nothing: no result, no error, and its signals run on an empty
series; the other conversions are unaffected. Before, nothing bounded the expansion: from 0001-01-01 to
9999-12-31 it built about 3.65 million items, then failed with a 500 (`OverflowError`). The ceiling is
the endpoint's: `convert_bulk()` itself, which the other callers use directly, has none.
{: #convert-range-ceiling }

### 🪟 Loading only the usable rate window {: #convert-bulk-window }

Portfolio reports call `convert_bulk()` with thousands of items: the engine preloads a rate for every
non-reporting currency and every day of the range. So the function reads only the rows the batch can
use, in one query for all pairs:

- for each pair it tracks the earliest (`min_date`) and latest (`max_date`) requested dates;
- it loads the rows from the **backward-fill anchor** — the last rate on or before `min_date`, a
  `MAX(date)` scalar subquery — up to `max_date`. The anchor keeps the unlimited backward fill exact:
  the earliest item still finds its rate, however old;
- it reads only the usable rates (X-R38): `rate >= 1E-10 AND rate < 1E+14`, the bounds of
  `usable_fx_rate_bounds()` (`backend/app/db/precision.py`), in the anchor subquery as in the window,
  so a legacy unusable row neither anchors the window nor is loaded. There is no per-row check in
  Python: any double within those bounds reads back as a rate `storable_fx_rate()` keeps, and this
  path is hot;
- it selects plain columns (`base`, `quote`, `date`, `rate`), not ORM objects;
- each item finds its rate with `bisect_right` over the pair's ascending dates.

The writers keep to the same upper bound (X-R50). SQLite keeps the rate as a double, so a rate within
about 0.008 of `1E+14` with more digits than a double holds (`99999999999999.995`) has 14 digits
before the point but would be stored as `1E+14`: `storable_fx_rate()` refuses it too, so a manual one
is refused and a provider's skipped, as for any rate the column cannot keep (`99999999999999.99`
stays the double `99999999999999.98` and is kept). Before, the limit was on the digits alone, as for
W-B58: the writers accepted `99999999999999.999`, stored it as `1E+14`, and these bounds then
skipped it as unusable.

Apart from the unusable rates left out, return values and errors are those of the full-history version
this replaced, which loaded every pair's whole history up to the latest requested date and scanned it
linearly for each item (PR #30 by Martin Sova, commit `5aa267f11`).

### 📅 Fixed-Period Changes {: #fixed-period-changes }

`POST /api/v1/fx/currencies/period-changes` returns the fixed-period changes of the FX table: 1D, 1W, 1M, 3M, 6M,
1Y, 2Y, 3Y and 5Y (developer decision D-MF6 b). `get_fx_period_changes_bulk()` in
`backend/app/services/fx/period_changes.py` values the days. The change itself is the house's
`fixed_period_changes()` ([Financial Math Layer](../financial_math.md#fixed-period-changes)).

- **Request**: a list of `{base, quote, as_of}`. `base` and `quote` must differ, or the request is refused (422).
- **Rate on a day**: the conversion of 1 `base` into `quote` on that day by `convert_bulk()`, with its unlimited
  backward fill. It is the rate `POST /api/v1/fx/currencies/convert` returns for that day, up to that endpoint's
  [ceiling](#convert-range-ceiling): `as_of` has none. One `convert_bulk()` batch serves every pair and day of the
  request.
- **Response**: `items[]`, in request order, of `{base, quote, as_of, periods[], errors[]}`. Each period is
  `{key, days, change_ratio, inverse_change_ratio}`.
- **`change_ratio`**: `rate(as_of) / rate(as_of − days) − 1`, the pair as asked (quote per base).
- **`inverse_change_ratio`**: `rate(as_of − days) / rate(as_of) − 1`, the change of the inverted pair (base per
  quote).

Both are fractions, null when either rate is missing. A day without a rate adds *No B/Q rate on or before D* to
`errors`.

## 🧹 Rate writes clear the portfolio caches {: #portfolio-cache-invalidation }

Every write that changes stored rates drops the two portfolio cache layers, `portfolio_layer2` and
`portfolio_blob`, through `clear_cache()`, so the next report recomputes with the new rates:

| Write | Function | Clears when |
|-------|----------|-------------|
| Provider sync (`POST /api/v1/fx/currencies/sync`, scheduler) | `sync_pairs_bulk()` | At least one rate point changed |
| Manual rates (`POST /api/v1/fx/currencies/rate`) | `upsert_rates_bulk()` | After the commit (any non-empty batch) |
| Rate deletion (`DELETE /api/v1/fx/currencies/rate`) | `delete_rates_bulk()` | At least one row was deleted |

Both layers also key their entries on an FX fingerprint of the scope
(`compute_portfolio_fx_cache_identity()` in `financial_math/portfolio/engine.py`); the explicit clear drops entries
right away instead of leaving them to their TTL. See [Cache Registry & Admin Endpoints](../../architecture/settings_cache.md)
for the caches themselves.
