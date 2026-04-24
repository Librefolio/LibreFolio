---
title: "FIFO Cost Basis Computed at Runtime"
category: decision
date: 2026
status: resolved
tags: [backend, calculations, fifo, transactions, performance]
related_features: [F-056]
---

# Decision: FIFO Cost Basis Computed at Runtime

## Context
LibreFolio needs to compute cost basis (average cost, unrealized gain/loss) for each asset position using FIFO (First In, First Out) matching of BUY/SELL transactions. The question was whether to persist FIFO results to the database or compute them on-demand at query time.

## Decision
FIFO cost basis is **computed on-demand at query time**, never persisted to the DB. Every time portfolio performance data is requested, the service re-runs the FIFO algorithm over the full transaction history for the relevant assets.

## Alternatives considered
- **Persist FIFO results as a snapshot table** — rejected: any retroactive edit to a historical transaction (add, modify, delete) would require cascading updates to all subsequent FIFO records; this is complex, error-prone, and requires migrations.
- **Compute and cache in Redis/memory** — rejected: adds infrastructure complexity; the dataset is small enough that in-process computation is fast.

## Rationale
Retroactive transaction edits are a first-class use case (users fix import errors, add missed historical trades). Computing at runtime means retroactive edits are always safe and correct without any migration or cache invalidation logic. The transaction set per asset is small enough that repeated computation is negligible.

## Consequences
- No FIFO snapshot table exists in the DB schema.
- Performance depends on the number of transactions per asset — acceptable for personal portfolios (hundreds, not millions).
- All FIFO logic lives in the service layer, making it testable in isolation.
- Adding a historical transaction immediately reflects in all calculations (no sync needed).

## Related
- [[F-056]] — FIFO at Runtime (the feature implementing this decision)

## Source files

| Role | Path |
|------|------|
| Transaction service (FIFO logic) | `backend/app/services/transaction_service.py` |
| DB model (Transaction) | `backend/app/db/models.py` |
