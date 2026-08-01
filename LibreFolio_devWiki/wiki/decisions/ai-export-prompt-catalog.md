---
title: "AI export: single kitchen-sink prompt replaced by a single-purpose prompt catalog"
category: decision
status: superseded
date: 2026-07-15
superseded_date: 2026-07-26
mkdocs: "developer/architecture/patterns/ai_export_snapshot.md"
tags: [frontend, ai-export, architecture, prompt-engineering, dashboard, asset-detail]
related: [problems/ai-export-name-not-ticker, features/F-054, decisions/ai-export-versioned-snapshot-boundary, decisions/ai-export-contextual-ui-memory, entities/ai-export-snapshot-service]
---

# Decision: AI export prompt catalog (replaces the single "Full/Data-only" prompt)

> **Historical status (2026-07-26):** this frontend-only architecture was superseded by
> [[decisions/ai-export-versioned-snapshot-boundary]]. Its single-purpose task rationale
> survives, but production data now comes from versioned backend snapshots and the current
> frontend catalog participates in a fail-closed backend contract.

## Phase 0 final UI closure

The final V2 interface retains the single-purpose-analysis principle but no longer exposes the historical prompt IDs or a separate Full/Data-only switch directly:

- one custom analysis select renders an icon, localized name, and localized description for both the selected item and each option;
- a synthetic **Data Snapshot** entry maps to the domain's factual snapshot task and `data_only`;
- every real analysis uses `full_prompt`;
- response language always follows the current UI locale;
- response-language, render-mode, web-research, and compatibility-status controls are hidden, while catalog compatibility remains fail-closed internally and web research is normalized off;
- draft task/detail/mode/notes persist per authenticated user and Portfolio/Broker/Asset/canonical-FX context under [[decisions/ai-export-contextual-ui-memory]];
- Snapshot hides notes but never exports them, even though the draft is retained for a later analysis;
- the options panel is body-portalized above chart controls and offers a domain-aware book link to the English domain manual or localized shared fallback.

The project owner approved this desktop/mobile UI on 27 July 2026.

## Context

The original AI Portfolio Export MVP (see `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/Ai_consultant_engine/report_ai_export_mvp.md`)
shipped exactly 2 clipboard actions: "Copy full AI prompt" (one big prompt mixing summary,
allocation evaluation, PAC scenario proposals, technical context, and data-quality notes into a
single 9-point "Requested Analysis" list) and "Copy portfolio data only".

After real usage, the user reported two problems:
1. The AI receiving the full prompt tended to just restate what's already visible on the
   dashboard (charts/animations) — low value.
2. Bundling every analysis into one prompt produced dispersive answers — too much requested at
   once, no single clear task per conversation.

