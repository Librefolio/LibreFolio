---
title: "Asset Orphan vs Portfolio-Level Cost/Income"
category: "concept"
tags: ["backend", "fifo", "fee", "tax", "data-quality"]
related: ["decisions/fifo-v4-cost-allocation-ladder", "decisions/fifo-v4-validation-and-scope", "entities/fifo-lot-engine", "entities/portfolio-engine", "concepts/deterministic-cost-matching-ladder"]
---

# Concept: Asset Orphan vs Portfolio-Level Cost/Income

## Definition
Two distinct, easily-confused "no specific lot" states for a FEE/TAX/income row, routed to completely different
places:

- **Asset orphan** (`asset_orphan_fees` / `asset_orphan_taxes` / `asset_orphan_income`): the row **is** linked
  to an asset (`asset_id` is set), but the deterministic matching ladder found no eligible lot for it (e.g. a
  fee booked after the position was fully closed, with no candidate trade on that day or the previous day).
  This stays inside [[entities/fifo-lot-engine]]'s territory — it is surfaced as an asset-level aggregate, not
  attached to any single lot, and is never silently dropped.
- **Portfolio/broker-level (assetless)**: the row has **no** asset link at all (`asset_id = null` — e.g. a flat
  platform fee). This never enters the FIFO engine's matching ladder in the first place; it is handled entirely
  by [[entities/portfolio-engine]] as a broker/portfolio-level effect.

## Where It Applies
- Every asset-linked FEE/TAX/income row that fails to match a lot under
  [[concepts/deterministic-cost-matching-ladder]] or [[concepts/d1-income-eligibility-window]].
- The FIFO-vs-Portfolio-Engine boundary decision in [[decisions/fifo-v4-cost-allocation-ladder]].
- Data-quality banners/aggregates surfaced in the lots-analysis UI.

## Why the distinction matters
Conflating the two would either (a) force asset-linked-but-unmatched costs onto an unrelated lot just because
"something" needed an owner, corrupting per-lot P&L, or (b) try to force genuinely assetless costs through a
lot-matching ladder that has no defensible anchor to match against. Keeping them separate means: no defensible
lot-level allocation is ever invented, and nothing is ever silently lost — every euro is either on a specific
lot, an asset-level orphan aggregate, or a portfolio-level bucket.

## Source files
| File |
|------|
| `backend/app/services/fifo_lot_engine.py` |
| `backend/app/services/portfolio_engine.py` |
| `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/implementation-plan-v5.md` §3.2, Fase 4 |
| `mkdocs_src/docs/financial-theory/instruments/transaction-types/fee.en.md` §"How LibreFolio attributes fees and taxes" |
