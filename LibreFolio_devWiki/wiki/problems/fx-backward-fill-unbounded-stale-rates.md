---
title: "Unbounded FX backward-fill turns interior gaps into silent stale rates"
category: problem
status: accepted
date: 2026-10-06
tags: [backend, fx, data-quality, silent-failure, dashboard, risk, accepted, backward-fill]
related: [problems/zero-purchase-cost-foreign-asset-paid-in-report-currency, decisions/financial-math-single-average-cost, decisions/manual-fx-sentinel, concepts/daily-point-policy, problems/fx-multi-route-no-fallback, features/F-017, features/F-057, sources/phase00-fx-dashboard-sync-2026-10]
---

# Problem: unbounded FX backward-fill turns interior gaps into silent stale rates

> The page promised by decision **D6** of the FX-in-Dashboard plan (§11) and never written; filed on 2026-10-09 as
> backlog item **N-9**. Status `accepted`: the behaviour is a deliberate trade-off, not a fix that is pending — but
> its consequence on the Dashboard is invisible, and that is what this page is for.

## Symptom

A pair whose stored history has a hole in the middle converts every day of the hole with the **last rate before
it**, however old. Nothing on the Dashboard says so: no data-quality banner, no badge, no warning in the report.

The case D6 is about is a hole the fix itself creates. A pair synced only for a recent period has no rate before
its first stored day, so an older transaction raises `MISSING_FX_RATES` ("NAV incomplete"). The banner's Sync
fetches that date ±7 days — an island of rates before the stored series. Every day between the island's end and
the first stored rate was *missing* before the sync (reported, although only for periods reaching back there);
after it, the same days are *filled* from the island's last rate and nothing reports them.

## Root cause

`convert_bulk()` (`backend/app/services/fx.py:1240`) is the one conversion path of the backend. Its docstring says
it plainly (`:1247`): *"unlimited backward-fill: if rate for exact date is not found, uses the most recent rate
available (no time limit)"*. For each conversion it does `bisect_right(pair_dates, date)` and takes the rate at
`pos - 1` (`:1384-1385`):

| Requested date | Result |
|---|---|
| on or after a stored rate, any distance | that rate, `backward_fill_applied = rate_date < date` |
| before the first stored rate (`pos == 0`) | `RateNotFoundError`, or `None` plus an error string with `raise_on_error=False` |
| after the last stored rate | the last rate, same as an interior gap |

The function does return what a caller needs to notice: each result is `(Currency, rate_date, backward_fill_applied)`,
and a `logger.debug("backward_fill_applied", days_back=…)` records the distance. There is **no maximum age** and no
warning above debug level. Whether staleness becomes visible therefore depends entirely on the caller:

| Caller | What it does with `rate_date` / the flag | Stale FX visible? |
|---|---|---|
| Portfolio engine, `_preload_fx_rates()` (`portfolio_engine.py:2629`, call at `:2705`) — every NAV, P&L and Dashboard figure | keeps only the converted amount in `fx_rate_map`; date and flag are **discarded** | **no** |
| Series preparation for Risk and Signals (`series_preparation.py:377`) | counts a point as carried-forward FX when `valuation_date − fx_rate_date > STALE_PRICE_THRESHOLD_DAYS` (7, `data_quality_thresholds.py:14`) → `DataQualityReport.carried_forward_fx_points/pairs` (`schemas/portfolio.py:230-232`), surfaced by `risk/service.py:1379` and `signal_service.py:627` | yes, above 7 days |
| `POST /fx/currencies/convert` (`api/v1/fx.py:524`, call at `:623`) | returns `BackwardFillInfo` with `days_back` | yes, to the API caller |
| Engine price marks (`portfolio_engine.py:1521`) | `is_stale = days_back > 7` — for **prices**, not FX | n/a |

So the same rate is "stale" in Risk and Signals and "fine" on the Dashboard. `MISSING_FX_RATES` fires only when no
earlier rate exists at all — and because conversion and data quality share `convert_bulk`, the moment one older
rate exists, an interior gap stops being reported.

## A worked example (generic numbers)

EUR/USD is stored only from 2026-01-10. A transaction on 2025-06-15 has no rate on or before its date, so the
Dashboard raises `MISSING_FX_RATES`. The banner's Sync fetches 2025-06-08 … 2025-06-22 (first date − 7 to last
date + 7, capped at today: `frontend/src/lib/utils/sync/syncRange.ts`, `SYNC_MARGIN_DAYS = 7`). From then on:

