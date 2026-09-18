# Performance charts - SP06 G3/G1c and SP07 G1a/G1b

**Status:** I10 and initial I60 integrated/validated; I60
UX/axis/comparison follow-up reopened for manual-review round 2.
**Implementation:** I10 completed on 2026-09-10. I60 implementation and
post-merge combined validation completed on 2026-09-11. Manual review closed
the I60 follow-up contract on 2026-09-11. All portfolio/GrowthChart phases
remain FROZEN.
**Revision:** 11 - I60 selected-range boundary and secondary-axis correction, 2026-09-12.
**Analysis baseline:** `f90d9801bd7a2d74aac6a27efe305314c6c004cc`
(`refs/heads/dev_release2`).
**Gate-0 execution baseline:** `0af66da5f366a9559549154631a4ee15ca620915`,
containing `dev_release2@973968ed2` and workstream F commit `e50d66408`.
**I10 implementation baseline:** `0af66da5f366a9559549154631a4ee15ca620915`;
developer authorization is limited to the signal-only I10 slice.
**I60 implementation baseline:** `0d57874303b1311c0f5ea3b8653d24a33d4245a6`,
including I10 and H.
**I60 combined-validation baseline:** `5524a0eda664834bcc1fe4e0effe007d18564030`,
including the committed I60 implementation and merged H renderer normalization.
**I60 follow-up implementation baseline:**
`9d270ccea9b6150eae9421385b3d12301a6e243e`, merge parents
`7df7ccbabb181c9924dcaeef4aceb1032a1299e1` and coordinator target
`4949b2f4c04050e46f643de848894b6706349f34`; exact clean baseline verified,
target contained, port 6157 free.
**Portfolio implementation baseline:** not yet authorized. It will be the later
post-H target SHA supplied after the H-before-I integration gate.
**Coordinator:** Release 2 coordinator, session
`c8328a01-f208-4ade-a352-0486d1f14de2`.
**Future runtime lane:** port `6157`, absolute data directory
`/tmp/librefolio-r2-i-charts`.

Previous/master:

- [Advanced charts backlog](../09_feedbackJobs/02_grafici_avanzati.md)
- [Sprint analysis and dependency map](../09_feedbackJobs/06_piano_sprint.md)
- [Feedback-jobs index](../09_feedbackJobs/README.md)
- [Workstream F plan](../17_assetDataOperations/plan-phase00AssetDataOperations.prompt.md)

This plan is the durable record of the final product decisions and the
dependency-safe split for an XL integration. It does not claim that any chart,
DTO, calculation, test, generated client, translation or documentation change
has been implemented.

## 1. Goal and scope

Deliver four related but differently owned chart slices:

| Slice | Product result | Revised size |
|---|---|---:|
| G3 | Historical rolling return for N calendar days in Asset detail | L end-to-end |
| G1a / F8a | Third GrowthChart mode for cumulative P&L, including selected-broker contribution lines | L |
| G1b / F8b | Synthetic total P&L candles plus selected-broker close lines | L |
| G1c / F8c | Signed personal DIVIDEND/INTEREST history as stacked bars | L |

Together they are an **XL integration**, not one implementation branch. The
shared theme is temporal performance; the real code ownership splits into:

1. Asset calendar-return backend.
2. Portfolio engine/service/schema integration.
3. GrowthChart frontend integration.
4. Asset-detail frontend integration.
5. Coordinator-owned generated/shared surfaces.

### 1.1 In scope

- Backend-owned financial transformations.
- Existing target-currency and broker-scope controls.
- Existing daily/weekly/monthly semantic zoom.
- Existing price/FX lookup, fallback, provenance and faded-line semantics in
  the now-integrated post-F source.
- Explicit data-quality states without silent zero-shaped fallbacks.
- Dashboard and Broker-detail GrowthChart behavior.
- Asset-detail primary chart mode.
- Future specialist tests, English documentation, generated API client and
  four-language UI strings, only in their authorized phases.

### 1.2 Out of scope

- A new price, FX or staleness resolver.
- Intraday portfolio truth or simultaneous cross-asset extrema.
- Volume for portfolio candles.
- Asset lines in portfolio P&L modes.
- A second broker, currency or resolution selector inside a chart.
- Standalone transfer-adjusted broker performance.
- New transaction-create semantics for negative DIVIDEND/INTEREST.
- New short-accounting support. The verified post-F engine does not value
  negative positions canonically, so candle output fails closed for that state.
- Feeding synthetic candles into risk, statistical-volatility or factual AI
  Export inputs.
- Database schema changes unless Gate 0 proves one is unavoidable; none is
  expected from the current analysis.

## 2. Hard Gate 0 - post-F code refresh and implementation authorization

**Gate 0 blocks every production/test implementation step in this plan.**

The F checkpoint is now present in the technical-refresh HEAD. The source
refresh items below are complete, but Gate 0 remains **BLOCKED** because the
developer has not authorized implementation.

The assigned owners must:

1. Verify exact target HEAD and clean worktree.
2. Read F's execution plan/checkpoint manifest and its final intended paths.
3. Re-read, rather than mechanically preserving current line claims:
   - `backend/app/services/portfolio_engine.py`;
   - the final shared price-resolution/retrieval modules;
   - `backend/app/services/asset_source.py`;
   - `backend/app/services/portfolio_service.py`;
   - `backend/app/schemas/portfolio.py`;
   - `frontend/src/routes/(app)/assets/[id]/+page.svelte`;
   - `frontend/src/lib/components/charts/PriceChartFull.svelte`;
   - `frontend/src/lib/components/dashboard/GrowthChart.svelte`;
   - `frontend/src/lib/components/charts/timeSeriesAggregation.ts`;
   - portfolio/asset stores and current tests.
4. Confirm how F preserves observation date, price/FX backward-fill metadata,
   split handling, quote base, ownership and current fallback provenance.
5. Record the post-F technical-refresh HEAD and changed symbols/paths.
6. Preserve the confirmed short-position result: no canonical short valuation
   exists, so retain the fail-closed candle contract; do not create one here.
7. Obtain a new **explicit developer implementation authorization**. The
   current authorization permits this Markdown plan only.

Gate 0 is released only for a phase whose dated note contains the exact
execution SHA, final resolver contract, file reservations and verbatim
developer authorization. I10 now satisfies that condition. Portfolio phases
remain blocked by H0, F engine release, a new post-H baseline and their own
explicit authorization.

### 2.1 Gate 0 technical refresh - 2026-09-10

> **Note implementazione (G0 technical refresh, 2026-09-10):** verified clean
> HEAD `0af66da5f366a9559549154631a4ee15ca620915` on
> `e-alfy-performance-charts-plan`. It merges current
> `dev_release2@973968ed2`, including F commit `e50d66408`. Read F's durable
> plan and exact committed diffs, then re-read the final engine, portfolio
> service/schema, resolver, Asset detail/query/cache path, GrowthChart,
> PriceChartFull, temporal reducers, stores and relevant tests. No production
> or test implementation and no runtime command was executed.

F's relevant delivered delta is narrower than the original conflict forecast:

- `portfolio_engine.py` now exports
  `compute_portfolio_fx_cache_identity(...)` and includes its result in the L1
  blob key.
- F did not change `price_resolver.py`, `portfolio_service.py`,
  `schemas/portfolio.py`, `GrowthChart.svelte`, `PriceChartFull.svelte`,
  `timeSeriesAggregation.ts`, portfolio store or Asset price-cache adapter.
- F's Asset-detail edit adds the transactions link in the header, outside the
  chart state/render block. G3 must preserve it.
- F's `asset_source.py` edits are in Asset deletion, not
  `get_prices_bulk()`/backward-fill/signal execution.
- F added FX-identity/invalidation tests to
  `test_financial/test_portfolio_service.py` and `test_fx_core.py`, plus an
  Asset-detail link test. Future tests extend these files without replacing
  F's coverage.

Final source reality:

- `AssetPriceSeries` remains the single close resolver:
  `MARKET -> TRADE_AVG -> CARRIED (LOCF) -> MISSING`. It carries native
  currency, actual observation date, estimated origin and price
  `BackwardFillInfo`; FX is still applied by the engine adoption layer.
- Asset `get_prices_bulk()` already emits a dense daily backward-filled OHLC
  series, applies target-currency FX to all OHLC fields, and retains price +
  FX provenance on a fresh API response.
- The frontend Asset cache adapter still stores only `originalClose` and price
  `daysBack`. A cache-hit reconstruction drops original O/H/L and FX
  provenance. G3 cannot claim full fade/tooltip parity until that existing
  cache representation is widened or the signal response carries the needed
  provenance independently.
- Existing `RISK_ROLLING_RETURN` remains prepared-observation based. Its
  `window` counts prepared returns, not calendar dates.
- `DailyStateBuilder` still keeps aggregate cash/capital state, per-broker
  quantities, no daily broker P&L DTO, and filters `qty <= 0`. True shorts
  remain unsupported.
- `InTransitInterval.share` is still hardcoded to `1` in the classifier helper.
  The additive broker/candle implementation must correct this before claiming
  ownership-scaled in-transit values.
- Portfolio engine price preload and `AssetPriceSeries` remain close-only even
  though `PriceHistory` stores OHLC. Candles must extend the existing resolver
  data shape, not create a parallel resolver.
- `PortfolioReportQuery/Response` contains none of the proposed broker-history,
  candle or income fields/flags.
- L2 report cache still keys access + transaction + price state only. It does
  not yet consume F's shared FX identity and still lacks split-event identity.
- Frontend `fetchReport(...)` still uses nine positional parameters and manually
  concatenated feature-key suffixes. Adding three more positional booleans
  would be unsafe; use one typed feature-options object/canonical feature key
  while preserving compatibility wrappers for existing callers.
- `PortfolioSummary.period_income`, engine income pools and contribution
  service still use `abs()`; signed legacy corrections are not canonical yet.
- GrowthChart remains `eur|pct`, with total P&L mapped only for the ABS tooltip;
  unused `periodBasePnl` must not be adopted because the approved P&L line is
  never rebased.
- `aggregateOHLCV()` is ready and tested; no flow-sum reducer exists.
- PriceChartFull already owns line/candle, absolute/percentage, semantic zoom
  and `disableCandlestick`, but lacks percentage-unit primary-series and
  hide-view-control props needed by G3.

### 2.2 H-before-I shared-surface gate

Coordinator decision: H/YOC integrates before I on shared portfolio surfaces.
Until H is merged and I re-reads the new target:

- H exclusively owns `portfolio_service.py`, `schemas/portfolio.py`, relevant
  portfolio service/API tests, any approved minimal FIFO eligibility seam, and
  `ExposureTable.svelte` plus its test.
- F retains `portfolio_engine.py` until the coordinator declares its integration
  stable.
- I20 and every dependent portfolio/candle/report/GrowthChart phase remain
  blocked.
- Only the isolated G3 **backend signal** slice may be considered for execution
  after explicit developer authorization, and only if its final file set avoids
  all H/F-owned surfaces.

After H integration, I must merge/rebase only through the developer/coordinator
workflow, verify the new exact SHA, re-read H/F changes and update reservations
before portfolio implementation. H is a sequence dependency, not a reason to
duplicate its YOC calculations or cache changes.

## 3. Final product contract

### 3.1 G3 - rolling return by calendar days

- Asset detail gains a primary mode `Price | N-day return`.
- Output is a historical rolling series, with one result state for every chart
  date in the selected range.
- Windows are `7`, `30`, `90`, `365` calendar days; default is `30`.
- Formula remains backend-owned:

  ```text
  return(t, N) = price(t) / price(t - N calendar days) - 1
  ```

- Prices at `t` and `t-N` come from the **existing final post-F Asset price
  retrieval/resolution path**, including its current backward lookup and
  staleness policy. No return-specific threshold, resolver or service is added.
- Currency is the target currency already selected in the top Asset toolbar.
  The return therefore includes FX movement when target differs from the
  asset's native currency.
- Backfilled/carried result portions reuse the existing faded-line visual
  semantics from Asset/FX price charts.
- Tooltip/point metadata preserves the requested reference date and actual
  observation-date provenance wherever the final resolver contract exposes it.
- The existing observation-count `RISK_ROLLING_RETURN` behavior remains
  backward compatible for saved signal configurations. The calendar view must
  not silently reinterpret those saved instances.
- No TypeScript price lookup or return formula.
- In N-day mode, price-only controls that would misrepresent the series are not
  active: no candlestick, Abs/% rebase or price editing. Saved price/signal
  settings remain untouched and return when the user switches back to Price.

### 3.2 G1a - cumulative P&L with additive broker contributions

- GrowthChart modes are mutually exclusive:

  ```text
  Value | Return % | P&L
  ```

- P&L contains three mutually exclusive submodes:

  ```text
  Line | Synthetic candles | Income
  ```

- Total uses existing canonical `PortfolioHistory.total_pnl`, calculated from
  inception and never rebased at selected-range or zoom start.
- Dashboard behavior uses the effective broker scope already produced by the
  existing top filter:
  - one selected broker: total line only;
  - two or more selected brokers: total line plus one line for every selected
    broker;
  - "All" means the existing explicit owned-broker set, not a new selector.
- Broker detail always renders total only.
- All required lines are initially visible. There are no asset lines.
- Broker lines are additive contributions inside the **one selected combined
  scope**, not independent one-broker engine calculations.
- For an internal transfer, in-transit value stays with the departure broker
  until arrival, then moves to the destination broker. Individual lines may
  jump; this is accepted.
- Mandatory daily Decimal identity:

  ```text
  sum(selected broker P&L contributions) == canonical scoped total_pnl
  ```

- UI wording/tooltips must not describe these lines as standalone
  transfer-adjusted broker performance.

### 3.3 G1b - synthetic P&L candles

- Synthetic candles are the second P&L submode. They do not become a fourth
  top-level GrowthChart mode.

- First release hybrid rendering:
  - total scoped portfolio as candlesticks;
  - when effective scope has at least two brokers, overlay one selected-broker
    **close-P&L line** per broker;
  - one broker or Broker detail: total candle only.
- For each calendar day, apply all transactions first and use historical
  end-of-day quantities, role-aware ownership, quote-base quantity and target
  currency.
- Compose asset contributions into one **daily portfolio candle first**.
  Weekly/monthly rendering then applies:

  ```text
  open  = first daily open
  high  = max daily high
  low   = min daily low
  close = last daily close
  ```

- Never sum daily candles. Never aggregate each asset to week/month before
  cross-asset daily composition.
- Cross-asset high/low are explicitly synthetic and potentially
  non-simultaneous. The label is always visible; tooltip/help repeats the
  limitation.
- No volume field in the backend contract. A frontend chart adapter may use
  `null` only because the shared chart point type allows it.
- Missing OHLC reuses the final existing valuation fallback chain. If no
  intraday variance is known for one asset/day, that resolved contribution is
  flat:

  ```text
  open = high = low = close = resolved valuation contribution
  ```

  The asset/day is not dropped and no new resolver is invented.
- Reuse existing data-quality and faded semantics for carried/fallback values.
- Daily total candle close must equal canonical total P&L exactly.
- The verified post-F engine still cannot value a true negative position.
  Therefore the candle series is unavailable for that unsupported state. Do
  not omit the short or fabricate a liability; broader short accounting needs
  separate authorization.
- Synthetic candles are presentation-only. They are not an intraday series,
  statistical-volatility input or factual AI Export dataset.

### 3.4 G1c - signed personal income history

- Income is the third P&L submode. It does not become a fourth top-level
  GrowthChart mode.
- Source is every personal, scoped, committed `Transaction` of type DIVIDEND or
  INTEREST.
- Include asset-linked and broker-level `asset_id=None` rows. Do not derive
  personal cash from global `AssetEvent` declarations.
- Reuse target currency, current broker scope and existing temporal resolution.
- Preserve the transaction amount sign for legacy corrections. The create API
  may continue requiring positive new income rows; this plan does not relax
  that rule.
- DIVIDEND and INTEREST render as distinct-color **stacked** bars. Tooltip shows
  both signed values and their total.
- Daily values are sparse economic flows. Weekly/monthly buckets sum them;
  they never use end-of-period/last-value semantics.
- Period boundary remains the canonical portfolio boundary
  `(date_from, date_to]`.
- Mandatory Decimal identity:

  ```text
  sum(dividend flow) + sum(interest flow)
      == canonical signed PortfolioSummary.period_income
  ```

- Signed corrections must be updated consistently in summary, contribution,
  engine return-pool accounting and history. They must not be pushed into the
  reconciliation residual by an `abs()` mismatch.
- Missing FX uses the existing portfolio data-quality/remediation contract.
  It must not become a known zero.

## 4. Backend architecture

### 4.1 Proposed report DTOs

Keep `PortfolioHistoryPoint.total_pnl` as the single total line source. Add
optional report outputs rather than duplicating total history:

```text
broker_pnl_history:
  - broker_id
  - broker_name
  - points:
      - date
      - total_pnl
      - quality/provenance when required

pnl_candles:
  - date
  - open
  - high
  - low
  - close
  - quality/provenance
  - hypothetical = true at series metadata level
  # no volume

income_history:
  - date
  - dividend
  - interest
  - quality/provenance
```

Names may be adjusted at Gate 0 to match final schema conventions, but the
separation and semantics above are fixed.

Proposed query flags:

| Flag | Caller policy |
|---|---|
| `include_broker_pnl_history` | Dashboard true only when effective scope has at least two brokers |
| `include_income_history` | Dashboard/Broker overview true; sparse payload keeps mode immediately available |
| `include_pnl_candles` | Lazy true on first candle activation; expensive OHLC work stays off ordinary reports |

All optional flags must enter:

- backend L2 report cache key;
- frontend cache/inflight key;
- report metadata `included_features`;
- L1 result key if the engine result shape or preload differs.

Frontend feature selection must move behind a typed options object and one
canonical cache-key serialization. Keep existing positional exports as
compatibility wrappers if current callers cannot migrate atomically; do not
append more order-sensitive boolean arguments.

Post-F, L1 already includes F's bounded
`compute_portfolio_fx_cache_identity(...)`; preserve and reuse it. L2 still
lacks both this FX identity and split-event identity. H owns L2's current file
until integration, so I must first consume H's result, then add only whatever
FX/split/feature-key coverage remains. Do not duplicate F's helper.

### 4.2 Additive broker contribution state

Do not run one engine calculation per broker. Sub-scope calculations change
linked internal transfers into external boundaries and are not guaranteed to
sum to the combined scope.

Inside one combined-scope daily replay, maintain additive values by broker:

- owned cash;
- held-position market value;
- external capital contribution;
- in-transit cash/asset value attributed to departure until arrival;
- final per-broker P&L contribution.

Internal transfers do not create external capital for the selected combined
scope. At arrival, custody/value attribution moves to the destination. The
implementation must build the total and broker values from the same Decimal
components, not calculate a residual line after the fact.

Every emitted day asserts, through a typed invariant/test:

```text
sum(broker_nav_contribution) == scoped nav
sum(broker_capital_contribution) == scoped capital_baseline
sum(broker_pnl_contribution) == scoped total_pnl
```

If rounding is needed only at serialization, keep internal Decimal values
unrounded and serialize all lines with the same policy.

### 4.3 Daily synthetic candle composition

Post-F confirms that `AssetPriceSeries` is the single resolver but currently
carries close only, while `PriceHistory` and Asset query responses carry OHLC.
The candle phase must widen the existing `PriceObservation`/`ResolvedMark`
family (or an equivalent same-resolver envelope) with optional OHLC. It must
not add a second lookup/fallback class.

The final implementation should expose one resolved per-asset/day valuation
record from that same path, carrying:

- resolved O/H/L/C or resolved close-only fallback;
- native/target currency provenance;
- price and FX observation dates/backward-fill metadata;
- quote-base quantity;
- data-quality state.

For an EOD owned quantity `q`, quote base `b` and daily FX factor `f`:

```text
factor = q / b * f
asset_open  = factor * open
asset_close = factor * close
```

For a canonically supported negative factor, high/low orientation reverses:

```text
asset_high = factor * low
asset_low  = factor * high
```

This formula is retained as the future orientation rule, but the verified
engine does not support negative-position valuation. This plan therefore fails
closed before composing a short candle; it does not execute this branch.

Compose all resolved asset contributions for the day. Then add one common
non-price offset:

```text
offset = canonical total_pnl - sum(asset_close)

portfolio_open  = offset + sum(asset_open)
portfolio_high  = offset + sum(asset_high)
portfolio_low   = offset + sum(asset_low)
portfolio_close = canonical total_pnl
```

The offset carries cash, capital baseline, realized/income effects, in-transit
and flat fallback contributions. Use the same daily FX observation for all four
fields; there are no intraday FX extrema.

### 4.4 Signed income foundation

Extract one signed-income accumulator used by summary, contribution and report
history:

1. Keep `tx.amount` sign through target conversion.
2. Apply role-aware ownership exactly once.
3. Group by `(date, transaction type, broker)` and preserve `asset_id=None`.
4. Update return-pool accounting with the signed value.
5. Replace positive-only inclusion checks with nonzero checks where legacy
   corrections must remain visible.
6. Keep the create/update validation rule unchanged unless separately
   authorized.
7. Update `period_income` schema prose so it no longer falsely promises a
   positive-only value.

For ordinary valid positive income, behavior is unchanged. For a legacy
negative correction, NAV already reflects signed cash; this change moves the
same value from "Other / reconciliation residual" into canonical Income.

### 4.5 Calendar-return signal

The technical refresh favors a dedicated calendar-return plugin because the
existing `RISK_ROLLING_RETURN` is statically coupled to prepared observation
returns. The isolated plugin can consume the already-resolved dense daily
`SignalPricePoint` input without changing `asset_source.py`, the price resolver,
portfolio engine/service/schema or H-owned tests.

If implementation evidence proves a smaller backward-compatible extension is
safer, it must still leave the existing signal's default and saved instances
unchanged.

Whichever is chosen:

- consume F's resolved daily series;
- request enough pre-visible history through the existing loader;
- produce one output state per visible chart date;
- include N=30 in normalized/default params;
- carry reference target date and actual observation provenance through an
  additive `SignalValuePoint` metadata contract (currently absent), or an
  equally typed signal-owned companion that does not depend on the lossy Asset
  price cache;
- use the existing signal status/warmup/availability structure;
- never duplicate price lookup, FX conversion, backward fill or finance math
  in TypeScript.

## 5. Frontend architecture

### 5.1 GrowthChart ownership

One owner implements G1a, G1b and G1c in
`frontend/src/lib/components/dashboard/GrowthChart.svelte`.

The component keeps two explicit state axes:

```text
coreMode   = value | return | pnl
pnlSubmode = line | candles | income
```

`pnlSubmode` is active only while `coreMode == pnl`; switching Value/Return does
not promote Income into the core-mode selector.

The same owner also coordinates:

- `timeSeriesAggregation.ts`;
- portfolio store request/cache options;
- Dashboard mount;
- Broker-detail mount;
- pure chart adapters/helpers.

No parallel writer may independently add one of the three modes.

Mode changes must:

1. Snapshot the current logical zoom range.
2. Hide the active ECharts tooltip before changing series structure.
3. Rebuild the selected series.
4. Restore the logical date window at the current semantic resolution.
5. Keep all required total/broker series visible.

Advanced-data fetches must not replace an unchanged `history` reference merely
to obtain optional candle data, because the current chart resets
resolution/zoom on a new history reference.

### 5.2 Temporal reducers

- Keep `aggregateLineSeries()` end-of-period behavior for cumulative P&L and
  broker close lines.
- Keep `aggregateOHLCV()` for already-composed daily total candles.
- Add a separate flow reducer, provisionally `aggregateSumSeries()`, for signed
  DIVIDEND/INTEREST buckets.
- Do not change generic bar-signal downsampling, which intentionally uses a
  last-value snapshot.
- Preserve UTC dates, ISO weeks, UTC months, bucket boundaries,
  representative dates, density thresholds, hysteresis and 200 ms settled
  zoom recomputation.

### 5.3 Asset-detail ownership

A separate owner integrates G3 after F and the backend calendar signal:

- primary selector `Price | N-day return`;
- window controls `7/30/90/365`, default `30`;
- existing target-currency/date/resolution controls only;
- PriceChartFull receives additive props for percentage-unit rendering and
  hiding incompatible controls if required;
- no return editing, price candlestick or extra percentage rebase;
- existing faded gradient and tooltip provenance;
- switching back restores existing Price state/settings.

## 6.0 G1a/G1b/G1c Gate 0 release — 2026-09-17

> **Note implementazione (Gate 0 re-verification for G1a/b/c + G3, 2026-09-17):**
> re-verified exact baseline before any merge: HEAD `2d22130bd58471463c4ae600139939680ded2ef8`,
> `dev_release2@e1f3fe177861d2b9b953b218f66ea7d4714ab405`,
> merge-base `4949b2f4c04050e46f643de848894b6706349f34`. H (`74afcebce`/`f092a194b`)
> and F (`e50d66408`/`cc57b6a38`) confirmed already-absorbed ancestors of both
> sides. `dev_release2` gained exactly 9 commits since merge-base: two
> unrelated-worktree merges, three docs-only commits, and two internal-only
> refactors explicitly authorized as no-product-contract-change — Workstream K
> (SP08, splits `asset_source.py` into `asset_sources/*.py`) and Workstream L
> (SP16, splits `TransactionService.execute_batch`). Every shared surface named
> in the original Gate 0 refresh (`portfolio_engine.py`, `portfolio_service.py`,
> `schemas/portfolio.py`, `price_resolver.py`, `GrowthChart.svelte`,
> `PriceChartFull.svelte`, `timeSeriesAggregation.ts`, `ExposureTable.svelte`,
> portfolio store) was individually re-diffed against current `dev_release2` —
> zero drift confirmed directly, not carried forward from stale prose. The
> single actionable drift: my I60G mixed-currency signal-price filtering fix in
> `get_prices_bulk` was not present in K's new `asset_sources/price_query.py`
> (K refactored the pre-fix baseline) — flagged as a bounded post-merge
> fix-forward, no other K/L file touched. No `git merge` was run by this
> workstream (forbidden by binding Git policy); merge was deferred to the
> coordinator/developer.

> **⚠️ Fuori pista (human direct review, 2026-09-17):** the human operator of
> this session (not only the relayed coordinator) asked directly for a recap
> and asked to see the exact no-force review server themselves before
> approving anything further. Server was started on lane 6157, health/root/
> assets/fx returned 200, human reviewed directly, then asked it stopped;
> stopped and port proven free. This was independent of and prior to the
> coordinator's own authorization relay.

> **Note implementazione (merge conflict resolution, 2026-09-17):** developer
> ran `git merge dev_release2`; exactly one conflict occurred, as predicted:
> `backend/app/services/asset_source.py`. Resolved by taking `dev_release2`'s
> side entirely (`git checkout --theirs`) — confirmed byte-identical to K's
> facade via `git diff dev_release2 -- ...` (empty). Applied the characterized
> fix-forward in `backend/app/services/asset_sources/price_query.py`'s
> `PriceQueryOperations.get_prices_bulk`: replaced the still-unfixed
> `neutral_prices = (...) if currency_coherent else []` with the I60G
> target-currency-valid filtering (`signal_price_points = result.prices if
> currency_coherent else [point for point in result.prices if target and
> point.currency == target]`) plus its warning-message wording. Diff against
> `dev_release2` isolated to exactly this one hunk. Staged only these two
> paths explicitly (no wildcard); every other merge file was already
> auto-staged by git's own merge machinery. Validated on lane 6157/data
> `/tmp/librefolio-r2-i-charts`: `services asset-signals` 20/20,
> `services risk-all calendar` 28/28 (119 deselected), `schemas signals`
> 477/477, `services signal-service` 50/50 — all green. `git diff --check`
> clean, no remaining conflict markers. Did not commit; developer committed
> the merge.

> **Note autorizzazione (G1a/G1b/G1c start, 2026-09-17):** developer confirmed
> merge committed, new HEAD `3c7e129c7b549f3e674403db8ea33268d6ed0e61`
> (parents `2d22130bd5...` + `e1f3fe177...`, both confirmed ancestors,
> worktree clean). Re-verified post-commit that `asset_source.py` and
> `asset_sources/price_query.py` content is byte-identical to what was staged
> pre-commit — no silent rewrite. This is now the authoritative baseline.
> Developer explicit start signal (verbatim intent): "authorized to begin
> implementation of Growth chart P&L submodes (Value/Return%/P&L ×
> Line/Synthetic-candles/Income) exactly as specified in your existing plan
> sections... G3 remains out of scope (already complete)... report back at
> each natural phase boundary (G1a, then G1b, then G1c) rather than one giant
> batch." Proceeding now with G1a (additive broker P&L contributions) as the
> first reported phase; I20-I50 phase-table rows below move from BLOCKED to
> IN PROGRESS accordingly. Lane 6157 / `/tmp/librefolio-r2-i-charts`,
> test-author owns new/repaired tests.

