---
title: "Global privacy: mask at the formatter, per device, money only, the sign and the currency stay"
category: decision
status: resolved
date: 2026-09-22
tags: [frontend, privacy, formatters, currency, ux, security-boundary, gates]
related: [features/F-101, concepts/premise-gate-keyed-by-content, decisions/asset-global-page-shows-no-money, concepts/echarts-chart-gotchas, decisions/ai-export-contextual-ui-memory, sources/phase00-privacy-global-2026-09]
---

# Decision: how "hide values" works

## Context

Release 2 (U2, SP15) asked for a global "hide values" switch: open LibreFolio in an office, a café or on a
projector without showing what you own. Money is rendered in hundreds of places — tables, KPIs, tooltips, chart
axes, `title` attributes — so the question was where to cut, and what counts as "what you own".

## Decisions (analysis §0, rounds 1 and 2)

| ID | Decision | Why / rejected |
|---|---|---|
| **Where** | Mask **at the formatter**, before the string exists: the currency formatters ask `maskable()` / `maskCurrencyParts()`, so a masked amount is safe in a cell, an ECharts tooltip or an attribute alike | a `SensitiveValue` component was designed and **suspended**: per-component masking misses every string built elsewhere |
| D1 | The setting belongs to the **device**, not the account; it survives closing the browser | the use is about place, not person |
| D2 | Plain storage key `librefolio-privacy` | a per-user key `lf_{userId}_privacy` was rejected |
| D3 | Off by default; the app starts from the saved value | — |
| D4 | No protection is promised against DevTools, the API, logs or raw exports | the declared limit: this is a screen feature, not access control |
| D5 → **D5′** (2026-09-23) | Money is hidden; **quantities are hidden only next to a price** (positions, lots) and stay visible in transactions; a market price is not wealth, so unit prices are public again | D5 classified by formatter and hid too much (review of 2026-09-22) |
| D6 | All percentages stay visible, percentage P&L included | — |
| D7 | Input fields holding amounts are out of scope | — |
| **D8** | The **sign stays**: `+•••` / `-•••` | masking the sign was built first and rejected by the product owner for readability; the cost is written in the code: the sign has three values, and a masked column still shows which periods had activity |
| Round 2 | **"Privacy hides the number, not the currency"**: the currency symbol always stays (`maskCurrencyParts`) | round 1 hid it too |

**Default to hiding.** An amount the caller did not classify is `personal`, hence masked (`AmountSensitivity`,
`'personal' | 'public'`): a public value hidden by mistake gets reported by users; a personal value shown by mistake
goes unnoticed. `public` skips the store read, so it causes no re-render.

## Consequences

- One switch in the header (`PrivacyToggle.svelte`), one rune (`privacyStore`), and the masking decided where a
  number becomes a string.
- ECharts formatters are not reactive: charts must put the privacy state in their rebuild key, and on a masked
  money axis even 0 is masked ([[concepts/echarts-chart-gotchas]]).
- A gate keeps the premise true — the set of places that render money is known — keyed by content, not line
  ([[concepts/premise-gate-keyed-by-content]]). It cannot see ECharts axis formatters (backlog **I-05**: the
  PerformanceChart `shortMoney` branches and `axisTickAmount`).
- Under privacy the risk formatter masks the whole string, which blinded a test net elsewhere:
  [[decisions/asset-global-page-shows-no-money]].

## Links

- [[features/F-101]] · Source: [[sources/phase00-privacy-global-2026-09]].

## Source files

| Role | Path |
|------|------|
| Masking primitives (`maskable`, `maskCurrencyParts`, `maskableQuantity`, D8 note) | `frontend/src/lib/utils/privacy/maskable.ts` |
| Device-scoped flag | `frontend/src/lib/stores/app/privacyStore.svelte.ts` |
| Header switch | `frontend/src/lib/components/ui/PrivacyToggle.svelte` |
| Currency formatter that asks the mask | `frontend/src/lib/utils/currency/currencyFormat.ts` |
| Money-site gate | `frontend/src/lib/utils/privacy/moneyRenderSites.test.ts` |
| E2E (desktop and mobile) | `frontend/e2e/portfolio/privacy-masking.spec.ts` |
| Developer doc ("Privacy masking") | `mkdocs_src/docs/developer/frontend/state/app-state.md` |
| User doc ("Privacy mode") | `mkdocs_src/docs/user/settings/preferences.en.md` |
| Analysis (§0 decisions) | `LibreFolio_developer_journal/Release_2/phases/24_privacyGlobal/analysis-phase00PrivacyGlobal.md` |
