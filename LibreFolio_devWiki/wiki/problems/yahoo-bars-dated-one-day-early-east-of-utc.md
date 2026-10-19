---
title: "Yahoo bars of exchanges east of UTC were stored one day early"
category: problem
status: resolved
date: 2026-10-17
tags: [backend, providers, yahoo, timezone, dates, workstream-z]
related:
  - problems/provider-event-dated-today-not-synced
  - features/F-025
  - features/F-031
  - entities/asset-sources-package
---

# Problem: Yahoo bars of exchanges east of UTC were stored one day early

## Symptom

Every daily price, dividend and split Yahoo Finance returned for an exchange east of UTC was stored **one day early**:
Milan and Frankfurt all year, London in summer, Tokyo, Sydney. Monday's close landed on Sunday. Every release up to
1.2.1 did it. The current value was dated by the UTC date of `regularMarketTime`, wrong for a session that crosses UTC
midnight (Sydney, Auckland). Found by workstream Z on 17/10/2026 (Z-33).

## Root Cause

yfinance stamps daily bars, dividends and splits at **midnight in the exchange's timezone** (`scrapers/history.py`,
`tz_localize(tz_exchange)`). The plugin's `_normalize_yahoo_date` converted that instant to UTC before taking its date;
for any zone ahead of UTC, local midnight is the previous day in UTC.

## Solution (what stays)

- `_normalize_yahoo_date` takes the index value's own date: the session's date.
- The current value reads `regularMarketTime` in the timezone of `info["exchangeTimezoneName"]` (UTC when it is
  missing or unknown). `_exchange_zone()`, private to the plugin, logs once per zone a name the server's timezone
  database does not know (a host without `tzdata`; backlog Z-36).

## Decision: no repair of the rows already stored (developer, 19/10/2026)

On 17/10 Z-33 also shipped a one-time repair: migration 011 added `asset_provider_assignments.exchange_timezone` with a
`'legacy-utc'` mark, and each marked asset's first refresh re-dated its old rows against the full history used as a
calendar (decision N86, variant D″), with a claim of the mark against concurrent refreshes and forward-only re-date
helpers. On 19/10 the developer removed all of it (lot Z-33r), verbatim: «fai solo la correzione, se servirà gli
utenti apriranno una issue e gli diremo di cancellare entrambi e rifare il sinc». A DB column born from one plugin's
problem ties the system to that plugin, and the system must stay generic. Migration 011 had never shipped in a release
(v1.2.1 stops at 004); a DB that had applied it is fixed by hand (a `downgrade` before the update, or two SQL lines
after: plan 06, section «Z-33r»).

## Consequences (what users see)

- The scheduler's first run after the update rewrites the last 14 days on the right dates; older rows stay one day
  early. Inside that window a Sunday or a holiday keeps the next session's close.
- A dividend or split in the window appears twice (the old one a day early). A split counts only through linked
  ADJUSTMENT rows, so figures change only if the new one is linked too. Remedy: delete both and sync again.
- A clean price history: «wipe market data» then a full sync (the wipe is refused, X-R48, while a split has linked
  adjustments without a purchase cost).

## Prevention

A provider reads a day stamp in the zone it was stamped in, never through UTC (`asset_plugin_guide.md`). The guard:
`test_z33_history_dates_each_bar_and_event_on_its_exchange_day` (Milan, London across both clock changes, Tokyo,
Beirut's skipped midnight, New York and UTC as guards).

## Source files

| Role | Path |
|------|------|
| Plugin (dates, current value, `_exchange_zone`) | `backend/app/services/asset_source_providers/yahoo_finance/plugin.py` |
| Tests | `backend/test_scripts/test_services/test_yahoo_finance_errors.py` |
| Docs | `mkdocs_src/docs/developer/backend/assets/provider_yahoo_finance.md` |
| Plan (Z-33, its reduction Z-33r, the repair guide) | `LibreFolio_developer_journal/Release_2/Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md` |
