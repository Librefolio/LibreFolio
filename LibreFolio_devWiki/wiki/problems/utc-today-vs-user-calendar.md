---
title: "`toISOString().slice(0,10)` is not today — 18 sites, 3 product defects"
category: problem
status: resolved
date: 2026-08-29
updated: 2026-10-16
tags: [frontend, dates, timezone, testing, product-defect]
related: [decisions/scheduler-converts-at-decision, concepts/load-only-red-is-a-product-defect, concepts/prices-current-side-effect]
---

# Problem: the UTC calendar day is not the user's calendar day

## How it was found

A full run finished after midnight and `tx-clone.spec.ts` went red. For 22 hours
a day the UTC date and the Europe/Rome date agree; the suite almost always runs
inside those 22 hours.

> The run that found it is the run nobody schedules.

## Root cause

`new Date().toISOString().slice(0, 10)` returns the **UTC** calendar day. East of
Greenwich, between local midnight and UTC midnight, that is *yesterday*.

An audit found the pattern in **18 places**.

## The classification, which is the useful part

| verdict | count | examples |
|---|---|---|
| **product defect** | 3 | `dateRangeStore.defaultRange()`, `resolveDateSentinel('max')`, `DataEditor.handleAddRow()` |
| **test defect** | 1 | `tx-clone.spec.ts` |
| **correct as written** | 14 | internal UTC arithmetic; dates that arrive from the backend already in UTC |

The three product defects are all *"what does today mean to the person looking at
the screen"*:

- `defaultRange()` — the dashboard opens on a range that **ends yesterday**, so
  a transaction entered this evening is not in the default view.
- `resolveDateSentinel('max')` — a `max` sentinel resolves to yesterday, so a
  filter that should include today excludes it.
- `DataEditor.handleAddRow()` — a new row is pre-filled with **yesterday's**
  date, and the user has to notice and correct it.

The fourteen correct ones matter too. A blanket replacement would have broken
them: UTC arithmetic on values that are already UTC is right, and rewriting it to
local time introduces the mirror-image bug.

> The audit's product is not the fix list. It is the **classification** — three
> categories with a reason each. A patch applied to all 18 would have fixed 3 and
> broken 14.

## Fix

`frontend/e2e/fixtures/dates.ts` exposes `localIso`, `todayIso`, `daysAgoIso`,
used by the specs. It is a **fixture** file, not `$lib`, for a mechanical reason:
Playwright specs run outside the SvelteKit build and do not resolve the `$lib`
alias.

The product sites were corrected to the local calendar; the internal-arithmetic
sites were left alone with a note.

The guard test **freezes the clock** rather than asserting a computed date —
otherwise it would be green for 22 hours a day, which is the failure mode it
exists to prevent.

## Relationship to the scheduler decision

This is the same family as [[decisions/scheduler-converts-at-decision]]: the
question is always *at which point does an instant become a calendar day, and in
whose calendar*. The scheduler answered it for stored times; this answers it for
`now()`.

## 2026-10-16 — a comparison is one site, not two (Z-3)

Seven weeks later two more product defects of the family turned up, and the fix
above had created one of their two faces.

Both asset pages decide whether to poll live prices with
`isHeadToday = dateEnd >= <today>`. The left side, `dateEnd`, comes from the
store: `defaultRange().end` or `resolveDateSentinel('max')`. The right side was
`new Date().toISOString().slice(0, 10)`. Until 2026-08-30 both sides were UTC, so
the comparison was consistent. The audit's commit (`2e104b919`) moved the store
to `todayIso()` — rightly — and left the two `isHeadToday` lines as they were,
though they carried the same idiom when the sites were counted. From then on the
comparison read two calendars.

Because the operator is `>=`, the two calendars disagree in two different ways:

