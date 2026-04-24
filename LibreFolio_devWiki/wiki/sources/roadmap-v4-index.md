---
title: "RoadMap V4 — Frontend Development Plan Index"
category: source
date: 2026-01-09
tags: [history, frontend, v4, roadmap, phases]
related_features: [F-004, F-008, F-066]
---

# Source: RoadMap V4 — Frontend Development Plan Index

**Source file**: `LibreFolio_developer_journal/RoadmapV4_UI/phases/00-index.md`
**Created**: 2026-01-09 — Version 4.0 (the first plan that included a complete frontend)

## What this represents

This is the master index of the V4 roadmap — the plan that introduced SvelteKit as the frontend (replacing the never-built React + MUI V1 plan). It tracks all phases from 0 through 10.

## Phase completion map (at time of ingest)

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Fix Login Page + Build Integration | ✅ Done |
| 1 | i18n, OpenAPI, API Client, Auth Store ([[F-008]], [[F-066]]) | ✅ Done |
| 2 | Backend Auth: DB, Service, API, CLI, Tests ([[F-001]], [[F-065]]) | ✅ Done |
| 2.5 | Login + Register modal integration | ✅ Done |
| 3 | Layout Sidebar + Settings Page ([[F-004]], [[F-005]], [[F-006]]) | ✅ Done |
| 4 | Brokers, Files, Image Crop, Modal base ([[F-009]]–[[F-014]]) | ✅ Done |
| 5 | FX Currencies, Pair Sources, Sync ([[F-015]]–[[F-023]]) | ✅ Done |
| 6 | Assets: Dual View, Chart, Signals, Wizard ([[F-024]]–[[F-036]], [[F-037]]–[[F-045]]) | ✅ Done |
| 7 | Transactions List, Add/Edit, Import ([[F-046]]–[[F-051]]) | 🔄 In progress |
| 8–10 | Scheduler, Dashboard, Polish ([[F-052]]–[[F-055]]) | ⏳ Planned |

## Key insight
Phase 4 (Brokers) expanded significantly — originally scoped at ~15 days but grew substantially with BRIM multiuser analysis, E2E testing infrastructure, data separation, image crop, dark mode, and component reorganization. This is the first example of a "phase that grew" — a pattern that repeated in Phase 6 (Assets).

## Source files
| Role | Path |
|------|------|
| Source | `LibreFolio_developer_journal/RoadmapV4_UI/phases/00-index.md` |
| Related | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-00-subplan/plan-frontendDevelopment.prompt.md` |
