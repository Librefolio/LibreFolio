---
title: "Scheduler converts at the decision, not at storage"
category: decision
status: accepted
date: 2026-08-31
tags: [backend, scheduler, timezone, dst, frontend]
related_problems: [playwright-route-stub-is-per-context]
related: [problems/utc-today-vs-user-calendar, concepts/characterisation-test-latch, sources/settings-lane-and-sixteen-defects]
---

# Decision: store scheduler days and times in the configured zone

## Context

Scheduler days and times were stored in **UTC**, and the config modal converted
**only the times** for display. Days were not converted — they cannot be: they
are one global set that does not know which time they belong to.

Consequence, verified in the payload: a job at **Monday 02:00 UTC**, viewed with
the timezone set to Bogotá (UTC−5), showed the *Monday* chip lit next to the time
**21:00**. Those 21:00 are Sunday. The combination on screen does not exist.

## The proposal that was wrong

The first plan was to replace the day×time cartesian product with explicit
`(day, time)` slots, so each slot would carry its own weekday and convert
exactly. It required a new storage format, a data migration, and a redesigned
modal — a grid instead of two chip rows.

The user pushed back: the UI was fine. That objection was correct, and it
relocated the defect. **The model was never the problem; the conversion point
was.**

## Decision

Store days and times **in the configured timezone**. Convert to UTC exactly
once, in `due_history_sync`, when deciding whether to run.

Then *"Mon–Sat at 06:00 and 23:00, Rome time"* is a well-defined rectangle
again, the modal has nothing left to convert, and the defect is gone **by
construction** rather than by handling. The UI did not change at all.

## The unlooked-for gain: DST

With times in UTC, "09:00 Rome" is 08:00 UTC in winter and 07:00 in summer — so
the job **moved by an hour twice a year**, unasked. Storing local removes it.

The codebase already knew this was a hazard: `_local_times_to_utc()` existed in
`settings.py`, but its docstring restricted it to first-boot defaults.

## The price, accepted deliberately

The timezone stops being a *reading lens* and becomes **part of the definition**:
changing it moves the execution instant. This reverses an earlier decision made
in the same campaign ("the absolute instant must not move"), and was reversed
knowingly, because it matches the ordinary expectation — *"run it at 6 in the
morning, wherever I am"* — and because it is what makes DST harmless.

The modal now says so, rather than letting the user discover it.

## Two things this exposed

**The migration preserves the screen, not the instant.** Times are re-read as
local and weekdays are left alone, because it is the modal the user configured
against, so that is their intent. For `scheduler_timezone = UTC` — the default —
it is a verified no-op. Other installations shift once; that belongs in the
changelog.

**The browser fallback became dangerous.** The modal did:

```ts
selectedTz = schedulerTimezone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
```

Harmless while the timezone only chose a lens. Under the new semantics, two
admins on two continents would fix **different execution times** depending on who
saved first. Removed: empty means `UTC`, which is already the schema default.

## How it is tested

The DST half is the part that fails silently, and a single date never sees it.
The test uses **two**, one per side of the changeover, in `Europe/Rome`:

| date | UTC | local |
|---|---|---|
| 2026-01-15 | 08:00 | 09:00 CET |
| 2026-07-15 | 07:00 | 09:00 CEST |

and asserts the local hour does not move.

## Source files

| Role | Path |
|------|------|
| Decision logic | `backend/app/services/scheduler/scheduler.py` — `due_history_sync` |
| Settings parsing | `backend/app/services/scheduler/settings.py` |
| Key descriptions | `backend/app/schemas/settings.py` (~114-133) |
| Migration | `backend/alembic/versions/5b1333fa6b07_scheduler_times_use_configured_timezone.py` |
| Modal | `frontend/src/lib/components/settings/SchedulerConfigModal.svelte` |
| Tests | `backend/test_scripts/test_services/test_scheduler_due.py`, `test_scheduler_settings.py` |

## See also

- [[problems/utc-today-vs-user-calendar]] — the same question asked of `now()`:
  at which point does an instant become a calendar day, and in whose calendar.
  Eighteen sites, three product defects.
- [[concepts/characterisation-test-latch]] — the weekday behaviour was frozen by
  a characterisation test before it was decided.
- [[sources/settings-lane-and-sixteen-defects]] — item D1, and the knowing
  reversal of the earlier B2 conclusion.
