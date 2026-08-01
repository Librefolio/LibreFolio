# ⏱️ AI Export Technical Sampling

AI Export reduces historical numeric density deterministically while preserving
scope, indicators, outputs, summaries, latest values, and selected events.

## 📐 Rational Bucket Formula

Let:

- \(x\): whole-calendar-day distance backward from `snapshot_as_of`;
- \(P\): shape exponent;
- \(M\): half-transition offset after the seven-day daily ramp;
- \(K\): asymptotic maximum bucket width in calendar days;
- \(T\): total requested inclusive calendar-day count.

The continuous width is:

$$
f(x;P,M,K)
=
1+(K-1)
\,
\frac{\max(x-7,0)^P}
{M^P+\max(x-7,0)^P}
$$

The integer width is:

$$
D(x;P,M,K)
=
\max\left(
1,
\operatorname{round}_{\text{half-up}}\left[f(x;P,M,K)\right]
\right)
$$

Boundaries are generated iteratively:

$$
x_0=0
$$

$$
x_{n+1}=\min\left(T,\ x_n+D(x_n;P,M,K)\right)
$$

Each offset interval becomes one bucket when translated back from
`snapshot_as_of`. Runtime arithmetic uses `Decimal` with explicit
`ROUND_HALF_UP`, not binary floating point or banker's rounding.

The result is deterministic, positive, monotonic in historical width, bounded by
\(K\), gap-free, overlap-free, and clipped exactly to \(T\).

## 📅 Recent Daily Window

For every detail level and temporal class:

$$
0 \le x \le 7 \Rightarrow D(x)=1
$$

The most recent seven calendar days therefore remain daily. This is calendar
sampling, not market-session sampling. Empty intervals remain in backend bucket
plans and diagnostics; the public renderer omits only completely empty temporal
rows and never invents observations or converts absence to zero.

## 🧮 Full Policy Matrix

Reference counts use exact inclusive periods of 90, 180, and 365 calendar days.

| Detail | Temporal class | P | M | K | 90d | 180d | 365d |
|---|---|---:|---:|---:|---:|---:|---:|
| Compact | Very Fast | 2 | 30 | 30 | 20 | 23 | 29 |
| Compact | Fast | 2 | 25 | 35 | 18 | 21 | 26 |
| Compact | Medium Fast | 2 | 20 | 42 | 16 | 18 | 23 |
| Compact | Medium | 2 | 10 | 42 | 14 | 16 | 20 |
| Compact | Slow | 2 | 5 | 49 | 12 | 14 | 17 |
| Compact | Very Slow | 2 | 5 | 84 | 11 | 12 | 14 |
| Standard | Very Fast | 2 | 30 | 14 | 26 | 33 | 46 |
| Standard | Fast | 2 | 21 | 15 | 23 | 29 | 41 |
| Standard | Medium Fast | 2 | 20 | 17 | 21 | 26 | 37 |
| Standard | Medium | 2 | 15 | 20 | 18 | 23 | 32 |
| Standard | Slow | 2 | 10 | 22 | 16 | 20 | 28 |
| Standard | Very Slow | 2 | 5 | 28 | 13 | 16 | 23 |
| Full | Very Fast | 2 | 30 | 7 | 35 | 49 | 75 |
| Full | Fast | 2 | 28 | 8 | 32 | 44 | 67 |
| Full | Medium Fast | 2 | 23 | 9 | 28 | 38 | 59 |
| Full | Medium | 2 | 16 | 10 | 24 | 33 | 51 |
| Full | Slow | 2 | 10 | 11 | 21 | 29 | 46 |
| Full | Very Slow | 2 | 9 | 14 | 18 | 24 | 38 |

Within one detail level, density decreases from Very Fast to Very Slow. For one
temporal class, Full is at least as dense as Standard, which is at least as dense
as Compact. Very Fast is the original detail-only baseline.

## 💹 Price and Rate Policy

Asset prices, FX rates, and equivalent reference series use **detail only**:

| Detail | P | M | K |
|---|---:|---:|---:|
| Compact | 2 | 30 | 30 |
| Standard | 2 | 30 | 14 |
| Full | 2 | 30 | 7 |

Signal temporal classes never change reference price/rate density.

## 📈 Indicator Policy

Indicator history uses:

```text
detail_level + plugin-owned temporal_class → P, M, K
```

AI Export does not branch on signal codes. The plugin resolves one temporal class
from normalized parameters; central policy resolves the matrix row.

### 🗂️ Initial Instance Mapping

The Asset bundle has 20 instances. Portfolio and Broker reuse it per eligible
asset. FX uses the marked 12-instance subset.

