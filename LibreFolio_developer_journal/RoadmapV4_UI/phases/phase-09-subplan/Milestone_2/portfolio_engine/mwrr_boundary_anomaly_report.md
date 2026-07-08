# MWRR Boundary Anomaly — Analysis Report

**Date**: 2026-06-24  
**Scope**: MWRR series warm-start contamination bug  
**Status**: Fix applied and verified

---

## 1. Executive Summary

The MWRR (Money-Weighted Rate of Return) chart displayed wildly incorrect values for certain `date_from` selections — e.g. cumulative MWRR reaching 80% when the true value was ~16%. The root cause is a **warm-start contamination bug** in `calculate_mwrr_series()`: Newton's method solver propagates extreme annualized rates from short initial sub-periods to all subsequent points.

This is **NOT** a single-date bug. A scan of 166 start dates (Jan–Jun 2026) found **20+ dates** with >20 percentage point divergence between series and summary MWRR, including one case (2026-04-07) where cumulative MWRR reached 532%.

**Fix**: Guard the warm-start — when the solver finds an extreme rate (|r| > 2.0), retry from the default initial guess (0.1). Post-fix: 0 mismatches across all 166 dates.

---

## 2. Reproduction

### 2.1 Boundary dates: 2026-03-22..25

Transactions on boundary:
```
2026-03-23: DEPOSIT +1000 EUR → broker 1
2026-03-23: BUY    -986.24 EUR → asset 5, broker 1
```

NAV snapshots:
```
2026-03-22: 25943.90 (pre-deposit)
2026-03-23: 26825.52 (post-deposit, post-buy — market value absorbed)
2026-03-24: 26929.55
2026-03-25: 27164.98
```

### 2.2 Pre-fix results

| date_from  | summary mwrr_ann | summary mwrr_cum | series[-1] mwrr_ann | series[-1] mwrr_cum | Match |
|------------|----------------:|----------------:|--------------------:|--------------------:|:-----:|
| 2026-03-22 | 0.7555          | 0.1560          | 0.7555              | 0.1560              | ✓     |
| 2026-03-23 | 0.7955          | 0.1608          | **9.0145**          | **0.7987**          | ✗     |
| 2026-03-24 | 0.7795          | 0.1564          | **23.1969**         | **1.2325**          | ✗     |
| 2026-03-25 | 0.7298          | 0.1464          | 0.7298              | 0.1464              | ✓     |

### 2.3 Post-fix results

| date_from  | summary mwrr_cum | series[-1] mwrr_cum | Match |
|------------|----------------:|--------------------:|:-----:|
| 2026-03-22 | 0.1560          | 0.1560              | ✓     |
| 2026-03-23 | 0.1608          | 0.1608              | ✓     |
| 2026-03-24 | 0.1564          | 0.1564              | ✓     |
| 2026-03-25 | 0.1464          | 0.1464              | ✓     |

---

## 3. Root Cause Analysis

### 3.1 The warm-start mechanism

`calculate_mwrr_series()` solves XIRR independently for each day, but uses the previous day's solution as the initial guess (`prev_guess`) for Newton's method. This normally makes convergence fast (~1–2 iterations vs ~20).

### 3.2 The contamination path

When `date_from = 2026-03-23`:

