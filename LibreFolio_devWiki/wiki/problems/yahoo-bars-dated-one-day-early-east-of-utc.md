---
title: "Yahoo bars of exchanges east of UTC were stored one day early"
category: problem
status: resolved
date: 2026-10-17
tags: [backend, providers, yahoo, timezone, dates, migration, events, scheduler, workstream-z]
related:
  - problems/provider-event-dated-today-not-synced
  - features/F-025
  - features/F-031
  - features/F-090
  - entities/asset-sources-package
---

# Problem: Yahoo bars of exchanges east of UTC were stored one day early

## Symptom

Every daily price, dividend and split that Yahoo Finance returned for an exchange east of UTC was stored **one day
early**: Milan and Frankfurt all year, London in summer, Tokyo, Sydney. Monday's close landed on Sunday.

- Every release up to 1.2.1 wrote such rows: any installation with Yahoo assets on those exchanges has them.
- The current value was dated by the UTC date of `regularMarketTime`: wrong for a session that crosses UTC midnight
  (Sydney, Auckland).
- Found by workstream Z on 17/10/2026 (Z-33, HIGH). The coordinator confirmed it with a probe:
  `2025-07-07 00:00+02:00` gave `2025-07-06` through UTC.

## Root Cause

yfinance (1.7.0 in the locks of 1.1.0 to 1.2.1) stamps daily bars, dividends and splits at **midnight of the
exchange's timezone** (`scrapers/history.py:494–501`). The plugin's `_normalize_yahoo_date` converted that timestamp
to UTC before taking its date. For any zone with a positive offset, local midnight is the previous day in UTC.

## Why the fix is not the code change alone

Fixing the date in the plugin alone would have made things worse at the next sync:
- **prices** merge by date (`asset_id + date` is unique): a re-sync rewrites the weekdays, but the rows on days
  without a session (Sundays, holiday eves) stay, each holding the next session's close;
- **events** are matched on (asset, date, type) within the same source, so the correct dividend or split is **added
  next to** the shifted one: at the first scheduler run (its 14-day window) and over the whole history at every full
  sync. A split counts only through the ADJUSTMENT rows linked to it (`load_split_links`), so an unlinked duplicate
  changes no figure, but a user who links both applies it twice;
- `transactions.asset_event_id` is `ON DELETE RESTRICT`, so a shifted event cannot simply be deleted.

So the code fix and a one-time repair ship together (decision N86).

## Solution

1. **Plugin**: the index's own local date; the history declares the exchange timezone (the index's, else
   `info["exchangeTimezoneName"]`) in `FAHistoricalData.exchange_timezone`; the current value is dated in that zone
   and declares it too (`FACurrentValue.exchange_timezone`). Neither field is in OpenAPI.
2. **Migration 011** adds `asset_provider_assignments.exchange_timezone` and marks every existing yfinance assignment
   `'legacy-utc'`. A NULL would not do as «to re-date»: an assignment removed and added again after the repair is
   born NULL and would be re-dated a second time.
3. **The refresh**, by state: a mark → the one-time check, then the timezone is stored; NULL (an assignment created
   in 1.3) → the timezone is stored, nothing moves; a timezone → updated if it changes, nothing moves.
4. **The one-time check (D″)**: one read of the full history, past the cache, used only as a **calendar** of sessions
   and events; its slice of the requested range is the data written. Stored values never change.
   - The rule: a row stored on S belongs to S+1 when the zone's UTC offset at local midnight of S+1 is positive.
   - A price row moves S → S+1 only if the rule agrees, the calendar has a session on S+1, and S ≤ D_f − 2, where D_f
     is the server-local date of the last fetch before the upgrade (no fetch recorded: no price moves).
   - An event moves only if the rule agrees and the calendar has the same type on S+1 and not on S.
   - Latest first. A price that meets a row already on its new date (any source) is dropped and that row stays. An
     event that meets one of the same source and type is merged into it: its transactions are re-pointed there, then
     it is deleted.
   - A moved SPLIT carries along the ADJUSTMENTs linked to it and dated on its old day S, since Yield on Cost refuses
     a split link whose transaction date differs from the event's (`yield_on_cost.py:404`). It is the one place
     where the repair moves transactions.
   - The moved rows get a fresh `fetched_at` / `updated_at`, which the portfolio cache keys on.
   - The moves and the timezone (which clears the mark) are written in one transaction, before any other write of the
     asset. No calendar, no timezone or an error: nothing is written for that asset, it is reported failed, the mark
     stays, and the next refresh tries again.
   - Rows older than Yahoo's history are logged per asset, as a count only.

