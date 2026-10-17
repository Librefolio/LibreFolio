# 🔀 FX Configuration & Routing

LibreFolio supports a sophisticated multi-provider routing system for Foreign Exchange (FX) rates. This allows administrators to define exactly which provider should be used for each currency pair, with automatic fallback capabilities and **multi-step conversion chains**.

## 🛤️ The Routing Logic

When the system needs to fetch FX rates (e.g., via the `/api/v1/fx/currencies/sync` endpoint), it consults the `fx_conversion_routes` table.

### 🔢 Priority System

Each currency pair can have multiple **routes** assigned, ranked by **priority** (1 = highest/primary).

1. **Primary Route**: The system first attempts to use the route with `priority=1`.
2. **Fallback**: If the primary route fails (API error, timeout, provider down, provider [paused](#paused-providers) after «too many requests»), the system automatically tries the route with `priority=2`, and so on.
3. **Failure**: If all configured routes fail, the sync operation reports an error for that specific pair.

### 🔗 Direct vs. Chain Routes

Each route is defined as a **chain of steps** (`chain_steps` JSON array):

- **Direct (1-step)**: A single provider converts the pair directly.
  Example: `EUR → USD` via ECB → `[{"from": "EUR", "to": "USD", "provider": "ECB"}]`

- **Multi-step (chain)**: Multiple steps are chained to compute a derived rate.
  Example: `RON → USD` via ECB+ECB → `[{"from": "RON", "to": "EUR", "provider": "ECB"}, {"from": "EUR", "to": "USD", "provider": "ECB"}]`

A chain's steps do not need to use *distinct* providers: `RON → USD` above uses `ECB` twice, once per leg, and that is a valid 2-step chain — "multi-step" only means "more than one step", not "more than one provider".

The system multiplies the intermediate rates to compute the final derived rate, which is stored in `fx_rates` with `source = "CHAIN:ECB+ECB"`.

### 📋 Example Configuration

| Base    | Quote   | Priority | Chain Steps                               | Description                  |
|:--------|:--------|:---------|:------------------------------------------|:-----------------------------|
| **EUR** | **USD** | 1        | `EUR →[ECB]→ USD`                         | Direct via ECB (primary)     |
| **EUR** | **USD** | 2        | `EUR →[FED]→ USD`                         | Direct via FED (fallback)    |
| **RON** | **USD** | 1        | `RON →[ECB]→ EUR →[ECB]→ USD`            | 2-step chain via ECB         |
| **GBP** | **USD** | 1        | `GBP →[BOE]→ USD`                         | Direct via BOE               |

In this example:

- For **EUR/USD**, the system prefers ECB. If ECB is down, it falls back to FED.
- For **RON/USD**, no provider offers this pair directly, so it uses a 2-step chain through EUR.
- For **GBP/USD**, it uses BOE directly.

## 🗃️ Database Schema

The configuration is stored in the `FxConversionRoute` model:

```python
class FxConversionRoute(SQLModel, table=True):
    __tablename__ = "fx_conversion_routes"

    id: int                     # Primary key
    base: str                   # e.g., "EUR" (alphabetically first: base < quote)
    quote: str                  # e.g., "USD"
    priority: int               # 1 = primary, 2+ = fallback
    chain_steps: str            # JSON array of conversion steps
    fetch_interval: int | None  # Optional refresh frequency (minutes), default 1440
    created_at: datetime
    updated_at: datetime
```

**`chain_steps` JSON format:**

```json
// Direct (1-step):
[{"from": "EUR", "to": "USD", "provider": "ECB"}]

// Multi-step chain (2-step):
[
  {"from": "RON", "to": "EUR", "provider": "ECB"},
  {"from": "EUR", "to": "USD", "provider": "ECB"}
]

// Manual-only pair:
[{"from": "NOK", "to": "SEK", "provider": "MANUAL"}]
```

**Validation rules:**

- **Continuity**: `step[i].to == step[i+1].from` for consecutive steps
- **No repeated edges**: The same currency pair cannot appear twice in a chain (any direction)
- **Alphabetical ordering**: `base < quote` constraint

## 🌐 API Endpoints

Configuration is managed via the `/api/v1/fx/providers/routes` endpoints.

### 📋 List Routes

`GET /api/v1/fx/providers/routes`

Returns all configured routes ordered by base, quote, and priority. Each route includes the full `chain_steps` array plus two response-only fields, derived from the stored steps and not stored themselves:

| Field           | Type         | Meaning                                                                                     |
|:----------------|:-------------|:----------------------------------------------------------------------------------------------|
| `is_chain`      | `bool`       | `true` if the route has more than one step (`len(chain_steps) > 1`)                          |
| `providers_used`| `list[str]`  | Sorted unique list of provider codes appearing in `chain_steps` (including `MANUAL`)          |

`providers_used` is a **sorted unique list representing membership**, not an ordered traversal and not proof that a fetch succeeded: it lists which provider codes are *configured* on the route, so a route with two `ECB` steps still reports `["ECB"]`, and a MANUAL-only route reports `["MANUAL"]` with `is_chain: false`.

**Example** — for the `EUR/USD` primary route and the `RON/USD` chain route from the table above:

```json
{
  "items": [
    {
      "base": "EUR",
      "quote": "USD",
      "priority": 1,
      "chain_steps": [
        {"from": "EUR", "to": "USD", "provider": "ECB"}
      ],
      "is_chain": false,
      "providers_used": ["ECB"]
    },
    {
      "base": "RON",
      "quote": "USD",
      "priority": 1,
      "chain_steps": [
        {"from": "RON", "to": "EUR", "provider": "ECB"},
        {"from": "EUR", "to": "USD", "provider": "ECB"}
      ],
      "is_chain": true,
      "providers_used": ["ECB"]
    }
  ]
}
```

Note that `RON/USD` is `is_chain: true` (2 steps) with a single-member `providers_used` — the flag and the set answer different questions: "how many steps" versus "which providers are configured".

### ➕ Create/Update Routes (Bulk)

`POST /api/v1/fx/providers/routes`

Creates or updates multiple conversion routes atomically.

**Request:**

```json
[
  {
    "base": "EUR",
    "quote": "USD",
    "priority": 1,
    "chain_steps": [
      {"from": "EUR", "to": "USD", "provider": "ECB"}
    ]
  },
  {
    "base": "EUR",
    "quote": "USD",
    "priority": 2,
    "chain_steps": [
      {"from": "EUR", "to": "USD", "provider": "FED"}
    ]
  },
  {
    "base": "RON",
    "quote": "USD",
    "priority": 1,
    "chain_steps": [
      {"from": "RON", "to": "EUR", "provider": "ECB"},
      {"from": "EUR", "to": "USD", "provider": "ECB"}
    ]
  }
]
```

The request body's inputs remain `base`, `quote`, `priority`, and `chain_steps` — clients simply omit the derived `is_chain`/`providers_used` metadata. If a client supplies them anyway, the values are ignored: they are never writable or authoritative, and are recomputed server-side from `chain_steps` for the response.

**Result:**

Each submitted item gets one result carrying the same `is_chain`/`providers_used` pair described for `GET`, computed from that item's own `chain_steps`, plus `success`, `action` (`"created"` or `"updated"`), and an optional `message`.

!!! note "Validation failures and the transaction"

    If any submitted route references a provider code not registered in the provider registry, that item's result reports `success: false`, `action: "error"`, and a `message` naming the unknown code(s) — with `providers_used` still derived from the *submitted* `chain_steps`, so an unknown code appears in `providers_used` too (it is membership of what was posted, not a check that the code is valid). When at least one item fails validation, the whole batch is rolled back and the endpoint responds `400` with the per-item results (including the successful ones, none of which were actually persisted) in the error detail body.

!!! note "Replacing a pair's routes: `?replace=true`"

    By default the endpoint only creates or updates the priorities it is given: a route at another priority stays. With
    `POST /api/v1/fx/providers/routes?replace=true`, each pair the request names keeps exactly the routes posted for it,
    and its other priorities are deleted in the same transaction, after the validation (X-R75). An edit is then one
    request: a refusal (`400`, `409`, `500`) or a request that never arrives leaves the pair as it was. The MANUAL rules
    are the same: a real provider posted removes the MANUAL route, and the MANUAL item alone
    (`{"from": base, "to": quote, "provider": "MANUAL"}`, priority `999`) leaves the pair manual. A pair not configured
    yet is created; one another request configured in the meantime keeps only what this one posts for it.

    The web app's provider editor (`FxPairAddModal`, the pair's detail page) saves this way. Before X-R75 it deleted the
    whole pair first and then posted the new routes, so a failed post left the pair with no route at all, and removing
    every route deleted the pair instead of leaving it manual.

### 🗑️ Delete Routes

`DELETE /api/v1/fx/providers/routes`

Removes routing rules. Can delete a specific priority or all rules for a pair.

**Request:**

```json
[
  {
    "base": "EUR",
    "quote": "USD",
    "priority": 2
  }
]
```

If `priority` is omitted, all routes for the pair are deleted, MANUAL included: the pair is removed, and no MANUAL
route is reinstated. When a delete that names a priority leaves the pair without a real provider, a MANUAL sentinel route
is reinstated to keep the pair in the system.

## 🔄 Auto-Sync Behavior

When calling `POST /api/v1/fx/currencies/sync`:

1. The system queries `fx_conversion_routes` to find all configured pairs and their routes.
2. For **1-step routes**, it groups target currencies by provider and fetches in batch.
3. For **multi-step (chain) routes**, it fetches each leg's rates from the respective providers, then computes the derived rate by multiplying the intermediate rates.
4. If a route fails, the system tries the next priority route for that pair.
5. Results are saved to the `fx_rates` table. Chain-derived rates are stored with `source = "CHAIN:provider1+provider2"`.

This ensures resilience to individual provider outages and supports currency pairs that no single provider covers directly.

### 📅 Chain Dates, Writes and Counters {: #chain-dates-writes-and-counters }

- **Strict date matching.** `compute_chain_rate()` (`backend/app/services/fx/conversion.py`) produces a chain
  rate for a date only when every leg has a rate on that exact date; a missing leg skips the date.
  A chain through a sparse series therefore has rates only on the dates that series publishes. A leg
  that is present but unusable (one `storable_fx_rate()` refuses, or at most 0) counts as missing
  (X-R38): a chain never divides by zero, nor yields an infinite or absurd rate.
- **Upsert, the provider wins.** Rates are written with
  `INSERT … ON CONFLICT (date, base, quote) DO UPDATE`, which replaces `rate`, `source` and
  `fetched_at`. A synced date overwrites whatever was stored, including a rate entered by hand
  through `POST /api/v1/fx/currencies/rate` (`upsert_rates_bulk()`, the same upsert). Dates outside
  the requested range are not written, nor is a date before 1900-01-01, whatever the start, `"min"`
  included (`_is_date_within_sync_range()`, X-R65; see
  [Normalization and Storage](architecture.md#stored-rate-dates)).
- **What the column keeps.** `fx_rates.rate` is `Numeric(24, 10)`: 10 decimal places and 14 digits
  before the decimal point (`max_integer_digits()`, precision − scale). `storable_fx_rate()`
  (`backend/app/db/precision.py`; X-R38, the FX side of W-B58) answers the rate as the column keeps
  it (`truncate_fx_rate()`: 10 decimal places, rounded down), or `None` when it is not finite, has
  more than 14 digits before the point, or is 0 once truncated (below `1E-10`): a rate is never 0,
  since its inverse and the conversions divide by it. It also answers `None` when the truncated
  rate's double reaches `1E+14` (`float(stored) >= 1E+14`; X-R50): SQLite keeps the rate as a
  double, and a rate within about 0.008 of `1E+14` with more digits than a double holds, such as
  `99999999999999.995`, has 14 digits before the point but would be stored as `1E+14`, which the
  conversions skip as unusable ([Loading only the usable rate window](architecture.md#convert-bulk-window));
  `99999999999999.99` stays the double `99999999999999.98` and is kept. Like W-B58's helpers (see
  [Decimal Columns](../../architecture/database/index.md#decimal-columns)), it counts the digits
  without a decimal context and never raises: `1E+1000000` and `1E-2000000` are refused, never an
  overflow or a zero. A negative rate is its callers' to refuse.
- **A provider's rate the column cannot keep is skipped.** While a provider's answer is read
  (`_collect_leg_rates()`), an observation that is not a finite rate above 0, or whose inverse
  overflows or underflows to 0, is set aside (`normalize_storable_rate()`) instead of making every
  leg of that provider fail. A rate `storable_fx_rate()` refuses once normalized is skipped when
  stored; before, from
  `1E+50` up the route failed with none of the pair's dates stored, and a failing primary route
  switched the pair to its fallback route. For a chain (`_storable_chain_rates()`), a date whose leg
  is present but unusable, or whose chain rate the column cannot keep (`1E+20`, or 0 once
  truncated), is skipped. A skipped rate is never stored and never fails the pair: its other dates
  are stored. One warning per pair and per sync (`_warn_unusable_rates()`), *FX rates skipped: the
  column cannot keep them*, covers its skipped rates, the observations of its legs set aside
  included, with `pair`, `provider` (the `CHAIN:…` source for a chain), `skipped` (the count),
  `dates` (the earliest ten, ISO) and `limits` (`fx_rate_limits_text()`). The unwired
  `ensure_rates_multi_source()` follows the same rules: one normalization pass, the rate skipped,
  one warning per pair.
- **A manual rate the column cannot keep is refused.** `upsert_rates_bulk()`
  (`backend/app/services/fx/storage.py`) refuses a base equal to its quote and a finite rate ≤ 0
  (*Rate must be positive*), then puts the pair in alphabetical order, inverting the rate when the
  base comes after the quote, and checks the limits on the rate as stored, never on the rate typed:
  MMK → KHR `1E-13` is stored as KHR/MMK `1E+13`, accepted. A rate that is not finite, whose inverse
  overflows (`1 / 1E-1000000`) or underflows to 0 (`1 / 1E+1000027`), or that `storable_fx_rate()`
  refuses is an `FXRateNotStorableError`, a `ValueError` (X-R46), naming the pair in stored order,
  the date and the limits
  (`fx_rate_refusal()`): *The rate of KHR/MMK on 2024-01-02 cannot be stored: an exchange rate
  keeps at most 14 digits before the decimal point and 10 decimal places, stays below
  100000000000000 (as the database stores it), and must stay above 0 once cut to them* (the
  bound below `1E+14` since X-R51, so that a rate of 14 digits the double rule refuses is told
  why). Nothing of the call is written; before, `1E+400` was stored as a REAL inf, and its
  inverse and `1E-11` as values that read back 0. A valid rate is still written as normalized,
  not truncated.
- **The manual-rate endpoint.** `POST /api/v1/fx/currencies/rate` (`upsert_rates_endpoint()`,
  `backend/app/api/v1/fx/currencies.py`) handles its items one by one: a refused item is left out
  while the others are stored (200), and the answer names it (next bullet). Before
  handling any of them, it checks every `date`: one outside `stored_date_bounds()` (1900-01-01 to
  tomorrow) refuses the whole request with a 422 `date_out_of_range`, nothing written, not even
  the valid items (X-R65, [Normalization and Storage](architecture.md#stored-rate-dates)). Its own
  inversion runs inside the item's `try` (`normalize_storable_rate()`), so an inverse that
  overflows is that item's error, never a 500, and one that underflows to 0 is refused naming the
  limits, like any rate the column cannot keep (X-R50; before, the item's error was *Rate must be
  positive (got 0E-1000026)*). The schema answers 422 to a rate that is not a
  number (`"abc"`, `true`, `"0x10"`), not finite (the JSON number `1E+400`, which JSON parsing
  turns into `inf`; `NaN`; `"Infinity"`) or ≤ 0 (`gt=0`): `FXUpsertItem.coerce_rate()` reads a
  finite float through its shortest decimal text (`0.1` → `Decimal("0.1")`) and hands anything
  else to Pydantic as it came, a non-finite float as its text (`"inf"`), which the 422 can echo.
  Before, `"abc"` made the validator raise `InvalidOperation` past Pydantic, and a non-finite rate
  was echoed as `Decimal('Infinity')`, which the JSON renderer cannot write: both were a 500.
- **A refused item is named twice.** Since X-R46, the 200 keeps its sentence in `errors`, unchanged
  (*Rate N: …*, N the item's 0-based index), and adds an entry to `rejected`,
  `{"index", "date", "reason"}` (`FXRateRejection` in `backend/app/schemas/fx.py`), in request
  order; `rejected` is empty when every item is stored. When every item is refused, the answer is
  400 and its `detail` is an object instead of a string:
  `{"code": "fx_rates_refused", "message", "rejected"}`, where `message` is the former string,
  *All rates failed:* followed by the `errors` joined with `"; "`, and `rejected` lists every item, as
  the 200 would. The web app's FX data editor counts only the `results` as saved and names the
  refused dates (up to five, then a count) with their reasons: in a warning after a 200, in its
  error banner and toast after the 400 (`frontend/src/lib/api/writeRefusal.ts`). The `reason` is
  one of:
    - `same_currency`: the base is the quote; `errors` says *Rate N: Base and quote must be
      different (got EUR)*;
    - `rate_not_storable`: a rate `fx_rates.rate` cannot keep once normalized (the limits above,
      X-R38), raised as `FXRateNotStorableError` by the endpoint or by `upsert_rates_bulk()`;
      `errors` says *Rate N: Validation error:* followed by `fx_rate_refusal()`'s text;
    - `invalid_rate`: any other `ValueError` of the item (*Rate N: Validation error: …*);
    - `internal_error`: an unexpected error, logged (*FX rate upsert failed*) and never echoed;
      `errors` says *Rate N: Failed: internal error*.
- **Counters.** `points_fetched` counts the rates computed for the pair in the range, the skipped
  ones left out; `points_changed` counts the new dates plus the dates whose value changed, compared
  at storage precision (`_count_actual_changes()`, which reads the stored rate through
  `storable_fx_rate()`). A legacy stored rate the column cannot keep (an infinite one, `1e60`, 0)
  compares as a change, and the upsert overwrites it; before, a stored inf or `1e60` made the
  comparison raise and the pair's sync fail. `ensure_rates_multi_source()` compares the same way.
- **Empty is not a failure.** The next route is tried only when a leg of the current one fails,
  its wait for the legs times out (120 s) or its computation raises; a rate the column cannot keep
  does none of these. A route that answers with no rate in the range ends the pair as `partial`:
  the next route is not tried. A single-step route whose every rate in the range was skipped says
  so in its `message`, *Provider P returned no rate the database can keep for B/Q in start–end:*
  followed by the limits; a chain keeps its *Chain … produced no complete rates* message, and the
  warning names the dates.

| Status | When |
|:-------|:-----|
| `ok` | The route produced at least one rate in the range |
| `partial` | The route answered but produced no rate in the range, or none the column can keep; `message` and `detail` (per leg: `dates_available`, `error`) say why |
| `skipped` | Every route of the pair is `MANUAL` |
| `failed` | The pair has no route, or every route failed; `errors` lists the failure of each route |

The scheduler's history-sync job (`run_history_sync()`, `backend/app/services/platform/scheduler/jobs.py`)
calls the same function once for every pair with a route that has no `MANUAL` step, up to today, from
today minus `scheduler_history_sync_horizon_days` (default 14), or earlier when a pair's last saved rate
is older: the day after the oldest of them, at most a year back (see
[History Sync](../scheduler.md#history-sync)).

### ⏸️ Paused Providers {: #paused-providers }

Every call to an FX provider goes through `call_fx_provider()` (`backend/app/services/fx/runtime.py`):
the fetches of `sync_pairs_bulk()`, those of the older `ensure_rates_multi_source()`, and the
supported-currency catalogue. A provider that refused for too many requests is paused, as the asset
providers are ([Provider Pauses](../assets/architecture.md#provider-pauses)): until the pause ends,
the boundary raises `FXRateLimitedError` (`error_code = "RATE_LIMITED"`, `retry_after` = the seconds
left) without calling it. A refusal met during a fetch pauses the provider the same way, and the
error carries the pause decided.

- **A paused provider is a failed leg.** `_fetch_provider()` records the refusal and fails every leg
  of that provider with its message, logged at INFO with no traceback. The pair goes on to its next
  route, as after any failed leg; the legs of every route were fetched in the same pass, so the next
  route is not delayed.
- **The cache comes first.** A fetch found in the 5-minute cache of the sync (`_fx_fetch_cache`) is
  used even while its provider is paused.
- **The pair result.** A pair that ended `failed` or `partial` while one of its routes uses a
  provider that refused or was paused carries `error_code: "RATE_LIMITED"` and `retry_after`: the
  shortest wait among those providers, the first moment one of its routes may work again. A pair
  that another route served (`ok`), and a `skipped` pair, carry neither.
- **The catalogue** (`GET /fx/providers`) answers with the provider's last known list, as after any
  failure, and asks again 5 minutes later.
