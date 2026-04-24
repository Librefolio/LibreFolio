---
title: "TODO Files — Project Root"
category: source
date: 2026-05-10
tags: [todo, planning, roadmap, features]
related_features: [F-075, F-076, F-077, F-078, F-079, F-080, F-081, F-082, F-083, F-084, F-085, F-086, F-087, F-088, F-089, F-090, F-091, F-092, F-093, F-094, F-095, F-096]
---

# Source: TODO Files — Project Root

**Source files**: `TODO_Completati.md` and `TODO_FUTURI.md` (project root)
**Maintained by**: developer (continuous updates)

## What these files contain

### `TODO_Completati.md`
A running log of completed development tasks with implementation details. Entries include:
- Component and service names created
- File paths for new code
- Key design decisions made during implementation
- Cross-references to phases

Completed items ingested into the wiki: i18n cleanup (2-pass, [[F-008]]), Image Crop / FileUploader ([[F-014]]), FX cache TTL 5min & Upload metadata cache TTL 1h ([[F-061]]), Scheduled Investment late interest with `generate_interest` flag ([[F-034]]), FX Page complete ([[F-022]], [[F-023]]), FX testing cleanup ([[F-072]], [[F-071]]).

### `TODO_FUTURI.md`
A roadmap of future features, improvements, and ideas. Entries range from high-priority architectural work to low-priority ideas. This file was the source for features F-075 through F-095.

## Features extracted (F-075 to F-095)

| Code | Title | Priority |
|------|-------|---------|
| [[F-075]] | TanStack Table v9 Migration | low |
| [[F-076]] | Log Level Policy & TRACE Level | medium |
| [[F-077]] | Mobile DataTable Touch Drag | low |
| [[F-078]] | User Filter in Files Page | medium |
| [[F-079]] | GDPR Broker Access Compliance | medium |
| [[F-080]] | Candlestick Chart / Volume Bars | medium |
| [[F-081]] | Fiscal Sale Method (FIFO/LIFO/PMC/SelectID) | HIGH |
| [[F-082]] | Cash Split Transactions | medium |
| [[F-083]] | Multi-File Multi-Broker Import | HIGH |
| [[F-084]] | Transaction Gain Chart | medium |
| [[F-085]] | QuarkAI AI Assistant | low (idea) |
| [[F-086]] | Client-side Image Preview Cache (LazyImage) | medium |
| [[F-087]] | Smooth Signal Line Style | low |
| [[F-088]] | Return-over-N Chart | medium |
| [[F-089]] | FX Provider Per-Plugin Documentation | low |
| [[F-090]] | AssetEvent → Transaction Link (Enrichment) | HIGH |
| [[F-091]] | Multi-Worker Cache Server | low |
| [[F-092]] | Default Language/Currency for New Users | low |
| [[F-093]] | Coupon Policy Field | low (idea) |
| [[F-094]] | Sync Date Range Dialog | medium |
| [[F-095]] | Asset Delete Transaction Count Link | medium |
| [[F-096]] | Scheduled Investment — Decoupled Frequencies + Anchor Day | medium |

## Update frequency
These files are updated continuously by the developer. Re-ingest when:
- A TODO_Completati entry references a new feature or design decision
- TODO_FUTURI contains a new entry not yet in the wiki

## Source files

| Role | Path |
|------|------|
| Completed TODOs | `TODO_Completati.md` |
| Future TODOs | `TODO_FUTURI.md` |
