---
title: "The money-render gate stayed green while the Growth chart's axis showed amounts in privacy mode: it could not see a formatter's consumers"
category: problem
status: resolved
date: 2026-09-24
tags: [frontend, privacy, masking, charts, gate, testing, static-analysis]
related:
  - features/F-101
  - features/F-055
  - sources/phase00-feedback-jobs-2026-09
  - sources/phase00-privacy-global-2026-09
---

# Problem: a gate that only saw money written in one place

## Symptom

With privacy mode on, the Growth chart's Y axis and labels still showed amounts, while the money-render gate
(`moneyRenderSites.test.ts`) stayed green. Item P4-11 of the structural backlog and §2.2 of the static analysis of
2026-09-22 (folder 09).

## Root Cause

The scanner recognised a money render only when a currency and a number met in the same template literal. Most
consumers of a formatter such as `fmtCurrency` never do, so they were invisible to it; the one consumer it did catch
matched only because of nearby variable names — a rename would have turned the gate red for the wrong reason.

## Solution

`804bc9903` («fix(privacy): mask growth and performance amounts»): mask at the formatter's definition with
`maskFormattedNumber` — in the Growth chart, and `shortMoney` in the Performance chart — so every consumer inherits it;
the gate now guards that boundary, and its list of residual sites is empty.

## Prevention

Mask where the value is formatted, not where it is shown, and make the gate check that boundary: a scanner that reads
call sites misses the ones that do not look like money.

## Source files

| Role | Path |
|------|------|
| Masked formatters | `frontend/src/lib/features/dashboard/GrowthChart.svelte` |
| The gate | `frontend/src/lib/utils/privacy/moneyRenderSites.test.ts` |
| Journal (P4-11) | `LibreFolio_developer_journal/Release_2/Phase_0/09_feedbackJobs/00_backlog_strutturale_P4.md` |
