---
title: "The gallery's price guard expected `toFixed` text: once the asset cards wrote prices in the interface's locale (M-18), the release gate went red, and no test run could show it"
category: problem
status: resolved
date: 2026-10-12
tags: [e2e, gallery, playwright, i18n, locale, numbers, intl, test-design, workstream-m, workstream-t, release-1.2]
related:
  - decisions/figures-in-the-interface-language
  - decisions/gallery-is-a-release-gate-with-real-data
  - problems/playwright-probes-ignore-timeout
  - features/F-074
  - sources/phase00-translation-round12-2026-10
---

# Problem: a guard that wrote figures the way the cards no longer did

> Filed at the train-70 ingest (M's batch 28, journal of round 12 §17.2), checked against the code at `afd7d4821`.

## Symptom

In the three «Asset list» scenarios of the gallery (the page, the table view, the filtered list),
`expectOfflinePricesDrawn` waits until every asset card shows the price that the offline fixture answered. After T's
CP1 of M-18 (`5b2aad5c4`, train 68), `dev.py mkdocs gallery -f "Asset list"` went red: 6 failed (3 tests, desktop and
mobile), all on `Gold Spot Price`, expected `4116.60`, drawn `4,116.60`.

## Root Cause

- The guard wrote the expected figure as `Number(price.value).toFixed(2)`. Since CP1 the card writes it with
  `formatFixed(value, 2)` (`AssetCard.svelte`): `toFixed`'s digits, written by Intl in `uiLocale()` —
  [[decisions/figures-in-the-interface-language]].
- **Red in English already.** English groups thousands too, and two fixture prices are over 1,000 (`4116.60` and
  `10956.03`), so the Italian, French and Spanish rounds, red on every price, were never reached.
- **Why no test run saw it.** `gallery.spec.ts` is a docs tool, not a test: the runner excludes it (`EXCLUDED_SPECS` in
  `scripts/test_runner/_inventory.py`, `frontend_excluded` in `scripts/test_runner/_cli.py`), so the guard runs only in
  `dev.py mkdocs gallery`. The other E2E that pin figures use values under 1,000 with the English interface and an
  en-US browser, where `toFixed` and a localized figure agree (T's survey of the specs).

**How it was found.** T, finishing CP1, checked the E2E that pin figures and found this guard; the file was not T's.
T proposed two one-line cures: compare the digits only (`replace(/\D/g, '')`, as `tx-import-degiro.spec.ts` does), or
write the expected price in the shot's locale. The coordinator chose the second, and M delivered it in batch 28,
through test-author.

## Solution

`e8d5a5668` («test(gallery): expect prices in the UI locale», train 70):

- the guard takes the shot's language from its three callers in `gallery.spec.ts`;
- in the page, it writes the expected figure with the browser's own `Intl.NumberFormat` in `GALLERY_LOCALES[lang]`
  (two decimals, French grouping included), after rounding with `toFixed(2)` as `formatFixed` does: Intl alone would
  round a half-way value its own way. The precedent is `frenchQuota` in `brokers-detail.spec.ts`;
- **a control before the assertion**: the expected text must end with the language's decimal mark and two digits
  (`.dd` in English, `,dd` in Italian, French and Spanish), so a browser without that locale's ICU data fails on the
  control, not as a wrong price.

The same command, red before the change, gave 6 passed after it: 48 of 48 shots, the guard green in the four
languages, desktop and mobile.

## Prevention

- **A change to how the interface writes figures must be searched in the guards that never run with the tests**:
  `gallery.spec.ts` and its fixtures run only in `dev.py mkdocs gallery`. T's survey caught this one before a release
  run did.
- **An English figure under 1,000 cannot tell `toFixed` from a localized figure**: a figure pinned that way proves
  nothing about the locale.
- **A control must be able to fail.** The first control, `toContain(',')` as in `frenchQuota`, also held for an
  `en-US` fallback on prices over 1,000, whose thousands separator is a comma; test-author found it, and the control
  was tightened to the decimal mark at the end. A control borrowed from a sibling spec has to be re-checked against
  its new range of values: `frenchQuota` checks a percentage, which never groups thousands.
- **A red after the change was not the guard's.** With the tightened control, the first run had 3 timeouts outside
  the guard (two waits for `data-busy="false"` over 20 s, one screenshot waiting for fonts), at a load of about 90 on
  10 cores from another lane's coverage suite. Run once alone, as the coordinator asked, it was green: the verdict was
  environment.

## Still open

- With CP2 (amounts, dates, chart axes), the header of `galleryLocale.ts` («the app formats with it wherever it passes
  no locale») goes out of date; T's note leaves it to M. *Done (train 74)*: M rewrote it in batch 31 (`172211a89`) —
  the app writes every figure in `uiLocale()`, and the browser locale still decides the English shots.

## Source files

| Role | Path |
|------|------|
| The guard (`expectOfflinePricesDrawn`) | `frontend/e2e/fixtures/galleryReportSets.ts` |
| Its three callers (the «Asset list» scenarios) | `frontend/e2e/gallery.spec.ts` |
| The shots' locales (`GALLERY_LOCALES`) | `frontend/e2e/fixtures/galleryLocale.ts` |
| The fixture prices | `frontend/e2e/fixtures/galleryOfflineData.ts` |
| The card that writes the price | `frontend/src/lib/components/assets/AssetCard.svelte` |
| The localized `toFixed` (`formatFixed`) | `frontend/src/lib/utils/core/formatFixed.ts` |
| The precedent (`frenchQuota`) | `frontend/e2e/brokers/brokers-detail.spec.ts` |
| The digits-only alternative | `frontend/e2e/transactions/tx-import-degiro.spec.ts` |
| The runner's exclusion of the gallery | `scripts/test_runner/_inventory.py` |
| Journal of M (§17.2) | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` |
| Journal of T (the finding, before the STOP) | `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` |
