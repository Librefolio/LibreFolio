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

> **Partly delivered.** CP1 is in `dev_release2` (train 68); CP2 — amounts, dates, chart axes and M-17 — is still to
> come. This page will be updated when it enters. *Train 74*: the 1.2 CHANGELOG already announces the whole rule
> (`e7bfa342f`, ported to it/fr/es in `96d937915`), ahead of CP2 and CP3.

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

## Consequences

- An English interface now writes British dates and times (`12/10/2026`, `12 Oct 2026`, `14:05`) unless the browser
  is `en-US`; regions also change numbers (`it-CH` keeps the decimal point).
- Chart formatters run outside Svelte's tracking: the effect that builds the options must read the locale itself
  (CP2, with the axes of [[problems/line-chart-axes-lost-the-day]]).
- Known limit, backlog T-DI: native `<input type="date">` stays in the browser's language.
- A test that pins a figure as `toFixed` writes it breaks under the rule: the gallery's price guard went red in English
  on prices over 1,000, and since M's batch 28 (`e8d5a5668`, train 70) it expects the figure as the shot's locale
  writes it — [[problems/gallery-price-guard-expected-tofixed-text]].

## Source files

| Role | Path |
|------|------|
| The single source | `frontend/src/lib/stores/app/uiLocale.ts` |
| The localized `toFixed` (`formatFixed`) | `frontend/src/lib/utils/core/formatFixed.ts` |
| Journal (M-18) | `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` |
