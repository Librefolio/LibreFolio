# 📅 Scheduled Investment Provider (`scheduled_investment`)

A synthetic, deterministic provider that calculates the value of an asset based on a predefined interest schedule. It makes **no external calls** and requires **no DB access** for calculation. It is one of the [Asset Providers](system_providers.md).

📖 **User Guide**: [Scheduled Investment — User Manual](../../../user/assets/providers/scheduled-investment.md)

---

## ⚙️ Configuration Schema

The asset's value is determined entirely by `provider_params`, which follow the `FAScheduledInvestmentSchedule` schema:

| Field | Type | Required | Description |
|---|---|---|---|
| `initial_value` | `Currency` | ✅ | Principal / face value (e.g., `{"code": "EUR", "amount": 10000}`) |
| `interest_type` | `SIMPLE \| COMPOUND` | — | Global interest method (default: `SIMPLE`) |
| `day_count` | `ACT/365 \| ACT/360 \| ACT/ACT \| 30/360` | — | Day count convention (default: `ACT/365`) |
| `schedule` | `FAInterestRatePeriod[]` | ✅ | List of interest rate periods (non-overlapping, contiguous) |
| `late_interest` | `FALateInterestConfig` | — | Optional penalty rate after maturity |
| `asset_events` | `FAAssetEventPoint[]` | — | Manually defined asset events |

The `ScheduledInvestmentEditor` shows these as **Initial Value** / **Currency**, **Interest Type** and **Day Count**; each period row as **Period**, **Rate %** (= `annual_rate` × 100), **Frequency** (`maturation_frequency`) and **Generate Coupon** (`generate_interest`). The **⚡ Late Interest** switch adds the late row — grace days are set from its Period cell — with a Simple/Compound select next to the switch. Asset events are added with **Add Event** (types **Interest**, **Price Adjustment**).

---

## 📊 Interest Rate Period (`FAInterestRatePeriod`)

| Field | Type | Default | Description |
|---|---|---|---|
| `start_date` | `date` | — | Period start (inclusive) |
| `end_date` | `date` | — | Period end (inclusive) |
| `annual_rate` | `Decimal` | — | Annual rate as decimal (e.g., `0.05` for 5%) |
| `maturation_frequency` | `MaturationFrequency` | `DAILY` | Emission granularity: DAILY, WEEKLY, MONTHLY, QUARTERLY, SEMIANNUAL, ANNUAL |
| `generate_interest` | `bool` | `false` | Auto-generate INTEREST events at each maturation date |

### 🚧 Bounds {: #bounds }

