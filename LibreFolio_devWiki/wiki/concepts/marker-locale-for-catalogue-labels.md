---
title: "Testing that a label comes from the catalogue: mount in a marker locale where every key shows as ⟦key⟧"
category: concept
tags: [testing, i18n, frontend, vitest, labels, catalogue]
related:
  - concepts/assert-on-identity-not-prose
  - concepts/brim-texts-translated-by-code
  - sources/phase00-promote-pair-checks-2026-10
---

# Concept: the marker locale

## Definition

A test that must prove a label is **not** hardcoded mounts the component in a fake locale, `qaa`, whose catalogue
renders every key as a marker: `⟦common.status⟧`, or `⟦datePicker.presets.weeks n=3⟧` for a message with arguments. A
label taken from the catalogue shows its marker; a literal written in the code shows itself. The assertion compares
markers, so it never depends on translated text, and a second test checks that the keys exist in the four catalogues.

## Where It Applies

Workstream P's test author introduced it on 2026-10-11 (plan 42, §8, item 8) for three components that still wrote
English labels in the code:

- `DataEditor` — the status column's header and its badges (`common.status`, `dataEditor.status.*`);
- `ChartAestheticsSection` — «Auto», «Min», «Max» (`chartSettings.yAxisAuto`, `common.min`, `common.max`);
- `DateRangePicker` — the presets (`datePicker.presets.{weeks,months,years}` with `{n}`), and then the rolling-return
  window of the asset page (`calendarReturnWindow.ts`, `CALENDAR_RETURN_UNIT_LABEL_KEYS`).

Labels already taken from the catalogue act as controls. The fixes landed with `0de730f3b` (train 38).

## Why

[[concepts/assert-on-identity-not-prose]] forbids asserting translated prose, and a hardcoded English label is
invisible in an English test run. The marker locale asserts identity — which key, with which arguments — and makes a
literal fail in any language.

## Source files

| Role | Path |
|------|------|
| `MARKER_LOCALE = 'qaa'` and the `marked()` helper | `frontend/src/lib/components/ui/data-editor/DataEditor.test.ts` |
| The presets, tested the same way | `frontend/src/lib/components/ui/date/DateRangePicker.test.ts` |
| «Auto», «Min», «Max» | `frontend/src/lib/components/charts/ChartSignalsSection.test.ts` |
| The rolling-return window's keys | `frontend/src/lib/components/charts/calendarReturnWindow.ts` |
