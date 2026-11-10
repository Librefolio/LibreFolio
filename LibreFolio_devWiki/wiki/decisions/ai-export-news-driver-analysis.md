---
title: "AI Export news-driver analysis separates movement evidence from causality"
category: decision
status: resolved
date: 2026-08-03
tags: [ai-export, portfolio, news, web-research, citations, causality]
related:
  - decisions/ai-export-versioned-snapshot-boundary
  - decisions/ai-export-technical-series-and-density-contract
  - entities/ai-export-snapshot-service
---

# Decision: AI Export news-driver analysis separates movement evidence from causality

> **2026-11-07 lint — current state:** the principle stands, the analysis ID does not. The focused V3 catalog
> (`5fa147532`, 04/08) published `portfolio.performance_market_drivers` and `broker.performance_market_drivers`
> (required dataset `*.overview_and_history`), and `7f4f59bc7` (05/08) removed `portfolio.market_events_review`
> with the legacy runtime (`test_ai_export_api.py` asserts it is gone). The link labels are now five: `supported`,
> `plausible`, `inferred`, `speculative`, `unexplained` (`PERFORMANCE_MARKET_DRIVER_STEPS` in `sharedInstructions.ts`).
> The sections below describe the decision as taken on 03/08.

## Context

Users need one Portfolio Analysis that can explain material security movements by
matching deterministic LibreFolio evidence with dated current news. LibreFolio
does not own a news database, and temporal coincidence cannot establish causality.

## Decision

`portfolio.market_events_review` requires `portfolio.overview` and
`portfolio.asset_comparison`, optionally includes `portfolio.performance_flows`,
and recommends the complete Portfolio Technical export only when materially useful.

The LLM must:

- identify observed movements and exact date windows before researching;
- prefer issuer filings, earnings, exchange/regulator notices, central-bank or
  government publications, then established financial reporting;
- provide publisher, title, URL, publication date, access date, and source type;
- separate issuer, sector/industry, and macro/market candidate drivers;
- label each link `supported`, `inferred`, or `speculative`;
- include conflicting evidence and explicitly list unexplained movements;
- never claim that timing alone proves causation;
- fall back to a deterministic movement inventory when web access is unavailable,
  without fabricating current news or citations.

External research remains an LLM-side task. The backend supplies deterministic,
versioned portfolio evidence and does not fetch or select news.

## Consequences

The catalog now contains 17 Analyses. The targeted real 3M Standard prompt in run
`20260803T100412.057382Z` included the required and optional datasets, rendered
9,266 token-equivalents, matched UI/probe bytes and hash, and had no public-output
violations.

## Source files

| Role | Path |
|------|------|
| Backend Analysis catalog | `backend/app/services/ai_export/analyses/catalog.py` |
| Analysis instructions | `frontend/src/lib/features/ai-export/templates/sharedInstructions.ts` |
| Response contract | `frontend/src/lib/features/ai-export/templates/responseContracts.ts` |
| Frontend catalog IDs | `frontend/src/lib/features/ai-export/catalog/shared.ts` |
| Real prompt evidence | run `20260803T100412.057382Z` (probe output, not tracked in the journal) |
