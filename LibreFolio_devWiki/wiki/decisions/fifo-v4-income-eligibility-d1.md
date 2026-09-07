---
title: "FIFO v4 income eligibility: D-1, broker-scoped, transfer-aware"
category: decision
status: resolved
date: 2026-07-22
tags: [backend, fifo, dividend, interest, income, transfers]
related: [fifo-v4-cost-allocation-ladder, fifo-v4-engine-architecture, entities/fifo-lot-engine, concepts/d1-income-eligibility-window]
---

# Decision: FIFO v4 income eligibility — D-1, broker-scoped, transfer-aware

## Context
Dividend/interest allocation across LONG lots previously used lot state **on the income date itself** and
spread pro-rata across **all** lots of the asset regardless of which broker was actually paid. This wrongly
included same-day BUYs, excluded same-day SELLs, and credited income to brokers that never received it.

## Options Considered
1. **Keep D-semantics (income-date lot state), asset-wide** — current/legacy behavior; rejected: ambiguous on
   same-day trades, wrong when brokers differ.
2. **D-1 semantics (previous-day open quantity), asset-wide** — removes the same-day ambiguity but still ignores
   which broker actually received the payment.
3. **D-1 semantics, broker-scoped, symmetric transfer handling (end-of-day grace on arrival day)** — considered
   in earlier drafts (`feasibility-analysis-v3.md` §22); rejected: retroactive/asymmetric grace windows reopen
   the same ambiguity D-1 was meant to remove.
4. **D-1 semantics, broker-scoped, asymmetric From/To transfer handling — CHOSEN.**
5. For same-key TAX pools specifically: **mixed allocable/orphan pool** (partial α-share to orphan, still on
   the table as late as the v4-review) vs **whole-pool all-or-nothing** — chosen: whole-pool, since eligibility
   depends only on asset/broker/D-1 state, which is identical for every income event sharing the same
   `(asset, broker, date, currency)` key, so a "partly eligible" pool is not actually reachable under the D-1 +
   broker-scope rules above.

## Decision
- `EligibleQuantity_i(D) = OpenQuantity_i(D-1)` — income eligibility uses **end-of-D-1** open quantity, never
  same-day (D) state.
- Eligible lots must additionally match: same asset, **paying broker**, LONG direction, and custody
  compatibility.
- **Transfer-aware, asymmetric by side**: on the **From** broker, eligible quantity includes both quantity still
  held at BROKER custody and quantity already `IN_TRANSIT` with `source_broker_id = From` (it still "counts" as
  originating there). On the **To** broker, only quantity already physically on `To` at D-1 counts — quantity
  that arrives on the income date itself, while still in transit at D-1, becomes **orphan income** on arrival
  day rather than being credited to `To` with a retroactive grace window.
- For one pool key `(asset, broker, date, currency)`, eligibility is **type-independent** — the whole income
  pool is either fully allocable or fully orphan, never split.

## Consequences
- A lot opened on D (BUY) earns no income from an event on D; a lot fully sold on D still earns income (D-1
  state still shows it open); a lot opened **and** closed on D is excluded entirely.
- Dividends credited on Directa never land on IBKR lots (or vice versa) even for the same asset.
- "Income arriving at the destination broker on the same day a transfer is still in transit" is **intentionally**
  orphan and flagged — a deliberate, documented trade-off for determinism over completeness.
- This is a real, user-visible behavior change from the pre-v4 service logic (see
  [[problems/fifo-income-silently-dropped-after-full-close]] for a related pre-existing silent-drop bug fixed
  in the same pass).
- Marked in the docs as **"Changed in FIFO v5"** (see `mkdocs_src/.../fifo-lot-analysis.en.md` "Income Allocation
  Across Lots").

## Related
- [[concepts/d1-income-eligibility-window]]
- [[decisions/fifo-v4-cost-allocation-ladder]] — TAX pools reuse the same broker/D-1 eligibility semantics before falling
  back to the cost ladder
- [[entities/fifo-lot-engine]]
- [[sources/fifo-v4-fee-tax-integration]]

## Source files

| Role | Path |
|------|------|
| Final design | `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/hig-level-analysis-v5.md` §8-§9 |
| Final feasibility pivot (whole-pool) | `.../v4-fee_tax_integration/feasibility-analysis-v4.1.md` §4.1-4.3 |
| Rejected grace-window draft | `.../v4-fee_tax_integration/feasibility-analysis-v3.md` §22 |
| Executable plan | `.../v4-fee_tax_integration/implementation-plan-v5.md` Fase 1.1-1.4 |
| Engine implementation | `backend/app/services/fifo_lot_engine.py` |
| User-facing doc | `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.en.md` §"Income Allocation Across Lots" |