> **Note implementazione (G1a backend engine, 2026-09-17):** implemented the
> additive per-broker accumulator design in `DailyStateBuilder.build()` per
> §4.2 — parallel accumulators (`cumulative_cash_by_broker`,
> `cumulative_ecf_by_broker`, `market_value_by_broker`, in-transit
> `it_by_broker`) incremented at the exact same Decimal-mutation sites as
> their scope-aggregate counterparts (pre-frame + frame date-only cash/ECF,
> both in-kind-adjustment BUY/SELL sites, the market-value-per-asset loop,
> `_compute_in_transit`), never a residual/derived pass. `external_cash_flows`
> widened from a 3-tuple to `(date, broker_id, amount, currency)` across all 6
> touch points. Fixed the pre-existing `InTransitInterval.share` bug: the
> caller now sets `interval.share = self.broker_shares.get(departure_broker_id,
> 1)` instead of leaving the constructor's hardcoded `1` placeholder — a real,
> plan-flagged (§2.1) behavior change for <100%-owned brokers with an
> in-flight internal transfer, covered by a hand-verified scratch scenario
> before handing off to test-author. New `BrokerDailyContribution` dataclass
> (`nav_contribution`/`capital_contribution`/`pnl_contribution`) wired into
> `DailyPortfolioState.broker_contributions` (both the stationary-day-reuse
> and full-compute construction branches) and into `EngineEndState` for
> cache-forward-extension parity. Verified the §4.2 invariant
> (`sum(broker_contributions) == scope aggregate` for nav/capital/pnl) holds
> on every emitted day via two hand-computed scratch scenarios (multi-broker
> deposit/buy/sell/dividend/withdrawal; and a cash in-transit transfer between
> brokers exercising the share-bug fix) — both matched hand-calculated
> expected values exactly before being handed to test-author to formalize.
> Repaired 17 existing tests broken by the tuple-shape change (mechanical
> literal/index adaptation only, no assertion semantics changed):
> `test_portfolio_engine_vnext.py` (1), `test_daily_state_builder.py` (1),
> `test_performance_inputs_inkind.py` (3), `test_cash_decomposition.py` (9),
> `test_scope_classifier.py` (5, index shift only). Backend gates green:
> `services portfolio-engine` 42/42, `services roi-fifo-utils` 384/384,
> `api portfolio` 24/24.
>
> Added the DTO/service layer: `BrokerPnlHistory`/`BrokerPnlHistoryPoint` in
> `schemas/portfolio.py`, `include_broker_pnl_history` query flag on
> `PortfolioReportQuery` (caller policy per §4.1: Dashboard sets it only when
> effective scope has ≥2 brokers — enforced by the frontend caller, not the
> backend), wired into the L2 report cache key and `PortfolioReportResponse`.
> `DerivedViewsBuilder.build_broker_pnl_history()` (engine, raw dicts) +
> `PortfolioService.get_broker_pnl_history()` (service, resolves broker
> names, slices to the requested date range) mirror the existing
> `build_history()`/`get_history()` adapter pattern exactly.
>
> test-author delivered `test_broker_pnl_contributions.py` (8 tests, no other
> file touched): multi-broker golden-number scenario + 60-day invariant,
> dedicated F2 in-transit-share-fix regression (`interval.share == 0.5` via
> real `classify()`) + mid-transit→post-arrival NAV composition, in-kind
> ADJUSTMENT-in/out broker attribution (pre-frame + frame), `EngineEndState`
> per-broker fields, `build_broker_pnl_history()` shape + per-date sum
> reproduces aggregate `total_pnl`. Zero discrepancies against the
> hand-verified golden numbers above. Final backend gate:
> `services portfolio-engine` 42/42, `services roi-fifo-utils` 392/392 (384 +
> 8 new), `api portfolio` 24/24, ruff+black clean.
>
> **Note implementazione (G1a frontend, 2026-09-17):** `GrowthChart.svelte`
> gets a third `viewMode` value `'pnl'` (kept as an extension of the existing
> `'eur'|'pct'` literal union rather than renaming to the plan's prose
> `coreMode` axis — avoids churn on 14 existing branches and the `data-testid`
> values `growth-toggle-eur`/`-pct` that E2E may already depend on) plus a
> `pnlSubmode: 'line'|'candles'|'income'` state (only `'line'` has a real
> branch; a defensive `if (viewMode === 'pnl') return []/return html` guard
> stops the other two from silently falling through into the pct branch once
> G1b/G1c add them). New `brokerPnlHistory` prop (optional, default `[]`) —
> the Total P&L line reuses the exact already-computed, non-rebased
> `eurStackedData.totalPnl` (no new derivation, no rebasing, per §3.2); broker
> overlay lines are only built when `brokerPnlHistory.length >= 2` (defensive,
> mirrors the Dashboard-side ≥2-broker gate). New `BROKER_PALETTE` (6 stable
> rotating colors) for broker lines, dashed/thinner than the solid Total line.
> Y-axis formatter and tooltip both widened from a 2-way to a 3-way branch
> (`pct` vs "not pct" for the axis; explicit `pnl` branch for the tooltip).
> `portfolioStore.svelte.ts`'s `fetchReport()` gained a trailing
> `options?: {includeBrokerPnlHistory?: boolean}` parameter — deliberately
> NOT another positional boolean, per the plan's explicit §4.1 anti-pattern
> warning (the function already had 5). Dashboard page wires
> `wantsBrokerPnlHistory = effectiveBrokerCount >= 2` (using
> `activeBrokerIds ?? ownedBrokerIds`) into the fetch and threads
> `brokerPnlHistory` down to `<GrowthChart>`; `brokers/[id]/+page.svelte`
> (broker detail) needed NO change — it never passes the prop, so it
> naturally renders Total-only, matching "Broker detail always renders total
> only" (§3.2).
>
> ⚠️ Process disclosure: I ran `./dev.py api sync` locally (needed to
> type-check/test my own frontend changes against the new
> `BrokerPnlHistory`/`include_broker_pnl_history` schema) and added one i18n
> key (`dashboard.pnl` = "P&L", identical in all 4 locales) via
> `./dev.py i18n add` for the new toggle button label. Both are technically
> coordinator-owned shared surfaces per the original kickoff ("Coordinator
> owns shared i18n/API generation/..."). The `api sync` output
> (`openapi.json`/`generated.ts`) is gitignored — no committed diff, purely
> local regeneration, already reflected in `git status` above (17 paths, no
> extras). The i18n key IS a tracked-file change (all 4 `frontend/src/lib/
> i18n/*.json`) — flagging this explicitly rather than silently including it;
> happy to have the coordinator take over any future i18n additions for
> G1b/G1c if preferred, this one is done and tests are already green against
> it.
>
> Full gate re-run after frontend work: `svelte-check` 0 errors (41
> pre-existing unrelated warnings in `GlobalSettingsTab.svelte`), Vitest full
> suite 4719/4719 (197 files, incl. the 65 `chartCoreHelpers.test.ts`
> source-contract tests against `GrowthChart.svelte` and the 2
> `portfolioStore.test.ts` tests), `front-portfolio dashboard` E2E 6/6,
> `./dev.py front build` clean.
>
> G1a considered complete and ready for phase-boundary report to the
> coordinator. G1b (synthetic candles) and G1c (signed income) not started.

> **Note implementazione (G1b synthetic candles, 2026-09-17):** coordinator
> accepted G1a and authorized G1b. Implemented per §4.3's exact formula:
> `factor = q/b*f`, `offset = total_pnl - sum(asset_close)`,
> `{open,high,low} = offset + sum(asset_{open,high,low})`, `close = total_pnl`
> exactly by construction (never a residual check) — hand-verified on a
> 2-day scratch scenario (day 1: BUY same-day as DEPOSIT, no OHLC yet →
> flat all-zero candle; day 2: a priced OHLC row → candle (50,100,20,80)
> against total_pnl=80) before handing to test-author.
>
> Backend: widened `price_resolver.py`'s `PriceObservation`/`ResolvedMark`/
> `AssetPriceSeries`/`build_asset_price_series` with optional OHLC —
> additive only (new `ohlc_by_date` param, defaults None), zero impact on
> `lots_analysis_service.py`'s independent call site (confirmed it builds
> its own `price_rows` separately, never shares `portfolio_engine.py`'s
> internal `price_map`). CARRIED days always report `open=high=low=None`
> (no intraday variance known for a day nothing traded on) — only an exact
> MARKET day with a full DB-sourced triple carries OHLC; a partial triple
> is treated as no-OHLC, never guessed. Widened `ValuationResult`/
> `_market_value_for` with an opt-in `compute_ohlc` parameter (default
> False, per §4.1 "expensive OHLC work stays off ordinary reports" — the
> ordinary NAV/market-value hot path is unchanged unless a caller asks).
> New `PnlCandleContribution` dataclass, `DailyPortfolioState.pnl_candle`
> (populated only when `compute_candles=True` AND the day has no MISSING
> held-asset valuation — mirrors `nav_complete`, a genuine gap rather than
> a guessed candle). Negative/short positions need no special-case
> handling: they were already excluded from every valuation loop via the
> pre-existing `if qty <= 0: continue` guard reused verbatim, which is
> exactly the plan's required fail-closed behavior for the unsupported
> short state.
>
> **Found and fixed a cache-correctness bug before it could ship**: neither
> the engine's L1 blob-cache key nor the service's L2 report-cache key
> included the new candle flag — a request WITH candles could have
> silently reused a blob/report computed WITHOUT them (empty `pnl_candle`
> forever within the cache TTL). Added `include_candles`/
> `query.include_pnl_candles` to both keys.
>
> DTO/service: `PnlCandlePoint`/`PnlCandleSeries` (`hypothetical: true`
> always, at series-metadata level per §4.1's sketch — no per-point
> variant, no volume field), `include_pnl_candles` query flag (lazy —
> Dashboard only requests it on first candles-submode activation),
> `PortfolioService.get_pnl_candles()` mirroring `get_broker_pnl_history()`.
>
> Frontend: `pnlSubmode` (G1a-introduced state axis) now has a second real
> branch — `'candles'` renders total as an ECharts candlestick series
> (`[date, [open,close,low,high]]` for a `time` xAxis — confirmed via
> documentation, distinct from `CandlestickChart.svelte`'s category-axis
> flat-array convention) plus broker close-P&L lines reusing G1a's exact
> `brokerPnlHistory` data (no new broker-level computation, per §3.3's
> hybrid design). Weekly/monthly rollup reuses the existing
> `aggregateOHLCV` reducer unchanged (first-open/max-high/min-low/last-close
> — confirmed already implements the mandated "daily first, then roll up"
> contract). New `pnlCandles`/`onRequestPnlCandles` props: GrowthChart
> fires the callback once when the user activates the candles submode and
> data isn't loaded yet; Dashboard owns the actual lazy fetch
> (`loadPnlCandles()`, mirrors `loadContribution()`'s existing pattern) and
> resets `pnlCandles` to null on every ordinary `loadAll()` (invalidates a
> stale prior-scope series, consistent with how `positions_contribution`
> already behaves).
>
> **Found and fixed a second real bug during this same phase**: the
> existing `needsFullInit` full-x-axis-rebuild trigger compared only
> `lastRenderedMode !== viewMode` — switching `pnlSubmode` (line→candles)
> without changing `viewMode` (stays `'pnl'`) would have taken the
> partial-update path and tried to feed candlestick-shaped data into a
> still-`type:'line'` series. Fixed by tracking a combined
> `` `pnl:${pnlSubmode}` `` key instead of bare `viewMode`; updated the one
> source-contract test (`chartCoreHelpers.test.ts`) that asserted the old
> literal line.
>
> ⚠️ Two new user-facing strings are temporary hardcoded EN pending the
> coordinator's i18n batch (per the new no-direct-i18n-additions
> instruction) — listed in the G1b checkpoint message to the coordinator,
> not added via CLI this time.
>
> Gates: `services portfolio-engine` 42/42, `services roi-fifo-utils`
> 384/384 (pre test-author), `api portfolio` 24/24, ruff+black clean,
> svelte-check 0 errors, Vitest 4719/4719 (1 source-contract test updated
> for the needsFullInit fix), `front-portfolio dashboard` E2E 6/6, front
> build clean.
>
> test-author delivered: 7 new tests in `test_price_resolver.py` (resolver
> OHLC semantics — full triple, missing-day, entirely-omitted,
> CARRIED-never, TRADE_AVG-never, partial-triple×2) + 20 new tests in new
> `test_pnl_candles.py` (golden 2-day scenario, `compute_ohlc` default-off
> regression, foreign-FX OHLC conversion, MISSING-gates-the-day, stationary
> -day `is`-identity reuse, negative-qty guard reuse,
> `DerivedViewsBuilder.build_pnl_candles()` shape/gap, `PortfolioService`
> slicing, L1 blob-key + L2 report-key cache sensitivity). Zero
> discrepancies against the hand-verified golden numbers. Final:
> `services roi-fifo-utils` 419/419 (392 + 27 new), `services
> portfolio-engine` 42/42 unchanged, `api portfolio` 24/24 unchanged,
> ruff+black clean, no leftover DB rows.
>
> G1b considered complete and ready for phase-boundary report to the
> coordinator. G1c (signed personal income history) not started.

