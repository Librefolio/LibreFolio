---
title: "Phase 06 Step 6 — i18n Dedup + Polish + Coverage"
category: source
source_type: plan
date_ingested: 2026-04-24
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step6/
tags: [phase06, i18n, translations, polish, coverage, testing]
related_features: [F-008]
related_decisions: [i18n-key-rationalization]
---

# Source: Phase 06 Step 6 — i18n Dedup + Polish + Coverage

## Summary

Final polishing phase for Phase 06, covering i18n duplicate key consolidation (18 groups eliminated), translation alignment across 4 languages, testing coverage analysis, and final documentation pass. Established the **context-aware rationalization** principle for i18n duplicates.

## Key Insights from i18n Cleanup

### Principle: Context-Aware Rationalization

**Rule**: Consolidate under `common.*` **only when meaning, context, AND value match in all 4 languages**.

**Accept duplicates when**:
1. **Semantic difference**: button "Close" ≠ OHLC "Close" price → `common.close` vs `dataEditor.col.close`
2. **Dynamic prefix**: `assets.types.*` must stay for runtime lookup `$t(\`assets.types.${var}\`)`
3. **Context specificity**: "Save" ≠ "Save Changes" (generic vs form-specific)
4. **Future flexibility**: EN identical today, but IT/FR/ES already diverge or will likely diverge

**Related**: [[decisions/i18n-key-rationalization]] — full rationale and examples.

## Consolidation Batches (from plan-phase06Step6-i18n-dedup.prompt.md)

### Batch 1: Shared Detail Page Keys

**Consolidated** (5 groups, 11 keys eliminated):
- `assetDetail.measures` + `fxDetail.measures` → `common.measures`
- `assetDetail.signals` + `fxDetail.signals` → `common.signals`
- `assetDetail.addMeasure` + `fxDetail.addMeasure` + `measure.addMeasure` → `common.addMeasure`
- `assetDetail.closeEditor` + `fxDetail.closeEditor` → `common.closeEditor`
- `assetDetail.exitMeasure` + `fxDetail.exitMeasure` → `common.exitMeasure`

**Pre-consolidation fix**: ES "Añadir medición" → "Añadir medida" (align with IT "Aggiungi misura"), FR "Fermer l'éditeur" → "Fermer éditeur" (align with IT).

### Batch 2: Modal ↔ Detail Duplicates (Assets)

**Consolidated** (4 groups, 8 keys eliminated):
- `assetDetail.classification` + `assets.modal.classification` → `common.classification`
- `assetDetail.identifiers` + `assets.modal.identifiers` → `common.identifiers`
- `assetDetail.geoDistribution` + `assets.modal.geographicDistribution` → `common.geoDistribution`
- `assetDetail.sectorDistribution` + `assets.modal.sectorDistribution` → `common.sectorDistribution`

### Batch 3: Cross-Feature Duplicates

**Consolidated** (3 groups, 6 keys eliminated):
- `assets.allCurrencies` + `fx.filter.allCurrencies` → `common.allCurrencies`
- `assets.empty.noMatchesTitle` + `fx.empty.noMatchesTitle` → `common.noMatchesTitle`
- `assets.provider.documentation` + `help.documentation` → `common.documentation`

### Batch 4: Point to Existing `common.*`

**Consolidated** (3 keys eliminated):
- `assets.schedule.confirmDelete` → `common.confirmDelete`
- `assets.schedule.deleteSelected` → `common.deleteSelected` (new key created)
- `brokers.name` → `common.name`

**Pre-consolidation fix**: FR "suppression" → "Suppression" (capitalize to match `common.confirmDelete`).

### Batch 5: Same-Namespace Merge

**Consolidated** (2 keys eliminated):
- `assets.schedule.emptyTitle` merged into `assets.schedule.empty` (identical string)
- `assets.modal.title` merged into `assets.addAsset` (both "Add Asset")

## Accepted Duplicates (~30 Groups)

**Examples with rationale**:

| Key A | Key B | EN Value | Why Separate |
|-------|-------|----------|--------------|
| `common.close` | `dataEditor.col.close` | "Close" | Button (Chiudi) vs OHLC price (Chiusura) |
| `common.reset` | `common.undo` | IT: "Ripristina" | EN different ("Reset to Default" vs "Undo") |
| `assets.types.OTHER` | `common.other` | "Other" | Dynamic prefix for runtime lookup |
| `chartSettings.signals.ema` | `chartSettings.signals.emaAbbr` | "EMA" | Name might expand to "Exponential Moving Average" |
| `assets.sync.assetsCount` | `assets.title` | "Assets" | Count label vs page title — may diverge |

**Documentation**: Full list in `knowledge_base/08_i18n_duplicates.md` (already ingested).

## Key Count Reduction

**Before cleanup**: 843 keys (60 duplicate groups, 0 unused)
**After cleanup**: ~825 keys (~30 accepted duplicate groups, 18 groups consolidated)

**Net reduction**: 18 keys eliminated (conservative approach — intentional duplicates preserved).

## Coverage & Test Improvements (from plan-phase06Step6-coverage-debt.prompt.md)

This file focuses on test coverage analysis and technical debt documentation, not on actionable decisions — content likely already captured in [[features/F-068]] (Backend Tests) and [[features/F-067]] (E2E Tests).

**Note**: Detailed coverage metrics belong in mkdocs developer documentation, not wiki (per SCHEMA.md — wiki is for decisions/patterns, not metrics).

## Polish Checklist (from plan-phase06Step6-Polish-Test-Docs.prompt.md)

Final pass covered:
- A11y warnings resolution (build clean)
- svelte-check error fixes (covered in [[sources/phase06-bugfix-migration]])
- Dark mode visual verification
- Responsive layout manual testing (4 breakpoints)
- i18n label verification across all pages

**Outcome**: Zero build warnings, zero svelte-check errors.

## Translation Alignment Notes

**Languages**: EN (source) → IT, FR, ES (targets)

**Alignment issues found and fixed**:
- ES inconsistent casing: "medición" vs "medida" → unified to "medida"
- FR inconsistent articles: "Fermer l'éditeur" vs "Fermer éditeur" → unified to no article (shorter, consistent with IT)
- IT/FR capitalization in confirmDelete keys → unified to capital-case

**Future guideline**: Before consolidating duplicates, **align translations first** (fix casing/wording differences), **then consolidate** (ensures winner has correct value for all languages).

## Source Files

| Role | Path |
|------|------|
| Source plans | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step6/` |
| i18n dedup plan | `plan-phase06Step6-i18n-dedup.prompt.md` |
| Polish plan | `plan-phase06Step6-Polish-Test-Docs.prompt.md` |
| Coverage plan | `plan-phase06Step6-coverage-debt.prompt.md` |
| i18n duplicates KB | `LibreFolio_developer_journal/knowledge_base/08_i18n_duplicates.md` (already ingested) |
| EN translations | `frontend/src/lib/i18n/en.json` |
| IT translations | `frontend/src/lib/i18n/it.json` |
| FR translations | `frontend/src/lib/i18n/fr.json` |
| ES translations | `frontend/src/lib/i18n/es.json` |
| i18n CLI | `dev.py` (i18n subcommand) |
