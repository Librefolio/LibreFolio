---
title: "STALE_PRICE was never emitted for three months — and `valuation_stale` is not only about market prices"
category: problem
status: resolved
date: 2026-09-30
first_seen: 2026-06-19
resolved: 2026-09-30
tags: [portfolio, data-quality, dashboard, prices, risk, testing, e2e, mockprov]
related: [problems/fx-backward-fill-unbounded-stale-rates, features/F-054, features/F-025, domains/dashboard, sources/phase00-taxonomy-select-2026-10]
---

# Problem: the stale-price banner existed, the report never filled it

> Backlog **K-25** asked for this page (workstream K, step 13, item 9 — decision D8 of 2026-09-30, commit
> `f1fe176a2`).

## What was wrong

- The Dashboard's data-quality report had a `STALE_PRICE` issue ("prices not updated"), with a banner, an i18n
  message and a CTA — but `PortfolioService.get_summary` never passed `stale_prices_dto` to
  `build_data_quality_report`. It had stopped doing so with the scope-aware engine rewrite (`77b976ebc`,
  2026-06-19): a holding whose price had been carried forward for weeks raised nothing.
- The cure could not simply forward the engine's flag: the engine's per-position `valuation_stale` means "the mark
  used for this valuation is more than `STALE_PRICE_THRESHOLD_DAYS` (7) days old" **whatever the mark is** — a real
  quote carried forward (`MARKET_PRICE`) **or a trade-derived mark** (`LAST_TRADE_PRICE`: the last BUY/SELL/priced
  ADJUSTMENT). Forwarding it raw would have flagged every manual asset (crowdfunding, a held bond with no provider),
  which is valued at its last trade price by design, and would have double-reported provider assets with no quote at
  all, which `TRANSACTION_IMPLIED` already reports.

## The rule (D8, confirmed by the developer)

An asset is reported once (its latest stale date across brokers) when **all four** hold for an open end-of-period
position:

1. `valuation_stale` (mark older than 7 days at the valuation date);
2. `valuation_source == MARKET_PRICE` — a trade-derived mark is excluded;
3. the asset has a **provider** — a manual asset is stale by design;
4. the position is still open at the end of the period.

The CTA became **`sync_asset_prices`**: the Dashboard calls `POST /assets/prices/sync` for the flagged assets from
`'resume'` (the day after the last stored price, the rule of every automatic sync) to the Dashboard's end date, one
toast per result (the name escaped), then reloads the report. The lab (Risk) treats any `sync_` action as its own
sync. Effect beyond the banner, also confirmed: `stale_prices` makes the report status `CARRIED_FORWARD`, so Risk
reports partial portfolio results while a filtered asset is stale.

## Lessons for tests

- **Opening `/assets` writes today's price.** The page polls `POST /assets/prices/current`, and every successful
  provider quote dated today is persisted as today's OHLC row (`get_current_prices_bulk`, "F.2 + F.3"). An E2E that
  needs a stale quote must use `mockprov` with `INVALID_TICKER_12345`, the one identifier the mock refuses — any
  other ticker is silently refreshed by a concurrent spec that opens the asset list.
- Each negative control first asserts the position row exists, so it cannot pass on an empty portfolio.

## Residuals

- **K-24** (assigned): `developer/frontend/data-quality-banner.md` still says "All 5 codes can appear together"
  (`:234`); the user Dashboard page says manual assets are "valued at purchase cost", while the engine uses the last
  trade price.
- The FX twin of this rule — rates carried forward without a bound — is not a Dashboard issue:
  [[problems/fx-backward-fill-unbounded-stale-rates]] (option C there).

## Source files

| Role | Path |
|------|------|
| The D8 rule, `stale_prices_dto` | `backend/app/services/portfolio_service.py` |
| `valuation_stale`, `STALE_PRICE` issue and CTA | `backend/app/services/portfolio_engine.py` |
| Threshold (7 days) | `backend/app/services/data_quality_thresholds.py` |
| `StalePriceAsset`, `DataQualityStatus` derivation | `backend/app/schemas/portfolio.py` |
| Risk: stale assets → partial results | `backend/app/services/risk/service.py` |
| Current price write-back | `backend/app/services/asset_sources/price_query.py` |
| Mock provider refusal | `backend/app/services/asset_source_providers/mockprov.py` |
| Dashboard CTA branch | `frontend/src/routes/(app)/dashboard/+page.svelte` |
| Banner (icon per CTA) | `frontend/src/lib/components/ui/feedback/DataQualityBanner.svelte` |
| Lab action mapping | `frontend/src/lib/components/risk/syncTargets.ts` |
| Service tests (`TestStalePriceDataQuality`) | `backend/test_scripts/test_services/test_financial/test_portfolio_service.py` |
| Pure test (CTA) | `backend/test_scripts/test_services/test_financial/test_portfolio_engine/test_data_quality_report.py` |
| E2E | `frontend/e2e/portfolio/stale-price-banner.spec.ts` |
| Doc (K-24 debt) | `mkdocs_src/docs/developer/frontend/data-quality-banner.md` |
| Plan (step 13, item 9) | `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep13DevNotesFixes.prompt.md` |