## Options rejected, and why

- **Delete and re-fetch**: the scheduler re-reads only 14 days, the links are RESTRICT, and it needs the network.
- **Re-date offline in a post-migration step**: exact only with a table from ticker suffix to timezone, which
  neither yfinance nor LibreFolio has.
- **Re-date by the rule alone**: the old current value was dated in UTC, which is right for a daytime session, and
  every sync wrote it as today's row. Legacy series therefore hold rows that are already correct: every synced
  Friday and holiday eve, and the last one or two rows. The rule alone would push them to Saturdays, holidays and
  tomorrow, hence the calendar's confirmation and the D_f − 2 bound.
- **Replace the stored closes from a fresh full history (D′)**: the plugin calls `ticker.history(...)` without
  `auto_adjust`, and yfinance defaults to `auto_adjust=True`. The stored closes are adjusted as of each fetch, so
  replacing them would rewrite the whole history to today's adjustment. That patchwork is a separate finding (Z-35).

## Limits (documented)

- An asset whose yfinance assignment was removed before the upgrade, or before its first refresh after it, keeps its
  shifted rows; if its identifier moved to a line on the other side of UTC before that refresh, the check applies the
  new line's timezone and calendar to the old line's rows. A report is planned after 1.3 (Z-34).
- Rows older than Yahoo's history stay (counted in the log).
- A database taken below 011 after the check, then upgraded again, is marked again, and its next refresh would move
  prices already on their day: no downgrade past 011 once the server has synced.
- The last two days before D_f never move: a release-era full sync on day D left session D's bar on D − 1, which the
  scheduler's first window rewrites.

## Prevention

- A provider's day stamp is read in the zone it was stamped in, never through UTC: `asset_plugin_guide.md` says so,
  with the optional `exchange_timezone`.
- Guard tests: the rule over a whole year for 12 zones, London's clock changes, Beirut (no local midnight on its DST
  day), Sydney's current value; the second run is a no-op; manual rows never move; an old backup restored gets the
  mark.

## Impact

Every Yahoo asset on an exchange east of UTC: extra rows on days without a session, dividends and splits a day early;
a fix of the plugin alone would have duplicated the events. After the update, each Yahoo asset's first refresh reads
its full history once, so the first scheduler run may take a little longer; a timeout keeps the mark and retries.

## Source files

| Role | Path |
|------|------|
| Plugin (local date, exchange timezone) | `backend/app/services/asset_source_providers/yahoo_finance/plugin.py` |
| The rule and the mark | `backend/app/utils/exchange_dates.py` |
| Migration 011 | `backend/alembic/versions/011_provider_exchange_timezone.py` |
| The one-time check | `backend/app/services/assets/refresh.py` |
| Price re-date | `backend/app/services/assets/price_store.py` |
| Event re-date (the SPLIT rule) | `backend/app/services/assets/event_store.py` |
| Schemas | `backend/app/schemas/prices.py` |
| Tests (plugin, rule) | `backend/test_scripts/test_services/test_yahoo_finance_errors.py` |
| Tests (the check) | `backend/test_scripts/test_services/test_asset_source_refresh.py` |
| Tests (migration, restore) | `backend/test_scripts/test_db/test_migration_011_exchange_timezone.py` |
| Docs | `mkdocs_src/docs/developer/backend/assets/architecture.md` |
| Docs (events) | `mkdocs_src/docs/developer/backend/assets/events.md` |
| Plan | `LibreFolio_developer_journal/Release_2/Phase_1/06_sleepWake/plan-phase01SleepWake.prompt.md` |
