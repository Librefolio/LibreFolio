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

---

## 📐 Calculation Engine

**Price formula**:

```
price(d) = initial_value + accrued_interest - Σ(INTEREST events) + Σ(PRICE_ADJUSTMENT events)
```

- **SIMPLE**: `I = P₀ × r × Δt` — interest always on initial principal
- **COMPOUND**: `I_day = V_{t-1} × r × Δt` — interest on running accumulated value

**Emission**: Price points are emitted only at maturation dates (not every day), matching the `maturation_frequency`. Start and end dates of each period always produce a point regardless.

---

## 🔄 Auto-Generated Events (`generate_interest`)

When `generate_interest = True` on a period:

1. At each **maturation date**, the engine checks if accrued interest is positive
2. If positive, generates an **💵 INTEREST event**: `value = current_value - initial_value`
3. After the event: `total_interest = 0`, `event_adjustment = 0` → value resets to `initial_value`
4. Interest accrual restarts from zero on the next day

!!! info "Coupon Reset Behavior"

    The INTEREST event represents a "coupon payout" — the accumulated interest is crystallized and paid out, resetting the running value back to the original principal.

### 🏁 `MATURITY_SETTLEMENT` Event

Auto-generated when:

- The last schedule period has `generate_interest = True` **and** no `late_interest` is configured
- **Or** `late_interest` has `generate_interest = True` (settlement at the last late maturation date)

After settlement, the engine is "off" — `get_current_value()` returns the settlement value for all future dates.

See [Asset Events](events.md) for the full event type reference.

---

## ⏰ Late Interest (`FALateInterestConfig`)

Applied after the asset's maturity date (last period `end_date`):

| Field | Type | Default | Description |
|---|---|---|---|
| `annual_rate` | `Decimal` | — | Annual late interest rate |
| `grace_period_days` | `int` | `0` | Days after maturity before late interest starts |
| `interest_type` | `SIMPLE \| COMPOUND` | `COMPOUND` | Late interest compounds by default (penalties grow) |
| `maturation_frequency` | `MaturationFrequency` | `DAILY` | Emission frequency for late period |
| `generate_interest` | `bool` | `false` | Auto-generate INTEREST + MATURITY_SETTLEMENT events |

During the grace period (from the day after maturity through `maturity + grace_period_days`) interest keeps accruing at the **last schedule period's** `annual_rate`; after it, the late `annual_rate` applies. Both segments start from the value at maturity and use the late `interest_type` and the global `day_count` (`_compute_late_interest_value`).

!!! warning "Skip Formula Optimization"

    SIMPLE late interest uses a closed-form calculation for efficiency. COMPOUND late interest uses day-by-day accumulation only within the late sub-period, not from asset start.

---

## ⚡ Caching & Invalidation

The engine caches the full schedule computation as a `tuple[dict, list[FAAssetEventPoint]]`:

- **Key**: MD5 of the canonical JSON of the validated schedule (`_cache_key`).
- **Invalidation**: Cache is invalidated when `provider_params` changes (i.e., the user reconfigures the schedule via the frontend `ScheduledInvestmentEditor`).
- **Hit behavior**: On cache hit, `get_history_value()` slices the pre-computed dict to the requested date range — O(1) per point.
- **Miss behavior**: Full schedule recomputation from `initial_value` through all periods. This is deterministic and fast (no I/O), typically < 10ms even for multi-year schedules.

The cache is a module-level TTL cache (`get_ttl_cache("scheduled_investment")`, 256 entries, 48 h TTL), in memory and per process. It survives across multiple sync calls but is cleared on server restart.

---

## 🔧 Internal State Variables

During computation, the engine tracks these internal variables per day:

| Variable | Description | Reset behavior |
|---|---|---|
| `total_interest` | Cumulative accrued interest since last coupon/start | Reset to 0 after INTEREST event |
| `event_adjustment` | Net sum of PRICE_ADJUSTMENT events | Reset to 0 after INTEREST event |
| `running_value` | `initial_value + total_interest + event_adjustment` | Computed per-day |

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
- **1 February** (first maturation): 💵 INTEREST event of ≈ €42.47 → value resets to €10,000
- **February**: value grows again from €10,000
- **Maturity**: 🏁 MATURITY_SETTLEMENT event → engine stops

---

## 🔧 Technical Notes

- **`financial_math.py` eliminated**: All financial math functions (`calculate_day_count_fraction`, `calculate_simple_interest`, `_compute_maturation_dates`) are now inside `scheduled_investment.py` as a `# Financial Math` section.
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

