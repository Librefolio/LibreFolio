---
title: "Knowledge Base: Frontend Reference"
category: source
source_type: knowledge_base
date_ingested: 2026-04-24
original_path: LibreFolio_developer_journal/knowledge_base/02_frontend.md
tags: [frontend, sveltekit, stores, components, signals, charts, i18n]
related_features: [F-004, F-008, F-021, F-033, F-037, F-071, F-072]
---

# Source: Knowledge Base — Frontend Reference

## Summary

Comprehensive overview of LibreFolio's SvelteKit frontend covering: directory structure, Tailwind 4 design system, ECharts-based chart library (14 components), Signal Library (10 technical analysis signals), component architecture (assets: 15 components/6317 lines, FX: 7 components, charts: 14 components/5100 lines), store patterns (TimeSeriesStore, EditBuffer, Svelte 5 runes), Zodios API client, and i18n system (840+ keys × 4 languages).

## Key Insights Extracted

### Store Patterns
- **TimeSeriesStore** ([[concepts/timeseries-store-pattern]]): Generic class for client-side time-series caching with gap-detection, delta-fetching, merge idempotence
- **EditBuffer** ([[concepts/editbuffer-pattern]]): Bidirectional inline editor pattern (click → CSV ↔ form), bulk save
- **Svelte 5 Runes** ([[concepts/svelte5-runes]]): Files with `.svelte.ts` extension use `$state`, `$derived` (chartSettingsStore, toastStore)

### Component Architecture
**Assets** (15 components, 6317 lines):
- ScheduledInvestmentEditor (1412 lines) — most complex, multi-step form
- AssetModal (1328 lines) — create/edit with SearchAutocomplete + provider auto-assign
- ProviderAssignmentSection (724 lines) — dynamic form generated from backend `params_schema`

**Charts** (14 components, 5100 lines):
- PriceChartFull (967 lines) — complete chart for detail pages (FX + Assets)
- ChartSignalsSection (734 lines) — signal overlay management with 3 categorized dropdowns
- LineChart (714 lines) — core multi-axis Y, visualMap (red/green), stale gradient

**Signal Library** (10 signals):
- Technical: EMA (IIR 1st order), RSI, MACD, Bollinger Bands
- Comparison: FX Pair, Asset Comparison
- Benchmark: Linear, Compound, Sine
- Measure: 2-click point-to-point (Δabs, Δ%, days)

### Design System
- Tailwind CSS 4 via `@theme {}` in `app.css` (no TS config file)
- Colors: `#1a4031` (libre-green), `#f5f4ef` (libre-beige)
- Dark mode complete with CSS variables in `html.dark`
- Font: Inter + `Noto Color Emoji` for flags (Windows compatibility)
- Icons: lucide-svelte

### i18n
- 840+ keys × 4 languages (EN, IT, FR, ES)
- svelte-i18n library
- CLI: `./dev.py i18n audit|add|remove|update|search|tree`
- Flag emoji with web font (Windows compatibility — [[problems/flag-emoji-windows]])

### Dual View Pattern
[[concepts/dual-view-pattern]]: Grid/table toggle with localStorage persistence (ViewModeToggle component) — used in Assets and FX list pages

## New Concepts Documented

None — all major patterns already in wiki. This source consolidates component counts and architecture details.

## Enrichments Made

- Added component line counts and complexity metrics to architecture overview
- Consolidated store pattern references
- Added Signal Library catalog with axis assignments
- Noted Svelte 5 `.svelte.ts` file naming convention

## Source Files

| Role | Path |
|------|------|
| Source KB file | `LibreFolio_developer_journal/knowledge_base/02_frontend.md` |
| Routes | `frontend/src/routes/(app)/` |
| Components | `frontend/src/lib/components/` |
| Stores | `frontend/src/lib/stores/` |
| Signal Library | `frontend/src/lib/charts/signals/` |
| Charts | `frontend/src/lib/components/charts/` |
| Asset components | `frontend/src/lib/components/assets/` |
| FX components | `frontend/src/lib/components/fx/` |
| API client | `frontend/src/lib/api/` |
| i18n files | `frontend/src/lib/i18n/{en,it,fr,es}.json` |
| Design system | `frontend/src/app.css` |
| E2E tests | `frontend/e2e/` |