| where, when | the UTC date is | what the page did |
|---|---|---|
| west of Greenwich, in the evening (New York: from 20:00 in summer time) | already tomorrow | a range ending **today** — the default view — read as past: no live price, the summary on the chart's last close. Every evening, since 2026-08-30 |
| east of Greenwich, just after midnight (Rome: until 02:00 in summer time) | still yesterday | a range that ended **yesterday** read as live and polled, and every poll is a write ([[concepts/prices-current-side-effect]]). Older than the audit |

**Fix** (`a43502298`, workstream Z, lot A): both sites compare with `todayIso()`
from `frontend/src/lib/utils/dateOnly.ts`, the function the store resolves
`dateEnd` with. Both sides of the comparison now come from one function.

**The rule it adds.** The audit classified lines, one at a time, and each
`isHeadToday` line was consistent *with its operand at that moment*. A date
comparison is one site, not two: when one side moves to the user's calendar,
every comparison that reads it moves with it. Before fixing a producer of
"today" (`defaultRange`, `resolveDateSentinel`, `getEnd`), grep its readers for
a comparison with a UTC "now".

**Classified in the same pass, left UTC on purpose**: the date of the FX
conversion of a live price (`#applyLiveSummary` in `assetDetailLive.svelte.ts`).
The conversion is a backward-filled lookup — the latest stored rate on or before
that date — so either calendar gives the same rate. It is not "what today means
to the person looking at the screen", and a comment there says so.

**Guard.** Cases (i)–(l) of `asset-live-pause.spec.ts` freeze the time zone as
well as the clock (`timezoneId`, then `page.clock.install({time})` at New York
21:00 and Rome 00:30): one case per face and per page. Each first reads the
page's own calendar — time zone, local date, UTC date — and fails as a premise
where the two dates agree, instead of passing. Four red before the fix, all
green after. For a comparison of two calendars, freezing the clock is not
enough: the zone decides which face a run sees.

Not re-audited: at `ac9671fd3` the idiom is still in six product lines of
`frontend/src` (`backupDownload.ts`, `AssetCurrencyChangeModal.svelte`,
`AssetModal.svelte` twice, the conversion above, `TransactionBulkModal.svelte`).
Only the conversion was classified here.

## Source files

| Role | Path |
|------|------|
| Spec date helpers | `frontend/e2e/fixtures/dates.ts` — `localIso` (L20), `todayIso` (L25), `daysAgoIso` (L30) |
| Dashboard default range | `frontend/src/lib/stores/dateRangeStore.svelte.ts` — `defaultRange()` (L20) |
| Sentinel resolution | `frontend/src/lib/stores/dateRangeStore.svelte.ts` — `resolveDateSentinel()` (L144) |
| New-row prefill | `frontend/src/lib/components/ui/data-editor/DataEditor.svelte` — `handleAddRow()` (L456) |
| Spec that first went red | `frontend/e2e/transactions/tx-clone.spec.ts` |
| Asset list live gate (2026-10-16) | `frontend/src/routes/(app)/assets/+page.svelte` — `isHeadToday` (L217) |
| Asset detail live gate (2026-10-16) | `frontend/src/routes/(app)/assets/[id]/+page.svelte` — `isHeadToday` (L324) |
| Product calendar helpers | `frontend/src/lib/utils/dateOnly.ts` — `localIso` (L76), `todayIso` (L81) |
| Conversion date, UTC on purpose | `frontend/src/lib/components/assets/detail/assetDetailLive.svelte.ts` — `#applyLiveSummary` (L146) |
| Two-face guard | `frontend/e2e/assets/asset-live-pause.spec.ts` — Z-3 cases (i)–(l) (L657, L688) |

> **Path note (2026-09-01)**: the substance of this page held up; the addresses did
> not. Three rows were wrong: the store had moved to `.svelte.ts`, `DataEditor.svelte`
> had moved to `ui/data-editor/`, and `resolveDateSentinel` was attributed to a
> `dateSentinels.ts` that does not exist — the function lives in
> `dateRangeStore.svelte.ts` next to `defaultRange()`, which is itself the point:
> **two of the three product defects are twelve lines apart in the same file.**
> All five rows re-verified against the tree, symbol by symbol.