> **Note implementazione (G1c signed income + history, 2026-09-18):**
> coordinator accepted G1b and authorized G1c.
>
> **Signed-income foundation (plan §4.4), found 3 independent abs() bugs
> before they could regress further**: `portfolio_engine.py`'s 3-pool
> DIVIDEND/INTEREST accounting (both pre-frame and frame loops — `R[bid] +=
> amt`) always used `abs(tx.amount)`-derived conversions, so a legacy
> negative correction was silently counted as positive income instead of
> reducing the returns pool. `portfolio_service.py` independently repeats
> this same abs() pattern 3 more times: `get_summary()`'s `_income_accum`/
> `income_by_pos` (feeding `PortfolioSummary.period_income` and per-holding
> annualized return), and `get_positions_contribution()`'s own separate
> `per_income`/`unalloc_income` (feeding the Performance/Contribution tab).
> Fixed all by dropping abs() and computing a signed value from the
> already-fetched conversion (flip `amt`'s sign to match the original
> unabs'd `tx.amount` — `_convert`/FX lookup is sign-agnostic, so no second
> rate query needed). Also fixed 5 "positive-only" inclusion-check sites in
> `get_positions_contribution()` that would have silently DROPPED an
> income-only position/unallocated row entirely when its only value was a
> negative correction (`income <= 0` → `income == 0`, `income if income >
> 0 else None` → `income if income else None`, etc. — left every
> FEE/TAX-specific `> 0` check untouched, out of this plan's scope).
> Updated `PortfolioSummary.period_income`'s docstring (dropped the false
> "(positive)" promise). Deliberately did NOT merge these into one shared
> accumulator (plan's own suggestion) — kept each existing call site's
> control flow intact and fixed only the sign bug in place, per "Edit >
> Rewrite" and to minimize regression risk on 3 already-shipped surfaces;
> noted as an explicit engineering trade-off, not an oversight. Confirmed
> via a targeted grep that no existing test exercised a negative DIVIDEND/
> INTEREST amount anywhere in the suite before this change — this is a
> previously-untested gap being closed, not a regression of covered
> behavior (all pre-existing gates stayed green throughout).
>
> **New `get_income_history()`** (`portfolio_service.py`): a pure
> transaction scan (no `PortfolioCalculationEngine` run needed — income is
> a direct signed sum of committed rows, not a resolved valuation),
> grouping every scoped DIVIDEND/INTEREST transaction by `(date, type)`
> with the exact same signed-conversion + F2 role-share pattern as
> `get_summary()`'s fixed `_income_accum`, so `sum(dividend)+sum(interest)`
> reconciles to `PortfolioSummary.period_income` by construction for the
> same scope/window — not a residual check. Sparse series: only dates with
> real DIVIDEND/INTEREST activity are emitted (never a zero-filled daily
> series). A transaction whose FX conversion fails is excluded from the
> sums (never a silently-wrong zero) and its pair reported via
> `missing_fx_pairs`, reusing the existing data-quality contract instead of
> inventing a new per-point quality flag.
>
> DTO: `IncomeHistoryPoint`/`IncomeHistorySeries` (`points` +
> `missing_fx_pairs`), `include_income_history` query flag — eager caller
> policy per §4.1 ("Dashboard/Broker overview true"), added to the L2
> report-cache key (same class of correctness fix as G1a/G1b's cache-key
> additions, applied proactively this time).
>
> Frontend: new `aggregateSumSeries()` reducer in `timeSeriesAggregation.ts`
> per plan §5.2 — sums every day in a weekly/monthly bucket instead of
> end-of-period/last-value semantics (distinct from `aggregateLineSeries`
> and `aggregateOHLCV`), since a flow value has no "current balance" to
> read at a bucket's end. `GrowthChart`'s `pnlSubmode` gained its third and
> final real branch — `'income'` renders DIVIDEND/INTEREST as distinct-
> color stacked bars (no broker overlay for this submode — that hybrid
> rule is specific to Line/Candles per §3.3, not extended to Income),
> tooltip shows both signed values plus their total. `income_history` is
> wired eagerly (not lazy like `pnlCandles`) into both Dashboard's
> `loadAll()` and the broker-detail page's `loadOverview()` — the plan's
> only G1a/b/c feature requiring a broker-detail-page code change, since
> its caller policy explicitly names "Broker overview" as a direct
> consumer (unlike G1a/G1b's broker-detail scope, which needed zero
> changes there).
>
> Reused three already-existing i18n keys with zero new additions this
> round: `transactions.types.DIVIDEND`/`.INTEREST` (dynamic-prefix
> protected but safe to reference statically) for the bar labels, and
> `assets.distribution.total` for the tooltip's combined-total row.
>
> Gates: `services portfolio-engine` 42/42, `services roi-fifo-utils`
> 419/419 (pre test-author), `api portfolio` 24/24, ruff+black clean,
> svelte-check 0 errors, Vitest 4719/4719, front build clean,
> `front-portfolio dashboard` E2E 6/6.
>
> test-author delivered 20 new tests: `test_signed_income.py` (new, 9 —
> engine-level, no DB) + `test_portfolio_service.py` (extended, +10 —
> `get_income_history`/`get_summary`/`get_positions_contribution`
> reconciliation) + `test_portfolio_api.py` (extended, +1 — report endpoint
> with `include_income_history`). Golden scenario confirmed exactly (35
> reconciles identically across all three surfaces); DEPOSIT+INTEREST(-50)
> engine scenario confirmed exactly (total_pnl=-50). Final (independently
> re-confirmed): `services roi-fifo-utils` 437/437, `services
> portfolio-engine` 42/42 unchanged, `api portfolio` 25/25. Ruff+black clean.
>
> **One real discrepancy found and reported precisely, not silently
> adjusted**: my "same-day correction before a BUY draws less from R"
> hypothesis does not hold literally — the unified per-day loop processes
> transactions in a fixed bucket order (additions/BUY → reductions/SELL →
> everything else, including DIVIDEND/INTEREST/DEPOSIT/WITHDRAWAL/FEE/TAX),
> regardless of same-day chronological intent; this is pre-existing
> architecture, unrelated to G1c, independently corroborated by the
> existing `test_buy_consumes_returns_first`. test-author kept both a
> cross-day test that unambiguously proves the intended signed-correction
> mechanism (verified via raw `capital_pool`/`returns_pool`, not the
> cosmetic display: a 60-unit swing) and a same-day test that locks in the
> actual (different from my assumption) bucket-ordering behavior — no
> change needed to `portfolio_engine.py` itself, my mental model of
> same-day ordering was simply wrong when I wrote the test-author brief.
>
> Also surfaced during test-author's parallel-safety diligence (`services
> --workers 4 all` / `api --workers 4 all`, not requested but run anyway):
> a load-sensitive failure in `test_assets_crud.py`, unrelated to
> income/portfolio, passing in isolation — correctly left untouched
> (outside this task's file boundary, and stashing to bisect would have
> risked ~26 other uncommitted files from concurrent G1a/b/c work).
>
> G1c considered complete. This closes the full G1a/G1b/G1c GrowthChart
> P&L feature (Value/Return% × [P&L: Line/Candles/Income]) as authorized.
> Ready for phase-boundary report to the coordinator.

### 6.0.1 Live-review round 2 — batch 1 (candles fix + Line-submode polish, 2026-09-18)

> **Note implementazione (data-richness enrichment, 2026-09-18):** before
> this round's manual review could proceed, the developer's lane DB
> (`/tmp/librefolio-r2-i-charts`) needed richer fixture data. Ran the
> standard `db populate --force` (server stopped first for safety) — this
> alone raised `price_history` from 7 rows (0 with full OHLC) to 1549 rows
> (1549 with full OHLC, spanning ~1yr) and gave `e2e_test_user` 2 owned
> brokers natively (no manual grant needed this time). DIVIDEND/INTEREST
> remained sparse (3 total points) — a genuine mock-fixture limitation, not
> fabricated further per the developer's own "not something to hand-invent"
> caveat. Developer then asked for more income data specifically: added 13
> new DIVIDEND/INTEREST transactions via a throwaway script mirroring
> `populate_mock_data.py`'s own `Transaction(...)` + `session.add()` +
> `session.commit()` ORM pattern (not raw SQL), spanning March-September
> 2026 across 4 brokers, including one deliberate negative "correction"
> (-15 USD) to visually confirm G1c's signed-bar behavior. Result: 16 income
> points, confirmed via live `/portfolio/report` API — no code/test touched
> for either step, both were pure data-fixture operations.

> **Note implementazione (#4 candlestick rendering fix, 2026-09-18):**
> developer reported the "Candles" submode showed only the broker overlay
> lines, no candle bodies. Root-caused via an isolated pixel-sampled ECharts
> test (same v6.0 bundle): candlestick series silently fails to paint any
> body/wick when `xAxis.type==='time'` — a known upstream ECharts
> limitation, not a data bug (the G1b OHLC composition itself was already
> independently verified correct). Developer confirmed fix strategy after
> I traced the codebase's own Asset Detail price chart
> (`PriceChartFull.svelte`/`CandlestickChart.svelte`) already solving this
> via a `category` axis, and found `GrowthChart`'s own `buildZoomWindow` is
> already index/percentage-based (same shape as `PriceChartFull`'s
> `computeZoomWindow`) — meaning the shared zoom pipeline needed zero
> changes to support a submode-conditional axis type. Implemented: `xAxis`
> becomes `{type:'category', data: activeChartData?.dates ?? dates}` only
> for `pnlSubmode==='candles'` (in `applyFullOption`, `updateChartData` —
> which must also refresh `xAxis.data` on every resolution-switch, not just
> when `compact` toggles like the time-axis branch — and the resize
> watcher, which stayed deliberately unforked since `splitNumber` is a
> time/value/log-axis-only concept ECharts ignores on category axes).
> Candle/broker-overlay data reformatted to flat/positional (not
> `[date,value]` pairs), matching the category-axis convention. Per
> explicit developer instruction ("generalizza e riusa il componente"),
> extracted a new shared `buildOhlcQuad()` in `candlestickChartHelpers.ts`
> out of the existing `buildCandleSeriesData` (behavior-preserving
> refactor for its existing caller) instead of re-deriving the
> easy-to-get-backwards `[open,close,low,high]` ordering convention
> independently. Visually confirmed via a throwaway Playwright script
> (screenshot diff Line vs Candles): 3035/219240 pixels differ, with exact
> green `#16a34a`/red `#dc2626` candle-body pixels present in Candles mode
> that weren't there before — a manual pixel-read attempt via the chat's
> own browser-canvas tool gave a false "no change" signal first (confirmed
> as a tooling artifact via a control test on the untouched Abs/% toggle,
> not a real regression) before the Playwright script gave a reliable
> answer.

> **Note implementazione (#1/#2/#3 Line-submode polish, 2026-09-18):**
> three additional developer asks, all confined to `GrowthChart.svelte`
> (this sprint's exclusively-owned surface), no backend/shared-file touch:
> (1) the Line/Candles/Income submode toggle now floats as an absolute
> overlay (`top-2 right-2 z-10`, semi-transparent, `opacity-75
> hover:opacity-100`) inside the chart's own `.relative` wrapper instead of
> its own row — matching `PriceChartFull.svelte`'s edit/settings-controls
> pattern exactly, so it no longer shrinks the chart area; (2) the Total
> P&L line in `pnlSubmode==='line'` now shows a signed green/red area fill
> — implemented as a **fixed 2-slot positive/negative split**
> (`clipToSign`, null-clip the wrong-sign half of each point) rather than a
> variable number of sign-crossing segments, specifically so
> `updateChartData`'s partial by-index series merge stays valid across
> zoom/pan (a variable segment count would desync that merge, since the
> number of sign-crossings in the visible window changes on every
> zoom/pan). Deliberately did NOT use ECharts' `visualMap` piecewise (the
> "obvious" approach) — empirically verified via an isolated test that it
> does not reliably recolor a line series' `lineStyle`/`areaStyle` per
> value, a documented upstream limitation (apache/echarts#8034); (3) a
> dashed gray reference line at the first-visible-day P&L value — a 3rd
> fixed series slot (flat line, `silent:true`, `tooltip:{show:false}`),
> deliberately NOT `markLine`, to avoid a documented ECharts crash where
> `markLine` + `visualMap` (piecewise, dimension:1, tuple data) throws
> "Cannot read properties of undefined (reading 'coord')" — same precedent
> already used by `LineChart.svelte`'s own `useBaselineColoring`/
> `__baseline__` flat-line series. The reference value is recomputed on
> every resolution-switching zoom/pan or full re-render (threaded via a new
> `referenceDate` parameter through `buildChartUpdateSeries`/
> `updateChartData`), but not on every pixel of a continuous in-place drag
> that stays within the same resolution bucket — a deliberate,
> documented scope limit (`syncResolutionToViewport` already returns early
> in that case for unrelated reasons).
>
> Gates: svelte-check 0 errors, Vitest 4759/4759 (4719 + 40 from
> test-author), Prettier clean, front build clean. test-author extended
> `candlestickChartHelpers.test.ts` (+6: `buildOhlcQuad` ordering/
> percentage-transform + `buildCandleSeriesData` delegation-consistency)
> and `chartCoreHelpers.test.ts` (+34: category/time xAxis completeness
> across all 3 sites, candles-submode positional alignment via a
> deliberately-offset dual-gap fixture, the line-submode fixed-3-slot
> invariant across 6 sign-crossing shapes, and the resize-watcher's
> "stays unforked" claim traced into `buildResponsiveXAxisPolicy` itself).
> No defect found in the 4 fixes; incidentally flagged (out of scope, left
> untouched): `aggregateSumSeries`/the Income submode's own branches have
> zero test coverage anywhere in the codebase, pre-existing gap.
>
> Batch 1 complete. Proceeding to batch 2 (full income package: window
> selectors + costs/deposit/acquisition-size aggregates + new-vs-reinvested
> liquidity split) as its own phase per developer/coordinator sequencing.

### 6.0.2 Crypto icon fix — Asset Allocation history chart (2026-09-18)

> **Note implementazione (crypto icon, 2026-09-18):** developer reported the
> Crypto category's icon invisible in the Asset Allocation history chart, unlike
> Liquidity/Stock. Root-caused via a throwaway Playwright zoomed screenshot
> (deviceScaleFactor 3, hover-triggered to reproduce the exact reported state):
> `AllocationHistoryChart.svelte`'s `getCategoryEmoji()` used `'₿'` (Bitcoin
> currency sign, U+20BF) — **not a real emoji**, unlike every other category.
> It has no color-emoji font coverage, so it renders as a thin pale gray
> system-font glyph, nearly invisible against the chart's light area fill.
> Both of the developer's hypotheses were partially right: primarily a
> "not an emoji" font-rendering issue, secondarily compounded by sitting in
> the thinnest topmost band. Fixed by swapping to `'🪙'` (coin, a genuine color
> emoji) — the only `₿` occurrence anywhere in the frontend (grepped). Re-verified
> visually with the same zoom+hover technique: now bold, gold, clearly visible,
> matching the other categories' visual weight. Gates: svelte-check 0 errors,
> Vitest 4759/4759 unchanged (no test referenced the old glyph), Prettier clean.

> **⚠️ Fuori pista (lane DB wipe discovered, 2026-09-18):** running the backend
> pytest categories for the checkpoint's fresh evidence **wiped this lane's
> manually-populated review DB back to empty** (0 users/brokers/prices) — those
> suites reset the shared test DB as part of their own fixture setup, not
> expecting a hand-populated "for manual review" state to persist alongside them.
> Had to re-run `db populate --force` before the investigation could even start.
> Durable lesson recorded for every future manual-review session on any lane:
> **backend pytest on a lane's data-dir always resets it**, so manual review data
> must be treated as ephemeral across test runs, not just across server restarts.

### 6.0.3 Batch 2 — income package (2026-09-18)

> **Note implementazione (batch 2 backend, 2026-09-18):** developer authorized the
> full package verbatim ("autorizzo a procedere con i prossimi task, la mia review
> parte quando la ui sarà pronta e sarà sia estetica che funzionale"), no per-item
> sign-off. Implemented four new backend aggregates for the Income submode:
>
> - `get_cost_history()` (FEE+TAX summed into one signed figure per date,
>   preserving the raw negative sign rather than flipping to a positive
>   magnitude — same signed-fidelity policy as G1c's income), `get_deposit_history()`
>   (DEPOSIT), both pure transaction scans like `get_income_history`.
> - Extracted `_signed_transaction_sums_by_date()` out of the original
>   `get_income_history` as a shared, behavior-preserving helper for all three —
>   same (date_from, date_to] boundary, same F2 OWNER-share scaling, same
>   FX-missing exclusion/reporting contract. This is the one method that was
>   *refactored* rather than merely extended, so its unchanged behavior is an
>   explicit test-author verification target.
> - `get_acquisition_funding_history()` — unlike the three scans above, this
>   **requires an engine run**: the new-vs-reinvested split depends on K/R pool
>   state accumulated over the entire prior history, not the day's transactions in
>   isolation. Mirrors `get_pnl_candles()`'s dual-mode
>   (`_precomputed_engine_result` vs standalone) exactly.
> - `portfolio_engine.py`: new `AcquisitionFundingContribution` dataclass +
>   `DailyPortfolioState.acquisition_funding` + `compute_acquisition_funding`
>   opt-in + `build_acquisition_funding()` derived view. The actual capture is
>   **two additive lines at the existing frame-loop BUY mutation site**: the engine
>   ALREADY computes `from_r`/`from_k` for every BUY to update the 3-pool
>   balances — batch 2 only stops discarding them. Per the coordinator's explicit
>   instruction this surfaces an existing validated computation and does **not**
>   invent a new reinvestment model. `from_new_capital + from_reinvested`
>   reproduces that day's total BUY outflow by construction, never a residual.
> - Deliberate asymmetry vs `pnl_candle` on stationary days: a candle carries
>   forward (`pnl_candle=prev.pnl_candle`), acquisition funding does **not**
>   (`acquisition_funding=None`) — a stationary day has zero transactions so can
>   never have a BUY, whereas a candle legitimately stays flat.
> - Both cache layers updated proactively: `include_acquisition_funding` in the L1
>   blob key, all three new flags in the L2 report key. (This exact
>   cache-key-omission bug class was caught twice before in this file's history
>   during G1b — fixed pre-emptively this time rather than found later.)
> - Pre-frame BUY branch deliberately untouched: pre-frame days emit no
>   `DailyPortfolioState`, so there is nothing to attach output to; those BUYs
>   still correctly feed the pool state that seeds the frame.
>
> All hunks kept narrow and additive at existing mutation sites, with zero
> restructuring or reformatting of surrounding code, per the standing
> shared-file rule (`portfolio_engine.py`/`portfolio_service.py` are shared with
> the concurrent Risk-management effort; developer accepted resolving at merge).
>
> Gates: `services portfolio-engine` 42/42, `services roi-fifo-utils` 437/437,
> `api portfolio` 25/25, ruff clean, black clean.

> **Note implementazione (batch 2 frontend, 2026-09-18):** `GrowthChart.svelte`
> Income submode grew from a fixed 2-slot series array (dividend/interest) to a
> fixed 6-slot one — `[dividend, interest, costs, deposit, acqNewCapital,
> acqReinvested]` — with both `buildChartUpdateSeries` and `buildFullSeries`
> agreeing on that exact index order (a mismatch would silently swap two bars'
> data, so it is an explicit test target). dividend+interest keep their existing
> `stack:'income'`; costs and deposit are standalone bars; acquisition is a 2-zone
> `stack:'acquisition'` bar **reusing EUR mode's own `cashContributed`/
> `cashGenerated` colors** — the same underlying K/R-pool concept, so the same
> color means the same thing across the app rather than introducing a fifth
> palette entry for an idea already represented.
>
> New dimensions reuse the existing, unmodified `aggregateFlowMetric()` (sum
> semantics — correct for sparse economic flows, unlike the line-mode
> last-value-in-bucket reducer).
>
> Window selector (1W/1M/1Y/All) implemented as a floating overlay below the
> submode toggle, Income-only. **Not a parallel windowing system**: a preset just
> sets the same `visibleStartDate`/`visibleEndDate` + `buildZoomWindow()`-derived
> `dataZoom` percentages that a manual drag/scroll zoom already sets — so a window
> picked in Income survives a submode switch, and manual zoom still works
> normally on top of it.
>
> Tooltip gained a conditional second section for the three new dimensions, shown
> only when at least one of those values is non-zero for that date, so a
> pure-income day still shows exactly the original dividend/interest/total block
> with no empty trailing rows.
>
> i18n: **zero new keys added by me.** Costs reuses the existing
> `dashboard.feesAndTaxes` (the dashboard KPI's own "Fees & taxes" grouping),
> deposit reuses existing `transactions.types.DEPOSIT`. Only two genuinely-new
> strings are needed — proposed `dashboard.pnlAcqNewCapital` = "New capital" and
> `dashboard.pnlAcqReinvested` = "Reinvested" — left as hardcoded EN with
> `TODO(coordinator i18n batch)` markers and reported to the coordinator, per the
> standing "locale files are coordinator-owned this sprint" rule.
>
> Gates: svelte-check 0 errors, Vitest 4759/4759, Prettier clean, front build
> clean. Live visual verification via a throwaway Playwright script (not
> committed, cleaned up): window selectors render/switch, all six legend entries
> present, bars draw, tooltip shows the new rows.
>
> **Disclosed scope limitation:** "Custom" window preset NOT implemented —
> 1W/1M/1Y/All only. The dashboard's own global Custom range picker remains a
> partial substitute. Flagged rather than silently dropped.

> **⚠️ Fuori pista (i18n keys added but never wired, 2026-09-18):** while handing
> the two new batch-2 keys to the coordinator, the coordinator discovered that the
> **five batch-1 keys were already committed in all four locales but never
> consumed** — `GrowthChart.svelte` still hardcoded all five in English behind
> `TODO(coordinator i18n batch)` markers. Net effect shipped in `8ed7a0f0d`:
> IT/FR/ES users saw English submode buttons and English candle-disclosure text.
> Root cause is a process gap, not a coding mistake: the sprint's i18n split
> (coordinator owns locale files, workstream owns the components) leaves a seam
> where "keys added" and "keys used" are two different actions, and **nothing
> automated closes it** — `svelte-check`, Vitest and the production build are all
> green with a hardcoded literal sitting where a `$_()` call belongs.
>
> Second, sharper trap found while fixing it: the TODO comment itself pointed at
> the **wrong key**. The comment said `replace with $_('dashboard.pnlCandlesHypothetical')`
> while the string on the next line was the *short* variant belonging to
> `pnlCandlesHypotheticalShort`. Following one's own past TODO literally would
> have swapped the long and short disclosure forms — the compact tooltip footnote
> getting the full sentence and the always-visible caption getting the truncated
> one. Substitution was therefore done by **comparing each literal against the JSON
> value**, not by trusting the marker.
>
> Durable lesson: `grep -n "TODO(coordinator i18n batch)"` (or the equivalent
> marker) belongs in the definition of done for any i18n batch, on both sides of
> the seam — the person adding keys and the person consuming them can each be
> green in isolation while the user-visible result is still wrong.

> **⚠️ Fuori pista (acquisition-funding date boundary was a latent bug, 2026-09-18):**
> test-author flagged that `get_acquisition_funding_history` sliced `>= date_from`
> (inclusive) while its five co-rendered Income-submode siblings
> (income/cost/deposit) use the canonical exclusive `(date_from, date_to]`, and
> asked whether the divergence was deliberate. **It was not.** Analysis: the two
> engine-backed methods it was modelled on — `get_pnl_candles` and
> `get_broker_pnl_history` — are **LEVEL** series (a cumulative value per day), so
> the period's opening day legitimately must appear as the baseline. Acquisition
> funding is a **FLOW** series (that day's own BUY split), so under the canonical
> convention a BUY dated exactly on `date_from` belongs to the *previous* period.
> It had inherited a level-series slicing rule purely because it shares the
> engine-backed *mechanism* — which is not the same thing as sharing the
> *semantics*. User-visible symptom: in the Income submode all six series render
> as bars on one x-axis, so a BUY on `date_from` drew a bar while a DIVIDEND on
> that same date drew none. Fixed to `> date_from`, with a comment recording why
> it deliberately diverges from the precedent it otherwise mirrors. Three
> test-author tests that had pinned the old behaviour were handed back for update,
> plus a request for a stronger *cross-series* invariant test (a flow dated on
> `date_from` must be absent from all four flow series alike) — that property is
> what actually protects the chart, stronger than each series' own boundary test.
>
> Lesson: "engine-backed" and "level series" travelled together in every prior
> example, so copying the nearest precedent silently copied a semantic that did
> not apply. When reusing a mechanism, the question to ask is which of the
> source's properties are incidental to the mechanism and which are load-bearing.

> **⚠️ Fuori pista (AcquisitionFundingSeries has no missing_fx_pairs — pre-existing
> engine gap, documented not patched, 2026-09-18):** test-author also flagged that
> this series, unlike income/cost/deposit, carries no `missing_fx_pairs` channel,
> so a BUY in a currency with no FX route that day vanishes with no data-quality
> signal. Investigated: the engine's pre-existing `amount_target is None ->
> continue` guard skips such a transaction *before* it reaches the funding split,
> and the engine's own `missing_fx_pairs` set is populated only from **valuation**
> paths (`_market_value_for`, `_compute_in_transit`,
> `_compute_open_cost_basis_inline`) — never from transaction-amount conversion
> failures. So the gap is pre-existing engine behaviour that equally affects the
> 3-pool/cash-decomposition accounting, not something batch 2 introduced, and
> `PnlCandleSeries` shipped with the identical omission.
>
> Deliberately **not** patched here: closing it properly means giving the engine a
> transaction-level FX-failure output channel — a genuine contract change to a
> file shared with the concurrent Risk-management effort, which the standing rule
> says to keep narrow and additive. Instead the schema docstring was made honest
> so the contract stops implying a completeness it does not have, the behaviour is
> locked by test-author's `test_buy_with_an_unconvertible_currency_is_skipped_not_zeroed`,
> and the finding is reported upward as a candidate for its own scoped work.

> **Note implementazione (batch 2 test coverage + i18n wiring, 2026-09-18):**
> test-author delivered **+58 backend** (`services roi-fifo-utils` 437 → 495, every
> pre-existing test passing verbatim — the `get_income_history` refactor gate) and
> **+67 frontend** (124 → 191 across the two files it touched; full suite 4759 →
> 4826). New file `test_acquisition_funding.py` (40 tests) plus extensions to
> `test_portfolio_service.py`, `chartCoreHelpers.test.ts` and
> `__tests__/timeSeriesAggregation.test.ts`. Four test files, zero non-test files.
>
> The `aggregateSumSeries`/Income coverage gap flagged at the batch-1 close is now
> genuinely closed: 10 dedicated direct tests for the reducer (including an
> explicit contrast against `aggregateLineSeries`, mass preservation and a
> cross-year ISO-week bucket), and the Income submode went from *one* incidental
> string match to full-pipeline coverage — sparse alignment → `aggregateFlowMetric`
> → 6-slot series → tooltip → window selector.
>
> All 7 i18n keys wired in `GrowthChart.svelte` and all 4 `TODO(coordinator i18n
> batch)` markers deleted (verified `grep -c` = 0; each key referenced exactly
> once). Edits were made at the 7 exact sites rather than by find-and-replace:
> test-author measured that the bare substrings `Line`/`Candles`/`Income`/
> `Reinvested` occur 27/33/20/15 times in the file, almost all inside legitimate
> identifiers (`aggregateLineSeries`, `LineDataPoint`, `incomeHistory`,
> `acqFromReinvestedValues`, `from_reinvested`…), so a blanket replace would have
> corrupted the file.
>
> Two test-authoring details worth keeping, both self-reported near-misses rather
> than successes: (1) the i18n sweep's first regex `$_('key')` silently skipped
> the three *interpolated* call sites (37 of 40), so a future interpolated key
> would have slipped through — widened and backed by a guard test asserting every
> `$_(` call uses a static literal, so the sweep cannot quietly stop being
> exhaustive; (2) the SHORT/LONG disclosure assertions match on the **full call
> including the closing quote**, because `pnlCandlesHypothetical` is a strict
> prefix of `pnlCandlesHypotheticalShort` — a bare `toContain` would be satisfied
> by the wrong key and prove nothing. Both guards were verified non-decorative by
> replaying them against in-memory mutated copies (typo'd key, transposed
> SHORT/LONG, re-hardcoded literal, un-wired key — all four caught).
>
> The LEVEL-vs-FLOW divergence is now executable rather than a comment:
> `test_diverges_from_get_pnl_candles_on_the_same_engine_result_and_window` feeds
> one engine result and one window to both methods and asserts the level series
> keeps its `date_from` day while the flow series drops it — so any future
> "harmonisation" in either direction turns exactly one assertion red and names
> which contract broke. The requested cross-series invariant landed as
> `TestIncomeSubmodeFlowSeriesShareOneBoundary`, opening with a positive control
> (widen `date_from` by one day, all four series must show both days) so that
> "absent" cannot silently mean "this series never had anything there".
>
> Final combined gates: `services roi-fifo-utils` 495/495, `services
> portfolio-engine` 42/42, `api portfolio` 25/25, ruff clean, black clean,
> svelte-check 0 errors, Vitest 4826/4826, Prettier clean, front build clean.

### 6.0.4 Post-review crash fix — candles on a category axis (2026-09-18)

> **⚠️ Fuori pista (batch 2 shipped broken; one `null` killed the whole chart, 2026-09-18):**
> batch 2 was committed as `d5e834de4` and the developer's review found the Growth
> chart dead: no candles, ~22 console errors on mouse-move, and an apparent freeze
> where changing the date range repainted nothing. Three symptoms, **one cause**.
>
> `toCandlestickPoint` returned `null` for a gap bucket. On a **category** base axis
> the candlestick series clones its data through
> `whiskerBoxCommon.getInitialData`, which branches
> `isArray(item) → … else if (isArray(item.value))` — so a `null` item dereferences
> `null.value` and throws **inside `SeriesModel.init`**, before `GlobalModel`
> finishes building. With no `_seriesIndices`, every subsequent `setOption`
> silently no-ops: the data layer kept fetching correctly (the report POST fired on
> every range change) but nothing could repaint, so the canvas kept showing the
> *previous* submode's paint. That is why "Candles" was selected while a line with
> an area fill was on screen — not a rendering bug, a dead model.
>
> Fixed by returning ECharts' documented empty-value sentinel `'-'` instead. The gap
> must still **occupy its slot**: a category axis aligns by position, so omitting
> gap points would desync every later candle. Verified against this exact echarts
> build rather than inferred — `null` throws
> `Cannot read properties of null (reading 'value')`, `'-'` renders. Both other
> symptoms disappeared with that one line; no separate work was needed for either.
>
> **A second-order concern was raised and disproved.** The same ECharts loop does
> `item.unshift(index)` with the comment "Modify current using data", which reads
> like it mutates caller-owned arrays — dangerous for a design that reuses series
> data across partial updates. Probed three ways (full `setOption`, then partial
> `setOption` twice with `updateChartData`'s exact
> `{notMerge:false, replaceMerge:['dataZoom']}`): the array came back untouched
> every time. ECharts deep-clones the incoming option *before* that loop, so the
> mutation hits its own clone. Recorded so nobody spends a cycle defending against
> a hazard that the public API already closes.
>
> **Root-cause lesson: the test suite could not have caught this.** Every guard was
> a source-contract/reimplementation test — they pin what the code *says*, and the
> crash only exists when real ECharts initialises the series. The suite was green,
> svelte-check was green, the production build was green, and the feature was
> dead on arrival. Closed by a new SSR regression guard (see below): the class of
> defect that reaches a developer is the one no layer of the pyramid was watching.

> **Note implementazione (legend sentinel + layout swap, 2026-09-18):** two further
> review findings fixed in the same pass.
>
> `legend` set no `data`, so ECharts derived entries from *every* series name and
> the internal `__pnlReference__` decoration leaked into the UI. Rather than
> hand-listing the real names (a second place that must remember the magic string),
> the sentinel became a single module-level `PNL_REFERENCE_SERIES_NAME` constant
> referenced at both construction sites, and `legend.data` is now **derived** from
> the series array with that constant filtered out — so a future series is included
> automatically and only genuine non-data decorations opt out. The `Set` dedupe is
> deliberate: the positive/negative halves deliberately share `pnlLabels.total` and
> must collapse to ONE "Total P&L" entry that toggles both halves.
>
> Layout swapped per the developer: submode toggle to the **left**, window selector
> into the vacated **top-right**. Measured, not eyeballed (chart midpoint 606,
> toggle x=306, window x=760). The move collided with `ResolutionBadge`'s former
> solo top-left slot; reconciled by reusing `PriceChartFull`'s own established
> pattern — its controls and the badge already share one left-aligned flex row with
> the badge last — rather than inventing a placement or displacing the badge
> silently. Note for future screenshots: `ResolutionBadge` self-hides at `daily`
> resolution (pre-existing), so its absence is not a regression.

> **Note implementazione (regression guard for the crash class, 2026-09-18):**
> test-author re-pinned the 2 source-contract tests that correctly went red on the
> deliberate literal changes, found **2 further knock-ons** coupled to the same
> literals, and — asked whether a real guard was feasible — built one: **+6 tests**
> driving a headless `echarts.init(null, null, {renderer:'svg', ssr:true})` with a
> gap-containing candlestick on a category axis.
>
> Three details worth keeping. (1) `renderer:'svg'` is **load-bearing**: the canvas
> painter dereferences the null root and dies inside zrender, so the choice is not
> incidental. (2) The control asserts the *consequence*, not merely the throw —
> probing found that on a crashed instance `chart.getOption().series` is `[]`, a
> public, type-legal measurement of the dead-model diagnosis, with the green path
> asserting the exact inverse (2 series, addressable via
> `convertToPixel({seriesIndex: 0})`). That pins the whole
> "throw → dead model → silent no-op → apparent freeze" chain rather than its first
> link. (3) test-author closed its own loop: the guard exercises the
> *reimplementation*, so it would still pass if the real source regressed — so a
> further test asserts the fixture's sentinel is literally the one the component
> declares. Verified by simulation: revert-to-null caught, sentinel changed to `''`
> caught twice, constant removed caught.
>
> Also pinned deliberately: the candlestick gap is `'-'` while the broker-overlay
> line gap stays `null` — these differ **on purpose** (different series types), and
> the test says so, because it reads like an inconsistency someone would otherwise
> "tidy" into one.
>
> Final gates: Vitest **4832/4832**, svelte-check 0 errors, Prettier clean, front
> build clean. Backend untouched this round (495/495 from the previous round still
> current). Browser-verified on the live lane: **181 green + 1331 red** candle-body
> pixels, **zero** console errors, canvas signature **changes** on range change
> (repaint live), legend reads `Total P&L · Interactive Brokers · Coinbase`.

### 6.0.5 Post-review UI pass + the invisible-candle finding (2026-09-18)

> **⚠️ Fuori pista (candles were painting all along; the defect was data shape, 2026-09-18):**
> after the crash fix shipped, the developer re-reviewed and still saw no candles. I had
> reported "181 green + 1331 red body pixels". Both were true, and reconciling them
> produced the most useful finding of the round.
>
> **My measurement was unsound.** It counted coloured pixels anywhere on the canvas and
> inferred "candles are visible" from the count being non-zero. Those pixels were real,
> but the metric could not distinguish *candle bodies painted* from *something coloured
> exists*. Worse: the same run captured a candles-mode screenshot that I never opened —
> I opened the Line-mode one, saw it healthy, and deleted both. The decisive artefact was
> on disk the whole time.
>
> Re-measured by column profile: **102 colour-bearing columns for 93 points, tallest
> vertical run 11px on a 360px plot**. The candles were drawn from the start and were too
> small to see. Console silent in candles submode throughout, so the series initialised
> cleanly — the crash fix was genuinely complete.
>
> Root cause, correlation exact: **310 of 354 candles were flat because the portfolio held
> no assets before 2026-07-30**, the date of the first BUY. A synthetic candle composes
> from held assets' OHLC; with nothing held, `{o,h,l} = offset = close` and a flat candle
> is the *correct* output. The 44 non-flat ones ran 2026-07-30 → 2026-09-18 exactly.
> `price_history` was sound (1547/1549 rows with `high > low`) — and my earlier "1549/1549
> with full OHLC" check had verified the columns were *present*, never that they *varied*.
>
> Not the caller, not the null, not the renderer. Lane data was enriched with a plain
> monthly accumulation (Oct-2025 → Jun-2026, quantities fixed, amounts computed from real
> closing prices, funded by deposits that had sat idle): holdings **51 → 338 days**, flat
> candles **310/354 → 15/354**, 3M window **0 flat**. Deliberately *not* tuned until the
> chart looked good — the full-range median candle is still **1.75%** of the true rendered
> y-span, and that thinness is the evidence that motivates the width ladder.
>
> **`yAxis: {scale: true}` was considered and rejected on verified grounds**: `scale:`
> appears nowhere in this component, so the axis includes zero by default, and zero is
> load-bearing — the P&L series fills green above it and red below, plus a dashed
> reference line. Removing zero from frame would make the chart misstate the sign of the
> user's P&L: a semantic change wearing a display tweak's costume. The thin-candle problem
> belongs to the ladder instead, because OHLC aggregation takes `max(high)`/`min(low)`
> across merged buckets, so candle range is monotonically non-decreasing in bucket width —
> the body grows while the axis span stays put. That is arithmetic, not hope.

> **⚠️ Fuori pista (the replacement metric was also unsound, 2026-09-18):** the column
> profile that corrected the pixel sum then under-reported in turn — median run 3px against
> an API-derived expectation of ~13px — because it mis-measures thin, bordered, ~5px-wide
> strokes broken by wick geometry. Relaxing the saturation threshold moved coloured columns
> 322 → 445 and left the runs unchanged, so anti-aliasing alone did not explain it.
>
> The durable guard is therefore **not** "use column profile instead of pixel sum". It is:
> **any proxy must be calibrated against ground truth before it can carry a verdict.** The
> criterion adopted for the ladder is the *ratio of median candle range to the true
> rendered y-span, computed from the API*, with the screenshot as confirming artefact —
> no canvas-derived number is allowed to carry a verdict.
>
> Related correction on the same numbers: the first ratio cited used the **close-span**
> (5889) as denominator rather than the true rendered span (6686), which also includes the
> broker-overlay extremes and the 8% `yAxis.min` pad. Right instrument, wrong baseline.
> And the *largest* candle was the flattering statistic all along — one outlier day says
> nothing about a year; the **median** is what characterises the defect.

> **Note implementazione (three UI items, 2026-09-18):**
>
> 1. **Overlay/axis overlap.** The submode toggle was drawn over the y-axis "600" label.
>    Fixed by reserving a band in `grid.top` (44px in P&L mode, 10px elsewhere) rather than
>    nudging the overlay: the plot then gives away exactly the space it yields instead of
>    silently drawing content underneath a control, which keeps it honest at small heights.
>    Measured: toggle bottom 33px from chart top at desktop, 31px at mobile — both inside
>    the band.
> 2. **Icons.** `ChartLine` / `ChartCandlestick` / `Coins` from `lucide-svelte`; the first
>    two deliberately match `PriceChartFull`'s existing choices so the same concept reads
>    the same across the app.
> 3. **Mobile fold.** Below `sm` the labels hide and only icons remain. Verified at **both**
>    breakpoints rather than assumed from the class name: 1400px icon + label, 420px icon
>    only. `data-testid` is **identical** in both states — a testid that changed with
>    viewport would make every E2E selector viewport-dependent — and the label survives as
>    `title` + `aria-label` in both, so the control stays usable with a screen reader
>    exactly where it is hardest to use. Added `aria-pressed` unprompted: a segmented
>    toggle without it announces three buttons and no state, which is worst on mobile where
>    the icon is the only remaining affordance.
>
> **Evidence that the testid-stability rule earns its keep:** this was a full markup
> rewrite of all three buttons — element structure, classes, children, added attributes —
> and test-author's contract tests passed **162/162 untouched**, because they assert
> `data-testid` and `onclick` handlers rather than markup. A constraint people usually find
> annoying paid for itself in a single pass.
>
> Gates: svelte-check 0 errors, `chartCoreHelpers` 162/162, Prettier clean, front build
> clean, zero console errors at both viewports.

> **⚠️ Fuori pista (the `grid.top` fix was rejected — the brief, not the patch, was wrong,
> 2026-09-18):** reserving a 44px band pushed the plot down, and the developer had asked
> for the control to stop sitting on the y-axis *numbers* while still floating over the
> plot — horizontal room, not vertical. The request reached me as "padding" plus the
> symptom, with the axis never named, so the patch solved the brief it was given. Reverted
> to `top: '10px'` unconditionally.
>
> The replacement is the part worth keeping. `grid.left` and the overlay cluster's `left`
> are now **one shared constant** (`CHART_PLOT_LEFT_PX`), because with `containLabel: true`
> the gutter width is **computed by ECharts from the widest tick label** — so any
> independently-chosen CSS offset would clear today's labels and silently desynchronise the
> first time one grew (another base currency, a larger portfolio, a negative thousands
> value). Two magic numbers whose agreement is a coincidence is the defect; one number with
> two uses is the fix. Measured after the change: toggle left edge 53px against
> `grid.left` 52 — the 1px is the button border.
>
> Also verified a collision that **did not exist before this change set**: widening the
> zoom-selector guard (all three submodes) and moving the cluster rightward make the two
> clusters approach from opposite sides. Worst case is 420px in candles submode — a state
> created only by the two changes together. Measured 145px cluster right edge against
> 199px selector left edge: **54px clear**, no overlap, zero console errors.

> **Note implementazione (zoom selector in all P&L submodes + rename, 2026-09-18):** the
> `1W/1M/1Y/All` selector was rendered only in the income submode, but `selectZoomWindow`
> had always written the **shared** `visibleStartDate`/`visibleEndDate` + dataZoom — so the
> mechanism already worked everywhere and only the `{#if}` guard was income-specific.
> Widening it to `viewMode === 'pnl'` exposed a capability that existed rather than adding
> one.
>
> That falsified the naming, so it was renamed in the same commit rather than left for the
> ladder work: `selectIncomeWindow` → `selectZoomWindow`, `computeIncomeWindowRange` →
> `computeZoomWindowRange`, `IncomeWindowPreset` → `ZoomWindowPreset`, `incomeWindowPreset`
> → `zoomWindowPreset`, testids `growth-income-window-*` → `growth-zoom-window-*`. Blast
> radius measured before deciding, not weighed: **two files, one regex** outside the
> component, **zero E2E specs**. The names also now align with the **existing**
> `buildZoomWindow` in the same file, so this is consistency with established vocabulary
> rather than a new coinage — and "zoom" keeps it distinct from the candle-**width** ladder
> (DBT-7), which is a different control answering a different question. A commit that
> falsifies a name and leaves it is committing a known falsehood on purpose.

> **⚠️ Fuori pista (candles still render as lines at high zoom — OPEN, 2026-09-18):** the
> developer reported candles rendering as lines at a **seven-day** x-axis. Reproduced via
> their exact path (income → 1W → candles). At that zoom the data says candles should be
> **large**: 8 points, median range 301 against a 4747 span including the broker overlay →
> **11.4% of height, ~34px**. Measured tallest coloured run: **11px**. Expected and
> observed disagree by 3×, and at eight visible points a candle *cannot* be thin — so this
> is **not** DBT-7 (thin-at-wide-range) wearing a different hat.
>
> Two hypotheses killed by measurement rather than reading: the y-axis **does** rescale on
> zoom (axis labels change between full and 1W), and the missing `filterMode` is **not** the
> cause because ECharts' default for `type:'inside'` is already `'filter'`.
>
> **Latent inconsistency recorded on the way past:** `GrowthChart` hand-rolls its dataZoom
> and spreads only `INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG` (scroll-safety flags), so it never
> sets `filterMode: 'filter'` the way the shared `buildDataZoom()` helper does. Harmless
> today because it matches the default — written down so the next person finds it instead
> of rediscovering it.
>
> **No conclusion recorded on purpose.** The remaining instrument is the column profile,
> which R11 has already caught under-reporting twice on exactly this shape (thin, bordered,
> ~5px strokes broken by wick geometry). Reporting "candles are 11px" as fact would be the
> third instance. Next step is to **calibrate the profile against a case whose true height
> is independently computable from the API**, then either it earns a verdict or it is
> retired — uncalibrated disqualifies a proxy, it does not disqualify it forever.

> **Open question (not a defect — 2026-09-13 P&L spike, 2026-09-18):** total P&L runs
> ≈1641 → ≈373 → ≈1984 across three consecutive days: a ~1300 single-day round trip.
> Surprising, not demonstrably wrong, so recorded as a question rather than a finding.
> It is **not** orthogonal to the developer's symptom, though it is orthogonal to the 3×
> discrepancy above: the spike sits inside the 1W window and inflates the axis the candles
> are measured against — remove it and the window's P&L span falls from ≈1611 to ≈343. Two
> separate questions therefore: *why is observed 3× below expected* (open), and *why is
> expected itself only 11%* (partly this spike). Either a mock-data artefact or a P&L
> computation defect; not chased.

### 6.0.6 The invisible candles — a stale memo, not a renderer (2026-09-18)

> **⚠️ Fuori pista (ZERO candles ever drawn; cause was my own cache, 2026-09-18):**
> after the crash fix and the data enrichment, the developer still saw no candles. The
> hunt that followed cost about an hour and produced four dead hypotheses — three of them
> about ECharts — before one integer closed it.
>
> **The measurement that collapsed the search.** Splitting the canvas by region and
> counting the series' own exact hexes (`#16a34a`/`#dc2626`) gave: **plot area 0 pixels**,
> legend band **133 pixels in a 15×9 box**. The legend config is `itemWidth: 14,
> itemHeight: 8`. So *every* "candle" pixel measured across the whole evening — back to the
> original "181 green + 1331 red" — was **the legend swatch plus the dashed broker
> overlay**. Not thin candles. No candles.
>
> Reading the live instance then gave the decisive integer:
> `xAxisType: 'category'` (correct), `xAxisDataLen: 93`, `candleDataLen: 93`,
> **`candleNonGap: 0`**, sample `['-','-','-']`. Correctly typed, correctly sized,
> correctly axed — and 93 gap sentinels.
>
> **Cause.** Probing the component's own state at the same activation: `propPoints 93`,
> `mapSize 93`, map keys and bucket dates **identical**, and
> `pnlCandleByDate.get('2026-06-18')` holding real numbers (open −601.25 … close −584.52)
> while the aggregated point *for that same date* was all-null. The lookup had not failed —
> **it had never re-run.** `getResolutionData()` memoises into `resolutionCache`, which is
> cleared only by `resetResolutionState()`, which fires only on
> `if (history !== lastHistoryRef)`. `pnlCandles` arrives *later* by design — it is the lazy
> fetch added in G1b. First candles render populates the cache while the map is still empty;
> the fetch lands; the `$effect` re-runs `renderChart()` because it voids `pnlCandles`; and
> `getResolutionData()` returns the entry computed **before the data existed**. Null forever
> after, surviving every timing (500/1500/3000/6000 ms) and surviving leaving and re-entering
> the submode, because nothing on that path invalidates the memo.
>
> **Stated structurally, which is the form worth keeping:** seven inputs wake the effect,
> **one** clears the cache, and the two lists sit adjacent in the same function. The cache
> key spans **one** dimension (`resolution`) while the value depends on **seven**. The memo
> is asked a question it already believes it has answered, because resolution is the only
> thing it uses to recognise a new question. That is why "the re-render genuinely happens
> and genuinely recomputes nothing".
>
> **This is a defect I introduced in G1b**: I added a lazily-arriving prop, wired the
> re-render, and never invalidated the memo the re-render reads. The `$effect` voiding
> `pnlCandles` *looks* like it closes the loop, which is precisely why it survived review.

> **⚠️ Fuori pista (R13 — four hypotheses inside the wrong layer, 2026-09-18):** both the
> coordinator and I generated hypotheses **inside ECharts**, because the symptom was pixels:
> candlestick-on-time-axis, a `filterMode` divergence, a merge path that never re-sets
> `type`, an `entry.dates` index mismatch. All four dead. **ECharts behaved perfectly
> throughout** — handed `'-'` ninety-three times, it faithfully drew ninety-three nothings
> and a legend swatch for the series that existed. The one component in the stack with
> nothing to answer for was the one we spent an hour theorising about.
>
> Rule: *a symptom surfaces in the layer that displays it, which is rarely the layer that
> caused it. Before hypothesising about how a layer behaves, measure what was handed to it.
> "It rendered nothing" and "it was given nothing to render" are indistinguishable from
> outside and have disjoint causes.* `candleNonGap: 0` converted an open question about
> rendering into a closed question about inputs, in one integer. It should have been the
> first thing asked for.
>
> Companion note on instruments: the run-length column profile was **retired**, not tuned —
> it could not separate a dashed overlay from a candle (125px of extent carrying 9 pixels).
> A threshold problem is fixable; a discrimination problem means the instrument was never
> answering the question. Its replacement keys on the series' own exact hexes. And an
> earlier lead of mine — "visible at 3M, absent at 1W" — was **retracted**: it came from
> reading a screenshot impressionistically rather than measuring it, and four identical
> zoom readings killed it. Opening the artefact is necessary and not sufficient.

> **Note implementazione (fix + regressione, 2026-09-18):** invalidazione resa corretta
> **per costruzione**, non per lista mantenuta a mano. Introdotto `aggregationInputs`, un
> `$derived` che contiene l'insieme COMPLETO dei valori che il memo legge;
> `getResolutionData()` ora legge i propri input **solo** da lì e la cache confronta
> `cached.inputs === aggregationInputs`. Poiché Svelte ricostruisce il `$derived` quando un
> membro cambia, un input modificato non può colpire una entry stale; e una prop futura non
> può essere *consumata* senza prima diventare membro, il che la iscrive automaticamente
> all'invalidazione. `buildBucketInfos` prende ora `dates` come parametro, così il contratto
> "legge solo dal bundle" è letterale e non solo rispettato di fatto.
>
> Estratto `pctValuesRaw` (solo valori) da `pctSeriesRaw` (che porta `name: $_(...)`):
> senza questa separazione il bundle sarebbe cambiato identità a ogni cambio lingua,
> svuotando la cache per un motivo che l'aggregazione non legge — cioè scambiando un bug
> silent-wrong con uno silent-slow. `eurLabels`, `pnlLabels`, `$locale` e `baseCurrency`
> restano deliberatamente fuori.
>
> **Verifica con ground truth, non a occhio.** Hook diagnostico temporaneo → `candleNonGap`
> passa da **0/93 a 93/93**, con quad reali già al primo render (t=1.5 s), stabile al cambio
> finestra e al rientro nella submode. Geometria misurata via `convertToPixel` sugli assi
> (non per colore): a 1W **body 1.82 px / wick 18.17 px, rapporto 9.98:1**, contro il 10.3:1
> derivato dall'API *prima* di misurare qualunque pixel. Le candele corrette restano quindi
> sottili come previsto: è la composizione sintetica che somma high/low per asset, non un
> difetto residuo — il problema di larghezza è DBT-7 (ladder), separato.
>
> Regressione via `test-author`: `frontend/src/lib/components/dashboard/GrowthChart.test.ts`,
> 6 casi che montano il componente reale e codificano l'**ordine di arrivo** (prop assente →
> memo popolato in quello stato → prop consegnata → quad reali). Dimostrata **rossa** contro
> il sorgente pre-fix committato (`0` invece di `40`/`80`, sempre sull'asserzione dati e mai
> su un barrier timeout), e una variante che monta con la prop già presente **passa** sul
> codice rotto — l'ordine di arrivo è portante, non decorativo.

> **⚠️ Fuori pista (il mio strumento exact-hex non discriminava, 2026-09-18):** la prima
> misura post-fix contava `#16a34a`/`#dc2626` nell'area del plot e dava 463 px contro 0.
> Numero vero, domanda sbagliata: **quegli stessi esadecimali sono usati anche dalla linea e
> dall'area P&L** (`:1440`, `:1456`, `:1485`, `:1500`), e il diagnostico conferma che in
> submode candele il grafico porta pure `line:Interactive Brokers` e `line:Coinbase`. I
> gruppi larghi 54/33/53 px erano estensioni orizzontali continue: linee, non corpi. È R11
> di nuovo, stavolta sullo strumento costruito *per* soddisfare R11 — dopo aver già ritirato
> il profilo run-length per lo stesso motivo. La misura valida non è arrivata dai pixel ma
> dagli assi, che sono keyed sulla cosa affermata.

> **⚠️ Fuori pista (void list incompleta — corretto per adiacenza, 2026-09-18):**
> `costHistory`, `depositHistory` e `acquisitionFunding` non erano nella dependency list
> dell'`$effect`. Oggi innocuo solo perché dashboard e broker detail assegnano le quattro
> prop della famiglia income in un blocco contiguo, quindi `incomeHistory` svegliava
> l'effect anche per le altre tre. Verificato leggendo le due pagine, non dedotto. Aggiunte
> le tre voci: la classe è ora uniforme e non dipende più dall'adiacenza di quattro
> assegnazioni in un file che non è questo.

> **⚠️ Fuori pista (2 mirror assertion in `chartCoreHelpers.test.ts`, 2026-09-18):** il
> refactor ha rotto due asserzioni che pinnano il sorgente **per stringa**. Verificato che
> le proprietà pinnate reggono ancora — un solo array `buckets` threadato ovunque e
> costruito una volta sola; tutti e sei i flussi via `aggregateFlowMetric` e mai
> `aggregateMetric` — ed è cambiata solo la grafia (`inputs.`). Ri-pinnate le 10 stringhe
> sulla nuova grafia: manutenzione del test, non indebolimento. Nota di metodo: un'asserzione
> che rispecchia il testo sorgente verifica una proprietà reale ma si rompe a ogni rinomina,
> e il costo ricade su chi rifattorizza.

> **Note implementazione (precedente locale della forma scelta, 2026-09-18):** la lista file
> di `front_asset_unit` (`scripts/test_runner/_frontend_asset.py:8-33`) ha **la stessa forma
> strutturale del bug appena corretto**: un elenco di membri mantenuto a mano, dove un nuovo
> membro va iscritto manualmente e dimenticarlo non produce alcun errore. La differenza è che
> il runner possiede un **controllo meccanico di iscrizione** (`_cli.py:275`, *"Checking that
> every test is reachable from an 'all' action"*, con warning esplicito *"Registered but never
> executed!"*) e il memo di `GrowthChart` non ne aveva alcuno. Quindi "derivare l'insieme di
> invalidazione da ciò che viene letto" non è una preferenza importata: è la convenzione che
> questo codebase applica già al proprio catalogo di test, con un precedente funzionante.
>
> Reachability verificata **per nome e non per aggregato**: `reachable_paths()` elenca
> esplicitamente `src/lib/components/dashboard/GrowthChart.test.ts` (e
> `timeSeriesAggregationGolden.test.ts`) nell'insieme vitest raggiungibile da `all`. Un
> "199/199" è un totale, non l'affermazione da dimostrare.

> **Regola strumenti (forma durevole, 2026-09-18):** *un colore identifica una voce di
> palette, non una serie.* Qualunque metrica basata sull'**aspetto** eredita ogni altro
> elemento che condivide quell'aspetto — e in un grafico a tema la condivisione è per
> costruzione, non per sfortuna. Questo spiega in una riga tutti e tre gli strumenti
> ritirati in giornata: la somma di pixel non poteva codificare la visibilità; il profilo
> run-length non separava una linea tratteggiata da una candela; l'exact-hex non separava
> una candela dall'area P&L che ne condivide il riempimento. Il terzo era stato costruito
> apposta per soddisfare la regola che il secondo violava.
>
> `convertToPixel` ha funzionato perché è keyed sulla **geometria di una serie nominata**:
> non può rispondere sull'elemento sbagliato, perché non si può interrogarlo su un elemento
> che non si è nominato. La proprietà da selezionare non è "soglie più accurate" ma
> *l'impossibilità di rispondere sulla cosa sbagliata*.
>
> Corollario sugli aggregati, dalla stessa giornata: un totale verde (`199/199`) dimostra
> che l'insieme non ha orfani, non che il tuo file ne faccia parte. Se il file fosse assente
> dal corpus ispezionato, il totale sarebbe verde ugualmente. **Risolvi per nome ciò che
> vuoi affermare per nome.**

## 6. Dependency-safe phases and owners

| Phase | Size | Owner | Dependency | Deliverable | Status |
|---|---:|---|---|---|---|
| I00 | XS | Workstream I planner | Plan-only developer authorization | Durable product contract, split, storyboards and backlog links | COMPLETE 2026-09-10 |
| G0 | M analysis | Coordinator + assigned integrators | F integrated on `dev_release2` | Post-F technical refresh + phase-specific implementation authorization | I10 RELEASED ONLY 2026-09-10; PORTFOLIO BLOCKED |
| H0 | external | H + coordinator | H/YOC accepted and integrated | Release portfolio service/schema/tests, provide exact target SHA, I re-read | COMPLETE 2026-09-11 |
| I10 | M | G3 backend owner | G0 developer authorization; no H/F files | Calendar-return backend series + provenance, no resolver duplication | COMPLETE AND INTEGRATED 2026-09-10 |
| I20 | L | Portfolio backend integrator | G0 + H0 + F engine released | Additive daily broker P&L + signed canonical income | BLOCKED |
| I30 | L | Portfolio backend integrator | I20 + same-resolver OHLC envelope | Daily total candles + flat fallback + strict close identity | BLOCKED |
| I40 | M | Portfolio backend integrator + coordinator | I20 + I30 + post-H report contract | DTO/report/cache wiring, then coordinator API sync | BLOCKED |
| I50 | L | GrowthChart owner | I40 | Value/Return/P&L core modes; Line/Candles/Income P&L submodes; broker lines and sum aggregation | BLOCKED |
| I60 | XL follow-up | G3 Asset UI + shared chart owner | Initial I60 integrated; explicit developer authorization | Compact duration, contextual Asset/FX axes, separate Return measures, same-N Asset comparisons | MANUAL REVIEW ROUND 2 IN PROGRESS 2026-09-12 |
| I70 | L | Test author + owners | Relevant implementation phases; H test ownership released | Targeted backend/frontend regressions and integration gates | BLOCKED |
| I80 | S | Docs writer + coordinator | Stable integrated UI | English docs, coordinator i18n/runner/changelog records | BLOCKED |
| I90 | M | Developer + coordinator | I50 + I60 + I70 + I80 | Desktop/mobile operational review, corrections, integration handoff | BLOCKED |

> **Note implementazione (I00, 2026-09-10):** only the durable plan, final
> product decisions, updated ASCII v2 storyboards and minimal feedback-job
> links were written. No production/test implementation, specialist, server,
> suite, API sync, i18n, generated output, staging or commit was started.

> **Note implementazione (I00 revision 2, 2026-09-10):** developer correction
> retained exactly three top-level modes (`Value | Return % | P&L`) and moved
> Income under P&L as the third mutually exclusive submode beside Line and
> Synthetic candles. Architecture, desktop/mobile storyboards, selectors,
> frontend test plan, phase I50 and DoD were realigned; implementation stayed
> frozen.

> **Note implementazione (G0 technical refresh, 2026-09-10):** F's merged
> source was re-read at `0af66da5...`; final findings and the H-before-I gate
> are recorded in section 2. Gate 0 is not complete because implementation
> authorization is absent. No implementation/test/runtime action was taken.

> **Note implementazione (G0 I10 release, 2026-09-10):** developer explicitly
> authorized only the signal-owned calendar rolling-return slice on
> `0af66da5f366a9559549154631a4ee15ca620915`. Authorized production boundary:
> dedicated plugin/helper plus minimal signal schema/catalog/service seam.
> Excluded: Asset/portfolio/UI/F/H/shared generated surfaces. Portfolio Gate 0
> remains blocked.

### 6.1 Parallel work after Gate 0

Before H integration, only I10 may be considered independently, after explicit
developer authorization. Its implementation file set must remain within the
signal layer and avoid `asset_source.py`, `price_resolver.py`,
`portfolio_engine.py`, `portfolio_service.py`, `schemas/portfolio.py` and
H-owned portfolio tests.

After H0, the portfolio backend integrator re-reads/re-reserves shared files,
then I20 starts. I30 waits for I20 and extends the same resolver path. I50 waits
for the integrated report contract. I60 waits for I10 plus an explicit
coordinator release so Asset UI work cannot outrun shared integration.

### 6.2 File reservations

| Owner | Reserved surfaces |
|---|---|
| H until integration | `portfolio_service.py`, `schemas/portfolio.py`, relevant portfolio service/API tests, approved FIFO eligibility seam, `ExposureTable.svelte` and test |
| F until coordinator release | `portfolio_engine.py`; preserve its shared FX cache-identity helper and current tests |
| G3 backend | New calendar signal plugin/helper plus signal-owned schema/service tests only; no H/F surface |
| Future portfolio backend integrator | After H/F release: `portfolio_engine.py`, `price_resolver.py`, `portfolio_service.py`, `schemas/portfolio.py`, portfolio cache behavior |
| GrowthChart owner | `GrowthChart.svelte`, `timeSeriesAggregation.ts`, portfolio store, Dashboard/Broker mounts |
| G3 Asset UI | Asset detail page and additive PriceChartFull props/helpers |
| Coordinator | API client generation, i18n catalogues, test runner, nav, changelog, master records |
| Test author | Distinct new/repaired tests only after authorization; portfolio service/API files wait for H release |
| Docs writer | English MkDocs pages after UI/contract stability |

The post-F overlap is now known: preserve the F transactions link in Asset
detail, F's L1 FX identity in the engine and F's tests. H remains the active
shared-file blocker. No I owner edits a reserved file before the coordinator
records its release.

### 6.3 Remaining developer/coordinator gates

No product decision remains open. Readiness still requires:

1. Explicit developer authorization to implement I10 or any later phase.
2. Coordinator confirmation that I10's final file set is signal-only.
3. H accepted/integrated SHA and release of service/schema/portfolio tests.
4. F release of `portfolio_engine.py` as integration-stable.
5. A new post-H exact baseline and conflict refresh before I20.

### 6.4 I10 execution progress

| Step | Scope | Status |
|---|---|---|
| I10.0 | Baseline, post-F resolver verification, authorization and exact file ownership | COMPLETE 2026-09-10 |
| I10.1 | Test-author characterization/regressions in assigned signal test files | COMPLETE 2026-09-10 |
| I10.2 | Sparse typed provenance + internal-catalog execution seam | COMPLETE 2026-09-10 |
| I10.3 | Dedicated calendar-day rolling-return plugin/helper | COMPLETE 2026-09-10 |
| I10.4 | Targeted schema/registry/plugin/asset-signal gates and lint/format | COMPLETE 2026-09-10 |
| I10.5 | Plan evidence, exact manifest and frozen integration handoff | COMPLETE 2026-09-10 |

> **Note implementazione (I10.0, 2026-09-10):** clean exact baseline
> `0af66da5...` verified. `AssetPriceSeries` and Asset query provide the
> approved existing resolution semantics; no new resolver is required.
> Signal-only implementation can avoid every H/F-reserved production file.
> Tests are delegated only in
> `test_signal_registry.py`, `test_risk_signal_plugins.py`,
> `test_asset_signals.py` and `test_signal_schemas.py`; no runner edit is
> required because all four files are already registered.

> **Note implementazione (I10.1, 2026-09-10):** `test-author` added
> contract-first coverage only to the four assigned, already-registered files:
> `test_signal_registry.py`, `test_risk_signal_plugins.py`,
> `test_asset_signals.py` and `test_signal_schemas.py`. Cases cover hidden but
> executable registration, sparse typed provenance, calendar-vs-observation
> windows, all four N values/default 30, target-currency integration,
> backward-resolved references, missing/invalid states and unchanged legacy
> rolling return. It ran no command and requested no runner edit.

> **Note implementazione (I10.2, 2026-09-10):** added strict
> `SignalCalendarReturnPointStatus`, typed provenance and a calendar-specific
> value-point subtype. Existing `SignalValuePoint` remains exactly
> `date + value`; provenance appears only on the new subtype. Added
> `SignalPlugin.catalog_visible=True` and filtered only
> `SignalPluginRegistry.list_definitions()`: hidden plugins remain
> auto-discovered/executable through `get_plugin()`, while public Asset/FX
> overlay catalogs and their existing 22/9 cardinalities stay unchanged.

> **Note implementazione (I10.3, 2026-09-10):** added hidden
> `ASSET_CALENDAR_ROLLING_RETURN`. Params are exactly
> `window_days=7|30|90|365`, default 30. The plugin consumes the existing
> target-currency dense daily `SignalPricePoint` series, performs exact
> `t-N` calendar lookup, emits one typed value/null point per input date and
> reports current/reference price plus available FX observation provenance.
> No resolver, staleness threshold, Asset/portfolio/UI or legacy
> `RISK_ROLLING_RETURN` behavior changed.

> **Fuori pista (I10.4 lint, 2026-09-10):** the first exact-file Ruff check
> stopped before test collection on one `I001` import-order finding in the new
> plugin. No DB, file generation or server was touched. Reordered the one
> import manually; no broad autofix was used.

> **Fuori pista (I10.4 risk selector, 2026-09-10):** command
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
> --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts services risk-all
> calendar` recreated only the assigned TEST DB, started no server, selected
> 16 tests and returned 15 pass / 1 fail. The sole mismatch was
> `RiskResultMetadata.computed_at`, correctly different between two sequential
> service calls; every reported stable field matched. A required test-author
> follow-up produced no patch, so the integrator normalized only `computed_at`
> in that one equality assertion without weakening any stable payload check.

> **Fuori pista (I10.4 exact-N warm-up, 2026-09-10):** tightening warm-up from
> N+1 to the exact required N calendar days correctly avoided false partial
> status at a boundary, but the targeted risk selector then returned
> 22 pass / 2 fail: with no resolvable visible reference, the plugin attempted
> to construct an all-null series and central schema validation classified it
> as FAILED before SignalService could produce UNAVAILABLE. The command touched
> only the assigned TEST DB and started no server. Added signal-owned
> `validate_input()` that raises typed `INSUFFICIENT_HISTORY` only when no
> visible date has its exact `t-N` point; exact-N warm-up remains unchanged.

> **Fuori pista (I10.4 code review, 2026-09-10):** final read-only code review
> found that unavoidable pre-visible warm-up nulls were counted in
> `UNDEFINED_METRIC_WINDOW` even though SignalService slices those points before
> returning the visible series. This could produce an OK visible result with a
> false warning. Restricted warning counts to `context.requested_range`;
> `test-author` added the focused no-warning assertion to the existing Asset
> warm-up integration case.

> **Note implementazione (I10.4, 2026-09-10):** all commands used
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc` and the assigned lane
> `--test-port 6157 --data-dir /tmp/librefolio-r2-i-charts`. Final evidence:
> Black exact-file pass; Ruff exact-file pass; `schemas signals` 477/477;
> `services signal-registry` 68/68; `services signal-service` 45/45;
> `services asset-signals` 18/18; `services signal-plugin-matrix` 65/65;
> final `services risk-all` 134/134. Earlier targeted selectors also proved
> six provenance schemas, all calendar windows/statuses, target-currency
> integration and the unchanged legacy sibling. Services commands recreated
> only the isolated TEST DB; no backend server was started.

> **Note implementazione (I10.5, 2026-09-10):** production delta is confined
> to `schemas/signals.py`, `provider_registry.py`, `signal_plugins/base.py`
> and new `signal_plugins/calendar_rolling_return.py`; test delta is confined
> to the four assigned registered files. Final read-only code review found one
> false warm-up-warning leak; its fix and focused regression are green. No
> runner, Asset/portfolio/UI, i18n, generated client, docs, nav or changelog
> file changed. Port 6157 is free. The hidden plugin is ready for integration;
> UI consumption and coordinator-owned API client generation remain deferred
> to authorized I60/shared integration.

### 6.5 I60 execution progress

| Step | Scope | Status |
|---|---|---|
| I60.0 | Verify clean post-H/I10 baseline and re-read final Asset/PriceChart contracts | COMPLETE 2026-09-11 |
| I60.1 | Test-author helper and Asset-detail regressions in registered files | COMPLETE 2026-09-11 |
| I60.2 | Typed calendar-result extraction and chart-point/provenance mapping | COMPLETE 2026-09-11 |
| I60.3 | Asset primary mode/window controls and request lifecycle | COMPLETE 2026-09-11; DESKTOP/MOBILE E2E GREEN |
| I60.4 | PriceChartFull percentage-unit, missing-point and provenance presentation seams | COMPLETE 2026-09-11 |
| I60.5 | Focused frontend gates, static checks and review corrections | AUTHORIZED GATES COMPLETE 2026-09-11 |
| I60.6 | Evidence, manifest and frozen integration handoff | COMBINED VALIDATION COMPLETE 2026-09-11; MANUAL REVIEW PENDING |

> **Note implementazione (I60.0, 2026-09-11):** verified exact clean HEAD
> `0d57874303b1311c0f5ea3b8653d24a33d4245a6`. I60 can avoid the three
> actively H-owned files (`backendRenderer.ts`, `backendTypes.ts`,
> `backendTypes.test.ts`) and every D portfolio surface. The locked production
> set is `assets/[id]/+page.svelte`, `PriceChartFull.svelte` and
> `priceChartHelpers.ts`; registered test owners are
> `priceChartHelpers.test.ts` and `e2e/assets/asset-detail.spec.ts`.
> Calendar results are requested explicitly by instance/code and parsed through
> a signal-owned structural helper, so the primary mode does not depend on the
> public overlay catalog or H's renderer normalization.

> **Note implementazione (I60.1, 2026-09-11):** `test-author` added focused
> extraction/state/provenance cases to registered
> `priceChartHelpers.test.ts` and a synthetic, no-DB-mutation Asset-detail
> workflow to registered `asset-detail.spec.ts`. No runner change is required.

> **Fuori pista (I60 formatter bootstrap, 2026-09-11):** the first exact-file
> Prettier invocation failed before formatting because this worktree has no
> `prettier-plugin-svelte` dependency available. No file, DB or server was
> touched by the failed command. Per coordinated-lane policy, no `npm ci` or
> other install was attempted without coordinator approval.

> **Note implementazione (I60 bootstrap resolved, 2026-09-11):** coordinator
> authorized `npm --prefix frontend ci` from the committed lock. It installed
> the worktree-local dependencies; SHA-256 of `package.json` and
> `package-lock.json` stayed unchanged. No audit fix/update or shared
> environment mutation was performed.

> **Fuori pista (I60 component runner, 2026-09-11):** the attempted focused
> `front-utility component-unit extractCalendarReturnView` action expanded to
> the full component catalogue and failed before executing tests because the
> coordinator-owned ignored files `api/generated.ts`, `generated-tools.ts` and
> tool contract map are absent in this worktree. Result: 41 files failed import,
> 25 skipped, 0 tests executed. No DB/server or generated file was touched.
> The exact already-registered `priceChartHelpers.test.ts` will be run directly
> through Vitest, avoiding any API sync or shared generated artifact.

> **Fuori pista (I60 review round 1, 2026-09-11):** coordinator review rejected
> the first I60 checkpoint for four regressions: calendar mode unmounted the
> stateful data editor and measure panel; the calendar generation guard covered
> only `calendarReturnView` instead of every asynchronous request write; FX
> carry age did not contribute to overall line opacity; and Risk-tab
> `Configure Signals` returned to Overview without first restoring Price mode.
> I60 reopened within the original three production files and two test files.
> H renderer/type files, D portfolio files, generated API artifacts and shared
> runner/i18n/docs remain excluded.

> **Note implementazione (I60 review correction 1, 2026-09-11):** the Asset
> editor and measure trees now stay mounted while calendar mode hides and makes
> them inert; Price mode restores their existing local and mirrored state.
> One chart-request generation now rejects stale success, empty-result, error
> and finalization paths before any asynchronous page-state write. FX carry age
> participates in overall `staleDays` while its dedicated `fxStaleDays` detail
> remains available. Risk-tab `Configure Signals` restores Price mode before
> returning to Overview and scrolling to the panel. Focused test-author
> regressions and exact-file formatting remain the completion gates.

> **Note implementazione (I60 review tests, 2026-09-11):** `test-author`
> extended the owned helper/E2E files with four regression witnesses. The
> Asset workflow verifies mounted-but-hidden/inert editor and measure trees,
> uses a forced cache miss plus deferred responses so stale `chartData`,
> no-data/error and loading-finalizer writes fail the pre-fix implementation,
> and verifies Risk `Configure Signals` restores Price mode before exposing the
> Signals panel. The pure helper asserts overall staleness is the maximum across
> current/reference price and FX carry while preserving the FX-only maximum.
> No production observability seam beyond the owned measures-section test id was
> required.

> **Note implementazione (I60 review gates, 2026-09-11):** exact command
> `cd frontend && npx vitest run
> src/lib/components/charts/priceChartHelpers.test.ts -t
> extractCalendarReturnView` passed 10 tests with 82 skipped in the same file.
> Exact Prettier check passed for the Asset page, `PriceChartFull`, helper,
> helper test and Asset-detail E2E spec. Per coordinator instruction no
> Playwright, server, API generation or full frontend check ran; those combined
> gates remain reserved for the post-merge target baseline.

> **Note implementazione (I60 review handoff, 2026-09-11):** replacement
> checkpoint contains exactly the durable plan, Asset-detail E2E, chart
> component, helper test, helper and Asset page (six tracked modified files;
> none staged or untracked). Diff is 1,210 insertions / 171 deletions before
> this final note. `git diff --check` is green, port 6157 is free, and ignored
> build/API/tool generated artifacts remain absent. Proposed commit:
> `feat(frontend): add calendar return chart`. State is FROZEN pending
> coordinator review, developer commit and merge of the current target before
> authorized combined frontend gates.

> **Fuori pista (I60 review round 2, 2026-09-11):** a second coordinator
> review accepted the four round-1 fixes but found that Calendar-to-Price mode
> switching invalidated the shared chart request without starting a successor.
> When filters changed during that pending request, Price could retain old data
> under the new filters indefinitely. The correction must preserve the pending
> shared price/events request and its loading state on a mode-only switch, while
> a later request-producing action remains responsible for superseding it.

> **Note implementazione (I60 review correction 2, 2026-09-11):**
> Calendar-to-Price now changes only presentation state and clears the
> calendar-specific view; it does not advance the shared request generation or
> clear `loading`/`signalsLoading`. The pending request can therefore publish
> price/events for the active filters and finalize normally. Price-to-Calendar
> still starts a real successor through `loadChartData()`, whose request
> generation supersedes any older request synchronously.

> **Note implementazione (I60 review test 2, 2026-09-11):** `test-author`
> added a regression distinct from the stale-vs-successor race. A forced
> 30-day calendar refresh is held with `include_price:true`, the UI switches to
> Price without issuing another request, and Price must remain loading/busy
> with Refresh disabled until that sole shared response resolves. Round-1 code
> fails the witness because it invalidates the request and immediately reports
> ready. The existing 90-to-365 successor race remains unchanged.

> **Note implementazione (I60 review gates 2, 2026-09-11):** focused helper
> command passed 10 tests with 82 skipped; exact Prettier check for the five
> owned frontend files and `git diff --check` are green. Per authorization no
> Playwright, server, generated API step or full frontend check ran. The
> replacement checkpoint is FROZEN for coordinator review.

> **Fuori pista (I60 post-merge type gate, 2026-09-11):** first combined
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front
> check` reached the generated H/I contracts and failed with two I60-local
> TypeScript diagnostics in the Asset page: Svelte narrowed the annotation-form
> `$state('price')` initializer to the `price` literal, and an `any[]` response
> left the calendar-result filter callback implicit-any. No server, DB or
> generated source was modified by the check. Switched to
> `$state<AssetChartPrimaryMode>('price')` and typed the raw transport array as
> `unknown[]`; behavior and ownership remain unchanged.

> **Note implementazione (I60 post-merge type gate, 2026-09-11):** rerunning
> the exact full frontend check after the two local type corrections returned
> exit 0: `svelte-check found 0 errors and 41 warnings in 2 files`. The warnings
> are the merged baseline's existing Svelte deprecation/a11y warnings; no I60
> error remains, and generated nested signal unions type-check through both H's
> public renderer normalizer and I60's hidden-result extraction seam.

> **Note implementazione (I60 post-merge production build, 2026-09-11):**
> canonical command `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run
> python dev.py front build` returned exit 0. It completed the built-in OpenAPI,
> Zodios discriminator and Tool generation checks, then production client and
> server builds (`17.50s` and `28.46s`), ending with `Frontend build complete`.
> Generated/build/cache artifacts remain ignored; post-build Git status contains
> only this plan and the two I60-local type corrections.

> **Note implementazione (I60 post-merge focused units, 2026-09-11):**
> lane command `... dev.py test --test-port 6157 --data-dir
> /tmp/librefolio-r2-i-charts front-utility core-unit
> extractCalendarReturnView` passed the 10 calendar helper tests (79 files /
> 1,944 tests skipped by the name filter). The analogous `component-unit
> MeasurePanel` selector passed 17 component tests (65 files / 1,758 tests
> skipped), preserving the stateful component contract I60 keeps mounted.
> Exact Vitest for H's `backendTypes.test.ts` plus
> `backendRenderer.test.ts` passed 20/20 in 2 files, including one-level
> generated point normalization and every public renderer series kind.

> **Fuori pista (I60 post-merge E2E selector, 2026-09-11):** registered lane
> command `... dev.py test --test-port 6157 --data-dir
> /tmp/librefolio-r2-i-charts front-asset asset-detail` populated only the
> assigned TEST DB, started the shared backend and ran desktop first. Result:
> 25 pass / 1 fail. The calendar workflow stopped before product interaction
> assertions because regex `^asset-calendar-window-` matched the controls
> container plus the four buttons (5 nodes vs expected 4). The runner then
> stopped before mobile and force-terminated its own backend process group after
> the graceful five-second timeout. This is a deterministic test-selector bug,
> not product evidence; repair is delegated to `test-author` before rerunning
> the full registered desktop+mobile action.

> **Note implementazione (I60 post-merge desktop E2E, 2026-09-11):**
> after `test-author` narrowed the count selector to numeric window ids, the
> registered `front-asset asset-detail` action passed desktop 26/26 in 54.0s.
> The runner action hardcodes Playwright project `desktop`; mobile was not part
> of that green result. Its owned backend again required runner process-group
> termination after the five-second graceful timeout, and port 6157 was
> confirmed free. The same registered spec must therefore run once more with
> Playwright project `mobile` under the assigned port/data environment.

> **Fuori pista (I60 post-merge mobile toolbar collision, 2026-09-11):**
> direct mobile project run of the registered Asset-detail spec reached 25 pass
> / 1 fail. The I60 calendar workflow itself passed. The existing
> `measure button reveals the measures panel` test timed out because
> PriceChartFull's later-rendered inner toolbar (`top-2 left-12 z-10 pr-24`)
> intercepted the Asset page's measure button (`top-0 right-0 z-10`) through
> its transparent reserved padding. Read-only parent-commit comparison confirms
> both stacking classes predate I60, so the triage verdict is a latent product
> defect, not a flaky test or I60 regression. Within the already-owned Asset
> page, raised the outer interactive toolbar to `z-20`; the reserved layout
> remains unchanged while its visible buttons correctly own pointer priority.

> **Note implementazione (I60 post-merge mobile E2E, 2026-09-11):**
> the exact failed mobile measure-button selector passed 1/1 after the stacking
> correction. The complete Asset-detail mobile project then passed 26/26 in
> 1.5 minutes, including calendar window selection, editor/measure preservation,
> no-successor and stale-successor request ownership, FX-staleness rendering
> inputs, Risk `Configure Signals`, Price state restoration and chart-type
> controls. Together with the registered desktop result, Asset detail is green
> 52/52 across both Playwright projects.

> **Note implementazione (I60 final combined gates, 2026-09-11):** after the
> mobile stacking correction, the full frontend check again returned 0 errors
> / 41 baseline warnings. The canonical production build repeated OpenAPI,
> Zodios/discriminator and Tool generation and completed both bundles in
> 18.28s / 28.85s. Focused stale-rendering unit selection passed 6/6: calendar
> provenance first maps maximum price/FX age to `staleDays`, then
> `buildMainSeries` converts that age into the configured opacity gradient while
> retaining `fxStaleDays` for tooltip detail. Automated evidence now covers
> Price/calendar state preservation, both request-race classes, FX fade,
> Configure Signals navigation and the merged generated nested-series union.
> Manual desktop/mobile visual review remains the only I60 gate not executed.

### 6.6 I60 manual-review follow-up

Developer authorization is explicit for this follow-up only. I20-I50 remain
strictly out of scope.

#### Closed product contract

- Window controls are compact `1W | 1M | 3M | 1Y | Custom`, mapped to exact
  fixed calendar days `7 | 30 | 90 | 365`.
- Custom reuses DateRangePicker's compact amount+unit editor, allows positive
  integers with abbreviated `W/M/Y`, starts at `3Y`, has no UX maximum and
  converts by `W×7`, `M×30`, `Y×365`.
- Last selected window/Custom amount/unit persists in the existing
  account+asset client chart-settings cache. Reload starts in Price; entering
  Return restores the saved window.
- Price/Return controls gain `ChartLine`/`Percent` icons.
- Area, baseline/zero color, grid and stale-gradient toggles are shared.
- Replace the current single Y triple with client-only profiles:
  `primary:absolute`, shared `primary:percentage` for Price `%` and Return, and
  one stable `${axisRole}:${axisKey}` profile for every rendered secondary Y.
- Aesthetics shows one Auto/Include0/Custom row per active axis. The shared
  model applies to Asset and FX; v1 localStorage migrates to v2. No backend
  model/API/DB persistence.
- Price and Return use two independently mounted MeasurePanel tables. Return
  displays `%` endpoints, delta `pp` and days, without currency, relative delta
  or annualization.
- Return Signals exposes only Asset comparison. It reuses the Price selection
  and style but backend-computes the identical N-day calendar return for every
  comparison asset in the same target currency. Incompatible Price signals
  remain cached and hidden in Return.

#### Persistence boundary

| Data | Backend DB | Client persistent cache | Runtime only |
|---|---|---|---|
| Asset/provider identity, OHLCV, events, FX rates | Existing source tables | No durable copy | Read/cache copies |
| Primary/comparison calendar returns + provenance | Never persisted; computed per request | Never | Page signal state |
| Window selection | Never | account+asset chart-settings localStorage | Active request |
| Visual and primary/secondary Y settings | Never | account/scoped/pair chart-settings localStorage | Hydrated copy |
| Asset comparison IDs/styles | Never | existing signal configs in localStorage | Resolved lines |
| Visible From/To | Never newly persisted | existing sessionStorage | Date store |
| Primary mode | Never | Never | resets to Price |
| Price/Return measures | Never | Never | separate mounted panels |
| Request generation/loading/errors | Never | Never | page state |

#### Execution ledger

| Step | Scope | Status |
|---|---|---|
| I60F.0 | Preserve validation checkpoint, merge target, verify clean authorized baseline | COMPLETE 2026-09-11 |
| I60F.1 | Generalize hidden calendar-return window to positive integer with safe date arithmetic | REOPENED - SELECTED-RANGE BOUNDARY |
| I60F.2 | Extract reusable compact duration editor without DateRangePicker regression | COMPLETE 2026-09-12 |
| I60F.3 | Upgrade shared Asset/FX contextual axis settings and localStorage migration | REOPENED - AUTO/INCLUDE0 |
| I60F.4 | Persist duration badges, icons and state in Asset detail | REOPENED - RANGE AVAILABILITY |
| I60F.5 | Mount separate Price/Return measurement tables and pp presentation | COMPLETE 2026-09-12 |
| I60F.6 | Add same-N Asset comparison overlays to Return | COMPLETE 2026-09-12 |
| I60F.7 | Backend/frontend/E2E/manual combined validation and frozen handoff | REOPENED - MANUAL ROUND 2 |

> **Note implementazione (I60F.0, 2026-09-11):** coordinator completed hard
> Gate 0 at clean merge HEAD
> `9d270ccea9b6150eae9421385b3d12301a6e243e`; target
> `4949b2f4c04050e46f643de848894b6706349f34` is a parent/ancestor. Manual-review
> server was already stopped and port 6157 verified free. Developer explicitly
> authorized the complete follow-up contract above. No I20-I50, portfolio,
> i18n, docs, runner, staging or Git-history work is permitted.

> **Note implementazione (I60F.1, 2026-09-11):** hidden calendar-return params
> now accept strict positive integers, retain default 30 and use
> implementation version 1.1.0. Window-one warm-up is exactly
> `minimum=1/stabilization=0/total=1`; all other windows retain exact N-day
> prehistory. Signal-owned date subtraction rejects visible references before
> `date.min` as typed `INSUFFICIENT_HISTORY` and skips only impossible
> pre-visible warm-up points, never clamping dates. `test-author` expanded only
> the registry/risk/Asset-adapter tests. Integrated lane evidence:
> signal-registry 65 pass; calendar risk selector 27 pass / 118 deselected;
> calendar Asset adapter 4 pass / 14 deselected; Ruff green; Black normalized
> the production plugin. Original 7/30/90/365/default behavior, arbitrary
> 1/14/60/1095 windows, invalid params, huge-window unavailable behavior,
> target-currency provenance and legacy observation return are pinned.

> **Fuori pista (I60F desktop E2E measure retention, 2026-09-12):** first
> registered Asset-detail desktop run returned 25 pass / 1 fail. The separate
> Return MeasurePanel retained its definitions, but Calendar-to-Price cleared
> `calendarReturnView`, so its hidden table had no source values and rendered no
> rows. This contradicted the closed two-table preservation contract. Price
> mode now keeps the last completed Return snapshot (still hidden and never
> chart-rendered); entering Return still starts a fresh guarded request.

> **Note implementazione (I60F.2-I60F.6 unit layer, 2026-09-12):** extracted
> `CompactDurationBadge` and migrated DateRangePicker without changing its
> D/W/M/Y, max-999, selector or auto-apply contract. Added fixed-window state
> and account+asset localStorage persistence; shared Asset/FX absolute,
> percentage and semantic-secondary axis profiles with v1→v2 migration;
> contextual axis rows; separate mounted Price/Return measures with `%`, `pp`
> and days semantics; Return-only Asset-comparison filtering and one bulk
> same-window/target-currency query mapped by `asset_id`. `test-author` updated
> ten registered files only. Integrated exact Vitest run passed 258/258 across
> duration, helpers, settings/SSR, axes, measures and filtered signals.
> `front check` is green with 0 errors and 42 merged warnings. Desktop/mobile
> browser execution remains the completion gate.

> **Fuori pista (I60F independent review, 2026-09-12):** independent review
> found five medium defects before final gates: rejected Custom drafts could
> appear committed; chart-settings persistence could serialize comparison
> `_resolvedData`; missing peer points were joined because overlay lines
> defaulted `connectNulls=true`; an in-flight Return request could erase the
> hidden measure snapshot; and style-only comparison edits recomputed the full
> bulk request. Fixes now separate draft/committed values with caller validation,
> strip exactly `_resolvedData` centrally, preserve explicit gaps with
> `connectNulls=false`, retain and refresh the last Return snapshot across mode
> changes, and fingerprint only comparison asset IDs for recomputation. The same
> reviewer re-read all five corrections and marked each resolved.

> **Fuori pista (I60F formatter invocation, 2026-09-12):** two attempted bulk
> Prettier wrappers failed before editing: the first resolved
> `prettier-plugin-svelte` from the repository root, and the second used an
> unsupported `git ls-files --relative` option. The corrected frontend-local
> path pipeline formatted the exact modified frontend set; no dependency,
> generated source or product file was changed by either failed invocation.

> **Fuori pista (I60F style-editor E2E, 2026-09-12):** expanded comparison
> style coverage first attempted to re-click a trigger behind its deliberate
> modal backdrop; switching to the backdrop itself then failed on mobile where
> the centered popover correctly covered that coordinate. Added semantic Escape
> dismissal to `SignalStyleEditor` and changed the test to the keyboard
> contract—no force click, coordinates, timeout increase or retry. The focused
> Calendar workflow then passed on both desktop and mobile.

> **Note implementazione (I60F automated completion, 2026-09-12):** final
> integrated evidence: backend registry 65 pass, calendar risk 27 pass / 118
> deselected, calendar Asset adapter 4 pass / 14 deselected; eight frontend
> unit/component files 266/266; full `front check` 0 errors / 41 merged
> warnings; canonical production build green; Asset detail 26/26 desktop +
> 26/26 mobile; FX detail 14/14 desktop + 14/14 mobile. Strict MkDocs build and
> cross-boundary link check (12/12) are green. Four English user pages document
> the final backend/localStorage/sessionStorage/runtime ownership boundary;
> translated siblings retain expected Aphra debt. Current coordinator target
> advanced to `e1f3fe177861d2b9b953b218f66ea7d4714ab405` after implementation
> started; no merge/rebase was attempted and integration must re-read overlap.

> **Fuori pista (I60F manual review round 2, 2026-09-12):** developer review
> clarified that the Calendar Return reference domain begins at the first
> DateRangePicker day. The previous contract intentionally loaded N pre-visible
> days, so a 1Y range + 1Y window produced almost a full series; this was
> backend warm-up behavior, not frontend caching. New contract: points before
> `selected_start + N` are expected gaps; a range with exactly N elapsed days
> yields one point. Presets longer than the selected elapsed-day span are hidden;
> Custom beyond it is invalid; shrinking the range auto-selects the longest
> fitting preset; a range under 7 days returns to Price and disables Return.
> Review also showed secondary Auto/Include0 were both honoring plugin bounds
> (RSI stayed 0–100). Auto must fit visible data; Include0 must fit visible data
> plus zero; only Custom supplies explicit limits. Server shell 721 was stopped
> immediately and port 6157 proved free before correction work.

> **Fuori pista (I60F E2E interaction repairs, 2026-09-12):** the expanded
> Calendar workflow first exposed the hidden Return measure snapshot reset; its
> product fix is recorded above. Later reruns reached two style-editor test
> interaction defects: desktop tried to re-click a trigger behind the deliberate
> modal backdrop, while mobile tried to click the backdrop through the popover
> centered above it. `SignalStyleEditor` now provides semantic Escape dismissal;
> `test-author` uses that keyboard contract and stable popover state. No force
> click, coordinate selector, timeout increase or retry was introduced.

> **Note implementazione (I60F selected-range correction, 2026-09-12):**
> Calendar Return now constrains every reference target to the selected
> DateRangePicker domain and emits a sorted, unique sparse subset of selected
> dates; the signal service keeps dense output as the default contract and
> validates the explicit sparse opt-in. Calendar Return declares zero
> pre-visible warm-up. Asset detail hides overlong presets, rejects overlong
> Custom windows, selects the longest fitting fallback after range shrink/MAX
> resolution and disables Return below seven elapsed days. Secondary Auto and
> Include 0 now aggregate finite visible extents across every series sharing
> the semantic axis; Custom remains explicit. Backend gates pass 50 signal
> service, 27 selected calendar-risk and 18 Asset-signal tests. Eight focused
> frontend files pass 272/272; selected-range Calendar desktop/mobile and FX
> shared-axis persistence focused browser checks pass. Full Asset detail now
> passes 26/26 desktop and 26/26 mobile after the test-only collection/counter
> repairs below. Full FX detail passes 14/14 desktop and 14/14 mobile. Final
> strict MkDocs build and 12/12 cross-boundary link validation pass. Final
> independent review and audit matrix remains in progress.

> **Fuori pista (I60F final Asset collection, 2026-09-12):** the first full
> Asset-detail rerun stopped before test collection because two new request
> snapshots reused `overlongCalendarRequestCount` in one test scope. No product
> test executed. `test-author` renamed the snapshots for their distinct
> selected-range and provisional-MAX roles; Babel TypeScript parsing and exact
> spec Prettier then passed without changing assertions or production code.

> **Fuori pista (I60F MAX request-counter race, 2026-09-12):** the next
> Asset-detail desktop run passed 25/26 and reached the complete Calendar
> workflow, but its concrete-MAX successor assertion read the route counter one
> microtask before the async route handler incremented it. The request event had
> already captured and validated the exact 30-day successor; no product
> regression occurred. `test-author` replaced only that immediate read with an
> exact `expect.poll` equality. The unchanged post-response equality still
> rejects duplicates. Targeted desktop rerun passed 1/1; exact-file Prettier
> and `git diff --check` passed.

> **Fuori pista (I60F round-2 independent review, 2026-09-12):** final
> independent review found two medium product blockers. First, an all-null
> Calendar Return result reaches `SignalLineSeries`, whose finite-value
> invariant converts the intended typed `UNAVAILABLE/UNDEFINED_METRIC` outcome
> into `FAILED/INVALID_OUTPUT`; the reviewer reproduced the dedicated
> all-unusable test red while 154 neighboring tests passed. Second,
> `setPairSettings()` removes comparison `_resolvedData` from the live reactive
> settings object as well as the serialized localStorage payload, so an
> unrelated axis/style save can erase rendered Asset comparisons without
> triggering the intentionally asset-ID-only reload fingerprint. Current
> authorization permits test repair and validation only, not further production
> edits; workstream is frozen pending coordinator/developer disposition.

> **Note implementazione (I60F blocker 1, 2026-09-14):** explicit surgical-fix
> authorization reopened I60. Calendar Return now detects a non-empty all-null
> selected-range result before constructing `SignalLineSeries` and raises
> `SignalUnavailableError(UNDEFINED_METRIC)` with window and per-status details.
> Generic finite-series validation remains unchanged. The plugin patch version
> is `1.2.1`; regression and integration gates remain pending.

> **Note implementazione (I60F blocker 2, 2026-09-14):** chart-settings live
> normalization now retains complete signal params, including comparison
> `_resolvedData`. A separate storage-copy sanitizer removes exactly that
> runtime field while parsing/writing localStorage; persistence never mutates
> the reactive pair override. Unrelated style/axis saves therefore preserve
> rendered comparisons without widening the asset-ID reload fingerprint.
> Regression and integration gates remain pending.

> **Note implementazione (I60F blocker regressions, 2026-09-14):**
> `test-author` strengthened the existing all-unusable Calendar Return test to
> require `UNAVAILABLE`, `UNDEFINED_METRIC`, no error, complete zero warm-up and
> no series. The existing chart-settings persistence regression now proves
> `_resolvedData` survives live pair/scoped style and axis saves, is absent from
> localStorage, and does not reappear after rehydration; durable private params
> and account/scope isolation remain covered. Exact-file Ruff, Black, AST and
> Prettier checks pass. Both exact red-before-fix selectors now pass: backend
> 1/1 (145 deselected) and frontend 1/1 (1,988 skipped). Broader integration
> gates remain pending.

> **Note implementazione (I60F blocker backend gates, 2026-09-14):** combined
> backend validation passes signal registry 65/65, signal service 50/50,
> complete risk analysis 146/146 and Asset signal adapter 18/18 on isolated
> lane data. This preserves generic dense/sparse output validation while
> confirming the calendar-specific all-null classification.

> **Note implementazione (I60F blocker frontend gates, 2026-09-14):** the exact
> eight-file duration, chart-helper, settings/SSR, axes, measures and filtered
> signal set remains green at 272/272, including the strengthened live-vs-stored
> comparison payload regression.

> **Note implementazione (I60F blocker frontend build, 2026-09-14):** full
> `front check` remains green with 0 errors and 41 known warnings in two
> unrelated files; the canonical production build completes successfully.

> **Fuori pista (I60F build CDN cache, 2026-09-14):** the production build
> could not verify the jsDelivr MathJax certificate, explicitly retained its
> existing cached copy and completed green. No dependency, source or generated
> API edit resulted.

> **Note implementazione (I60F blocker Asset desktop, 2026-09-14):** registered
> Asset detail passes 26/26 desktop, including the complete Calendar Return,
> MAX fallback, comparison, settings, measures and request-race workflow.

> **Fuori pista (I60F runner teardown, 2026-09-14):** after the green desktop
> suite, the runner-owned shared backend did not exit within its five-second
> SIGTERM allowance, so the runner killed its own process group. No manual
> process action or force-server command was used; final port-freedom proof
> remains mandatory.

> **Note implementazione (I60F blocker Asset mobile, 2026-09-14):** the same
> complete Asset detail suite passes 26/26 mobile; its Playwright-owned backend
> completed graceful shutdown.

> **Note implementazione (I60F blocker FX desktop, 2026-09-14):** registered FX
> detail passes 14/14 desktop, including distinct primary scales and semantic
> RSI scale persistence across reload.

> **Note implementazione (I60F blocker FX mobile, 2026-09-14):** the same FX
> detail suite passes 14/14 mobile and its Playwright-owned backend completed
> graceful shutdown.

> **Note implementazione (I60F blocker docs gates, 2026-09-14):** strict MkDocs
> build and all 12/12 frontend/backend-to-doc links remain green. English-only
> ownership documentation is unchanged by the surgical blockers; no
> translation, stamp or docs server was run.

> **Note implementazione (I60F blocker static gates, 2026-09-14):** exact
> changed-file Prettier passes for every frontend TS/Svelte source, Ruff and
> Black pass for all seven changed backend Python files, and `git diff --check`
> is clean. Fresh independent review remains pending.

> **Note implementazione (I60F blocker independent recheck, 2026-09-14):**
> fresh read-only review marks both prior MEDIUM findings resolved and reports
> no significant issue. It confirmed typed all-null unavailability without
> weakening insufficient-history/partial/zero/empty distinctions, plus
> clone-only localStorage scrubbing without shared-reference mutation.
> Residual manual checks are limited to comparison-line flicker after unrelated
> style/axis saves and the rendered all-invalid Calendar unavailable state.

> **Note implementazione (I60F blocker final audit, 2026-09-14):** checkpoint
> inventory is 43 tracked modified files plus two untracked source files, zero
> staged, 45 intended paths total. Forbidden H renderer, D portfolio,
> generated/API, i18n, changelog, navigation and shared-runner surfaces have no
> overlap. HEAD remains `9d270ccea9b6150eae9421385b3d12301a6e243e`;
> target `e1f3fe177861d2b9b953b218f66ea7d4714ab405` is not contained and the
> merge base is `4949b2f4c04050e46f643de848894b6706349f34`; no merge/rebase occurred.
> `git diff --check` is clean and lane port 6157 is free. I60F is ready for the
> no-force manual-review server once the coordinator authorizes it.

> **Fuori pista (I60F manual review round 3, 2026-09-14):** developer rejected
> the review for two distinct work items. A Return Asset comparison selected
> `Amundi MSCI Semico` in EUR but rendered warning/no data although its own
> Asset detail had history and the user had synchronized both the Asset and
> three years of FX; the main Return series remained ready. Triage must preserve
> the exact typed peer status/reason and follow request shape → selected-range/N
> coverage → source dates → evidenced FX route → `asset_id` join/client filter,
> then add a `test-author` regression and fix the root cause. Separately, narrow
> mobile charts show overlapping X-axis labels, especially Dashboard. That item
> is analysis-only pending product review: inventory shared ECharts builders,
> rendered options and affected charts, then propose one responsive policy
> without implementing label hiding/rotation/abbreviation.

> **Note implementazione (I60F review teardown, 2026-09-14):** exact attached
> review shell `38` / uvicorn PID `83656` was stopped immediately after
> rejection. Port 6157 proved free. Lane DB and log evidence were preserved;
> no reset, repopulation, API sync, staging or Git mutation occurred.

> **Fuori pista (I60F preserved-DB inspection, 2026-09-14):** the first
> read-only SQLite lookup assumed an obsolete `assets.symbol` column and failed
> during SQL preparation with `no such column: symbol`; no row or file was
> changed. `PRAGMA table_info(assets)` confirmed current identifier fields and
> the corrected lookup uses only real columns. The preserved manual log records
> FX backward-fill activity and shutdown but does not serialize HTTP request or
> typed response bodies, so the exact payload must be reconstructed from the
> live client contract and preserved DB rather than guessed from access logs.

> **Fuori pista (I60F manual-log parsing, 2026-09-14):** the first `jq`
> extraction stopped at a non-JSON Alembic setup line in the mixed application
> log after writing only a disposable partial file under `/tmp`. The preserved
> lane log and database were read-only and untouched. The corrected evidence
> pass filters JSON-object lines before timestamp selection; no server or test
> rerun is used.

> **Fuori pista (I60F read-only response probe bootstrap, 2026-09-14):** the
> first `/tmp` diagnostic invocation failed before importing LibreFolio because
> Python placed `/tmp`, not the worktree, on `sys.path`
> (`ModuleNotFoundError: backend`). It did not open the DB or append application
> logs. The retry supplies only worktree-local `PYTHONPATH=.` and the assigned
> shared venv; no dependency/environment mutation or data write is involved.

> **Note implementazione (I60F Amundi evidence/root cause, 2026-09-14):**
> preserved DB identifies peer `asset_id=14`, Amundi MSCI Semiconductors
> (`CHIP`), native EUR. It has 364 positive observed rows from 2025-09-14
> through 2026-09-14; only the final weekend is a three-day source gap.
> Manual-session logs reconstruct repeated EUR-target queries over
> 2025-09-14..2026-09-14 after 363 historical rows were synchronized. A
> read-only `AssetSourceManager.get_prices_bulk` probe using the exact two-item
> main+peer shape, `include_price=false` for the peer and 7/30/90/365-day
> windows returns peer status `OK` with 359/336/276/1 points respectively.
> The exact 365-day result has coverage 366/366, 364 observed + 2 backfilled,
> one +72% point on 2026-09-14 and no warnings/errors. Because peer and target
> are both EUR, no FX conversion job exists; synchronized EUR/USD history is
> not causal. Numeric `asset_id=14` is present in the response and the client
> join contract is correct.

> **Note implementazione (I60F Amundi UI diagnosis, 2026-09-14):** the false
> warning is client-side. Calendar comparison summaries pass the first valid
> point (`selected_start + N`, by contract) as generic `firstDate`; shared
> `ChartSignalsSection` interprets every `firstDate > dateStart` as missing
> source history, so even a typed `OK` peer receives a warning. Conversely,
> `CalendarReturnView` reduces typed partial/unavailable/failed results to a
> coarse state, so genuine `insufficient_history`/`undefined_metric` reasons
> become generic no-data. Fix must suppress the generic first-date heuristic
> for Calendar Return and feed each peer's typed backend problem into the
> existing signal-problem formatter, while preserving no-line behavior only
> for true unavailable/failed states.

> **Note implementazione (I60F Amundi client fix, 2026-09-14):** Calendar
> comparison response mapping now retains one typed `SignalProblem` per peer
> from the backend result joined by numeric `asset_id`. Calendar summaries no
> longer feed the expected `selected_start + N` first point into the generic
> price-history warning; typed partial/unavailable/failed problems take
> precedence and ready peers remain warning-free. `undefined_metric` is
> preserved as a first-class problem code and uses the backend warning message
> with the existing unavailable fallback. Signal issue icons expose
> `data-problem-code` for stable, non-translated verification. Missing or
> malformed peer results remain explicit `result_missing`; no peer is silently
> dropped and FX remediation remains outside this identity-EUR path.

> **Fuori pista (I60F typed-reason precedence, 2026-09-14):** review of the
> new regression fixtures exposed an adjacent mapper defect before execution:
> an unavailable result carries generic warning code `data_quality` alongside
> the authoritative `availability.reason_code=insufficient_history`; the old
> null-coalescing order selected the generic warning first, failed to recognize
> it, and fell back to `unavailable`. Problem normalization now resolves the
> typed availability reason first and uses recognized warning codes only as a
> fallback. This also preserves `undefined_metric` when the warning code is
> `undefined_metric_window`.

> **Fuori pista (I60F typed-reason regression, 2026-09-14):** focused frontend
> execution passed 30 tests and failed one existing partial-result test because
> unconditional availability-first precedence changed
> `incomplete_warmup` into the broader `partial_input_coverage`. Precedence is
> now status-aware: unavailable results use their authoritative typed
> availability reason; partial results retain the previous specific warning
> priority. The assertion was not weakened.

> **Fuori pista (I60F lane evidence lifecycle, 2026-09-14):** after completing
> and recording the preserved manual-state investigation, the first canonical
> `services asset-signals` validation automatically recreated the assigned test
> DB before pytest. This was not used as a diagnostic workaround—the Amundi row
> counts/date bounds, exact request probe JSON and filtered manual-session logs
> had already been captured under `/tmp` and in this plan—but the mutable
> post-review SQLite file itself is no longer available. The original
> `librefolio.log` remains preserved. Future manual review requires ordinary
> test fixture population; no attempt will be made to reconstruct or claim the
> discarded DB state.

> **Note implementazione (I60F Amundi focused regressions, 2026-09-14):**
> `test-author` added an owned, rollback-only native-EUR main+peer service
> matrix for 7/30/90/365 days and strengthened the existing Calendar browser
> workflow for `selected_start + N`, exact one-point 365-day output, reversed
> response order and typed ready/partial/unavailable/failed diagnostics.
> Component/pure tests cover typed-problem precedence, machine-readable
> `data-problem-code`, and exact `undefined_metric` formatting. Backend peer
> selector passes 4/4; the corrected frontend mapper/component set passes
> 31/31.

> **Note implementazione (I60F Amundi integration units, 2026-09-14):** full
> Asset signal service file passes 22/22 and the ten-file Calendar/settings/
> measures/problem frontend matrix passes 298/298. This includes all four
> selected windows, native-target currency identity, signal-only peer output,
> status-aware reason precedence and the pre-existing Calendar interaction
> contracts.

> **Fuori pista (I60F Amundi type gate, 2026-09-14):** first post-fix
> `front check` stopped before build with three TypeScript diagnostics in the
> new unknown-response lookup: the compound `find` predicate did not expose its
> record narrowing, so `item.signals` read as `{}` and the nested candidate
> became implicit `any`. The callback now declares an explicit record type
> predicate and the signal array is explicitly `unknown[]`; no cast or generated
> type edit was introduced. The command did not mutate DB or start a server.

> **Note implementazione (I60F Amundi frontend gate, 2026-09-14):** corrected
> `front check` passes with 0 errors and the same 41 known warnings in two
> unrelated files; canonical production build passes. The existing cached
> MathJax copy was retained after the already-recorded jsDelivr certificate
> warning.

> **Fuori pista (I60F Amundi E2E fixture density, 2026-09-14):** full Asset
> desktop passed 25/26; all new peer diagnostics and the 365-day exact-boundary
> assertion passed, but a later measure-table check missed the ready peer. The
> synthetic ready fixture emitted only `selected_start + N` and range end,
> whereas the main measure anchors remained 2026-08-01/02; the real backend
> emits every selected daily point after `start + N`. This is a test-fixture
> assumption, not product state loss. `test-author` is adding the intermediate
> overlapping dates while preserving the exact first point, one-point boundary,
> and original measure expectation. The assertion is not relaxed.

> **Note implementazione (I60F Amundi browser gates, 2026-09-14):**
> `test-author` restored representative ready-peer density by keeping
> `selected_start + N`, the existing measure-anchor dates and range end,
> filtered/sorted/deduplicated; the exact 365-day range still emits one point.
> Registered Asset detail now passes 26/26 desktop and 26/26 mobile, including
> request shape, reversed `asset_id` order, typed peer diagnostics, exact
> boundary, comparison style persistence, measures and stale-response races.
> The desktop runner again killed only its own backend process group after the
> green suite exceeded the five-second SIGTERM allowance; mobile shutdown was
> graceful and final port proof remains pending.

> **Fuori pista (I60F Amundi independent review, 2026-09-14):** fresh review
> found two adjacent medium defects after the primary fix. First, the generic
> generated signal schema accepts some Calendar-invalid `OK` payloads that the
> strict extractor rejects; `getSignalProblem` would otherwise see `OK` and
> reduce them to generic no-data. Peer problem mapping now treats strict-view
> `error` as `result_missing` unless the backend explicitly returned `FAILED`,
> whose calculation error remains authoritative. Second, a ready Calendar peer
> could inherit stale `_conversionFailed` state from Price mode. Calendar
> summaries now mark their backend status authoritative, bypassing only the
> price-overlay conversion issue while leaving the flag intact for Price.
> Page-level comparison/event FX diagnostics are likewise gated to Price mode;
> the main chart FX pair remains active because it is still causal. New
> regressions are delegated to `test-author`.

> **Note implementazione (I60F adjacent-review regressions, 2026-09-14):**
> `test-author` added a schema-valid but Calendar-invalid `OK` peer, ready-peer
> stale Price conversion state, authoritative Calendar bypass, Price
> restoration and page-level FX-banner mode assertions. Component/problem
> selectors pass 33/33 and `front check` remains 0 errors / 41 known warnings.

> **Note implementazione (I60F adjacent-review browser gates, 2026-09-14):**
> full registered Asset detail passes 26/26 desktop and 26/26 mobile with the
> malformed Calendar peer isolated as `result_missing`; a ready peer bypasses
> stale Price conversion/card/banner state in Calendar mode, then restores the
> Price diagnostic and FX banner when switching back. Typed partial,
> insufficient-history and calculation-failure peers remain isolated.

> **Note implementazione (I60F adjacent-review final frontend gates,
> 2026-09-14):** final ten-file chart/settings/problem set passes 300/300;
> production build is green and its embedded Svelte check confirms 0 errors /
> 41 known warnings. The cached MathJax fallback warning is unchanged.

> **Fuori pista (I60F Calendar FX actions recheck, 2026-09-14):** the next
> independent pass found that authoritative Calendar state suppressed the stale
> Price conversion icon and page banner but left the comparison card's add/sync
> FX control visible. The complete comparison FX-control block is now gated to
> non-authoritative (Price) summaries; the asset sync/detail controls and
> currency badge remain available. Stable `signal-fx-create|sync|detail-*`
> selectors were added for non-translated regression coverage. Price behavior
> is preserved; `test-author` validation is pending.

> **Fuori pista (I60F FX-action component fixture, 2026-09-14):** first
> component run passed 6/8 and failed the two new action tests before their
> assertions because `definitions: []` prevents the Asset-comparison parameter
> and FX-control branch from mounting. Mere action absence would therefore be
> vacuous. `test-author` is supplying a minimal real comparison definition and
> asset metadata, retaining the parameter presence barrier and action
> assertions; no product change or assertion removal is accepted.

> **Note implementazione (I60F FX-action test repair, 2026-09-14):** the
> component fixture now supplies a minimal real local Asset-comparison
> definition, configured asset 42 (USD), EUR display target, configured
> EUR-USD pair and create/sync callbacks. Both authoritative Calendar and
> ordinary Price modes mount the actual parameter/FX controls; the exact
> component file passes 8/8 with all presence and action assertions intact.

> **Fuori pista (I60F final state-boundary review, 2026-09-14):** another
> independent pass found three medium cross-state leaks. Changing a comparison
> `assetId` retained the old target's resolved points, conversion error and
> metadata; the actual parameter update path now removes exactly the
> target-specific runtime keys before emitting the replacement config. Calendar
> partial undefined windows carried typed `partial_undefined_metric` plus an
> unrecognized `undefined_metric_window` warning; problem selection now chooses
> the first recognized candidate with status-aware precedence, and formats the
> typed partial reason using the backend message/existing partial fallback.
> Finally, same-route Asset navigation could preserve mounted Calendar measure
> anchors into the next asset; `MeasurePanel.clearMeasures()` resets committed,
> pending, expanded, table-ref, ID/debounce and mode state, and `reloadPage()`
> invokes it for both Price and Calendar panels before loading the new asset.
> `test-author` regressions are pending; no B axis implementation was added.

> **Note implementazione (I60F final state regressions, 2026-09-14):**
> `test-author` drives the real Asset SearchSelect and proves all eight
> target-runtime fields clear while style/durable params survive; maps and
> formats `partial_undefined_metric` without weakening `incomplete_warmup`; and
> invokes `MeasurePanel.clearMeasures()` after completed + pending work, proving
> rows, overlays, mode, refs and ID sequence reset before a fresh measure. The
> four exact files pass 57/57.

> **Note implementazione (I60F final state frontend gates, 2026-09-14):**
> complete ten-file chart/settings/problem matrix passes 304/304; `front check`
> remains 0 errors / 41 known warnings and canonical production build is green.

> **Note implementazione (I60F final state browser gates, 2026-09-14):**
> complete Asset detail remains green at 26/26 desktop and 26/26 mobile after
> peer-target runtime cleanup, typed partial-undefined mapping and same-route
> measure resets.

> **Fuori pista (I60F comparison async boundary, 2026-09-14):** final review
> found the shared Price-comparison loader mutated captured signal configs
> before the caller's stale-response guard and merged its event map with prior
> peers. A late range/currency/peer response could therefore overwrite current
> points or retain removed-peer markers/FX diagnostics. The loader now accepts
> immutable peer IDs and returns per-peer runtime params/events without touching
> caller state; a shared apply step mutates only current configs after validation
> and rebuilds events solely from current peers. Asset detail adds a dedicated
> generation + fingerprint over route/session, Price mode, peer IDs, range and
> target currency; FX detail applies the same contract over route direction,
> session, peer IDs and range. Empty peer sets invalidate in-flight work and
> clear events. `test-author` owns loader/race regressions; B axis code remains
> untouched.

> **Note implementazione (I60F immutable comparison loader tests,
> 2026-09-14):** `test-author` rewrote the loader suite as 18 immutable
> load/apply contracts covering deduped IDs, request shape, response order,
> nonmutation, currency filtering/provenance, explicit missing-result clears,
> current-peer-only application, explicit eight-field invalidation and
> event-map replacement. The existing Asset workflow now gates an old
> long-range Price comparison response against a
> 90-day successor and asserts current points/events/FX state survive. Loader
> tests pass 18/18 and `front check` remains 0 errors / 41 known warnings.

> **Fuori pista (I60F immutable apply boundary, 2026-09-14):** after request-
> manager integration, the loader test passed 16/17: `applyComparisonAssetsData`
> cleared a current config absent from that particular loaded result, while the
> immutable contract correctly expects unmatched configs to remain untouched.
> Explicit changed-fingerprint invalidation is now a separate
> `clearComparisonAssetsData` operation; normal apply clears/replaces only
> returned current peers. `test-author` is adding the direct clear contract.

> **Fuori pista (I60F comparison race E2E string ID, 2026-09-14):** first
> desktop run passed 25/26 but could not render the expected FX action because
> seeded comparison configs used numeric IDs while the real SearchSelect stores
> strings; request code coerced the numbers and masked the invalid card
> precondition. `test-author` switched only seeded/persisted ID expectations to
> strings; numeric bulk requests remain asserted. The immutable stale-vs-
> successor workflow then passes in full: Asset detail 26/26 desktop and 26/26
> mobile.

> **Note implementazione (I60F immutable comparison integration,
> 2026-09-14):** final eleven-file loader/chart/settings/problem matrix passes
> 323/323; production build and embedded Svelte check are green (0 errors / 41
> known warnings). Shared FX caller browser validation remains pending.

> **Note implementazione (I60F immutable comparison browser gates,
> 2026-09-14):** shared FX caller passes 14/14 desktop and 14/14 mobile. The
> strengthened Asset stale-vs-successor workflow and all surrounding detail
> behavior pass 26/26 desktop and 26/26 mobile. Both Playwright-owned mobile
> servers shut down normally; lane teardown is rechecked at final audit.

> **Fuori pista (I60F comparison race E2E fixture ID, 2026-09-14):** full
> desktop reached the successor state but failed its ready-peer FX-action
> assertion. The snapshot showed all comparison SearchSelect controls unresolved:
> seeded configs used numeric `assetId`, while the real control and
> `getParamString` contract store string IDs. Page-level numeric coercion still
> produced requests/summaries, masking the invalid card precondition.
> `test-author` is switching seeded IDs to the real string shape and updating
> only persisted-value assertions; numeric request/join and all race/action
> assertions remain unchanged.

> **Note implementazione (I60F FX-action integration gates, 2026-09-14):**
> complete ten-file chart/settings/problem matrix remains 300/300; `front
> check` is 0 errors / 41 known warnings and the production build is green
> after the final FX-control gate.

> **Note implementazione (I60F FX-action browser gates, 2026-09-14):** complete
> Asset detail remains green at 26/26 desktop and 26/26 mobile after hiding
> stale comparison FX remediation in authoritative Calendar mode and preserving
> it in Price. Desktop runner-owned backend again exceeded its five-second
> teardown allowance; mobile shutdown completed normally.

> **Note implementazione (I60F comparison request-manager closure,
> 2026-09-14):** ordinary same-fingerprint loads now coalesce; style-only
> signal edits do not request; force refreshes supersede in-flight work while
> retaining already-applied same-fingerprint data if the refresh fails. A
> changed fingerprint clears current runtime/events before loading so failure
> cannot present old data under a new peer/range/currency. FX session and route
> orientation changes invalidate comparison state and chain a replacement load.
> Final shared results: loader 18/18, eleven-file matrix 322/322, Asset detail
> 26/26 desktop + 26/26 mobile, FX detail 14/14 desktop + 14/14 mobile.

> **Fuori pista (I60F comparison FX-sync closure, 2026-09-14):** closure
> review found the Asset-page FX sync action refreshed the FX store and main
> chart but not comparison runtime/events. The handler now invalidates any
> pre-sync comparison request immediately. After a successful sync, Price mode
> force-loads the same-fingerprint comparison so corrected points/events/
> conversion status publish; Calendar mode clears stale hidden Price runtime
> and relies on its refreshed typed Calendar response, forcing a new Price load
> when the user returns. Failed sync retains the last applied valid comparison.
> `test-author` regression is pending.

> **Fuori pista (I60F definitive review follow-up, 2026-09-14):** review also
> found that Asset sync itself did not invalidate a pre-sync Price comparison,
> migrated chart settings stayed unsanitized on disk until a later edit, and
> zero-warm-up Calendar `insufficient_history` rendered a contradictory
> “0 required”. Asset sync now invalidates before I/O; successful Price sync
> force-refreshes peers, successful Calendar sync clears hidden Price runtime
> after its typed Calendar reload, and failed sync retains the last applied
> data. Hydration immediately rewrites sanitized/migrated payloads under the
> same localStorage key. Zero-required insufficient history uses its exact
> backend reason; ordinary positive-required signals keep localized counts.
> `test-author` regressions are pending.

> **Note implementazione (I60F definitive-review regressions, 2026-09-14):**
> `test-author` extended the existing workflow with pre-sync Price response →
> Calendar Asset sync → Price successor → late-old-response rejection; added
> immediate v1/v2 storage sanitization checks across account/global/scope/pair
> state; and pinned zero-vs-positive insufficient-history formatting. Focused
> storage/formatter tests pass 64/64 and `front check` remains 0 errors / 41
> known warnings.

> **Fuori pista (I60F FX-sync mobile activation, 2026-09-14):** final desktop
> passes 26/26. Mobile reached the visible/enabled FX sync action, but its
> pointer click was intercepted after scrolling by the sticky header/mobile
> chevron; the armed response waiter then timed out. `test-author` is switching
> only this activation to focus + Enter, the semantic button keyboard contract.
> No force click, coordinate action, timeout increase or product edit is
> permitted.

> **Fuori pista (I60F FX-action keyboard semantics, 2026-09-14):** focus +
> page-level Enter still emitted no request on mobile. The focused native button
> was nested in Tooltip's default role-button wrapper; the wrapper's bubbling
> keydown handler called `preventDefault`, cancelling the child's native Enter
> activation. FX create/sync tooltips now declare `interactiveChild`, removing
> wrapper keyboard semantics and preserving the button's own accessible
> behavior. The same unchanged mobile regression verifies the fix.

> **Note implementazione (I60F asset-sync closure gates, 2026-09-14):**
> `test-author` extended the existing workflow through pre-sync Price request,
> Calendar Asset sync, Price successor and late-old-response rejection. Final
> Asset detail passes 26/26 desktop and 26/26 mobile, including native keyboard
> activation and the corrected comparison/measure state.

> **Note implementazione (I60F definitive frontend gates, 2026-09-14):**
> final eleven-file loader/chart/settings/problem matrix passes 327/327;
> `front check` remains 0 errors / 41 known warnings and canonical production
> build is green after asset-sync invalidation, eager storage rewrite and
> zero-warm-up reason formatting.

> **Fuori pista (I60F FX action accessible names, 2026-09-14):** final review
> found the icon-only create/sync FX buttons had no accessible names after their
> Tooltip wrappers were correctly marked `interactiveChild`. Both native
> buttons now carry localized `aria-label` values identifying the action and
> pair; Tooltip text remains visual help. `test-author` owns the direct
> accessibility assertions.

> **Fuori pista (I60F sync result status, 2026-09-14):** closure review found
> HTTP 200 sync envelopes with per-item `failed`, `skipped` or missing status
> still entered refresh/clear paths. Both Asset and FX handlers now render the
> standard result toast first, then treat only `ok` and `partial` as data-
> changing success. Failed/skipped/missing results retain applied comparison
> runtime/events while the already-bumped generation still prevents a pre-sync
> response from publishing. `test-author` failure-path coverage is pending.

> **Fuori pista (I60F failed-sync mode fixture, 2026-09-14):** first desktop
> execution of the new failed-FX scenario entered Calendar and then expected
> the Price-only FX sync action to remain visible, contradicting the already
> closed authoritative-Calendar contract. `test-author` is keeping the full
> HTTP-200/per-item-failed retention and late-response assertions in Price,
> then entering Calendar for the existing accepted Asset-sync flow. Only the
> impossible precondition moves; no counter/state assertion is removed.

> **Note implementazione (I60F sync-status browser closure, 2026-09-14):**
> final failed/partial/ok sync matrix passes in the full Asset workflow:
> 26/26 desktop and 26/26 mobile. Failed HTTP-200 item status emits the error
> toast, invalidates the pending response, launches no conversion/comparison/
> Calendar successor and retains the applied Price comparison. Accepted FX and
> Asset sync paths still refresh and reject late pre-sync payloads.

> **Note implementazione (I60F definitive closure review, 2026-09-14):**
> final independent review reports CLEAN for sync status gating, comparison
> request invalidation/retention, eager localStorage sanitization, zero-warm-up
> messaging and native accessible FX controls. It confirms B remains analysis-
> only. Residual manual checks are the real Amundi 7/30/90/365 flow,
> Calendar↔Price FX restoration, measure rows through live sync/same-route
> navigation, and FX keyboard/touch/screen-reader behavior.

> **Note implementazione (I60F FX action accessibility tests, 2026-09-14):**
> real configured/missing FX controls are selected by stable test ID; both
> `aria-label` and computed accessible name identify action + pair using
> existing translations. Exact ChartSignalsSection component suite passes 9/9.

> **Note implementazione (I60F accessibility closure gates, 2026-09-14):**
> final Asset detail passes 26/26 desktop and 26/26 mobile after the localized
> native-button labels; the mobile workflow activates FX sync through focused
> Enter and completes both FX-sync and Asset-sync stale-response barriers.

> **Note implementazione (I60F exact-final shared FX gates, 2026-09-14):**
> after every shared settings, comparison-manager and accessible-control change,
> FX detail passes 14/14 desktop and 14/14 mobile on the exact final source.

> **Note implementazione (I60F FX-sync mobile closure, 2026-09-14):** after
> `interactiveChild`, the full Asset detail suite passes 26/26 mobile including
> focused native Enter activation, exact sync payload, forced corrected peer
> response and rejection of the late pre-sync payload.

> **Fuori pista (I60F FX-convert route fixture scope, 2026-09-14):** the next
> desktop run passed the complete sync correction, then a legitimate later
> long-range FX conversion hit the new global mock, which asserted every
> post-sync request used the earlier 90-day range. `test-author` is narrowing
> the exact payload/counter to the sync-specific call and returning coherent
> deterministic data for other valid ranges. The sync count remains exactly
> one; no product change or assertion removal is required.

> **Fuori pista (I60F comparison-card reactivity, 2026-09-14):** the first FX
> sync browser run confirmed the forced corrected response but the card's sync
> action stayed visible. Runtime mutation already refreshed overlay lines and
> summaries through `overlayDataVersion`; the separately compiled
> `signals={[...signals]}` prop depended only on settings identity, so
> ChartSignalsSection retained the old conversion flag. Asset and FX pages now
> derive panel configs from both settings and `overlayDataVersion`, publishing
> post-guard runtime changes without persisting them. The existing sync
> regression remains unchanged and must turn green.

> **Fuori pista (I60F comparison-card object identity, 2026-09-14):** the
> follow-up desktop run still showed the stale sync action although corrected
> summaries had landed. The panel's bindable local signal array retained its
> previous object identities; rebuilding only the outer array was insufficient
> to publish deep runtime-param changes. Asset and FX panel configs now clone
> each signal and `params` whenever `overlayDataVersion` changes, forcing the
> child to consume current conversion metadata without persisting runtime data.

> **Fuori pista (I60F measure overlay reactivity, 2026-09-14):** the same
> desktop run proved corrected peer cards/points/events but a later restored
> Price measure table showed only the main row. `MeasurePanel`'s measurement
> derived value tracked measures and chart data, while its summary helper's
> `overlaySignals` dependency was opaque to Svelte's compiler. The derived
> calculation now explicitly tracks overlay changes, so mounted measure rows
> disappear while peer runtime is intentionally cleared and repopulate when the
> guarded Price response lands, without recreating the measure. `test-author`
> rerender coverage is pending.

> **Fuori pista (I60F Price-race measure fixture, 2026-09-14):** after the
> MeasurePanel dependency fix, the full desktop workflow still reached a
> main-only Price measure table. Current peer cards correctly showed the
> successor points, but that synthetic series contained only 90-day range
> start/end while the preserved measure anchors were the interior
> 2026-08-01/end dates. Real daily history contains the interior anchor.
> `test-author` is adding it, changing the successor badge from two to three
> points while retaining the stale one-point contrast and every race/event/FX
> assertion. No product change or expectation removal is involved.

> **Note implementazione (I60F comparison closure gates, 2026-09-14):**
> final request-manager, FX-sync, runtime-publication and measure-overlay
> behavior passes loader 18/18, eleven focused files 323/323, Asset detail 26/26
> desktop + 26/26 mobile, and FX detail 14/14 desktop + 14/14 mobile. `front
> check` and production build remain green; exact static audit is clean.

> **Note implementazione (I60F defect-A closure review, 2026-09-14):** final
> independent read-only review remains pending after the FX-sync correction.
> Manual checks, once green, remain the real Amundi 7/30/90/365 flow,
> Calendar↔Price FX restoration, measure rows through live sync/same-route
> navigation, and keyboard/touch/screen-reader behavior.

> **Fuori pista (I60F manual review round 4, 2026-09-14):** developer confirmed
> that a three-year Amundi Calendar comparison works only after separately
> synchronizing EUR/USD over the same range. The peer Asset sync currently does
> not orchestrate its already-configured conversion FX pair, and the signal
> surfaces the conversion gap as generic missing `close`. Review also rejected
> native-looking Custom min/max typography, bare unit-only names for every
> configurable Y-axis row, and the still-visible mobile X-axis overlap on
> Dashboard. Exact review server shell 846 was stopped; port 6157 proved free.

> **Note implementazione (I60F A1-A3+B authorization, 2026-09-14):** coordinator
> relayed explicit implementation authorization. A1 synchronizes a comparison
> Asset plus every already-configured required conversion pair for the same
> selected range, never auto-registering a missing pair, and preserves exact FX
> causality. A2 fixes compact numeric typography at the shared mobile anti-zoom
> cascade. A3 gives every shared Asset/FX primary and contextual secondary Y
> axis a localized semantic name; locale catalogs stay coordinator-owned and I
> emit `/tmp/libreFolio_i60_axis_i18n_lease.json`. B applies one width-budget,
> locale-aware, 0-degree responsive X-axis policy to Line, Candlestick,
> PriceChartFull, Growth, AllocationHistory and the three lot charts;
> PerformanceChart stays exempt. New/repaired tests remain `test-author` owned.
> No target merge, staging, history, D portfolio, H renderer, shared runner or
> generated API changes are authorized.

> **Note implementazione (I60F A1, 2026-09-14):** comparison Asset sync now
> resolves the peer native currency against the current target, filters to
> already-configured route slugs, and submits those pairs in one FX sync for
> the exact Asset sync range. Asset and FX outcomes are independent; any
> accepted `ok|partial` leg triggers the guarded Calendar/Price recompute,
> while failed legs retain applied data. Missing pairs are never registered.
> Calendar peer mapping converts conversion-error-backed missing-close results
> into typed `fx_conversion_unavailable` with the exact backend cause; truly
> missing close remains `missing_input_fields`. Tests pending.

> **Note implementazione (I60F A2, 2026-09-14):** Custom min/max use the shared
> `lf-compact-number-input` typography contract. Desktop keeps Tailwind's
> 0.75rem/1rem compact scale; the existing mobile anti-zoom rule still enforces
> 16px, now paired with intentional inherited font, tabular numerals and a
> coherent 1.25rem line-height. Surrounding Min/Max labels scale with the same
> responsive row. No user-agent or browser-specific branch was added.

> **Note implementazione (I60F A3, 2026-09-14):** new pure
> `axisLabelHelpers.ts` resolves every Asset/FX configurable axis row through
> semantic keys: price+currency, percentage, exchange-rate+pair, volume and a
> generic signal-name axis for RSI/MACD/etc. Bare `%`/currency labels are gone.
> Fallback English prevents raw keys before catalog integration. Exact EN/IT/
> FR/ES lease is `/tmp/libreFolio_i60_axis_i18n_lease.json`; locale files remain
> untouched.

> **Note implementazione (I60F A3 i18n lease integration, 2026-09-14):**
> coordinator applied the exact five-key lease to all four locale catalogs in
> this worktree. Source artifact SHA-256 is
> `276a56281e95cbd723e235a1f9dd810814f0c029dfdcc03f6a6eb9adf5c8d807`;
> integrated patch `/tmp/libreFolio_i60_axis_i18n_integrated.patch` SHA-256 is
> `95d2e25ec8b0c28dbd6cf764d2f8d90d4517679158a718d0e306df764d2e25`. I18n
> audit reports 2765/2765 complete, zero incomplete/missing-backend and only
> 122 pre-existing/shared unused keys; locale Prettier and diff-check pass.
> Locale files remain coordinator-owned and will not be edited by I.

> **Note implementazione (I60F B, 2026-09-14):** new shared
> `responsiveXAxis.ts` computes usable-width/density compact mode, locale-aware
> day/month/multi-year labels, category stride or time split budget, preserved
> endpoints, `hideOverlap` and rotation 0. It is wired into LineChart,
> CandlestickChart, PriceChartFull, GrowthChart, AllocationHistoryChart,
> LotGantt, LotComparison and LotWacPrice. Resize callbacks patch xAxis only,
> preserving dataZoom; resolution renders recompute the policy. PerformanceChart
> is untouched. No 30-degree fallback was added. Tests pending.

> **Note implementazione (I60F A1-A3+B test-author coverage, 2026-09-15):**
> existing registered suites now cover A1 orchestration/causality and all
> accepted/failed leg combinations; A2 compact class, decimal and arrow
> interaction plus mobile computed typography; A3 exact semantic keys/params/
> fallbacks; and B thresholds, density, stride, endpoints, time budgets,
> locale/multi-year formatting, rotation 0, eight chart adoptions and explicit
> PerformanceChart exclusion. Tests live only in registered
> `asset-detail.spec.ts`, `chartCoreHelpers.test.ts` and
> `ChartSignalsSection.test.ts`; inventory remains 197/197 with zero orphans.
> Focused component/helper execution passes 52/52.

> **⚠️ Fuori pista (I60F A1 fixture schema, 2026-09-15):**
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
> --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts front-asset
> asset-detail` reached Playwright and passed 25/26 tests, but the extended
> Calendar workflow stopped at its own precondition because
> `buildFxConversionGapCalendarResult(30)` did not satisfy the current generated
> `SignalResult` schema (`asset-detail.spec.ts:1181`). No product assertion ran
> for that fixture; the runner populated only the isolated lane DB and stopped
> its shared backend. Repair is test-author-owned before rerunning the selector.

> **⚠️ Fuori pista (I60F A1 sync-idle observation, 2026-09-15):**
> test-author corrected the FX-gap warning code from invalid
> `missing_input_fields` to schema-valid `data_quality`, retaining
> `availability.reason_code=missing_input_fields`, and the fixture now parses.
> The next run again reached 25/26, then exposed a test assumption: after the
> native comparison Sync button disables itself during the async operation, the
> browser moves focus away, so `document.activeElement` becomes non-button
> (`null`) and cannot prove idle. Added stable
> `signal-sync-asset-${signal.id}` instrumentation; the regression must wait for
> that exact control to become enabled, not infer readiness from focus.

> **⚠️ Fuori pista (I60F date-range commit assumption, 2026-09-15):**
> after the exact sync-button idle barrier passed, the workflow reached the next
> range transition but `commitSyntheticRange()` tried to commit by clicking
> `asset-detail-info`. The open DateRangePicker backdrop and retained failure
> toasts legitimately intercepted that unrelated target, then the expected
> response timed out. This is a test interaction assumption, not a product
> failure: the helper must use the picker's documented keyboard commit/close
> contract on the focused end field.

> **Note implementazione (I60F Asset desktop gate, 2026-09-15):**
> test-author changed the FX-gap warning to schema-valid `data_quality`, waits
> for the exact `signal-sync-asset-${signalId}` control to re-enable, and commits
> synthetic date ranges with Enter on the focused end input. All request,
> response, typed-causality, keyboard activation and closed-picker assertions
> remain. Exact registered lane command now passes 26/26 desktop Asset-detail
> tests; the runner stopped its shared backend (forced process-group teardown
> only after its normal five-second SIGTERM grace period).

> **⚠️ Fuori pista (I60F mobile runner syntax, 2026-09-15):**
> appending `--project mobile` to `dev.py test ... front-asset asset-detail`
> failed at argument parsing before setup (`unrecognized arguments`), so no DB,
> files or server were touched. The registered action is intentionally
> desktop-only; mobile must use the same registered spec's Playwright project
> with explicit `TEST_PORT=6157` and
> `LIBREFOLIO_TEST_DATA_DIR=/tmp/librefolio-r2-i-charts`.

> **⚠️ Fuori pista (I60F mobile Playwright venv, 2026-09-15):**
> the first direct mobile-project invocation failed before collection: its
> Playwright webServer runs repository `./dev.py`, and invoking npm outside
> Pipenv selected an interpreter without `pydantic`. Port 6157 remained free;
> no product test ran and no dependency was installed. The corrected invocation
> wraps npm itself in the mandated shared `LibreFolio-SAUMUTtc` Pipenv so the
> spawned webServer inherits the approved interpreter.

> **Note implementazione (I60F Asset mobile gate, 2026-09-15):**
> the corrected shared-venv mobile invocation passed 26/26 in 1.5 minutes,
> including A1 configured-FX orchestration and exact typed causality, A2
> computed compact-input typography, comparison refresh/race coverage and all
> existing Asset-detail mobile interactions. Together with desktop, the
> registered Asset spec is green 52/52. Playwright shut down PID 94891 through
> its attached webServer lifecycle.

> **Note implementazione (I60F focused/full frontend gates, 2026-09-15):**
> registered Asset helper suite passed 277/277; registered Svelte component
> suite passed 1805/1805 (only existing deprecation/localStorage warnings).
> Full `front check` returned 0 errors / 41 baseline warnings. Canonical
> production build completed both bundles in 17.05s / 27.20s; the external
> MathJax refresh hit the known local certificate failure and retained the
> cached resource, without failing the build.

> **⚠️ Fuori pista (I60F A3 shared-modal audit, 2026-09-15):**
> docs source verification found that Asset/FX detail panels used the approved
> semantic axis resolver, but the shared global/per-card
> `ChartSettingsModal` still built configurable rows as bare `Abs`, `%` and raw
> secondary labels. This contradicts A3's every-row contract. The modal now
> reuses the same five-key resolver, receives explicit Asset/FX domain plus
> currency/pair context from both list pages, and keeps `Preview` as the
> localized global synthetic context. No locale key or catalogue changed.

> **Note implementazione (I60F A3 modal coverage, 2026-09-15):**
> test-author extended the registered `chartCoreHelpers.test.ts` contract to
> require all four semantic resolvers in `ChartSettingsModal`, reject bare
> `Abs`/`%`/raw secondary row labels and require explicit Asset/FX domain plus
> context at both list-page consumers. Focused file passes 43/43; Prettier and
> scoped diff-check pass.

> **⚠️ Fuori pista (I60F FX modal translator alias, 2026-09-15):**
> the first post-gap full check failed before build with exactly two diagnostics
> at the new FX list binding: that page imports the i18n store as `_` and
> therefore exposes `$_`, not `$t`. Replaced only that alias; no runtime,
> storage or localization contract changed.

> **Note implementazione (I60F A3 modal/browser revalidation, 2026-09-15):**
> registered Asset unit suite passes 280/280; full check is again 0 errors /
> 41 baseline warnings; production bundles complete in 17.32s / 28.13s.
> FX global settings modal passes 3/3 on desktop and 3/3 on mobile after the
> semantic-row correction. Asset-list consumers pass 24/24 on each viewport.

> **Note implementazione (I60F B browser gates, 2026-09-15):**
> Dashboard registered chart/view-matrix spec passes 6/6 desktop and 6/6
> mobile. Broker-detail passes 25/25 on each viewport, including WAC,
> Gantt and comparison chart rendering/interactions. FX detail/settings passes
> 17/17 desktop and 17/17 mobile before the shared-modal correction; the
> corrected modal-specific rerun remains green 6/6 across viewports.

> **Note implementazione (I60F docs/i18n/static audit, 2026-09-15):**
> docs-writer aligned the four owned English pages with comparison Asset+FX
> sync, exact conversion causality, semantic axes across detail/global/per-card
> surfaces, compact Min/Max controls, responsive X axes and the storage
> ownership matrix. Strict MkDocs build and all 12 cross-boundary links passed;
> translation validation honestly reports substantive existing EN→IT/FR/ES
> debt, so no stamp was applied. i18n audit is 2765/2765 in all four locales,
> 0 incomplete, 0 missing backend keys and 122 pre-existing/shared unused.
> Full frontend Prettier, backend Ruff and Black checks pass.

> **⚠️ Fuori pista (I60F independent review blockers, 2026-09-15):**
> fresh read-only review found six actionable gaps before manual review:
> (1) the new modal-adoption test hard-coded `$t` although FX uses `$_`;
> (2) peer Asset and FX sync legs read live range/context on opposite sides of
> an await, permitting mixed requests after navigation/range changes;
> (3) compact X-axis formatters are omitted rather than explicitly cleared on
> compact→desktop merge updates;
> (4) global/per-card axis scales saved by the shared modal do not reach
> `AssetCard`/`FxCard` through `PriceChartCompact`;
> (5) inverted FX cards label the modal axis with canonical rather than displayed
> pair direction; and (6) comparison errors do not distinguish price conversion
> from third-currency event conversion, so sync can target the wrong FX route.
> Manual review remains blocked until all six have focused regressions and the
> full affected gates return green.

> **Note implementazione (I60F independent-review fixes, 2026-09-15):**
> all six blockers were corrected surgically. The adoption test now recognizes
> the consumer's actual Svelte translation-store alias; responsive policy
> always supplies a desktop formatter and lot charts preserve their historical
> formatter through the same helper; compact Asset/FX cards forward active
> primary and semantic-secondary profiles; FX modal context follows persisted
> inversion; comparison loading flags price conversion only from surviving
> non-target price rows; converted/failed event currencies produce explicit,
> deduplicated configured dependencies; and peer Asset+FX calls launch from one
> captured range/context with stale-publication guards. No missing FX route is
> registered.

> **Note implementazione (I60F review-regression coverage, 2026-09-15):**
> test-author added coverage only to existing registered files:
> `chartCoreHelpers.test.ts`, `loadComparisonData.test.ts` and
> `asset-detail.spec.ts`. Focused helper/loader tests pass 74/74. The expanded
> Asset desktop workflow passes 28/28, including native+third-event FX pairs,
> identical captured ranges, stale range/context suppression, event-only error
> isolation and the accepted/failed leg matrix. Targeted Prettier and full
> diff-check pass.

> **⚠️ Fuori pista (I60F formatter reset typing, 2026-09-15):**
> the first explicit reset used `formatter:null`, which is accepted by ECharts
> at runtime but rejected by its TypeScript axis option. No build ran. The
> policy now always returns a concrete formatter: compact uses its budget-aware
> label, general desktop uses the shared locale-aware full date, and lot charts
> inject their existing multi-year desktop formatter. This both replaces stale
> compact merge state and stays type-safe without casts.

> **⚠️ Fuori pista (I60F second independent review, 2026-09-15):**
> the follow-up review found four further edge cases before manual review:
> Calendar comparison requests omitted peer events and therefore could not know
> third-currency dependencies in that mode; sync start invalidated an initial
> comparison load even if both sync legs failed; MAX correctly sent `min` to
> both backend sync legs but reused that sentinel for the in-memory FX cache
> refill; and exact 365/366-day spans could format both endpoints without a
> year. Calendar peer requests now fetch and atomically retain events without
> rendering their markers, comparison invalidation waits for an accepted leg,
> backend and concrete cache ranges are snapshotted separately, and year-bearing
> labels begin at 365 elapsed days.

> **Note implementazione (I60F second-review regression/gates, 2026-09-15):**
> test-author extended the existing Asset-detail and chart helper suites for
> Calendar peer `include_events`, third-currency dependency sync in Calendar
> mode, total-failure preservation of the initial comparison request, separate
> MAX backend/cache ranges and exact 365/366-day endpoint disambiguation.
> Focused responsive tests pass 51/51; Asset detail passes 28/28 on desktop and
> 28/28 on mobile; core suite passes 1992/1992. Final combined Dashboard +
> broker-detail execution passes 62/62 across desktop/mobile. Full Prettier,
> Svelte check (0 errors / 41 baseline warnings) and production build
> (19.04s / 37.41s bundles) pass.

> **⚠️ Fuori pista (I60F third independent review, 2026-09-15):**
> a third review found four adjacent lifecycle/edge gaps: standalone required-FX
> Sync still invalidated comparisons before success and used a resolved start
> for MAX; a late Calendar response could publish removed peer events because
> its peer fingerprint was not checked; local-midnight subtraction made a
> 365-day span shorter across DST; and GrowthChart's series-only resolution
> update did not refresh its x-axis policy. The standalone path now snapshots
> and guards the full context, defers invalidation until accepted, separates
> backend `min` from concrete cache range and preserves Calendar peer events.
> Calendar peer publication checks the captured comparison fingerprint, day
> spans use UTC calendar dates, and GrowthChart updates xAxis together with
> series/dataZoom.

> **⚠️ Fuori pista (I60F standalone-FX mobile test activation, 2026-09-15):**
> the third-fix Asset mobile run reached 27/28; the new MAX standalone-FX
> regression timed out before emitting its request because a mobile reorder
> chevron overlapped the button's mouse hit point. The exact Sync button was
> visible and enabled, so this is a pointer-assumption in the test, not missing
> product wiring. The regression must activate that focusable control with
> keyboard Enter, preserving the accessible path without force-click or sleep.

> **Note implementazione (I60F third-review regression/gates, 2026-09-15):**
> test-author added existing-suite coverage for stale Calendar peer-event
> suppression, standalone FX failure/acceptance/context/MAX behavior, DST-safe
> 365/366-day labels and GrowthChart xAxis+dataZoom updates. Focused tests pass
> 52/52; Asset detail passes 28/28 on desktop and, after replacing an overlapped
> mobile mouse click with focus+Enter, 28/28 on mobile. Core passes 1992/1992;
> combined Dashboard+broker-detail passes 62/62 across both projects. Full
> Prettier, Svelte check and production build pass.

> **⚠️ Fuori pista (I60F fourth independent review, 2026-09-15):**
> the lifecycle review found three last races: accepted sync invalidation still
> waited until after FX cache refill; one global standalone-FX generation token
> made different slugs supersede each other; and MAX resolution in Price could
> reject a provisional comparison without scheduling its concrete successor.
> Accepted coordinated/standalone syncs now invalidate chart+comparison
> generations before the first post-acceptance await, while all-failed requests
> remain untouched. Standalone generations are keyed per slug and the spinner
> remains active until the map empties. Resolving MAX in Price schedules one
> forced concrete-range comparison successor.

> **⚠️ Fuori pista (I60F lifecycle regression diagnosis, 2026-09-15):**
> the new concurrent-route regression first exposed a real Svelte keyed-list
> crash: two `FX_PAIR_NO_DATA` rows shared the same `code`-only key, aborting
> the reactive flush after comparison runtime data was applied. Every per-pair
> missing/no-data/partial issue now carries `group_key=pair.slug`. The MAX
> successor was already accepted and rendered in Candlestick mode; its test
> helper falsely returned no series because Candlestick did not expose the
> `__lfChart` E2E/gallery hook used by the line chart. Candlestick now exposes
> and removes the same hook through its lifecycle.

> **Note implementazione (I60F final Asset lifecycle gate, 2026-09-15):**
> with per-pair issue identity, mode-independent chart instrumentation,
> same-fingerprint in-flight joining, immediate accepted-sync invalidation,
> per-slug standalone generations and Price MAX successor scheduling, the
> expanded Asset workflow passes 28/28 on desktop and 28/28 on mobile.

> **⚠️ Fuori pista (I60F final review corrections, 2026-09-15):**
> the final review found three remaining contract edges: coordinated peer sync
> invalidated a pending main chart but refreshed only local comparisons; a
> forced comparison refresh could join pre-refresh same-fingerprint work; and
> Calendar mapping treated any item error—including event-only FX failure—as
> price conversion causality. Accepted Price peer sync now starts a guarded
> `loadChartData` successor before reloading local comparisons; force bypasses
> same-fingerprint in-flight joining after explicit ownership invalidation; and
> Calendar remapping accepts only the first non-event error with explicit
> FX/conversion/currency semantics.

> **⚠️ Fuori pista (I60F final mobile toast cleanup, 2026-09-15):**
> the post-final-correction mobile run reached 27/28; its synthetic workflow
> cleanup read two actionable toasts, clicked one dismiss control, then asserted
> exactly one remained. The other toast legitimately auto-expired in the same
> interval, so the observed count jumped directly to zero. This is a
> clock/count assumption in test cleanup, not product behavior; cleanup must
> require monotonic progress to zero rather than an exact decrement of one.

> **Note implementazione (I60F final corrections + closing gates, 2026-09-15):**
> test-author extended the existing Asset workflow for accepted peer-sync chart
> successors, forced-vs-non-force comparison ownership and Calendar event-only
> FX causality; desktop passes 28/28. Mobile toast cleanup now requires monotonic
> progress rather than an exact one-row decrement and mobile passes 28/28.
> Coordinator-authorized serialized closing gates all pass on lane 6157:
> core/lifecycle 1992/1992; Dashboard+broker responsive 62/62 across both
> projects; Asset/FX list + settings-modal seams 78/78 across both projects;
> full Prettier and Svelte check; canonical production build; backend Ruff and
> Black on all seven changed Python files; i18n 2765/2765 per locale with zero
> incomplete/missing-backend keys (122 pre-existing/shared unused); strict
> MkDocs build and all 12 cross-boundary links. No review server is active.

> **⚠️ Fuori pista (I60F exact-revision review, 2026-09-15):**
> exact-revision review found five final lifecycle edges: Price/MAX refresh
> duplicated its auto-scheduled forced comparison; a sub-seven-day Calendar MAX
> fallback entered Price without refreshing backend signals; cosmetic settings
> replaced the signal array reference and could abort an already-accepted sync
> before its successor; deleting per-slug generations allowed ABA token reuse;
> and FX-detail comparison-Asset sync force-refreshed failures/stale routes.
> MAX refresh now joins its owned auto-successor, Calendar→Price fallback loads
> Price backend data then comparisons, sync guards use a runtime-stripped
> data-context fingerprint, per-slug counters remain monotonic with separate
> active tokens, and FX-detail Asset sync snapshots route/session/range and
> refreshes only current accepted results.

> **Note implementazione (I60F exact-edge regressions, 2026-09-15):**
> test-author extended only the registered Asset/FX detail workflows for
> single-successor Price/MAX refresh, Calendar MAX `<7d` Price backend-signal
> fallback, cosmetic-vs-computational sync ownership, same-slug ABA protection,
> FX-detail accepted/failure outcome matrices and range/swap/navigation stale
> completion. Prettier and diff-check pass; exact desktop Asset passes 28/28 and
> exact desktop FX detail passes 17/17 on lane 6157.

> **⚠️ Fuori pista (I60F exact-edge FX mobile activation, 2026-09-15):**
> combined mobile Asset+FX detail passed Asset 28/28 and FX 16/17. The new
> same-slug ABA regression never emitted its request because the visible/enabled
> FX Sync button's mouse hit point was intercepted by the mobile reorder
> chevron/header. This is the already-known mobile pointer assumption; activate
> the exact focusable button with keyboard Enter, with no force-click or sleep.

> **Note implementazione (I60F exact-edge mobile repair, 2026-09-15):**
> test-author replaced all six potentially-overlapped actions in the FX
> same-slug ABA scenario with focus+enabled+Enter on exact testids. Prettier and
> diff-check pass; FX detail mobile passes 17/17. Together with the preceding
> combined run, Asset detail mobile remains 28/28.

> **Note implementazione (I60F exact final closing matrix, 2026-09-15):**
> all coordinator-authorized serialized gates pass after the exact-edge fixes:
> Asset detail 28/28 desktop and 28/28 mobile; FX detail 17/17 desktop and
> 17/17 mobile; core/lifecycle 1992/1992; Dashboard+broker responsive 62/62;
> Asset/FX list + settings-modal seams 78/78. Full Prettier and Svelte check,
> canonical production build, backend Ruff + Black, strict MkDocs build and
> 12/12 cross-boundary links pass. i18n remains 2765/2765 in every locale,
> zero incomplete/missing-backend keys and 122 shared/pre-existing unused.

> **⚠️ Fuori pista (I60F refresh ownership review, 2026-09-15):**
> exact-final review found two orchestration gaps: a completed auto-scheduled
> MAX comparison was forgotten after clearing `comparisonInFlight`, allowing a
> later non-force owner to duplicate it; and stale Asset/FX refresh workflows
> could continue after a newer range/route operation because callers could not
> distinguish an obsolete `loadChartData` return from success. Non-force loads
> now no-op on a successfully applied fingerprint (without caching the
> peer-present/line-empty early state). Asset and FX refreshes use monotonic
> operation tokens plus captured URL/route/mode/currency/runtime-stripped signal
> context and re-check after every await.

> **Note analisi/implementazione (I60G Growth Sep→Jan tick spacing, 2026-09-16):**
> measured ECharts SSR with the reported one-year Sep→Sep span and 315/337px
> chart widths. Existing time split `4` produced irregular interior gaps of
> 67.6–72.7px (calendar-nice quarter ticks plus forced endpoints); split `5`
> produced uniform two-month gaps of 43.4–48.2px. Plot margins were not causal.
> Shared compact time-axis budget is therefore 48px instead of the category
> budget 56px; category axes, outer grid, endpoints, rotation, hideOverlap and
> dataZoom are unchanged.

> **⚠️ Fuori pista (I60F refresh regression — Price measures, 2026-09-15):**
> final refresh-ownership tests passed FX 17/17 and reached Asset 27/28. A
> completed Price measure disappeared while its panel was hidden in Calendar:
> a refresh transiently exposed empty `chartData`, and MeasurePanel's normal
> non-preserve path interpreted that transport state as a definitive range
> mismatch and deleted the measure. Auto-pruning now runs only against a
> non-empty dataset; genuine non-empty range changes still remove incompatible
> anchors, while temporary absence cannot mutate the Price table.

> **Note implementazione (I60F MeasurePanel refresh regression, 2026-09-15):**
> Price measures now retain their anchors across transient empty chart data and
> restore the summary/`deltaPct` table when data returns; a later non-empty
> incompatible range still prunes them. Focused MeasurePanel passes 23/23. The
> stale Calendar→Price refresh test now correctly expects no stale comparison
> continuation.

> **⚠️ Fuori pista (I60F short-MAX fallback gate, 2026-09-15):**
> the first reactive fallback effect tracked range/currency/signals after its
> token and re-fired on later MAX selection; wrapping captures in `untrack`
> fixed that. The remaining timeout was then diagnosed as a test circular wait:
> product intentionally awaits Price backend data before comparison, while the
> test awaited comparison before releasing the backend response. The gate now
> validates backend request/response first, then comparison, with exact
> no-duplicate counts. Asset desktop passes 28/28.

> **⚠️ Fuori pista (I60G manual review — partial Calendar history, 2026-09-16):**
> developer rejected the all-or-nothing selected-range contract. Calendar
> output dates remain inside the selected range, but calculation may consume
> factual source history before the selected start. For each primary/peer line,
> the first output is the earliest selected date `t` where current price/FX at
> `t` and reference `t-N` are both resolvable. Late inception, leading/interior
> source gaps and FX gaps produce that line's own valid subset plus typed partial
> causality; they never suppress other factual lines. Only zero valid outputs
> are unavailable. No interpolation/fabrication; exact calendar-day N,
> deterministic ordering and unique output dates remain mandatory. Price-%
> comparison rebasing is unchanged.

> **Note autorizzazione (I60G partial history + X-axis measurement, 2026-09-16):**
> developer/coordinator authorized backend/service/API and frontend independent
> primary+multi-peer corrections with test-author coverage. The reported
> Sep→Jan Growth spacing is analysis-first: capture actual option, usable plot
> width, selected ticks and pixels before any shared-policy adjustment; preserve
> endpoints, hideOverlap, dataZoom and desktop density. No new lifecycle scope.

> **Note implementazione (I60G partial Calendar histories, 2026-09-16):**
> Calendar rolling return v1.3.0 now requests an exact `N`-day pre-visible
> warmup, admits sparse input dates through an explicit plugin capability and
> emits only selected-range dates from the first factual point onward. Leading,
> interior and trailing source/FX gaps retain typed provenance and partial
> causality; only zero factual outputs are unavailable. AssetSource passes the
> target-currency-valid subset through mixed conversion history instead of
> suppressing all signals. The Asset page maps primary and each peer
> independently, renders their sorted union of dates with real gaps, preserves
> each peer's own inception/FX status and keeps Price-% per-line rebasing
> unchanged. Calendar Page Sync discovers already-configured primary, peer and
> event FX routes regardless of the currently visible chart mode; it still
> never auto-registers a missing pair.
>
> **Note implementazione (I60G responsive X-axis correction, 2026-09-16):**
> measured ECharts SSR at 315/337px confirmed that split `4` created irregular
> 67.6–72.7px gaps while split `5` produced approximately 43.4–48.2px spacing.
> Only the shared compact time-axis label budget changed from 56px to 48px.
> Category budgets, plot margins, endpoint preservation, `hideOverlap`, zero
> rotation, dataZoom and desktop behavior remain unchanged. The rendered
> regression reads actual ticks and pixel positions; its local structural
> adapter avoids direct TypeScript access to ECharts' private `getModel`
> declaration without weakening SVG/tick/pixel assertions.
>
> **Note implementazione (I60G exact closing gates, 2026-09-16):**
> Calendar plugin passes 27/27, SignalService 50/50, focused first-factual-point
> matrix 8/8 and Calendar AssetSource/API integration 7/7. Asset detail passes
> 28/28 desktop and 28/28 mobile. Dashboard plus broker responsive coverage
> passes 62/62 across desktop/mobile. Thirteen affected unit/component files
> pass 465/465; the exact rendered responsive file passes 55/55 after the
> type-safe test adapter. Prettier is clean, Svelte check reports 0 errors /
> 41 baseline warnings, production build completes, and the eight changed
> backend files pass Ruff plus Black. i18n is complete at 2765/2765 in all four
> locales with 0 missing/incomplete keys and 122 pre-existing/shared unused
> candidates. Strict MkDocs build and all 12 cross-boundary links pass.
>
> **⚠️ Fuori pista (I60G closing static/docs gates, 2026-09-16):**
> the first Prettier check found only the Asset detail page and the first Black
> check found only the Calendar plugin; canonical formatters normalized both.
> The first full Svelte check then exposed a test-only access to ECharts'
> private `getModel` declaration. Test-author replaced it with a narrow local
> structural reader; focused Vitest stayed 55/55 and full check returned to
> 0 errors. `mkdocs translate-validate` remains red on repository-wide Aphra
> structural debt, including the intentionally rewritten English Asset chart,
> measure, signal and FX settings pages; no IT/FR/ES documentation was edited
> or stamped. Strict build and link validation are green.

> **⚠️ Fuori pista (I60G exact-revision independent review, 2026-09-16):**
> the single authorized final review did not clear manual review. It reported
> three HIGH blockers: the frontend still rejects `N > selected range` despite
> valid pre-range warmup; a current Calendar request failure can retain and
> relabel stale primary/peer snapshots as current partial data; and the render
> branch still gates on primary Price `lineData`, hiding a factual peer-only
> Calendar union. It also reported three MEDIUM findings: trimmed leading
> undefined windows can return `OK` instead of typed partial; the primary
> Calendar view discards typed failure/problem detail; and the shared responsive
> helper applies formatter/endpoint/overlap overrides above compact width,
> changing desktop behavior. State is FROZEN before another implementation
> loop. Findings remain inside the authorized Calendar/X-axis domains, but the
> coordinator must confirm the repair loop because the prior scope was declared
> exact/final; no review server may start on this revision.

> **Note implementazione (I60G repair M1, 2026-09-16):**
> finite output accompanied by `UNDEFINED_METRIC_WINDOW` now always receives
> `PARTIAL_UNDEFINED_METRIC` availability before final status derivation,
> including when the Calendar plugin trimmed leading undefined points. The
> existing all-undefined branch still returns typed unavailable and deterministic
> sparse dates/issues remain unchanged.

> **Note implementazione (I60G repair H1, 2026-09-16):**
> Calendar mode and every supported positive preset/custom `N` are now
> independent of visible-range length. The old `<7d` disable/fallback, preset
> filtering and `N <= selected span` validation were removed. Short visible
> ranges keep the exact chosen `N`; the backend's factual pre-range lookback and
> typed availability alone decide whether output exists.

> **Note implementazione (I60G repair M2, 2026-09-16):**
> `CalendarReturnView` now carries the primary signal's existing typed
> `SignalProblem`, derived through the shared backend-result mapper rather than
> a Calendar-specific issue taxonomy. The Asset chart exposes structured
> primary problem code/status and renders its formatted cause independently
> when peers remain factual, including unavailable, failed and partial results.

> **Note implementazione (I60G repair H2, 2026-09-16):**
> Calendar primary/peer snapshots are now owned by a full data fingerprint
> (asset, selected range, target currency, exact window and peer set) in
> addition to the monotonic request/session guards. A changed fingerprint starts
> with empty loading state; a same-fingerprint refresh may retain only its own
> current snapshot while loading. Any current request failure or missing primary
> item clears primary points, peer views and peer problems before publishing
> `error`, so an older peer can no longer promote the new failure to `partial`.

> **Note implementazione (I60G repair H3, 2026-09-16):**
> the chart shell now gates by active mode: Price still requires primary
> `lineData`, while Calendar renders from its independent union/state even when
> primary Price history is empty. The Price empty state keeps the primary mode
> toggle available, so the user can enter Calendar and display a factual
> peer-only series without fabricating primary points.

> **Note implementazione (I60G repair M3, 2026-09-16):**
> the shared responsive helper now emits formatter, interval, endpoints,
> overlap, rotation and split overrides only while compact. Desktop initial
> options retain each chart's prior contract: category charts add no responsive
> keys, Growth/Allocation keep their original rotation, and lot charts keep
> their existing formatter plus overlap policy. Each consumer tracks a compact
> transition and performs a full x-axis rebuild when returning to desktop, while
> existing logical/external dataZoom state remains reapplied.

> **⚠️ Fuori pista (I60G repair MAX fingerprint, 2026-09-16):**
> test-author identified that resolving a provisional MAX start to the first
> factual date could make an accepted Calendar snapshot appear stale. The
> fingerprint now uses the semantic URL range (`min`/`max` while MAX is active),
> so factual resolution does not orphan the same request; ordinary concrete
> range changes still produce distinct fingerprints.

> **Note implementazione (I60G repair regressions, 2026-09-16):**
> test-author added the required leading-undefined typed-partial backend case,
> short-visible-range/exact-N helper coverage, primary typed problem mapping,
> A-success/B-failure snapshot isolation, peer-only factual rendering contracts,
> and compact-versus-exact-desktop x-axis assertions. Its permitted focused
> evidence is 2/2 backend regressions, 34/34 Calendar helper tests and 290/290
> Asset unit tests; Prettier, targeted Ruff/Black, Svelte check (0 errors / 41
> baseline warnings) and `git diff --check` also pass. Playwright remains for
> the parent-owned serialized lane gate.

> **⚠️ Fuori pista (I60G repair backend gate, 2026-09-16):**
> `... dev.py test --test-port 6157 --data-dir
> /tmp/librefolio-r2-i-charts services risk-all calendar` collected 28 Calendar
> tests and passed 27. The sole deterministic red is an older sibling-isolation
> assertion expecting `DATA_GAP`; the authorized M1 contract now correctly
> reports `PARTIAL_UNDEFINED_METRIC` because that sparse Calendar result contains
> an undefined reference window plus later factual output. Collection/setup and
> DB creation succeeded; test-author owns the superseded assertion repair.

> **Note implementazione (I60G repair backend assertion, 2026-09-16):**
> test-author updated only the superseded sibling-isolation expectation while
> preserving its legacy-result identity and both `DATA_GAP` plus
> `UNDEFINED_METRIC_WINDOW` warning checks. The parent-equivalent Calendar gate
> now passes 28/28; the two coupled M1 cases pass 2/2.

> **⚠️ Fuori pista (I60G repair selector, 2026-09-16):**
> `... services signal-service calendar` exited 5 before test execution because
> that file has no test name containing `calendar` (50 deselected). Database
> setup succeeded and no server ran. Validation continues with the registered
> full `signal-service` action, then the separate Calendar-filtered AssetSource
> action; this is a selector error, not a product red.

> **⚠️ Fuori pista (I60G repair AssetSource assertions, 2026-09-16):**
> the corrected full SignalService gate passes 50/50. The subsequent Calendar
> AssetSource gate passed 4/7; its three deterministic reds are older expected
> reason codes (`PARTIAL_INPUT_COVERAGE` or `DATA_GAP`) on results that also
> contain `UNDEFINED_METRIC_WINDOW`. Under the authorized M1 precedence these
> are now `PARTIAL_UNDEFINED_METRIC`, while conversion/gap warnings and
> independent line behavior remain separately asserted. Test-author owns these
> three superseded expectations; no production rollback is warranted.

> **Note implementazione (I60G repair AssetSource assertions, 2026-09-16):**
> test-author updated only those three reason-code expectations and preserved
> every mixed-currency, data-gap, deterministic point/provenance and sibling
> isolation assertion. The exact Calendar AssetSource gate now passes 7/7.

> **⚠️ Fuori pista (I60G repair Asset E2E gate, 2026-09-16):**
> the combined desktop/mobile Asset detail run passed 54/56. Both deterministic
> reds are the same timeout in the expanded Calendar workflow at
> `waitForCalendarResponseForRange` after line 2712; all other 27 tests per
> viewport pass. Server startup/setup and teardown completed normally. Per the
> triage protocol this is not labeled flaky: test-author must determine whether
> the expected short-range request was armed against the wrong transition or
> whether product failed to issue the authorized request before any edit.

> **⚠️ Fuori pista (shared-venv resume collision, 2026-09-16):**
> the post-update import smoke confirmed NumPy 2.5.3, SciPy 1.18.1, highspy
> 1.15.1 and PySCIPOpt 6.2.1. The first chained backend gate then stopped during
> database setup, before collection, because test-author's already-authorized
> focused Asset E2E had acquired lane 6157 between the precheck and migration.
> Listener PID 76437 belongs to parent test command PID 76423. This is a
> serialized-lane collision, not a dependency or product red; the backend gates
> will resume only after that exact test command exits and the port is free.

> **Note implementazione (I60G repair Calendar→Price MAX handoff, 2026-09-16):**
> test-author proved the original E2E timeout was an assertion-order mistake:
> the test expected a 7-day request without selecting 1W, and now performs that
> explicit action with the listener armed immediately before it. The corrected
> flow then exposed one product defect caused by the new fingerprint guard:
> switching to Price before a still-current Calendar response returned discarded
> the response's factual prices, so MAX could not resolve its concrete start or
> schedule Price comparison. `loadChartData` now separates route/session/range/
> currency ownership of the factual price/event payload from stricter
> Calendar-mode snapshot publication. A current payload may resolve MAX after
> mode change, while stale Calendar primary/peer state remains rejected.

> **Note implementazione (I60G repair final gates, 2026-09-16):**
> after the shared numerical environment update, imports report NumPy 2.5.3,
> SciPy 1.18.1, highspy 1.15.1 and PySCIPOpt 6.2.1. Calendar backend gates pass
> 28/28 risk/plugin, 50/50 SignalService and 7/7 AssetSource. The focused
> corrected Calendar E2E passes 1/1 per viewport, then the complete Asset detail
> matrix passes 28/28 desktop + 28/28 mobile. Responsive Dashboard, broker and
> FX detail pass 96/96; Asset/FX list plus chart settings pass 78/78. Thirteen
> affected unit/component files pass 463/463. Full Prettier is clean, Svelte
> check reports 0 errors / 41 baseline warnings, production build completes
> (cached MathJax retained after a certificate warning), and changed backend
> files pass Ruff plus Black. i18n remains 2765/2765 in every UI locale, strict
> MkDocs build passes and cross-boundary links pass 12/12.
>
> **⚠️ Fuori pista (I60G final translation validation, 2026-09-16):**
> `mkdocs translate-validate` confirms the intentionally unstamped translation
> debt: 159 repository-wide structural errors, 194 warnings and 472 localized
> differences across 549 checks. This is known debt from substantial English
> documentation work, not a docs build/link failure; no translated page was
> edited.

> **⚠️ Fuori pista (I60G repair exact-revision review, 2026-09-16):**
> the single fresh review found two in-scope M3 defects. Growth's compact→desktop
> callback calls `renderChart`, but its same-mode path uses `updateChartData`
> with `replaceMerge: ['dataZoom']`, so compact x-axis keys survive. Candlestick
> does fully rebuild its x-axis, but unlike Line/Price it does not preserve the
> user's active dataZoom window around `setOption(option, true)`. Manual review
> remains blocked until both transitions have runtime regressions and the
> affected/final gates plus one new exact-revision review are green.

> **Note implementazione (I60G repair Growth desktop reset, 2026-09-16):**
> Growth's compact→desktop resize now explicitly forces its full-option path;
> that path replace-merges `xAxis` and reapplies the current logical
> `zoomWindow`. Same-mode data/resolution updates retain their lighter series +
> dataZoom path, but can no longer prevent removal of compact-only axis keys.

> **Note implementazione (I60G repair Candlestick zoom reset, 2026-09-16):**
> Candlestick now snapshots the active inside-dataZoom percentage window before
> any full option replacement and dispatches the same start/end immediately
> afterward. Compact→desktop can therefore rebuild an exact desktop x-axis
> without resetting the user's zoom/pan selection.

> **Note implementazione (I60G review regressions, 2026-09-16):**
> test-author added focused Growth compact→desktop full-axis/zoom-window and
> Candlestick pre-rebuild zoom capture/post-rebuild restoration regressions.
> The exact rendered/source-contract chart core file passes 55/55 with Prettier
> and `git diff --check` clean; private chart/ResizeObserver closures remain
> unexposed, so the tests combine runnable ECharts option evidence with explicit
> operation-order contracts.

> **⚠️ Fuori pista (I60G Growth data-density review, 2026-09-16):**
> the next exact review found one remaining M3 transition: history/resolution
> data could change Growth from compact to desktop without a resize. The
> same-mode incremental path then sent an empty x-axis patch and retained
> compact keys. `updateChartData` now compares the previous/new compact state
> for every data update and routes compact→desktop through `applyFullOption`,
> which replace-merges the full x-axis and reuses the current `zoomWindow`.
> Ordinary compact or desktop updates stay incremental.

> **Note implementazione (I60G Growth data-density regression, 2026-09-16):**
> test-author replaced the prior empty-desktop-patch acceptance with a contract
> that both Growth data-update paths detect compact→desktop, rebuild full
> series, invoke the full x-axis replacement with the current zoom window, and
> leave ordinary incremental updates distinct. The exact chart-core file passes
> 55/55; the resize transition regression remains intact.

> **Note implementazione (I60G final Growth density gates, 2026-09-16):**
> Dashboard passes 6/6 per viewport (12/12 total) after the data-density
> transition fix. Full Prettier is clean, Svelte check remains 0 errors / 41
> baseline warnings and the production rebuild succeeds, retaining the cached
> MathJax asset after the same external certificate warning.

> **⚠️ Fuori pista (I60G Growth history-range review, 2026-09-16):**
> the next exact review found that a new `history` reference still called
> `resetResolutionState` before preserving the active chart range. Even though
> the compact x-axis was rebuilt correctly, the rebuild received the full new
> domain (0–100) instead of the user's zoomed range. This remained the sole
> manual-review blocker at the developer hard stop.

> **Note implementazione (I60G Growth history-range preservation, 2026-09-16):**
> before clearing resolution caches for a new history reference, Growth now
> resolves the visible logical range from the still-active old dataset and
> ECharts dataZoom. The range is clamped to the new history domain and restored
> into `visibleStartDate`/`visibleEndDate`; only a missing prior range defaults
> to the full new domain. `getLogicalRangeFromChart` prefers `activeChartData`
> so the old zoom cannot be interpreted against newly derived dates before the
> cache reset. The subsequent compact→desktop full-axis path therefore receives
> the preserved/clamped range rather than 0–100.

> **Note implementazione (I60G Growth stateful range regressions, 2026-09-16):**
> test-author added pure boundary cases for retained, left-clamped,
> right-clamped, fully clamped and missing prior ranges, plus a real ECharts
> SVG-SSR compact-dense → desktop-sparse transition. The transition proves the
> formatter, interval and forced endpoint flags are removed while the non-full
> logical/dataZoom range remains preserved; only the explicit no-prior-range
> fallback maps to 0–100. The exact chart-core file passes 61/61.

> **⚠️ Fuori pista (I60G Growth range-state review, 2026-09-16):**
> the next exact review found three coupled edges in the same state machine:
> empty history left stale ECharts zoom available for the next dataset; restored
> partial ranges reset to daily without density-based resolution selection; and
> a resize/mode full rebuild inside the 200ms debounce could use stale stored
> bounds instead of the live chart zoom. All remain inside the authorized
> history-range preservation contract.

> **Note implementazione (I60G Growth range-state closure, 2026-09-16):**
> `getLogicalRangeFromChart` now returns a range only when an active rendered
> dataset matches the current resolution, so empty→populated cannot map stale
> ECharts percentages onto new dates. Every history reset marks resolution
> selection pending; the first render chooses density from the restored full,
> partial or clamped logical range before building dataZoom. Every render also
> synchronously captures the live chart range before a possible full option
> replacement, closing the debounce race for resize and mode changes.

> **Note implementazione (I60G Growth range-state regressions, 2026-09-16):**
> test-author added stateful nonempty→empty→replacement history, clamped-range
> resolution-selection and immediate live-zoom→full-rebuild cases. They verify
> stale ECharts percentages are ignored without an active dataset, the restored
> partial range—not the full domain or hardcoded daily—drives first resolution,
> and live zoom wins over debounced stored bounds while compact-only x-axis keys
> are cleared. Production-helper plus ECharts SVG-SSR evidence passes 64/64.

> **Note implementazione (I60G Growth range-state final gates, 2026-09-16):**
> parent rerun confirms chart core 64/64 and Dashboard 6/6 per viewport
> (12/12). Full Prettier is clean, Svelte check reports 0 errors / 41 baseline
> warnings and production build completes. No backend, locale or MkDocs source
> changed in this final Growth-only loop; their preceding exact green gates
> remain applicable.

> **⚠️ Fuori pista (I60G deferred-history review, 2026-09-16):**
> the next exact review found that two history references arriving before the
> deferred render could preserve stored bounds after the first reset even though
> no active dataset remained to prove them current. The history effect now
> preserves only `getLogicalRangeFromChart()` evidence from active rendered
> data; a null active range is passed through as null, so the next render
> initializes the full new domain instead of recycling stale stored dates.

> **Note implementazione (I60G deferred-history regression, 2026-09-16):**
> test-author added a stateful A-partial-zoom → A-reset → B-before-render case.
> It proves cleared active data yields null capture, B receives its own full
> domain and 0–100 window, and no A date reaches B's range/zoom mapping. The
> paired source-order contract rejects any `ensureLogicalRange` fallback in the
> history-change effect. Chart core passes 65/65.

> **Note implementazione (I60G deferred-history final gates, 2026-09-16):**
> parent rerun confirms chart core 65/65 and Dashboard 6/6 per viewport
> (12/12). Full Prettier is clean, Svelte check reports 0 errors / 41 baseline
> warnings and production build completes. No backend, locale or MkDocs source
> changed in this final narrow loop.

> **Note review finale (I60G Growth range-state, 2026-09-16):**
> the fresh exact-revision independent review reports `No blockers` and confirms
> manual review is safe. Active-data ownership, empty/rapid history fallbacks,
> clamping, resolution reselection, synchronous live-zoom capture and
> compact→desktop x-axis replacement were reviewed together on the final
> revision.

> **⚠️ Fuori pista (manual review follow-up 3, 2026-09-16):**
> developer accepted the overall Calendar/spacing/localization behavior and
> reported two bounded sync defects. During a coordinated peer sync the Asset
> can finish before required FX, so an existing typed FX banner is legitimate
> while work remains; after all required configured FX routes are accepted the
> current comparison facts must be reloaded so the banner disappears without a
> page reload, while failed/skipped routes retain it. The peer Asset and every
> required configured price/event FX route must also share a sync interval made
> from the already-required Calendar lookback plus seven calendar days before
> and up to seven after (capped at today). The review server was stopped first
> and lane 6157 proved free.

> **Note implementazione (I60H comparison sync padding, 2026-09-16):**
> `buildComparisonSyncRange` now composes the selected start with the current
> Calendar N-day warmup when applicable, then adds seven calendar days before;
> it extends a historical end by seven days capped at the user's today and
> never emits a future end. `min` remains the unbounded start sentinel. The same
> immutable padded range is sent to the peer Asset sync and every required
> configured price/event FX route; cache refill uses the equivalent concrete
> padded range while chart/output queries keep the original selection. The
> Calendar window is included in the request-current guard.

> **Note implementazione (I60H FX banner lifecycle, 2026-09-16):**
> Calendar comparison data quality now tracks price-conversion failures from
> the current bulk response separately from general signal problems. During a
> same-fingerprint coordinated sync the existing failure state stays visible;
> only after all required FX requests settle and accepted data is reloaded does
> the current response replace that state. Price mode continues to derive the
> banner from refreshed comparison runtime data. Failed/skipped routes retain
> their typed issue, and existing account/route/range/mode/window/generation
> guards prevent stale completion from publishing or clearing it.

> **⚠️ Fuori pista (I60H focused E2E triage, 2026-09-16):**
> the first focused desktop/mobile run exposed two test assumptions, not product
> defects. A global conversion count included an unrelated already-in-flight
> Calendar conversion while both banners and reload counters correctly remained
> unchanged before FX acceptance; the regression now identifies only owned
> post-baseline refills by configured pair and exact padded interval. The MAX
> refill expectation also omitted the 365-day Calendar warmup and now correctly
> expects 365 + 7 days before the concrete cache start. The corrected focused
> Calendar workflow passes 1/1 per viewport (2/2 total); an initial direct
> non-Pipenv mobile invocation failed before collection and the canonical
> shared-venv invocation passed.

> **⚠️ Fuori pista (I60H final banner review, 2026-09-16):**
> exact review found two remaining same-domain banner edges. A missing/rejected
> same-fingerprint Calendar reload cleared prior FX diagnostics even though no
> authoritative conversion result existed; and scanning every mixed error let
> an event-only generic conversion message mark the peer price route failed.

> **Note implementazione (I60H authoritative banner state, 2026-09-16):**
> same-fingerprint Calendar reload failures now clear stale plotted peer views
> but preserve the prior typed comparison problem/price-FX failure state until
> a present current response replaces it. New fingerprints still clear all
> prior diagnostics/events. Price-FX failure extraction is shared and ordered:
> only the first non-event conversion error may classify the peer price route;
> event-scoped failures continue through their own event dependency banner.
> Present peers authoritatively clear or replace their failure, while a missing
> peer item retains its previous failure rather than inventing success.

> **⚠️ Fuori pista (I60H unavailable peer continuity, 2026-09-16):**
> after test-author made Ready-peer selection an owned precondition, the
> authoritative response proved a selected peer was present but returned typed
> unavailable during its FX gap; replacing the complete view map removed the
> peer's previously factual same-fingerprint line.

> **Note implementazione (I60H factual peer continuity, 2026-09-16):**
> a present peer whose current same-fingerprint result is explicitly
> `unavailable` now keeps its last factual ready/partial line while adopting the
> current typed problem and FX banner. This preservation is deliberately narrow:
> absent peers, failed results and malformed responses are not retained; a new
> fingerprint still clears all prior facts and diagnostics. A later present
> factual response replaces the preserved line authoritatively.

> **⚠️ Fuori pista (I60H Price runtime cache marker, 2026-09-16):**
> the expanded missing-peer lifecycle returned from Calendar to Price after its
> runtime comparison params had been cleared, but the applied Price fingerprint
> still matched. `maybeLoadComparison` therefore treated an absent runtime
> payload as a cache hit and emitted no authoritative Price peer query.

> **Note implementazione (I60H authoritative Price runtime cache, 2026-09-16):**
> a matching Price comparison fingerprint can now short-circuit only when every
> requested comparison config retains the `_conversionFailed` runtime marker
> written by `applyComparisonAssetsData` for both success and authoritative
> no-data outcomes. Clearing runtime params deletes that marker, so returning to
> Price necessarily reloads the current peer data even if a stale applied
> fingerprint survived a Calendar path.

> **Note implementazione (I60H authoritative banner final gates, 2026-09-16):**
> the corrected focused lifecycle passes 1/1 per viewport and the complete
> Asset detail matrix passes 28/28 per viewport (56/56). Seven affected
> sync/chart unit files pass 285/285, including 33 ordered-error/padding loader
> cases. The first final format check identified only Asset detail source and
> its E2E file; canonical Prettier normalized both, then full Prettier passed.
> Svelte check reports 0 errors / 41 baseline warnings and production build
> completes.

> **⚠️ Fuori pista (I60H event/cache final review, 2026-09-16):**
> the next exact review found that Price's authoritative-runtime cache check
> covered peer price markers but not the shared peer event map; a Calendar
> fingerprint clear could therefore remove events while Price still
> short-circuited. It also found that the factual-line continuity guard trusted
> a raw `unavailable` string even when the result failed the generated backend
> schema.

> **Note implementazione (I60H complete runtime ownership, 2026-09-16):**
> a Price comparison cache hit now requires both the loader-written
> `_conversionFailed` marker and a `comparisonEvents` entry for every requested
> peer, so returning after a Calendar event clear reloads price data, event
> markers/counts and event-FX diagnostics together. Calendar parsing now rejects
> any schema-invalid result as `error` before interpreting its status; only a
> generated-schema-valid typed `unavailable` result can retain prior
> same-fingerprint factual peer data.

> **⚠️ Fuori pista (I60H unavailable schema seam, 2026-09-16):**
> applying generated-schema validation before all Calendar normalization broke
> the intentionally supported one-level nested ready/partial transport shapes
> in five helper tests. Validation is now mandatory specifically before an
> `unavailable` state can be accepted for factual-line retention; ready/partial
> continue through the existing structural normalizer, while real schema-valid
> responses still carry typed problems.

> **⚠️ Fuori pista (I60H bulk transport isolation, 2026-09-16):**
> the malformed-unavailable E2E then proved Zodios rejected the complete
> `FAPriceQueryResponse` before per-asset parsing because one peer signal failed
> `SignalResult`; valid primary and sibling results could not remain isolated.

> **Note implementazione (I60H per-signal transport isolation, 2026-09-16):**
> Asset detail's signal-bearing bulk query now uses the shared authenticated
> Axios instance and validates every non-signal item field with the generated
> `FAPriceQueryResult` schema after filtering only invalid signals for that
> validation pass. It then restores the raw signal array for existing per-item
> parsing, so one malformed peer becomes only that peer's typed error while
> valid primary/siblings continue. Top-level, price, event and item-shape
> failures still reject explicitly; `SignalResult` itself is not weakened.

> **Note implementazione (I60H transport isolation final gates, 2026-09-16):**
> the focused authoritative lifecycle passes 1/1 per viewport and the complete
> Asset detail matrix passes 28/28 per viewport (56/56). Full parser/helper
> coverage passes 117/117; the final loader/parser/chart-core aggregate passes
> 215/215. Full Prettier is clean, Svelte check reports 0 errors / 41 baseline
> warnings and production build completes.

> **Note review finale (I60H, 2026-09-16):**
> the fresh exact-revision independent review reports `No blockers` and marks
> manual review safe. It reviewed padding, accepted-only banner transitions,
> ordered event/price errors, valid-unavailable factual continuity,
> price+event runtime ownership and per-signal transport isolation together.

> **Note implementazione (I60H final focused gates, 2026-09-16):**
> pure sync-range coverage passes 31/31; the corrected focused lifecycle passes
> 1/1 per viewport; the complete Asset detail matrix passes 28/28 per viewport
> (56/56); and seven affected sync/chart unit files pass 283/283. The first
> final Prettier check identified only the Asset detail page, canonical format
> normalized it, then full Prettier passed. Svelte check reports 0 errors / 41
> baseline warnings and the production build completes. Backend, locale and
> MkDocs sources were unchanged by I60H, so their preceding exact gates remain
> applicable.

> **Note implementazione (I60G Growth range final gates, 2026-09-16):**
> parent rerun confirms chart core 61/61 and Dashboard 6/6 per viewport
> (12/12 total). Full Prettier is clean, Svelte check reports 0 errors / 41
> baseline warnings, production build succeeds and i18n remains complete at
> 2765/2765 in EN/IT/FR/ES with 0 missing/incomplete keys. Backend and MkDocs
> sources were unchanged by this final Growth-only correction, so their prior
> exact green gates remain applicable.

> **Note implementazione (I60G post-review gates, 2026-09-16):**
> after the two M3 fixes, the complete 13-file affected unit aggregate passes
> 465/465. The final combined Asset detail plus Dashboard matrix passes 34/34
> per viewport (68/68 total), covering Calendar lifecycle, Candlestick rebuild
> and Growth responsive rendering. Full Prettier remains clean, Svelte check
> remains 0 errors / 41 baseline warnings, and the production frontend rebuild
> completes; its external MathJax certificate warning used the existing cached
> asset and did not affect the build.

> **Note implementazione (I60G repair documentation, 2026-09-16):**
> the English Asset chart guide now documents unrestricted positive Calendar
> windows, selected-range output bounds with factual pre-range lookback,
> line-local primary/peer inception and gaps, typed partial versus zero-valid
> unavailable, and mode-independent Page Sync of already-configured
> primary/peer/event FX routes. No translated page was edited or stamped.
> Strict MkDocs build and all 12 cross-boundary links pass.

> **Note autorizzazione (I60F final three lifecycle fixes, 2026-09-15):**
> developer/coordinator explicitly authorized the three final MEDIUM findings:
> force main asset-price reload when an accepted peer FX route is also the
> main conversion route; invalidate hidden Price comparison state after an
> accepted Calendar page sync; and move per-asset sync generation/active
> ownership into Asset and FX page parents so panel remounts cannot admit stale
> same-peer completions. No additional lifecycle or feature scope is authorized.

> **Note implementazione (I60F final three lifecycle fixes, 2026-09-15):**
> coordinated peer FX sync now detects an accepted route shared with the main
> asset conversion, invalidates the converted main asset-price cache and forces
> `include_price:true`; accepted Calendar Page Sync invalidates hidden Price
> comparison runtime/fingerprint before refresh; and Asset+FX pages own
> monotonic per-peer active sync tokens exposed to ChartSignalsSection across
> true remounts. Test-author coverage passes ChartSignalsSection 13/13, Asset
> desktop 28/28 and FX desktop 17/17, including no duplicate request after
> collapse/reopen, refreshed main conversion, and exactly one fresh Price peer
> query after Calendar Page Sync.

> **⚠️ Fuori pista (I60F accepted Page Sync outcome, 2026-09-15):**
> final three-fix review found that SyncModalBase invokes `onsynced` even when
> every item fails or skips. PageSyncModal now reports current-run
> `{accepted}` from actual `ok/partial` section results and resets that value on
> callback/open. Calendar hidden Price invalidation is accepted-only; all-failed
> still refreshes the visible page but preserves its valid hidden Price cache.
> PageSyncModal passes 17/17 and Asset desktop passes 28/28, covering mixed
> partial, reopen, retry, accepted fresh peers and all-failed reuse.

> **⚠️ Fuori pista (I60F PageSync epoch + Risk forwarding, 2026-09-15):**
> accepted-only review found that an abandoned accepted response could mutate a
> component-wide flag after close/reopen, and Risk dropped the acceptance
> detail. PageSyncModal now epochs each open/close generation and records
> acceptance only for its still-open current generation. RiskAnalysisPanel and
> AssetRiskScenariosView forward the same `{accepted}` object end-to-end.
> Focused PageSync/Risk suites pass 82/82; Asset desktop passes 28/28.

> **Note implementazione (I60F final three-fix mobile gate, 2026-09-15):**
> the parent-owned sync, shared main-FX cache force and Calendar hidden-Price
> invalidation regressions also pass on mobile: Asset detail 28/28 and FX detail
> 17/17 in one serialized lane invocation. No deterministic red remains.

> **Note implementazione (I60F final three-fix component gate, 2026-09-15):**
> full registered Svelte component suite passes 1809/1809, including
> ChartSignalsSection true-remount parent-owned sync state and MeasurePanel
> transient-empty retention/non-empty pruning.

> **⚠️ Fuori pista (I60F final frozen review, 2026-09-15):**
> the final frozen review found one in-scope duplicate owner: an ordinary
> Calendar range change below seven days incremented the Price fallback token,
> while `handleDateRangeChange` also continued into its own chart/comparison
> loads. The handler now snapshots the fallback generation and returns when
> `ensureCalendarWindowFitsRange` schedules that token, leaving exactly one
> sequential Price backend + comparison owner.

> **Note implementazione (I60F final frozen-review gate, 2026-09-15):**
> the ordinary six-day Calendar→Price regression now proves exactly one token-
> owned main Price request followed by exactly one comparison request, with no
> duplicate from `handleDateRangeChange`. Asset detail passes 28/28 desktop and
> 28/28 mobile on the final revision; full Prettier, Svelte check and production
> build pass after the fix.

> **Note implementazione (I60F refresh ownership final gates, 2026-09-15):**
> completed comparison fingerprints now survive promise cleanup for later
> non-force owners, while peer-present/empty-main states remain retryable.
> Asset and FX refresh workflows own monotonic tokens plus captured
> route/range/mode/currency/runtime-stripped signal context. The Calendar
> `<7d` fallback is owned by a token-only Svelte effect (`untrack` prevents
> unrelated range re-runs), loads Price backend signals first, then comparisons;
> its regression gate follows that sequential order. Exact final evidence:
> Asset detail 28/28 desktop + 28/28 mobile; FX detail 17/17 desktop + 17/17
> mobile; MeasurePanel 23/23; core 1992/1992; Dashboard+broker responsive 62/62;
> Asset/FX list + settings modal 78/78; full Prettier/check/build, Ruff/Black,
> i18n 2765/2765, strict docs and 12/12 links all pass.

> **Note implementazione (I60F post-review combined gates, 2026-09-15):**
> expanded Asset detail passes 28/28 desktop and 28/28 mobile; core unit suite
> passes 1992/1992; Dashboard passes 6/6 per viewport; broker detail passes
> 25/25 per viewport; Asset list passes 24/24 per viewport; FX list passes
> 12/12 per viewport; corrected FX settings modal passes 3/3 per viewport.
> Final Svelte check is 0 errors / 41 baseline warnings and production bundles
> complete in 16.46s / 26.22s. Strict MkDocs build and 12/12 link check pass.

> **Note analisi (mobile X-axis overlap, 2026-09-14 — implementation not
> authorized):** confirmed date-axis owners are `LineChart.svelte` x-axis/
> dataZoom at 565-660 (axis 605-611), `CandlestickChart.svelte` grids/axes at
> 361-399 and option 491-509, `PriceChartFull.svelte` option 860-874,
> `GrowthChart.svelte` option 760-786, and `AllocationHistoryChart.svelte`
> `buildChartOption` around 656-739. Every affected axis keeps 11-14px date
> labels but defines no shared `hideOverlap`, density interval or endpoint
> policy; inside dataZoom/resolution changes do not thin the initial 430px
> render. Dashboard `PerformanceChart.svelte` is a horizontal diverging bar
> chart, not a Growth wrapper, and is exempt. LotGantt/LotComparison/
> LotWacPrice are additional date-axis surfaces requiring an explicit inclusion
> decision before implementation.
>
> Proposed shared policy: compute usable plot width after grid margins; enter
> compact mode below 480px or when a category point receives <24px; budget
> category labels at `min(12, floor(width/72))`, full-date time labels at
> `floor(width/88)` and compact month labels at `floor(width/56)`. Preserve
> first/last labels, enable `hideOverlap`, thin interior labels automatically,
> keep rotation 0 and use 30 degrees only as a measured last fallback. Recompute
> on initial render, ResizeObserver and resolution switch without altering the
> dataZoom window; keep full dates in tooltips and desktop options unchanged
> above budget. Future `test-author` work should cover the pure policy,
> rendered x-axis options, 430x932 adjacent-label bounding boxes/endpoints and
> desktop screenshots using `asset-detail-chart`, `candlestick-chart`,
> `growth-chart`, and `allocation-history-chart`; `performance-chart` asserts
> the exemption. Developer/coordinator must review formatter granularity,
> lot-chart inclusion and rotation fallback before any B source edit.

> **Note implementazione (I60F final automated gates, 2026-09-12):** final
> backend results are signal registry 65 pass, calendar risk 27 pass / 118
> deselected, and calendar Asset adapter 4 pass / 14 deselected. Eight focused
> frontend files pass 266/266. Full frontend check reports 0 errors / 41 merged
> warnings; canonical production build is green. Registered Asset detail passes
> 26/26 desktop and 26/26 mobile; FX detail passes 14/14 desktop and 14/14
> mobile. Strict MkDocs build and 12/12 cross-boundary links pass. English docs
> cover chart, measures, signals and shared FX axis settings; translated siblings
> intentionally retain Aphra structural debt. Independent review found five
> medium issues and verified all five fixes. Manual desktop/mobile acceptance
> remains the only open I60F gate.

#### Follow-up validation

- test-author owns every new/repaired backend, unit, component and E2E test;
- arbitrary windows cover 1/14/60/1095 days, invalid values and huge safe
  unavailable outcomes while preserving 7/30/90/365/default and legacy signal;
- settings tests cover v1→v2 migration, sanitizer, account/scope isolation,
  absolute/percentage separation and semantic secondary axes;
- Return tests cover pp measurement, separate table state, same-N comparison
  lines, partial peers and both request-race classes;
- final gates: targeted backend/frontend, full front check/build, Asset desktop
  + mobile, FX regressions, exact format/lint/diff checks, lane teardown and
  manual desktop/mobile review.

## 7. ASCII storyboards v2

These storyboards record the closed product contract. They are implementation
inputs, not proof of a rendered UI.

### 7.1 G3 desktop - historical calendar return

```text
TOP TOOLBAR (unchanged)
[Date range........................] [Target currency] [Sync]

+ Asset chart ------------------------------------------------------+
| [Price] [N-day return]        Window: [7] [30*] [90] [365]       |
|                              [Daily/Weekly/Monthly badge]         |
| Return %                                                        0%|
|      observed line -------- faded carried line ........          |
|                                                                  |
| Tooltip                                                          |
|  Chart date: 2026-09-10                                          |
|  N target: 2026-08-11                                            |
|  Actual reference observation: 2026-08-10                        |
|  Return (30d): +4.21% | existing carry/provenance status         |
+------------------------------------------------------------------+
```

Price mode remains unchanged. N-day mode does not show candlestick, Abs/% or
price-edit controls. No second date/currency/resolution selector appears.

Proposed stable selectors/state:

```text
asset-chart-primary-price
asset-chart-primary-calendar-return
asset-calendar-window-7
asset-calendar-window-30
asset-calendar-window-90
asset-calendar-window-365
data-primary-mode="price|calendar-return"
data-window-days="7|30|90|365"
data-series-state="loading|ready|partial|unavailable|error"
```

### 7.2 G3 mobile

```text
[Date range]
[Target currency] [Sync]

+ Asset chart -------------------------------+
| [Price] [N-day return]                     |
| [7] [30*] [90] [365]        [resolution]  |
| provenance/data-quality state              |
|                                            |
|             rolling return line            |
|       observed ------ carried ......       |
|                                            |
| tap tooltip: chart date / target date /    |
| actual observation / return / carry state  |
+--------------------------------------------+
```

Window chips wrap or scroll without reducing the plot to an unusable width.
Tooltip remains confined to the chart viewport.

### 7.3 P&L desktop - Dashboard with two or more brokers

```text
+ Growth -----------------------------------------------------------+
| [Value] [Return %] [P&L*]                  [resolution badge]     |
| [Line*] [Synthetic candles] [Income]                              |
|                                                                  |
|  TOTAL (prominent) ==========================================     |
|  Broker A ----------------  Broker B ----------------             |
|  0 -----------------------------------------------------------    |
| Legend: Total | Broker A | Broker B  (all initially visible)     |
| Tooltip: Total; each broker; Sum brokers = Total                 |
+------------------------------------------------------------------+
```

Exactly one selected broker, or Broker detail:

```text
+ Growth -----------------------------------+
| [Value] [Return %] [P&L*]   [resolution] |
| [Line*] [Synthetic candles] [Income]      |
| TOTAL only ============================== |
+-------------------------------------------+
```

No broker selector exists inside the chart. Colors are stable by broker ID.

Proposed stable selectors/state:

```text
growth-toggle-value
growth-toggle-return
growth-toggle-pnl
growth-chart-canvas
data-mode="value|return|pnl"
data-pnl-submode="line|candles|income"
data-resolution="daily|weekly|monthly"
data-series-state="loading|ready|partial|unavailable|error"
```

Compatibility note: current selectors may retain aliases during the local
refactor if tests or released integrations require them; Gate 0 decides from
the final code, not from this label proposal.

### 7.4 P&L mobile

```text
+ Growth -----------------------------------+
| [Value] [Return %] [P&L*]   [resolution] |
| [Line*] [Candles] [Income]                |
| scroll legend: Total | A | B | ...       |
| total + every selected broker line       |
| tap tooltip lists all required lines     |
+-------------------------------------------+
```

Legend may scroll, but no selected broker starts hidden.

### 7.5 Synthetic candles desktop

```text
+ Growth -----------------------------------------------------------+
| [Value] [Return %] [P&L*]                  [resolution]          |
| [Line] [Synthetic candles*] [Income]                              |
| Synthetic/hypothetical extremes - not simultaneous - no volume   |
|                                                                  |
|       TOTAL candlesticks                                         |
|       |#|  flat/faded fallback |-|  |#|                         |
|  Broker A close -----------  Broker B close -----------          |
| Legend: Total OHLC | Broker A close | Broker B close             |
| Tooltip: total O/H/L/C; each broker close; fallback provenance   |
+------------------------------------------------------------------+
```

One broker/Broker detail shows total candles only. Flat fallback contributions
remain in the total rather than disappearing.

Proposed stable selectors/state:

```text
growth-pnl-submode-line
growth-pnl-submode-candles
growth-pnl-submode-income
growth-synthetic-badge
data-pnl-submode="line|candles|income"
data-series-state="loading|ready|partial|unavailable|error"
```

### 7.6 Synthetic candles mobile

```text
+ Growth -----------------------------------+
| [Value] [Return %] [P&L*]                |
| [Line] [Candles*] [Income] [resolution]  |
| Synthetic (tap for explanation)          |
| total candles + broker close lines       |
| tap: O/H/L/C + broker closes + fallback  |
+-------------------------------------------+
```

The synthetic warning stays visible in compact form. No volume row exists.

### 7.7 Income desktop

```text
+ Growth -----------------------------------------------------------+
| [Value] [Return %] [P&L*]                  [resolution badge]    |
| [Line] [Synthetic candles] [Income*]                              |
|                                                                  |
|       + DIVIDEND                                                  |
|       + INTEREST     stacked signed bucket SUM                   |
|  ------------------------------------------------------------- 0 |
|       legacy negative corrections stack below zero               |
| Legend: Dividend | Interest                                      |
| Tooltip: bucket range; Dividend; Interest; signed Total          |
+------------------------------------------------------------------+
```

Both types are always present in the stacked view; there is no income-type
selector. Known zero income and unavailable/missing-FX data are distinct states.

Proposed stable selectors/state:

```text
growth-pnl-submode-line
growth-pnl-submode-candles
growth-pnl-submode-income
growth-income-zero
data-mode="value|return|pnl"
data-pnl-submode="line|candles|income"
data-income-state="loading|ready|zero|partial|unavailable|error"
```

### 7.8 Income mobile

```text
+ Growth -----------------------------------+
| [Value] [Return %] [P&L*]   [resolution] |
| [Line] [Candles] [Income*]                |
| legend: Dividend | Interest              |
| stacked signed bars                      |
| tap: bucket / both values / total        |
+-------------------------------------------+
```

The chart reuses top-level broker and currency controls. No duplicate selector
is added.

## 8. Data states

| State | Calendar return | P&L lines | Candles | Income |
|---|---|---|---|---|
| Loading | Existing chart skeleton/state | Preserve old data while refreshing | Explicit lazy-load state | Existing report load state |
| Ready | Full historical series | Total and required broker lines | Total candle + required broker closes | Stacked signed flows |
| Zero | Valid zero return | Valid line at zero | Valid flat zero candle | Explicit known-zero income |
| Partial/carried | Existing faded line + provenance | Existing portfolio DQ | Flat fallback/faded candle metadata | Available signed flows + missing-FX DQ |
| Unavailable | Existing resolver/signal reason | No canonical history | Unsupported canonical short or missing resolved valuation | No convertible canonical flow data |
| Error | Signal error, retry through existing flow | Report error | Candle payload error, line mode remains available | Report error |

No missing/partial state is represented by invented zero.

## 9. Future test plan

Tests are not authorized in the current plan-only checkpoint. When
implementation is authorized, invoke `test-author` and give it distinct files.
F has already added FX-identity cases to
`test_financial/test_portfolio_service.py` and cache-clear cases to
`test_fx_core.py`; H now owns relevant portfolio service/API tests until
integration. I test work must append to the integrated tests, never replace
those contracts.

### 9.1 Backend cases

- Calendar N is measured by date, not observation count, over weekends and
  irregular source observations.
- Default 30 and options 7/30/90/365.
- Existing observation-based rolling signal remains unchanged.
- Selected target currency and final resolver provenance are preserved.
- One combined-scope replay emits additive broker lines; internal transfer
  stays at departure while in transit, moves at arrival, and daily sum remains
  exact.
- Owner share, 0% owner behavior, editor/viewer visibility and selected scope.
- Daily candle close equals canonical total P&L.
- Daily-first vs wrong asset-first weekly aggregation uses a discriminating
  fixture with extrema on different asset/days.
- Quote-base, split, FX, flat fallback, carried values, missing values and
  unsupported short.
- Assetless DIVIDEND/INTEREST and legacy signed correction.
- Signed income changes decomposition, not NAV/total P&L.
- Income bucket total equals `period_income`.
- Cache keys distinguish optional features and split-event changes.

### 9.2 Frontend cases

- Three mutually exclusive core Growth modes and three mutually exclusive P&L
  submodes (`Line | Synthetic candles | Income`).
- Dashboard effective scope of one vs at least two brokers.
- Broker detail total-only behavior.
- Total/broker lines all initially visible; stable broker colors.
- Hybrid total candle + broker close lines.
- Synthetic warning and no volume.
- Stacked signed income bars.
- Mode/resolution/zoom switch preserves logical window and clears stale tooltip.
- G3 historical series, default window, all window controls, no double rebase
  or editing.
- Faded return/candle portions reuse existing chart semantics.
- Desktop/mobile/dark mode; selectors never depend on translated text.

### 9.3 Proposed future selectors

All future commands use the assigned lane and never run concurrently inside it:

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts schemas signals <filter>
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts services signal-service <filter>
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts services asset-signals <filter>
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts services portfolio-engine <filter>
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts services roi-fifo-utils <filter>
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts api portfolio <filter>
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts front-asset asset-unit
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts front-asset asset-detail <filter>
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts front-portfolio store-unit
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts front-portfolio dashboard <filter>
```

Runner registration remains coordinator-owned.

## 10. Documentation and generated/shared work

Only after stable implementation:

- coordinator runs API sync from the integrated schema;
- coordinator adds UI keys through the i18n CLI for EN/IT/FR/ES;
- docs-writer updates English pages:
  - `mkdocs_src/docs/user/dashboard/charts.en.md`;
  - `mkdocs_src/docs/user/assets/detail/chart.en.md`;
  - `mkdocs_src/docs/user/assets/detail/signals.en.md` if the final signal is
    user-configurable;
  - the directly related portfolio P&L theory page if semantics need
    clarification;
- coordinator updates changelog/master records only for delivered behavior;
- no translation pipeline runs without explicit developer request.

## 11. Definition of done

### 11.1 G3

- Historical backend series covers each chart date with value or explicit
  unavailable state.
- Calendar windows and default are exact.
- Final existing lookup/fallback/staleness is reused, with no parallel resolver.
- Selected target currency is honored.
- Carried sections use existing fade/provenance.
- Observation-based saved signals remain unchanged.
- No frontend finance math, rebase or editing.

### 11.2 G1a

- Top-level GrowthChart controls are exactly `Value | Return % | P&L`.
- Total is canonical cumulative P&L.
- Effective broker count drives total-only vs total-plus-broker lines.
- Dashboard and Broker detail follow the closed surface rules.
- Daily broker Decimal sum equals total, including internal-transfer windows.
- Lines are initially visible and no extra selector exists.

### 11.3 G1b

- Synthetic candles are the second P&L submode, not a top-level mode.
- Total close equals canonical total P&L every day.
- Broker close overlays reuse the exact G1a series.
- EOD quantity, ownership, quote-base, split and target FX are correct.
- Missing OHLC uses flat final-resolver fallback.
- Synthetic label is persistent; no volume or factual-risk reuse.
- Daily composition precedes temporal aggregation.
- Unsupported short fails closed; broader short accounting is separately
  authorized work.

### 11.4 G1c

- Income is the third P&L submode, not a top-level mode.
- Every scoped DIVIDEND/INTEREST, including assetless rows, enters exactly once.
- Signed legacy corrections remain signed throughout all canonical
  decompositions.
- Stacked buckets sum flows, with exact KPI reconciliation.
- Zero, partial FX and unavailable are distinct.

### 11.5 Cross-cutting

- Optional report payloads and both cache layers are coherent.
- API/client types, i18n, docs and tests describe the same contract.
- Zoom, viewport, theme, account/session and broker/currency changes preserve
  correct state.
- No CSS/text selectors; stable `data-testid`/state attributes.
- Developer completes pre-code storyboard/plan review and post-code operational
  walkthrough on desktop/mobile.
- Final workstream handoff contains actual SHA, manifest, evidence, conflicts,
  generated exclusions, stopped runtime proof and proposed commit message.

## 12. Progress protocol

After every authorized implementation phase:

1. Update the phase row immediately with date/status.
2. Add `Note implementazione` describing real code and evidence.
3. Add `Fuori pista` for every meaningful detour/failure.
4. Record exact commands and results.
5. Cross-link any corrective round in both directions.

No pending row may be marked complete from a plan, fixture or test name alone.
The current durable state remains:

```text
PLANNED / IMPLEMENTATION FROZEN / HARD GATE 0 WAITING FOR F
```
