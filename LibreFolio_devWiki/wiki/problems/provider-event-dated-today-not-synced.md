---
title: "A sync never writes a provider event dated today: it arrives with the first sync of a later day"
category: problem
status: open
date: 2026-10-15
tags: [backend, assets, sync, providers, asset-events, scheduled-investment, dates]
related:
  - features/F-027
  - features/F-031
  - features/F-034
  - concepts/daily-point-policy
  - concepts/prices-current-side-effect
  - decisions/asset-event-saves-all-or-nothing
---

# Problem: a provider event dated today is not synced on its day

## Symptom

Release 1.3, workstream W, lot E1b, 15/10. The E2E test of «+ New event» against a provider's event set up its own
asset: a `scheduled_investment` with a DIVIDEND planned for today, then `POST /api/v1/assets/prices/sync`. The test
was red in its precondition: the sync reported `events_fetched` 0, and no provider event was stored. A planned
event dated today is missing on its own day, and arrives only with the first sync of a later day.

## Root Cause

A provider's events reach the database through the history only:

- the fetch reads the history up to yesterday when the requested range reaches today:
  `history_end = min(end, today - timedelta(days=1)) if end >= today else end` (`refresh.py:227`);
- today's point comes from `get_current_value()`. Its `FACurrentValue` holds a value, a currency, `as_of_date` and a
  source, and no events;
- the events of `FAHistoricalData` are what `_upsert_asset_events()` writes (`refresh.py:557`).

So an event dated today is written once today has become history: by the first sync, on a later day, whose range
covers that date.

What follows from the code, not observed: on the event's own day, «+ New event» finds no provider event on that date
and type, so decision 20 lets the user create a manual one. The next day's sync then adds the provider's event on the
same key. Rows of different sources never match: `_write_asset_events()` filters on `provider_assignment_id`.

## Solution

None yet. The test-author found the cause, and W reported it to the coordinator on 15/10. The behaviour belongs to
`services/assets/`, workstream X's area. There is no backlog entry at filing.

The E2E test works around it: the event and the transaction form are dated yesterday (`setFormDate`). The spec says
why in a comment.

## Prevention

- A provider that plans events (Scheduled Investment) produces today's events only through `get_history_value()`.
  A test that needs a provider event right after a sync must date it before today.
- A fix would have to bring today's events in while today's price keeps coming from the current value, upserted
  through the day ([[concepts/daily-point-policy]], [[concepts/prices-current-side-effect]]).

## Impact

- Small for users: a planned dividend or interest dated today shows on the chart and in the editor one day late. A
  transaction booked that day cannot link it yet.
- One E2E red in the wrong place: the precondition failed, not the behaviour under test. It cost a rerun in the shared
  slot.

## Source files

| Role | Path |
|------|------|
| `history_end` (line 227); the provider events written (line 557) | `backend/app/services/assets/refresh.py` |
| `FACurrentValue` (no events), `FAHistoricalData.events` | `backend/app/schemas/prices.py` |
| Events planned by the Scheduled Investment provider | `backend/app/services/asset_source_providers/scheduled_investment/plugin.py` |
| Upsert of the provider events, matched on their own source | `backend/app/services/assets/event_store.py` |
| E2E with the workaround (`setFormDate`, the comment on `history_end`) | `frontend/e2e/transactions/tx-event-create-exists.spec.ts` |
| Plan 04, section E1, step 3 | `LibreFolio_developer_journal/Release_2/Phase_1/04_importTransactions/plan-phase01ImportTransactions.prompt.md` |