A third, unrelated but tightly-coupled bug was found while implementing the fix: several places
used `ticker ?? name` (or the ticker alone) as the *primary* display label for an asset (e.g.
`technicalExportBuilder.ts`'s technical events, `by_asset` allocation, technical-summary labels),
contradicting the intent of exporting a human-readable `name` field. See
[[problems/ai-export-name-not-ticker]] for that half of the fix.

## Options Considered

1. **Keep one big prompt, just trim its "Requested Analysis" list.** Rejected — doesn't solve the
   "too many analyses at once" complaint, and doesn't give users a way to start a narrowly-scoped
   conversation (e.g. "just tell me what's driving recent price moves").
2. **In-app interview wizard**: build a LibreFolio UI that asks the user questions (PAC ideas, target
   allocation, etc.) and bakes the answers into the generated prompt. Rejected (for now) — much
   larger UI scope (new modal/wizard per activity, i18n for every question) for a frontend-only,
   experimental feature; the same effect is achieved by instructing the *receiving* AI to run the
   interview directly in its own chat.
3. **Prompt catalog**: one dropdown with several single-purpose prompts, each with its own
   role/task text and a subset of exported sections, sharing common data-building/rendering
   infrastructure. **Chosen.**

## Decision

Replaced the binary `mode: 'full' | 'data-only'` with a `PromptId` catalog
(`frontend/src/lib/features/ai-export/promptCatalog.ts`), in this fixed display order:

1. **`snapshot`** — pure data, no instructions (behavior identical to the old "Data only"); reframed
   as the most reusable option to start/continue an AI conversation across days — intentionally first.
2. **`pac_planning`** — the *external* AI interviews the user about new investment ideas/themes/
   budget, then (if it has web access) researches compatible instruments and proposes 2-3 PAC
   allocations. The interview happens entirely in the external AI's chat — LibreFolio only ships the
   instruction text asking it to do so.
3. **`rebalancing`** — external AI interviews the user on a target allocation, then proposes
   sell/reinvest vs. PAC-driven vs. hybrid rebalancing. Its `pac_context` section is intentionally
   **excluded** from the render (see `promptCatalog.ts`'s `sections.pac_context` flag) — that section's
   fixed `avoid_sale_suggestions: true` framing would directly contradict a prompt whose whole point is
   evaluating a sale.
4. **`market_trend`** — matches recent technical events/price moves with news the external AI finds
   online; gets the *full* per-day technical series+events (`technicalDetail: 'full'`), unlike the
   other instruction-bearing prompts which only get `technical_summary` (one compact line per asset) to
   keep the prompt focused.
5. **`income_review`** *(added during this session, not originally requested — proposed and accepted)*
   — surfaces `period_income`/`period_fees_taxes`, fields that were already exported but never used by
   any dedicated prompt.
6. **`describe_portfolio`** — the old "Full AI Prompt" content, trimmed (PAC-scenario generation
   removed — now owned by `pac_planning`) and deliberately placed **last** — the user explicitly
   wanted the generic "describe my portfolio" behavior deprioritized since it's the one most likely to
   just restate the dashboard.

Shared infrastructure (all instruction-bearing prompts get these in their header):
- `templates/responseStyleTemplate.ts` → `PROMPT_CONCISE_RESPONSE` (terse, no filler/preamble, lead
  with the conclusion — principle borrowed from the repo's own `caveman` skill, but written in plain
  professional English, not literal caveman-speak, since the text is read by an external AI *and* by
  the user) and `PROMPT_ASSET_NAMING` (never refer to assets by ticker/ISIN in prose).
- `yamlSerializer.ts` — the `toYaml`/`fmt` pair, previously duplicated verbatim in both renderer files.
- A generic `renderPrompt(data, promptId)` in `aiPromptRenderer.ts` replaced the old hardcoded
  `renderFullPrompt` — it composes header + catalog-selected sections + prompt-specific task text.

Same pattern extended to a **new single-asset export** (Asset Detail page): a "Brain" button was added
to the **Signals panel header** (always visible, left of/beside the collapse toggle, not nested inside
it — a `<button>` cannot contain another `<button>`), offering `asset_snapshot` (data only) and
`asset_classify` (asks the external AI to research the asset online and cross-reference with computed
metrics). Placement was decided after explicitly rejecting the existing 2×2 action toolbar (already
full of important actions: Edit/Sync/Refresh/Abs-%) and a floating persistent button (no precedent
elsewhere in the app) — the Signals panel header was the user's own suggestion once those two were
ruled out.

A new shared `AiExportMenu.svelte` component (trigger button + `fixed`-positioned, viewport-clamped
dropdown via the existing `getFixedDropdownPosition` helper) replaced 2 near-duplicated dropdown
implementations (dashboard + broker detail — the broker-detail one was actually the less robust of the
two, using `absolute` positioning that could clip inside `overflow-hidden` ancestors) and is now reused
a third time on the asset detail page.

## Consequences

- `AiPosition.symbol?: string` / `AiTechnicalMetadata.symbol?: string` / `AiTechnicalSummaryItem.symbol?: string`
  were replaced by `identifiers?: Record<string, string>` (ISIN/Ticker/CUSIP/SEDOL/FIGI/... — all of
  them, reusing the existing `buildIdentifiersList()` from `$lib/utils/assetTypes.ts`) — see
  [[problems/ai-export-name-not-ticker]].
- `buildTechnicalInputs()` in `aiExportBuilder.ts` now threads the asset id directly through an
  internal `InternalPosition` type instead of re-deriving it via `allAssets.find(a => a.display_name === p.name)`
  — that name-matching lookup was a latent bug (silently mismatches/drops technical data whenever two
  different assets share a display name) fixed as a side effect of the identifiers refactor.
- i18n: `dashboard.aiExportFull` / `aiExportDataOnly` / `aiExportCopied` / `aiExportCopiedData` removed;
  replaced by `dashboard.aiExportMenu.<id>.{label,description}` (6 entries) +
  `assetDetail.aiExportMenu.<id>.{label,description}` (2 entries) + one generic, interpolated
  `dashboard.aiExportCopiedGeneric` toast (`'{label}' copied to clipboard`) reused by every catalog entry.
- At the time, this round intentionally made no backend changes and composed prompts from
  `/portfolio/report` plus frontend-computed technical signals. Phase 0 later superseded that
  ownership model: see [[entities/ai-export-snapshot-service]].
- `svelte-check`: 0 errors/warnings; `./dev.py i18n audit`: 0 incomplete keys. No e2e tests existed for
  the old `ai-export-full`/`ai-export-data-only` test ids, so none needed updating.

## Links
- [[problems/ai-export-name-not-ticker]]
- [[features/F-054]] (Dashboard KPI & Overview — mentions the old AI export in passing; still accurate re: NAV/KPI, not re: AI export shape)
- [[decisions/ai-export-versioned-snapshot-boundary]] — current production architecture
- [[entities/ai-export-snapshot-service]] — current backend snapshot platform
- Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/Ai_consultant_engine/report_ai_export_mvp.md` (superseded for the prompt catalog shape; allocation-basis/compaction/WAC-policy sections it documents are still accurate and unchanged)

## Source files

| Role | Path |
|------|------|
| Historical MVP report | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_2/Ai_consultant_engine/report_ai_export_mvp.md` |
| Superseding Phase 0 plan | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/plan-phase00AiExportBackendSnapshotImplementation.prompt.md` |
| Current backend platform | `backend/app/services/ai_export/` |
| Current frontend task catalog | `frontend/src/lib/features/ai-export/catalog/` |
| Current analysis/options UI | `frontend/src/lib/features/ai-export/AiExportOptionsPanel.svelte`, `frontend/src/lib/features/ai-export/aiExportOptions.ts` |
| Current contextual memory | `frontend/src/lib/features/ai-export/aiExportMemory.ts`, `frontend/src/lib/features/ai-export/AiExportMenuV2.svelte` |
| Domain-aware manual link | `frontend/src/lib/components/ui/DocsLink.svelte` |
| Current prompt renderer | `frontend/src/lib/features/ai-export/templates/promptRenderer.ts` |
| Final cross-surface E2E | `frontend/e2e/ai-export.spec.ts` |
| Completed Phase 0 index | `LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/README.md` |
| Developer architecture | `mkdocs_src/docs/developer/architecture/patterns/ai_export_snapshot.md` |