1. **Period rebasing** creates synthetic CF of -26825.52 on 2026-03-23
2. The €1000 deposit on 2026-03-23 is excluded (it's embedded in the starting NAV)
3. **Day 1** (2026-03-24): solver sees flows = `[(-26825, day 0), (+26929, day 1)]`
4. NPV equation: `-26825 + 26929/(1+r)^(1/365) = 0` → `r ≈ (26929/26825)^365 - 1 ≈ 3.1`
5. This 310% annualized rate is **mathematically correct** for a 0.39% daily return annualized to 365 days
6. `prev_guess = 3.1` — warm-start is now contaminated

7. **Day 2** (2026-03-25): solver starts at `x0 = 3.1` → Newton converges to a **different local root** at ~8.9 (892% annualized)
8. The NPV equation has multiple roots when the time horizon is very short and CFs are large relative to daily returns
9. `prev_guess = 8.9` → all subsequent days converge near 8.9 because Newton never escapes this basin

### 3.3 Why summary is correct

The summary `calculate_mwrr()` solves XIRR once for the **entire period** (93 days), starting from `x0 = 0.1`. With the full period, the NPV equation has a unique moderate root (~0.80) and Newton converges correctly.

### 3.4 Bug category

**Warm-start contamination in iterative XIRR solver with non-convex objective.**

The XIRR NPV function is not convex — it can have multiple roots, especially for short periods with large initial CFs. The warm-start optimization assumes the rate changes smoothly between consecutive days, which fails catastrophically when:
- The period starts on or near a large cash flow date
- The first few sub-periods are very short (1–3 days)
- The annualized rate for these short periods is extreme (>200%)

---

## 4. Other Anomalous Dates (Pre-fix)

Full scan of 166 date_from values (2026-01-01 to 2026-06-15):

| date_from  | series mwrr_cum | summary mwrr_cum | Δ (pp) | 
|------------|----------------:|----------------:|-------:|
| 2026-01-05 | 1.6707          | 0.1536          | 151.7  |
| 2026-01-27 | 1.5577          | 0.1400          | 141.8  |
| 2026-02-05 | 2.1693          | 0.1492          | 202.0  |
| 2026-02-10 | 1.1532          | 0.1344          | 101.9  |
| 2026-02-23 | 1.0237          | 0.1192          | 90.5   |
| 2026-02-24 | 1.1078          | 0.1139          | 99.4   |
| 2026-03-04 | 0.5513          | 0.1333          | 41.8   |
| 2026-03-09 | 0.8559          | 0.1398          | 71.6   |
| 2026-03-23 | 0.7987          | 0.1608          | 63.8   |
| 2026-03-24 | 1.2325          | 0.1564          | 107.6  |
| 2026-03-30 | 1.3890          | 0.1745          | 121.5  |
| 2026-03-31 | 1.9961          | 0.1660          | 183.0  |
| 2026-04-06 | 1.7527          | 0.1505          | 160.2  |
| 2026-04-07 | **5.3269**      | 0.1483          | **517.9** |
| 2026-04-23 | 0.6955          | 0.0879          | 60.8   |
| 2026-05-04 | 0.7603          | 0.0753          | 68.5   |
| 2026-05-05 | 1.2669          | 0.0692          | 119.8  |
| 2026-05-12 | 0.3645          | 0.0490          | 31.6   |
| 2026-05-13 | 0.4407          | 0.0430          | 39.8   |

**All 20+ anomalies eliminated post-fix.**

---

## 5. Fix Applied

**File**: `backend/app/utils/financial/roi_utils.py`, function `calculate_mwrr_series()`

**Changes**:
1. Added `_WARM_START_CAP = 2.0` — if |rate| exceeds this, the warm-start resets
2. When an extreme rate is found, retry from `x0 = 0.1` (default guess)
3. If the retry finds a smaller-magnitude root, use that instead
4. The warm-start only propagates moderate rates (<= 200% annualized)

**Why this is the right fix**:
- Does not cap or clip the MWRR result itself (mathematical integrity preserved)
- Only controls the warm-start seed to prevent solver contamination
- Extreme early-period rates are still computed correctly (they're mathematically valid for 1-day periods)
- As the period grows, the solver naturally converges to the moderate root
- Consistent with the summary MWRR which uses `x0 = 0.1` unconditionally

---

## 6. Invariants Verified

| Invariant | Pre-fix | Post-fix |
|-----------|:-------:|:--------:|
| `history[0].roi == 0` | ✓ | ✓ |
| `history[0].twrr == 0` | ✓ | ✓ |
| `history[0].mwrr_cumulative == 0` | ✓ | ✓ |
| `summary.mwrr_cum == history[-1].mwrr_cum` | ✗ (20+ failures) | ✓ (0 failures) |
| `summary.twrr == history[-1].twrr` | ✓ | ✓ |
| MWRR sign consistent with NAV direction | ✗ (extreme positives when NAV down) | ✓ |

---

## 7. GrowthChart Frontend Mapping

Verified correct:
- Chart uses `history[].mwrr_cumulative` (line 92 of GrowthChart.svelte)
- Does NOT use `mwrr` or `mwrr_annualized`
- `pctSeries` correctly maps all three metrics (MWRR cum, TWRR, ROI)

The anomaly was **purely backend** — the chart faithfully displayed the incorrect series data.

---

## 8. Additional Changes

### Period scope note
Added `"periodScopeNote"` i18n key: "Metriche calcolate sul periodo selezionato" (IT), displayed as a discreet right-aligned note below the KPI row.

---

## 9. Validation

```
✅ ruff: 0 errors (roi_utils.py, portfolio_service.py, portfolio.py)
✅ svelte-check: 0 errors
✅ 150+ financial tests: all pass
✅ JSON i18n: all 4 files valid
✅ MWRR scan: 0/166 date_from values with series/summary mismatch
```

---

## 10. Recommended Future Tests

1. **Unit test**: MWRR series with large CF on day 1 → verify series[-1] matches single-shot MWRR
2. **Unit test**: MWRR series where first day has >1% daily return → verify warm-start doesn't contaminate
3. **Property test**: for any `date_from`, `series[-1].mwrr_cumulative ≈ summary.mwrr_cumulative` (within rounding)
4. **Regression test**: specific case with deposit on period start date