- the issue is gone — the transaction now has a rate;
- 2025-06-23 … 2026-01-09 (~200 days), *missing* before the sync, convert at the 2025-06-22 rate;
- the engine values NAV on those days with it, and no banner appears;
- only Risk and Signals list the pair in `carried_forward_fx_pairs`.

Any other interior hole behaves the same way: a pair stored up to some date and again from a later one fills the
whole hole with the rate before it.

## Why it was accepted (D6, 2026-10-06)

Plan `plan-phase00FxDashboardSync.prompt.md` (§ D6, ~lines 306-319, summary at ~61-64):

- **A — chosen**: the banner syncs only ±7 days around the missing dates. New pairs no longer get holes, because
  decision **D1** of the same plan makes a pair created with a real provider sync its whole history (`start = 'min'`
  in `frontend/src/lib/services/fxCreationSync.ts`). Old pairs synced piecemeal before the fix are repaired once,
  by hand: FX → MAX → Sync all. A CHANGELOG note says so.
- **B — rejected**: the banner's Sync runs to today. It closes the hole in one go, but re-downloads and rewrites
  the whole series from `date_from − 7`, because the provider is treated as the authority
  (`mkdocs_src/docs/user/fx/sync.en.md`).
- **C — not chosen**: treat stale FX the way `STALE_PRICE` treats prices. Separate backend work; the developer chose
  A and nothing was deferred (alignment of 2026-10-09) — this page is the only trace it leaves.

The same backward-fill is what makes weekends and bank holidays convert at all (a central bank publishes no rate on
those days), so "no backward-fill" is not an option; the open question is only the **bound** and the **report**.

## What a real fix would need (not decided)

- carry `rate_date` (or `days_back`) into the engine's `fx_rate_map` instead of the bare amount;
- a Dashboard data-quality issue for FX carried forward beyond `STALE_PRICE_THRESHOLD_DAYS`, the rule Risk and
  Signals already apply;
- optionally a maximum age in `convert_bulk` beyond which a conversion is "missing", not "filled" — which would
  change `MISSING_FX_RATES` and the cost-basis paths that rely on it
  ([[problems/zero-purchase-cost-foreign-asset-paid-in-report-currency]],
  [[decisions/financial-math-single-average-cost]]).

## Prevention

- When a figure looks wrong for a foreign-currency position, check the pair's history for holes before suspecting
  the engine: the Dashboard will not tell you.
- Anyone touching `_preload_fx_rates()` should know it throws away the only staleness signal the FX service gives.
- A new FX pair should be created through the creation service, which fetches the full history.

## Impact

Silent: NAV, P&L and allocation of positions in a currency whose history has holes can use rates months or years
old. Affects mainly pairs synced range-by-range before 2026-10-06. No data is lost; a full "sync MAX" of the pair
repairs it.

## Source files

| Role | Path |
|------|------|
| `convert_bulk()` — unlimited backward-fill, flag and debug log | `backend/app/services/fx.py` |
| Engine FX preload — discards date and flag | `backend/app/services/portfolio_engine.py` |
| Carried-forward FX count for Risk and Signals | `backend/app/services/series_preparation.py` |
| Staleness threshold (7 days) | `backend/app/services/data_quality_thresholds.py` |
| `DataQualityReport.carried_forward_fx_*`, `MISSING_FX_RATES` | `backend/app/schemas/portfolio.py` |
| Risk surfacing of carried-forward pairs | `backend/app/services/risk/service.py` |
| `POST /fx/currencies/convert` with `BackwardFillInfo` | `backend/app/api/v1/fx.py` |
| Banner sync range (±7 days, capped at today) | `frontend/src/lib/utils/sync/syncRange.ts` |
| Full history on pair creation (D1) | `frontend/src/lib/services/fxCreationSync.ts` |
| User doc: provider as the authority on sync | `mkdocs_src/docs/user/fx/sync.en.md` |
| Plan, decisions D1-D7 and §11 | `LibreFolio_developer_journal/Release_2/phases/28_fxDashboardSync/plan-phase00FxDashboardSync.prompt.md` |
| Backlog item N-9 | `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/README.md` |
