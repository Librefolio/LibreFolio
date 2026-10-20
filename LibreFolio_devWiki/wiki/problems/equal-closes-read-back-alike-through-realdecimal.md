---
title: "Equal closes read back alike through RealDecimal; only a trade mark differs in form"
category: problem
status: resolved
date: 2026-10-19
tags: [backend, db, decimal, real-decimal, testing, lots, price-marks]
related:
  - entities/lots-analysis-service
  - concepts/self-parity-needs-the-shared-step-pinned
---

# Equal closes read back alike through RealDecimal

## Summary

An L1a parity book wrote three equal closes in different forms (115, 115.0, 115.00), to prove that a change of
representation alone is a change day. Its precondition failed on HEAD: the service read all three as `115.000000`.
`PriceHistory.close` is a `RealDecimal(24, 12)` column, which reads a value back as the shortest decimal padded to at
least six decimals (`READ_MIN_SCALE = 6`), and `_load_prices()` re-reads the closes from the database.

## Details

- Through the database two equal closes never differ in form. A trade's mark does: `amount / quantity`
  (`-1650.000000 / 15.000000`) is `Decimal('110')`, exponent 0, while a close of 110 reads `Decimal('110.000000')`.
  A carried trade mark that meets an equal close is the reachable «same value, other form» day — and there the
  estimated flag flips too.
- Why it matters: a `Decimal`'s form reaches the JSON (`"110"` against `"110.000000"`). An optimisation that skips the
  «unchanged» days must compare the exact representation (`Decimal.as_tuple()`), never `==`. L1a does, and its unit
  tests pin that contract with forms the database cannot produce (`1.1` against `1.10`).
- The book was rebuilt on the trade mark (a BUY of 15 for 1 650 on Wednesday, an equal close on the next Monday, no
  transaction that day).

## Source files

| Role | Path |
|------|------|
| The padding | `backend/app/db/real_decimal.py` |
| The close column | `backend/app/db/models.py` |
| Trade marks | `backend/app/services/financial_math/price_marks.py` |
| Exact comparison | `backend/app/services/financial_math/lots/change_days.py` |
| The book that proves it | `backend/test_scripts/test_services/test_financial/test_lots_change_days_parity.py` |
