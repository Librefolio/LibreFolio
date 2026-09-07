---
title: "D-1 Income Eligibility Window"
category: "concept"
tags: ["backend", "fifo", "dividend", "interest", "income"]
related: ["decisions/fifo-v4-income-eligibility-d1", "entities/fifo-lot-engine", "concepts/deterministic-cost-matching-ladder"]
---

# Concept: D-1 Income Eligibility Window

## Definition
Entitlement to an asset-linked income event (dividend/interest) is decided by lot state as of the **end of the
day before** the income date, never by same-day (D) state:

```
EligibleQuantity_i(D) = OpenQuantity_i(D-1)
```

A lot is eligible for a share of the income only if it was already open, at the paying broker, at close of
D-1. This is deliberately **asymmetric with respect to transfers**: on the broker the position is transferring
**from**, quantity still `IN_TRANSIT` but originating there still counts; on the broker it's transferring
**to**, only quantity already physically settled there at D-1 counts — quantity that arrives on the income
date itself, while still in transit at D-1, becomes orphan income rather than being credited to the
destination broker under a retroactive grace window.

## Where It Applies
- Dividend/interest allocation in [[entities/fifo-lot-engine]].
- Scoped additionally to the **paying broker** (not asset-wide) — see [[decisions/fifo-v4-income-eligibility-d1]].
- The income-first step of the TAX cost-matching ladder reuses this same D-1/broker eligibility test before
  falling back to trades — see [[concepts/deterministic-cost-matching-ladder]].

## Why D-1 (not D)
Using the income date's own end-of-day state is ambiguous: a BUY executed *on* the income date would wrongly
appear entitled, and a lot SOLD on the income date would wrongly appear excluded, even though real-world
record-date conventions look at ownership *before* the event, not after same-day trading. D-1 removes that
ambiguity and is deterministic and split-invariant.

## Rejected alternative
Earlier drafts also allowed **adjacent-day matching on both sides** (D-1 *and* D+1, for both income eligibility
and cost matching) with tie-break rules to resolve conflicts. This was rejected project-wide: D+1 is
future-looking (attributing today's event to a trade that, relative to the booking date, hasn't happened yet)
and the tie-breaks never fully removed the ambiguity. The final rule across FIFO v4/v5 is uniformly
**previous-day only, never next-day**.

## Examples
- Lot bought on D (the income date): **not** eligible — was not open at end of D-1.
- Lot fully sold on D (the income date): **still** eligible — was open at end of D-1.
- Lot bought **and** fully sold on D: **not** eligible (never existed as of D-1).
- Position transferred from Broker A to Broker B, arriving on D itself, income posted on D by Broker B: **not**
  eligible on B (not settled there at D-1) — becomes orphan income, flagged, not silently dropped.

## Source files
| File |
|------|
| `backend/app/services/fifo_lot_engine.py` |
| `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/hig-level-analysis-v5.md` §8-9 |
| `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.en.md` §"Income Allocation Across Lots" |