| Instance | Signal | Temporal class | In FX |
|---|---|---|:---:|
| `ema_20` | EMA(20) | Medium | ✓ |
| `ema_50` | EMA(50) | Slow | ✓ |
| `ema_200` | EMA(200) | Very Slow | ✓ |
| `sma_50` | SMA(50) | Slow | ✓ |
| `sma_200` | SMA(200) | Very Slow | ✓ |
| `kama_20` | KAMA(20) | Medium | ✓ |
| `aroon_25` | Aroon(25) | Medium | |
| `adx_14` | ADX(14) | Medium | |
| `donchian_20` | Donchian(20) | Medium Fast | |
| `rsi_14` | RSI(14) | Very Fast | ✓ |
| `macd_12_26_9` | MACD(12,26,9) | Medium Fast | ✓ |
| `ppo_12_26_9` | PPO(12,26,9) | Medium Fast | ✓ |
| `roc_20` | ROC(20) | Fast | ✓ |
| `stoch_rsi_14_3` | StochRSI(14,3) | Very Fast | ✓ |
| `cci_20` | CCI(20) | Fast | |
| `bollinger_20_2` | Bollinger(20,2) | Medium Fast | ✓ |
| `atr_14` | ATR(14) | Fast | |
| `natr_14` | NATR(14) | Fast | |
| `mfi_14` | MFI(14) | Very Fast | |
| `obv` | OBV | Medium | |

EMA and SMA use exact parameter-match rules because one plugin produces multiple
time horizons. Other listed plugins use one fixed class for their current curated
instances. Unknown or ambiguous matches raise; official plugins do not silently
fall back.

## 🧺 Multi-output Indicators

MACD, PPO, Bollinger, Donchian, Aroon, StochRSI, and ADX produce multiple outputs.
Every output of one instance shares the same bucket boundaries. Scalar outputs and
band components become columns in one row-oriented table.

For each populated cell:

- one observation uses compact `value` + real `date`;
- multiple observations preserve count, first, min, max, last, and their real
  observation dates.

`period_summary` is calculated across the entire exported period, independent of
bucket density. Each output column also carries its latest observed value/date.

## 🔥 Calculation Range, Exported Range, and Warm-up

Indicators calculate from observation-level input with plugin-owned,
parameter-aware warm-up. States and annotations are also derived before numeric
bucket aggregation.

Only the requested exported period is serialized:

```text
warm-up-inclusive calculation input
→ full observation-level indicator and event calculation
→ slice to exported period
→ aggregate numeric history
```

Asset loading delegates warm-up to `SignalService` through
`AssetSourceManager`. FX explicitly loads the required earlier daily rate range.
The component response declares `warmup_policy: component_owned`; the current
aggregate `calculation_range` and `earliest_calculation_date` metadata fields are
not populated.

FX source history may begin after the requested start. Dates before the first
stored rate are omitted from the warm-up input rather than failing the entire
snapshot. SignalService then includes calculable `ok`/`partial` instances and
reports unavailable instances through technical coverage. The snapshot metadata
publishes requested/available ranges and calendar-day coverage. No future rate is
ever used.

## 🎯 Event Selection

Events are validated, observed-only filtered, epsilon checked, gap checked, and
semantically deduplicated before selection. They are detected from original
observations, never from buckets.

Policy is independent for every:

```text
entity_id + annotation_key
```

For Portfolio and Broker, `entity_id` retains the originating Asset identity before
events are merged. FX uses the canonical pair identity.

For each group:

1. sort newest to oldest;
2. include every event satisfying
   `event_date >= snapshot_as_of - 30 calendar days`;
3. if fewer than 20 are included, continue linearly backward to 20;
4. if fewer than 20 exist, include all;
5. if more than 20 are recent, include all recent events;
6. restore deterministic public chronological order after group selection.

Formally:

$$
\text{exported\_count}
=
\min\left(
\text{total\_count},
\max(20,\text{recent\_count})
\right)
$$

The 30-day boundary is inclusive. There is no ranking, relevance score, distributed
historical sampling, family quota, episode consolidation, detail-specific event
policy, or cap on recent events.

Each group exports a selection summary with detected/recent/exported counts,
selection status, oldest/newest detected and exported dates, and optional
upward/downward counts.

## 🧭 Focused Context Policies

The complete technical datasets and explicitly technical analyses continue to use
the global policy above unchanged.

Semantic Composition V2 also exposes separate focused context components for
financial analyses. Their backend-declared policies are intentionally narrower and
do not alter global Compact/Standard/Full:

- Portfolio/Broker snapshots expose current/summary market fields and at most the
  latest selected structural event per Asset;
- multi-Asset comparisons expose a bounded set of latest structural event types;
- Portfolio Description uses an aggregate 30-day event digest, with the latest
  prior event when a type has no recent occurrence;
- Asset Position Context exposes three recent rows in Compact, six in Standard,
  and twelve in Full;
- FX Market Context exposes no context history in Compact, four recent rows in
  Standard, and eight in Full;
- Drawdown context sections carry no numeric history at all: they reuse the Risk
  `drawdown_summary` current/maximum episode dates and coverage verbatim;
- PAC's per-Asset Drawdown snapshot is one observed-price row per Asset and also
  carries no Drawdown history;