The schedule is walked day by day (see [the accrual walk](#accrual-walk)), so its span is the work and the memory of a computation. The schema (`backend/app/schemas/assets/scheduled_investment.py`) refuses a schedule outside these limits (night decision N73):

| Limit | Value | Checked in |
|---|---|---|
| Every period's `start_date` and `end_date` | 1900-01-01 … 2200-12-31 (`SCHEDULE_MIN_DATE`, `SCHEDULE_MAX_DATE`) | `FAInterestRatePeriod.validate_date_bounds` |
| Span, from the first period's start to the last period's end | at most 36 525 days, 100 years (`SCHEDULE_MAX_SPAN_DAYS`) | `FAScheduledInvestmentSchedule.validate_schedule_continuity` |
| Number of periods | at most 1 200 (`SCHEDULE_MAX_PERIODS`) | `FAScheduledInvestmentSchedule.validate_schedule_continuity` |
| Late interest `grace_period_days` | 0 … 36 525 (`LATE_INTEREST_MAX_GRACE_DAYS`) | `FALateInterestConfig.validate_grace_period` |

The `ValueError` reaches `validate_params()`, which raises `AssetSourceError` with `error_code="INVALID_PARAMS"`. The provider probe (**Test Configuration**, a dry run) reports it on its current-price and history operations; a sync fails the asset before any computation (`refresh.py` validates the parameters first) with *Invalid provider params*. The plugin adds two limits of its own: late interest is valued up to `SCHEDULE_MAX_DATE` at most (see [Late Interest](#late-interest)), and a large result is never cached (see [Caching & Invalidation](#caching)).

100 years cover any dated security and the model of a perpetual; dates outside 1900–2200 are not a live security's.

Tests: `./dev.py test schemas scheduled-investment-bounds` (each limit and its boundary value, `validate_params()` → `INVALID_PARAMS`) and `./dev.py test services scheduled-investment-cost-bounds` (the COMPOUND late closed form against the former day-by-day walk, each late history point equal to the value on its date and independent of the read window, a late-history cost linear in its days, the cache cap, the late horizon, the late settlement).

!!! info "Why: R13-SEC7-2"

    Before the bounds, the period dates were only checked for order and contiguity. A dry-run probe of a DAILY schedule from year 1 to year 9999 walked millions of days, in provider threads that the probe's 15 s timeout stops waiting for but does not stop, and cached about 0.7 GB for that one schedule. Any signed-in user can run a probe, and the same schedule saved on a shared asset blocked its sync too.

---

## 📐 Calculation Engine

**Price formula**:

```
price(d) = initial_value + accrued_interest - Σ(INTEREST events) + Σ(PRICE_ADJUSTMENT events)
```

The three terms run from the first period's start, or from the last auto-coupon, which resets them; the events in the formula are the manual ones.

- **SIMPLE**: `I = P₀ × r × Δt` — interest always on initial principal
- **COMPOUND**: `I_day = (P₀ + accrued_interest) × r × Δt` — interest on the principal plus the interest accrued so far; the manual events do not enter the base

**Emission**: Price points are emitted only at maturation dates (not every day), matching the `maturation_frequency`. Start and end dates of each period always produce a point regardless. A maturation date's point is the day's value before its coupon.

**History range**: `get_history_value(start_date, end_date)` returns the points and events dated in the range; a start before the schedule's first value adds an `initial_value` anchor point on that start. `start_date="min"` (`AssetHistoryStartDate`, «from the earliest available point») is the earliest of the schedule's first value date and its first manual event's date, or `end_date` with neither. The history is then the one an explicit start on that date returns: a manual event before the schedule's start brings the anchor on its date. The refresh asks for `"min"` when it resumes an asset with no stored price yet, that is on its first sync. Before lot MF-SI1, `"min"` raised `CALCULATION_ERROR` (the literal was still compared with dates), so the first sync of every new Scheduled Investment asset failed. Test: `./dev.py test services scheduled-investment-min-start`.

### 👣 The Accrual Walk {: #accrual-walk }

One generator, `_accrual_days(schedule, until)`, walks the schedule day by day from the first period's start to `until`; every value of the scheduled range comes from it. Each day, in this order:

1. **Interest**: the day's interest at the rate of the period that covers the day, on the base of the interest type above — `calculate_simple_interest(base, annual_rate, Δt)` with `Δt = calculate_day_count_fraction(day − 1, day, day_count)`, both from `financial_math/interest.py`. None on the first day, nor on a day no period covers.
2. **Manual events** of the day: an INTEREST lowers the value, a PRICE_ADJUSTMENT moves it by its signed amount.
3. **Value**: `initial_value + accrued interest + manual adjustments`, yielded as an `_AccrualDay` with the day's coupon, if any.
4. **Auto-coupon**: on a maturation date of a `generate_interest` period, when the value is above `initial_value`, the coupon pays everything above it, and the accrual restarts from `initial_value` the next day.

The value of a maturation date is therefore the one before its coupon: the peak the chart shows on the day the coupon is paid. Emitted after the reset instead, a `generate_interest` + DAILY schedule would draw a flat `initial_value` line.

Two readers share the walk, so they cannot disagree:

- `_generate_schedule_values()` walks to the last period's end, keeps the value of every maturation date and turns each coupon into an INTEREST event; its result is cached (see Caching & Invalidation below).
- `_compute_value_at(schedule, target_date)` walks to `target_date` and returns that day's value — on a maturation date, the same pre-coupon value. `get_current_value()` calls it for a day between two maturation dates, where the last cached point would miss the days since, and after a coupon would be the pre-coupon peak.

A golden test pins, digit for digit, what `_generate_schedule_values()`, `_compute_value_at()` and `_compute_late_interest_value()` return on 33 schedules — four shapes under the four day counts and both interest types, plus the empty schedule: `backend/test_scripts/test_services/test_synthetic_yield.py` against `backend/test_scripts/fixtures/scheduled_investment/accrual_golden.json`, run with `./dev.py test services synthetic-yield accrual_golden`. Regenerate the file only for a reviewed, intended change of these numbers, with `LIBREFOLIO_TEST_REGEN_SI_ACCRUAL_GOLDEN=1` in front of the same command.

---

## 🔄 Auto-Generated Events (`generate_interest`)

When `generate_interest = True` on a period (step 4 of [the accrual walk](#accrual-walk)):

1. At each **maturation date**, after the day's interest and manual events, the engine checks whether the value is above `initial_value`
2. If it is, it generates an **💵 INTEREST event** dated that day: `value = current_value - initial_value`, the accrued interest plus the manual adjustments since the last coupon. If it is not, no coupon is paid and nothing resets
3. After the event: `total_interest = 0`, `event_adjustment = 0` → value resets to `initial_value`; the maturation date's own price point keeps the value before the coupon
4. Interest accrual restarts from zero on the next day

!!! info "Coupon Reset Behavior"

    The INTEREST event represents a "coupon payout" — the accumulated interest is crystallized and paid out, resetting the running value back to the original principal.

### 🏁 `MATURITY_SETTLEMENT` Event

Auto-generated when:

- The last schedule period has `generate_interest = True` **and** no `late_interest` is configured
- **Or** `late_interest` has `generate_interest = True` (settlement at the last late maturation date)

Without late interest, the settlement is worth what the last day leaves after its coupon: the principal when the final coupon is paid that day, as the INTEREST event of the same date, or the day's value when no coupon is paid (no gain above the principal). `values[last_end]`, the chart's last point, stays the pre-coupon peak. Before CP-14b (J-39) the settlement read that peak, so the final coupon was counted twice.

After settlement, the engine is "off" — `get_current_value()` returns the settlement value for all future dates.

See [Asset Events](events.md) for the full event type reference.

---

## ⏰ Late Interest (`FALateInterestConfig`) {: #late-interest }

Applied after the asset's maturity date (last period `end_date`):

| Field | Type | Default | Description |
|---|---|---|---|
| `annual_rate` | `Decimal` | — | Annual late interest rate |
| `grace_period_days` | `int` | `0` | Days after maturity before late interest starts |
| `interest_type` | `SIMPLE \| COMPOUND` | `COMPOUND` | Late interest compounds by default (penalties grow) |
| `maturation_frequency` | `MaturationFrequency` | `DAILY` | Emission frequency for late period |
| `generate_interest` | `bool` | `false` | Auto-generate INTEREST + MATURITY_SETTLEMENT events |

During the grace period (from the day after maturity through `maturity + grace_period_days`) interest keeps accruing at the **last schedule period's** `annual_rate`; after it, the late `annual_rate` applies. Both segments start from the value at maturity and use the late `interest_type` and the global `day_count` (`_compute_late_interest_value`).

Both interest types are closed-form, one segment per rate. With `m` the maturity date, `V_m` the value on it, `g = m + grace_period_days` and `Δt` from `calculate_day_count_fraction()`:

- **SIMPLE**: `V(t) = V_m + P₀ × r_last × Δt(m, min(t, g)) + P₀ × r_late × Δt(g, t)`, the last term only once `t > g`.
- **COMPOUND**: `V(t) = V_m × compound_growth(m, min(t, g), r_last) × compound_growth(g, t, r_late)` (`_late_compound_growth`). `compound_growth(a, b, r)` from `financial_math/interest.py` is `Π (1 + r × Δt(d − 1, d))` over the days `d` in `(a, b]`, 1 for an empty or reversed span: the daily step `V += V × r × Δt` in closed form, at a cost that does not grow with the span (see Technical Notes below). The grace-period factor is the same for every date after the grace period, and the memo of `compound_growth` computes it once.

Every reader values a late date the same way, with `_compute_late_interest_value()`:

- `get_history_value()` builds the late maturation grid, from the day after maturity to the end of the late range (below), and values only the dates of the requested range plus the last date of the grid (`_late_interest_values`), SIMPLE and COMPOUND alike;
- `get_current_value()` values today's date;
- with `generate_interest`, the late MATURITY_SETTLEMENT is dated on the last date of the grid and carries that date's late price, the value the chart draws on it.

A day therefore has the same digits in the history, in the current value and in the settlement, and a date's value never depends on the window it is read in.

Late interest is valued up to `SCHEDULE_MAX_DATE` (2200-12-31) at most: `get_history_value()` ends the late range, and its grid, at `min(end_date, SCHEDULE_MAX_DATE)` and emits no point after it; a schedule with late interest that matures on that very day emits nothing after maturity (the flat line drawn after the maturity of a schedule without late interest does not apply).

!!! info "Closed form per date (R13-SEC7-2, MF-SI1)"

    Before R13-SEC7-2, COMPOUND late interest walked day by day from maturity for every date it was asked on, so a long DAILY late history cost a number of steps quadratic in its days. Now a date costs the same however far it is from maturity, so a history costs in proportion to the dates it values, and the horizon caps how many there can be. Under ACT/ACT, SIMPLE late interest reads the memoized year prefix of the day count (see Technical Notes below). The closed form is also more exact than rounding at every step: the COMPOUND late values differ from the former day-by-day walk only in the last digits of the 28-digit `Decimal`, far below the 12 decimals a stored price keeps.

---

## ⚡ Caching & Invalidation {: #caching }

The engine caches the full schedule computation as a `tuple[dict, list[FAAssetEventPoint]]`:

- **Key**: MD5 of the canonical JSON of the validated schedule (`_cache_key`).
- **Invalidation**: Cache is invalidated when `provider_params` changes (i.e., the user reconfigures the schedule via the frontend `ScheduledInvestmentEditor`).
- **Hit behavior**: On cache hit, `get_history_value()` slices the pre-computed dict to the requested date range — O(1) per point.
- **Miss behavior**: Full schedule recomputation from `initial_value` through all periods. This is deterministic (no I/O); see the measured times below.
- **Size cap**: a result with more than 3 660 points (`_CACHE_MAX_POINTS`, ten years of DAILY points, about 1 MB) is never stored: it is computed again on every call. The 256 entries stay bounded by about 256 MB (R13-SEC7-2; see [Bounds](#bounds)).

The cache is a module-level TTL cache (`get_ttl_cache("scheduled_investment")`, 256 entries, 48 h TTL), in memory and per process. It survives across multiple sync calls but is cleared on server restart.

Measured times, rounded (one process at nice 10; indicative, not a benchmark). The first, second and last rows were measured at a machine load around 35, the late-interest rows (after MF-SI1) around 25:

| Schedule | Time |
|---|---|
| Typical: 5 years, MONTHLY | ~13 ms the first time, then ~0 ms from the cache |
| The bounds' worst case: 100 years, DAILY, SIMPLE or COMPOUND (over the cap, never cached) | ~130 ms for the current value, ~250 ms for the full history |
| Matured in 1900, DAILY COMPOUND late interest: a 7-day history | ~40–130 ms (120–270 ms before MF-SI1) |
| The same, full history to 2200-12-31 (≈ 110 000 points) | ~1.9 s under ACT/365, ~2.9 s under ACT/ACT, ~3.9 s under 30/360, within the 55 s timeout of the sync's history call |
| The same, current value | ~1–2 ms |
| The report's DAILY schedule from year 1 to year 9999 | refused in < 1 ms (`INVALID_PARAMS`) |

---

## 🔧 Internal State Variables

During computation, the walk (`_accrual_days`) tracks these internal variables per day:

| Variable | Description | Reset behavior |
|---|---|---|
| `total_interest` | Cumulative accrued interest since last coupon/start | Reset to 0 after an auto-coupon |
| `event_adjustment` | Net sum of the manual events since last coupon/start: − INTEREST, + PRICE_ADJUSTMENT | Reset to 0 after an auto-coupon |
| `value` | `initial_value + total_interest + event_adjustment` | Computed per day; yielded in an `_AccrualDay` (`day`, `value`, `is_maturation`, `coupon`) |

These variables are NOT persisted — they exist only during computation.

---

## 📋 Use Cases

- **P2P/Crowdfunding Loans**: Model a loan with fixed interest rate and periodic coupon payouts.
- **Fixed-Rate Bonds**: Calculate bond value including accrued interest and coupon payments.
- **Any asset with predictable, deterministic cash flows**.

---

## 📐 Example

A P2P loan of €10,000 with 5% simple annual interest (ACT/365), one period from 1 January, monthly coupons (`generate_interest: true`). Maturation dates fall on the start date and then every month after it:

- **1 January → 1 February**: value grows from €10,000 to ≈ €10,042.47 (31 days × 10,000 × 5% / 365)
- **1 February** (first coupon): the day's price point is ≈ €10,042.47, and a 💵 INTEREST event of ≈ €42.47 pays out everything above the principal → the value restarts from €10,000 on 2 February
- **February**: value grows again from €10,000
- **Maturity**: 🏁 MATURITY_SETTLEMENT event → engine stops

---

## 🔧 Technical Notes

- **Interest math in the financial math layer**: the day count conventions and simple interest — `calculate_day_count_fraction()`, which implements ACT/365, ACT/360, ACT/ACT (ISDA: a span is cut at each 1 January it crosses, each piece over its own year's length, the pieces summed in calendar order) and 30/360 through three helpers, and `calculate_simple_interest()` — live in `backend/app/services/financial_math/interest.py` (lot CP-14a, U10, developer decision D-8), and the plugin imports them from there. `_compute_maturation_dates()` stays in `scheduled_investment/plugin.py`: it reads the domain's `MaturationFrequency`. Before U10 the primitives lived in the plugin itself, which had absorbed the former `backend/app/utils/financial_math.py`; the [layer guard](../financial_math.md#layer-guard) now fails if one of them is defined anywhere else in `backend/app`.
- **Daily compounding and the memos (R13-SEC7-2, MF-SI1)**: `interest.py` also holds `compound_growth()`, the closed form of daily compounding that COMPOUND late interest uses (see [Late Interest](#late-interest)). Its cost does not grow with the span:
    - ACT/365 and ACT/360: one power;
    - ACT/ACT: the first year's days, one power for the whole common years and one for the whole leap years in between, then the last year's days;
    - 30/360: one power per step size (0, 1, 2 or 3 days over 360). The step counts of the span are differences of closed-form counts up to each date: a whole year has 7 steps of 0 (onto the 31sts), one of 3 (common year) or 2 (leap year) onto 1 March, the rest of 1, then month by month in the last year. Integers, so exact.

    It is memoized (`_compound_growth`, an LRU cache of 4 096 entries), keyed on the span, the rate as written (`0.05` and `0.050` are equal `Decimal`s with other digits), the convention and the caller's `Decimal` precision and rounding. The ACT/ACT day count across years memoizes its full-year prefix with the same precision-and-rounding key: `_act_act_years_before(start, end_year, …)`, the pieces from the start to 1 January of the end year, in an LRU cache of 4 096 entries. A long run of dates from one start, such as a SIMPLE late-interest history, sums the years once per end year instead of once per date, with the same digits as the plain per-year sum.
- **`identifier_type`**: Always `AUTO_GENERATED` — the engine generates its own UUID identifier.
- **`params_schema`**: Exposes a single `ui_component` field (`key: "_ui_component"`, `default: "scheduled_investment"`) telling the frontend to render the dedicated `ScheduledInvestmentEditor` instead of generic fields.
- **Events**: there is no `supports_events` flag. `get_history_value()` returns price points and events together in `FAHistoricalData.events` (auto-generated + manual, filtered to the requested range).

---

## 🔗 Related Documentation

- 📖 [Scheduled Investment — User Guide](../../../user/assets/providers/scheduled-investment.md) — End-user configuration guide
- 📅 [Asset Events](events.md) — Event types, dedup strategy, MATURITY_SETTLEMENT
- 📐 [Day Count Conventions](../../../financial-theory/fundamentals/day-count.md) — ACT/365, ACT/360, 30/360, ACT/ACT
- 📊 [Asset Types](../../../financial-theory/instruments/asset-types/index.md) — CROWDFUND, BOND, etc.
- 💰 [Asset Architecture](architecture.md) — Sync pipeline and event persistence
- 📦 [Providers Overview](system_providers.md) — All available providers

