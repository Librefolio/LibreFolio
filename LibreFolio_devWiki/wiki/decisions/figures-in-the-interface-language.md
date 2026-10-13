---
title: "Every figure is written in the interface language: one source, uiLocale(), with the browser's region only when it speaks that language and en-GB for English"
category: decision
status: accepted
date: 2026-10-12
tags: [frontend, i18n, locale, numbers, dates, percentages, intl, reactivity, release-1.2, workstream-t]
related:
  - features/F-008
  - problems/playwright-probes-ignore-timeout
  - problems/line-chart-axes-lost-the-day
  - problems/gallery-price-guard-expected-tofixed-text
---

# Decision: numbers and dates follow the interface language

> **Delivered** (trains 68, 75 and 76; M-18 closed). CP1 `5b2aad5c4`, CP2 `ff7c96fd0`, CP3a `c17d39d5a`, CP3b
> `33cc145b5`, all of 2026-10-12. The 1.2 CHANGELOG announced the whole rule in train 74 (`e7bfa342f`, ported to
> it/fr/es in `96d937915`): with CP2 and CP3 in, it now describes the code. *Until train 75 this page said «partly
> delivered».*

## Context

Shooting the gallery in each language (M-14) showed figures written two ways side by side: «+4788,01 €» next to
«14.07%» in Italian. Percentages, file sizes, durations and other decimals were written with `toFixed`, which goes
through no locale (M-18). Workstream T analysed a narrow fix first; the developer chose the whole rule.

## Decision

The developer (2026-10-12), verbatim: «Lingua della UI per tutto, importi e date compresi: lavoro più grande, con più
rischio sulla 1.2».

- **One source**, `uiLocale()` (`stores/app/uiLocale.ts`): the interface language, with the browser's region only when
  the browser's primary tag (`navigator.language`) is in that language (`en-GB`, `it-CH`, `es-MX`); otherwise the
  language's default — **`en-GB` for English**, the bare language for Italian, French and Spanish. Only the primary
  tag is read: browsers list `en-US` among most users' secondary languages.
- **Reactive**: runes code reads it through the formatters' defaults, so a language switch re-renders a figure in
  place; legacy components read `$uiLocaleStore` in the template.
- **CP1** (`5b2aad5c4`, journal `d00c06685`): `formatPercent` defaults to it, and `formatFixed` is the localized
  `toFixed`, rounding included; the hand-written `toFixed` sites for percentages, decimals, bytes and durations moved
  to it.
- **CP2** (`ff7c96fd0`): amounts (`currencyFormat`, default `uiLocale()`), dates (`formatDateTime`), chart axes,
  tooltips and the charts' percentages; every effect that calls `setOption` reads `uiLocale()`. Text that follows
  the language, not the locale, stays so: country names, scenario texts, sorting by name, list formats. M-17 went
  with it: the date range picker and the «Updated» time of the global settings now use the same source.
- **CP3a** (`c17d39d5a`): `formatExactDecimal()` writes an exact quantity or rate in the interface locale by handing
  Intl the digits as a string, never through a float, so a long decimal comes out whole; twelve read-only sites use
  it, while inputs stay on `formatDecimalForDisplay`.
- **CP3b** (`33cc145b5`): the provider check in the asset's provider section writes its figures the same way.
- **en-GB for English**: `resolveUiLocale()` keeps the browser's tag only when it carries the interface language and
  a region (`es-419` stays), so a bare `en` becomes `en-GB` (`uiLocale.test.ts`, 31 cases).

## Consequences

- An English interface now writes British dates and times (`12/10/2026`, `12 Oct 2026`, `14:05`) unless the browser
  is `en-US`; regions also change numbers (`it-CH` keeps the decimal point).
- Chart formatters run outside Svelte's tracking: the effect that builds the options must read the locale itself —
  done in CP2 (with the axes of [[problems/line-chart-axes-lost-the-day]]).
- Known limit, backlog T-DI: native `<input type="date">` stays in the browser's language.
- T-EN1 and T-EN2, closed in 1.2 (`f31bd6cfd`, train 79): the what-if signals' labels and units, the price chart's
  tooltip for a converted event and the provider check's count of points now follow the language; `ChartSignal` reads
  the catalogue through a formatter tracked like `uiLocale()`. The CHANGELOG lists them as a fix (`4e11c2f83`): the
  English texts were already in 1.1.
- Left for after 1.2 (backlog): T-ST, T-ICU, T-COL, T-DEAD — plurals of stale days, ICU figures of a language without
  region, collation, dead code. Two more found with T-EN were first left for after 1.2, then pulled in by the
  coordinator because the 🔄 line promises «chart axes and tooltips»: **T-ISO** (`2a17ae3af`, train 88) — the price,
  candlestick and line charts' tooltip dates and the provider probe's dates through a new `formatDay`
  (`formatAxisDate.ts`) — and **T-FB** (`03dba53f8`, train 88) — the comparison signals' fallbacks («Asset #N»,
  «FX Pair») and the asset page's errors from the catalogue. The date fields of the date-range picker stay ISO, by
  choice.
- The developer guide explains the rule: `developer/frontend/i18n.md`, «Numbers, amounts and dates» (`133259913`).
- A test hook that read the displayed figure follows the language too: `data-dist-pct` in
  `ProviderComparisonModal.svelte` — found by M's full gallery run (2026-10-13), cured by T in `dfc4f9ccc` (train 85)
  with a machine form for the attribute; the probe rows' `data-operation` (`8684d29fe`, train 90) followed the same
  rule — [[problems/test-hooks-read-the-localized-text]].
- A test that pins a figure as `toFixed` writes it breaks under the rule: the gallery's price guard went red in English
  on prices over 1,000, and since M's batch 28 (`e8d5a5668`, train 70) it expects the figure as the shot's locale
  writes it — [[problems/gallery-price-guard-expected-tofixed-text]].

## Source files

| Role | Path |
|------|------|
| The single source | `frontend/src/lib/stores/app/uiLocale.ts` |
| The localized `toFixed` (`formatFixed`) and `formatExactDecimal` | `frontend/src/lib/utils/core/formatFixed.ts` |
| Amounts | `frontend/src/lib/utils/currency/currencyFormat.ts` |
| Dates | `frontend/src/lib/utils/core/formatDateTime.ts` |
| The en-GB rule, tested | `frontend/src/lib/stores/app/uiLocale.test.ts` |
| The what-if signals' tracked catalogue (T-EN2) | `frontend/src/lib/charts/signals/ChartSignal.ts` |
| Developer guide | `mkdocs_src/docs/developer/frontend/i18n.md` |
| Journal (M-18) | `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` |
