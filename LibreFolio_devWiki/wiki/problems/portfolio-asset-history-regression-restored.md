---
title: "GET /portfolio/asset-history accidentally removed, then restored"
category: problem
status: resolved
date: 2026-07-06
tags: [backend, api, portfolio, regression]
related:
  - entities/portfolio-engine
  - domains/dashboard
  - sources/phase09-m3-broker-redesign-2026-07
---

# Problem: `GET /portfolio/asset-history` accidentally removed, then restored

## Symptom

During Milestone 3 gap analysis, `GET /portfolio/asset-history` (WAC vs. market price series for one asset)
was found missing from `backend/app/api/v1/portfolio_api.py`, even though the underlying service method
`get_asset_history()` still existed (orphaned) and the file's own module docstring still listed the route as
available.

## Root Cause

Commit `3184a969` removed the route as part of a broader cleanup of legacy endpoints that **were** genuinely
superseded by the unified `/portfolio/report` entrypoint (see [[concepts/portfolio-report-unified]]) —
`asset-history` was swept into that same cleanup by mistake even though it was not superseded (there is no
per-asset WAC/market-price series in the unified report response).

## Solution

Verified via `git log` that the route existed, was functional, and had tests before the removal. Restored in
commit `1a734008`; confirmed present again at `backend/app/api/v1/portfolio_api.py:137-151`.

## Prevention

When bundling an endpoint cleanup with "supersede by unified endpoint" as the stated rationale, verify each
removed route individually maps to something in the new unified response — a route with no direct
replacement (like a per-asset historical series) should not be removed just because it sits alongside routes
that genuinely are superseded.

## Impact

Low — caught during a planned gap-analysis pass (Milestone 3, Fase 1) before any user-facing consequence;
fixed same day.

## Source files

| Role | Path |
|------|------|
| Endpoint (restored) | `backend/app/api/v1/portfolio_api.py:137-151` |
| Gap analysis that found it | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_3/README.md` |
