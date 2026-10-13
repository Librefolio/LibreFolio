---
title: "Test hooks that read the text shown to the user broke when the text followed the interface language: `data-dist-pct` and the probe's date range — a machine attribute for tests, localized text for people"
category: problem
status: resolved
date: 2026-10-13
tags: [frontend, testing, i18n, locale, test-hooks, data-attributes, gallery, vitest, workstream-t, release-1.2]
related:
  - decisions/figures-in-the-interface-language
  - problems/gallery-price-guard-expected-tofixed-text
  - sources/phase00-financial-math-home-2026-10
---

# Problem: the hook spoke the user's language

## Symptom

Twice on 2026-10-13, after figures and dates started following the interface language
([[decisions/figures-in-the-interface-language]]), tests that had not changed went red:

- **The gallery, two reds** (M's full run, group B): the provider comparison expected `data-dist-pct="100.00%"` and
  read `"100,00%"` in Italian, on desktop and mobile. T's plan records it as high priority: it blocked the tag.
- **Eight unit reds** in `AssetModal.providerLifecycle.test.ts`, after T-ISO formatted the provider probe's dates:
  the test found the history row by the raw `date_range` in its text, and the text now carried a formatted date.

## Root Cause

Both hooks were the text shown to the user. `data-dist-pct` had held the displayed, localized string since
`5b2aad5c4` (M-18's first checkpoint), and the probe rows had no identity other than their wording. A text that
follows the language is a moving target for a test, by design.

## Solution

One split, applied to each case:

- `dfc4f9ccc` (T-CL): `formatDistribution` in `ProviderComparisonModal.svelte` returns the localized `pct` for the
  screen and a `hook`, the value times 100 with two decimals and a dot, which the attribute publishes — `60.00%` in
  every language. Neither
  the gallery nor the tests changed.
- `8684d29fe` (the T-ISO probe repair, train 90): each `provider-test-result` row publishes `data-operation` — the
  backend's own operation names, `current_price` and `history`, or `probe` when the call itself failed — and
  `data-status`; the test matches the rows by operation. T's plan: «La cura: ogni riga pubblica `data-operation`, e il
  testo resta nella lingua della UI.»

T-ISO's gate had missed the eight reds because it ran only the lot's files and the chart and risk neighbours, not the
whole `component-unit` selector.

## Prevention

- A value a test reads goes in a **machine attribute** with a fixed form; the localized text is for people. The rule
  that selectors are `data-testid`, never text, extends to the values tests compare.
- A change that formats text for the user runs the whole unit selector of every component that shows it, not only
  the lot's own files.
- The same family, earlier: [[problems/gallery-price-guard-expected-tofixed-text]] (train 70).

## Source files

| Role | Path |
|------|------|
| `data-dist-pct` and its hook | `frontend/src/lib/components/assets/ProviderComparisonModal.svelte` |
| The gallery's check | `frontend/e2e/fixtures/galleryProviderCompare.ts` |
| `data-operation` | `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte` |
| The repaired test | `frontend/src/lib/components/assets/AssetModal.providerLifecycle.test.ts` |
| T's lots (T-CL, T-ISO, the repair) | `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` |
