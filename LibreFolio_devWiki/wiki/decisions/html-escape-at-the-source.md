---
title: "HTML sinks: escape at the source, sanitise only mixed markup — and two gates that keep it so"
category: decision
status: resolved
date: 2026-09-30
tags: [frontend, security, xss, html, svelte, echarts, i18n, gates, testing]
related: [concepts/premise-gate-keyed-by-content, concepts/echarts-chart-gotchas, decisions/datatable-tooltip-custom-cell, features/F-047, features/F-032, sources/phase00-taxonomy-select-2026-10]
---

# Decision: how user text reaches hand-built HTML

> Backlog **K-25** asked for this page (workstream K, step 13, item 0, 2026-09-30 – 10-01).

## Context — a stored XSS shipped in v1.1.0

The Name column of `AssetTable` returned an `html` cell whose template interpolated the asset's display name — and
its `icon_url` — raw, and `DataTable` renders `html` cells with `{@html}`. The backend stores any string as an asset
name, and assets are global: a name written by one user ran as script in the browser of every user who opened the
asset list, the administrator included. `e2e/assets/asset-name-xss.spec.ts` was red 6/6 in table view.

The audit then covered every place where data meets markup: asset, broker and transaction names, icon URLs, event
notes, original file names, the parameters of validation messages, ECharts tooltip names. Later passes found more:
`signalLabelToHtml` escaped its icons but not its text, `ExposureTreemap` passed broker names raw, and two sites the
first gate could not see yet — the P&L line tooltip of `GrowthChart` (fixed by workstream I, which owned that code)
and four `html` cells of `DataEditor` rendering `r.values[col.key]` raw (asset event notes), which gave the gate its
computed-key rule.

## Decision — the rules

1. **Escape at the source**, with the one helper `escapeHtml` (`$lib/utils/core/escapeHtml.ts`): `& < > " '`. The
   apostrophe is escaped on purpose — it makes the result safe inside a single-quoted attribute too, and the parser
   decodes it back, so the text is unchanged. It replaced copies that had been pasted into thirteen places in two
   variants; the local `esc`/`escHtml` escapers were removed (they left `"` — some even `>` — unescaped, so a value
   could close the attribute it sat in).
2. **Sanitise only mixed markup.** Sinks fed with markup of mixed origin — toasts (`ToastContainer`), `Tooltip`,
   validation and result messages in the transaction form, bulk, import-wizard and parse-detail modals,
   `TransactionResultBanner` (later also the PAC planner's `CurrencyCode`) — render `sanitizeHtml(…)` (new,
   `$lib/utils/core/sanitizeHtml.ts`, DOMPurify; browser only, the app runs with `ssr = false`).
3. **Name what you hold**: variables that carry HTML end in `Html`/`Badge`; variables that carry URLs end in `Url`/
   `Src`.
4. **Truncate first, escape after** — cutting an escaped string can split an entity.

## The two gates

| Gate | Guards | Does not see (stated in its header, "Completeness, stated honestly") |
|---|---|---|
| `src/htmlInterpolation.gate.test.ts` — the **sources** | every non-test `.ts`/`.svelte` file, parsed (TypeScript, Svelte's own parser — never line matching). In a template literal that is HTML (it contains a tag, or interpolates a fragment named `…Html`/`…Icon`/`…Badge`), a user/provider text field (names ending in `name`, `notes`, `url`, `src`, `currency`, …) must pass through `escapeHtml(…)`; `esc`/`escHtml` are violations; a value read through a computed key is a violation unless it is a number format; helpers taking HTML in their first parameter (`buildTooltipRow`) are checked too. It also reads the **i18n catalogues**: a translation must render as itself (no `<`, no `&` starting a reference) unless reviewed | renamed fields, string concatenation, `{@html v}`/`innerHTML` with no template, fragments not named like fragments, parameters other than the first, ECharts formatters without static markup |
| `src/htmlSink.gate.test.ts` — the **sinks** | every `{@html X}` in a non-test `.svelte` file is either exactly `sanitizeHtml(…)` or an entry of `REVIEWED_SINKS` (file, expression, reason), **keyed by content, never by line**; a stale entry, or one whose reason is too short to check, fails the gate | `innerHTML`/`outerHTML`/`insertAdjacentHTML` in scripts, and HTML handed to a library that renders it (an ECharts formatter) |

Both run in `core-unit`. They are the same family as the privacy money-site gate: they test a premise, are keyed by
content and do not judge intent ([[concepts/premise-gate-keyed-by-content]]). The catalogue half of the first gate is
the one the tooltip-HTML fix of 2026-10-09 extended ([[concepts/echarts-chart-gotchas]]).

## Consequences and gotchas

- `escapeHtml` is defined **three** times at `083ed26dc`: the canonical helper; `$lib/utils/inlineMath.ts`, which
  deliberately does not escape the apostrophe (its output goes to KaTeX, where `f'(x)` is prime notation); and a
  local copy in `CorrelationHeatmap.svelte` (Risk, 2026-09-24) that escapes only `& < >`. The interpolation gate
  accepts any call **named** `escapeHtml`, so a weaker copy with that name passes it; the heatmap's uses are all text
  content, where `& < >` suffice, so it is safe today — but "one helper" is a convention the gate does not enforce.
- [[features/F-047]] listed "`escapeHtml()` × 4 copies cleanup (deferred)" — done by this work (corrected there).
- **Residual K-15** (low, defence in depth): ECharts tooltip *function* formatters return HTML that ECharts renders
  as such. The ones reviewed escape their text with `escapeHtml`, but none of the 21 files with a `formatter` under
  `components/charts`, `charts`, `dashboard`, `risk` and `brokers/lots` ends with `sanitizeHtml`, and neither gate
  sees them. Open in the backlog.

## Source files

| Role | Path |
|------|------|
| The escape helper | `frontend/src/lib/utils/core/escapeHtml.ts` |
| The sanitiser (DOMPurify) | `frontend/src/lib/utils/core/sanitizeHtml.ts` |
| Gate on sources and catalogues | `frontend/src/htmlInterpolation.gate.test.ts` |
| Gate on `{@html}` sinks | `frontend/src/htmlSink.gate.test.ts` |
| E2E — a hostile asset name stays text | `frontend/e2e/assets/asset-name-xss.spec.ts` |
| Helper tests | `frontend/src/lib/utils/core/__tests__/escapeHtml.test.ts` |
| Sanitiser tests | `frontend/src/lib/utils/core/sanitizeHtml.test.ts` |
| KaTeX variant (apostrophe kept) | `frontend/src/lib/utils/inlineMath.ts` |
| Local copy (text content only) | `frontend/src/lib/components/risk/CorrelationHeatmap.svelte` |
| Plan (step 13, item 0) | `LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep13DevNotesFixes.prompt.md` |
