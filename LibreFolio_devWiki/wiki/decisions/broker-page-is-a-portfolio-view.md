---
title: "The broker page is a `PortfolioView`, fed by one data controller shared with the Dashboard"
category: decision
status: resolved
date: 2026-11-03
tags: [frontend, dashboard, broker-page, portfolio, data-controller, live-prices]
related: [domains/dashboard, domains/brokers, entities/portfolio-service, decisions/api-routes-removed-without-deprecation]
---

# Decision: the broker page is a `PortfolioView`

## Context
The Dashboard and the broker page showed the same kind of numbers (report, contribution, candles, series, rolling
return) but loaded them in two ways. Each page asked the backend its own set of questions, with its own retries and
its own cache, so the same broker could show different figures on the two pages, and every fix had to be made twice.

## Decision
- The Dashboard page body moved, unchanged, into one component, `PortfolioView` (a pure move: markup, test ids, URLs
  and behaviour stayed the same, and the gate sources were updated).
- The broker page mounts the same component for one broker. A **single data controller** (`portfolioData`, scoped by
  `portfolioDataScope`) feeds report, contribution, candles, series and rolling from one scope, with a cache-first
  background refresh and retries at 2, 4 and 8 seconds.
- **Whole-broker amounts on the broker page.** The broker page sends `apply_ownership_share=false`, so it shows the
  broker's full amounts; the Dashboard keeps the owner's share. One engine run per page serves all the questions.
- **Live prices (FB-28).** The controller polls a light report (summary only) a minute after each full report and
  every minute after, with the held assets' prices first. It pauses when the tab is hidden or after two minutes
  without input («Updates paused») and backs off on errors. Summary, KPIs, positions, allocation and the last growth
  step update in place.
- **The broker summary route is gone.** The broker page reads `GET /brokers/{id}`; cash and positions come from
  `POST /portfolio/report` (see [[decisions/api-routes-removed-without-deprecation]]).

## Consequences
- A change to a portfolio number is made in one place and appears on both pages.
- The Dashboard's page-size selector for the Transactions table works on the broker page too, and the Refresh button
  no longer wraps onto a second line.
- A test of "the broker page" is now a test of `PortfolioView` with a broker scope: prefer `data-testid` on the shared
  component over page-specific selectors.

## Source files
| Role | Path |
|------|------|
| Shared view | `frontend/src/lib/features/dashboard/` |
| Dashboard page | `frontend/src/routes/(app)/dashboard/+page.svelte` |
| Broker page | `frontend/src/routes/(app)/brokers/[id]/+page.svelte` |