- task-specific evidence datasets apply component-local monotonic detail (for
  example income Compact aggregates by `(month, asset, income_type)`, Standard
  adds bounded recent dated rows, Full exposes every dated row).

These limits are semantic component contracts, not token-triggered truncation.
They never change the complete technical Export Data payload.

### 🧹 Public Empty Temporal Rows

The generic public renderer applies the same no-empty-row principle to financial
temporal tables that technical histories already use.

A row is omitted only when it contains nominal start/end/index metadata and no
observation, flow, variation, P&L, extrema, reconciliation, meaningful observed
date, or explicit non-absence status. Numeric zero remains meaningful and keeps
the row.

This presentation rule does not modify:

- backend bucket boundaries;
- calculations or requested frequency;
- sampling policy;
- requested/effective/available periods;
- coverage or insufficient-history warnings.

Probe diagnostics count empty rows detected/omitted and temporal rows remaining.

### 🏷️ Latest-per-category Context Events

Focused market-context components select **at most one latest event per
`(entity_id, signal_category)`**. The category is plugin-owned (read from the
Signal plugin's `category`, failing loudly for unknown plugins); candidates are
the allowlist-filtered observation-level discrete events. Tie-breaks within a
category are deterministic by `(date, annotation key, signal code)`, and
categories with no eligible event are omitted rather than emitted as null rows.

This is distinct from the complete/technical global event policy above, which
keeps the 20-event minimum plus every recent event. The permanent density probe
therefore tracks these event families **separately**: `detailed_event_rows`
(complete-policy events), `context_event_rows`, `latest_event_rows` with
`latest_event_category_count`, and the Portfolio Description
`event_digest_group_count` / `event_digest_underlying_event_count`.

### 💱 FX Observed Range Position

FX conversion-timing evidence frames the current rate against the observed period
minimum/maximum as a plain range position `(current - min) / (max - min)`,
deliberately **not** a historical percentile or rank and **not** a forecast. A
flat range (`observed_maximum == observed_minimum`) or an empty period reports
`range_position_ratio = None` with an explicit reason
(`flat_observed_range` / `no_observed_rates_in_period`). Partial source history is
explicit through `is_partial_history` plus a `partial_history_reason`
(`source_history_starts_after_period_start` /
`no_genuine_observations_in_period`); only genuine, non-backfilled observations
count and no future rate is ever consulted.

## 🧾 Manifest Examples

The public prompt manifest exposes only information that helps interpret the
sampled data:

```yaml
technical_sampling:
  detail_level: standard
  price_policy:
    bucket_count: 46
  indicator_policies:
    - signal_instance_id: ema_200
      signal_code: EMA
      temporal_class: very_slow
      bucket_count: 23
```

`detail_level` appears once because every policy in one request shares it.
`temporal_class` explains the indicator horizon, while `bucket_count` reports
the density actually exported.

`P`, `M`, and `K` remain normative internal policy parameters. They stay in the
matrix, formula tests, mathematical probes, and engineering reports above, but
are intentionally absent from the API response and copied prompt.

Top-level event policy audit:

```yaml
event_selection:
  minimum_latest_events_per_annotation: 20
  complete_recent_window_days: 30
  grouped_by:
    - entity_id
    - annotation_key
```

Per-group payload summary:

```yaml
entity_id: asset:42
annotation_key: ema_50_ema_200
detected_count: 37
recent_30d_count: 6
exported_count: 20
selection_applied: true
oldest_detected_event_date: 2024-02-01
newest_detected_event_date: 2026-07-29
oldest_exported_event_date: 2025-04-12
newest_exported_event_date: 2026-07-29
```

## 🧪 Extension and Testing Checklist

When adding or changing an exportable indicator:

1. declare plugin-owned `ai_export_temporal_rules`;
2. use fixed rules only for one semantic horizon;
3. use explicit parameter matching for multi-horizon plugins;
4. verify exactly one rule resolves for every curated instance;
5. keep warm-up, input validation, output validation, AI descriptions, states, and
   annotations plugin-owned;
6. verify all outputs share one grid;
7. test all relevant detail/class matrix rows and 90/180/365 counts;
8. test daily first seven days, monotonic widths, \(K\) bound, exact final boundary,
   no gap, and no overlap;
9. test unavailable/failed omission without sibling loss;
10. test event boundary inclusivity, 20-event minimum, unlimited recent events,
    grouping, deduplication, and order;
11. inspect `technical_sampling`, `event_selection`, and selection summaries;
12. run documentation validation.

```bash
./dev.py test services ai-export
./dev.py test services signal-plugin-matrix
./dev.py mkdocs build
./dev.py mkdocs check-links
```

## 🔗 Related Documentation

- [AI Export Overview](ai_export_snapshot.md)
- [Composition & Prompt](ai_export_composition.md)
- [Probe Workflow & Review](ai_export_probe_workflow.md)
- [Signal Plugin Guide](signal_plugin_guide.md)
