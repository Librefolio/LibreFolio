---
title: "No range of a single day, in every date-range picker"
category: decision
status: resolved
date: 2026-10-19
tags: [frontend, date-picker, charts, measure, ux]
related: [features/F-045, problems/zrender-resets-cursor-on-every-move, problems/dispatched-click-reaches-disabled-button-in-jsdom]
---

# Decision: No range of a single day, in every date-range picker

## Context
Defect N65, reported by the developer on 19/10 while reviewing night decision N65 on the measures (whose Δ% half
is in [[features/F-045]]): on the asset and FX charts, the measuring ruler's card has its own range picker.
Choosing the same day for «From» and «To» left the picker showing that day twice, while the measure kept its old
dates: «il componente mostra il dato corretto, ma il resto rimane calcolato sul vecchio valore».

The cause: `DateRangePicker`'s `start` and `end` are `$bindable`, so the picker writes them before calling
`onchange`. `MeasurePanel.updateMeasureDates` then refused a same-day range in silence, and nothing reset the
picker.

A one-day range could come from five places:
1. a double click in the calendar;
2. a typed date equal to the other end;
3. a typed date with the other end empty or on a `min`/`max` sentinel (the date was copied onto that end);
4. the arrow keys;
5. a chart click (`MeasurePanel.addPoint`).

## Options Considered
1. **The ruler accepts a measure of zero length.** The smallest change, but a measure of one day says nothing,
   and the other pickers would still allow the same range.
2. **An option of `DateRangePicker`, turned on by the ruler only.** Keeps a single date possible elsewhere, at
   the cost of two behaviours for one component.
3. **No range of a single day in any range picker.** The developer's choice: «in tutti i selettori di intervallo
   dell'app», knowing that a table's date filter can no longer hold a single day.

## Decision
Option 3, decided by the developer on 19/10, with every recommendation of the analysis (N65-2 to N65-7)
accepted:
- **Calendar.** The pending day is disabled, with the not-allowed cursor of the future days. A second click on it
  is ignored, and hovering it previews nothing.
- **Typed dates.** A date equal to the other end is refused like a typed future date: it stays red until the
  other end moves, then both apply as a pair.
- **Arrow keys.** They skip the equal day, and do nothing when that skip would land on a refused future day.
- **Open ends.** A typed date no longer fills an empty or sentinel end, so an open range stays open.
- **The ruler.** It ignores a second click on its start point. `updatePendingEnd` answers `true` there, and the
  chart shows the not-allowed cursor (N65-7, which also made the measure-mode crosshair visible for the first
  time).
- **Saved one-day ranges** (session storage, URL, filters, scheduled-investment periods) are left as they are:
  rewriting them would change a user's bookmark.

## Consequences
- **Visible change in table filters.** A single date in «From» now means «from that day on», not «only that day».
- **No backend change.** The backend still accepts one-day ranges everywhere; the rule is UI-only.
- **Defence in depth.** `CalendarMonth` refuses the click in its handler as well as through `disabled` (see
  [[problems/dispatched-click-reaches-disabled-button-in-jsdom]]).
- **`MeasurePanel.updateMeasureDates` no longer refuses `s === e`.** The picker cannot produce such a range any
  more, and a measure of one day would compute correctly anyway.

## Source files
| Role | Path |
|------|------|
| Range picker | `frontend/src/lib/components/ui/date/DateRangePicker.svelte` |
| Day grid | `frontend/src/lib/components/ui/date/CalendarMonth.svelte` |
| Measuring ruler | `frontend/src/lib/components/charts/MeasurePanel.svelte` |
| Chart cursor (line view) | `frontend/src/lib/components/charts/PriceChartFull.svelte` |
| Chart cursor (candles) | `frontend/src/lib/components/charts/CandlestickChart.svelte` |
| Tests | `frontend/src/lib/components/ui/date/DateRangePicker.test.ts`, `frontend/src/lib/components/ui/date/CalendarMonth.test.ts`, `frontend/src/lib/components/charts/MeasurePanel.test.ts`, `frontend/src/lib/components/charts/PriceChartFull.test.ts` |

## Links
- [[features/F-045]]
- [[problems/zrender-resets-cursor-on-every-move]]
- Source: `LibreFolio_developer_journal/Release_2/Phase_1/09_dashboardCharts/plan-phase01DashboardCharts.prompt.md`,
  sections «19/10 · Y-N65» and «Il lotto Y-N65».
