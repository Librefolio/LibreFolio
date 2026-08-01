---
title: "Crédit Agricole securities-only BRIM cash-neutral model"
category: decision
date: 2026-07-25
tags: [backend, brim, broker, credit-agricole, transactions, cash]
---

# Crédit Agricole securities-only BRIM cash-neutral model

## Summary
Crédit Agricole Italia `Lista Movimenti Deposito Titoli` is a securities-only export: it contains trades and coupons, but not the bank-account cash flows that fund buys or receive sell proceeds. The BRIM plugin therefore imports every BUY with a same-day DEPOSIT before it, and every SELL with a same-day WITHDRAWAL after it.

## Details
Succession causali `GIRO ALTRO DOSSIER` and `VERS.TITOLI` are now modeled as BUY transactions, not ADJUSTMENTs. Because their reported countervalue is zero, the BUY cash amount is derived from `Prezzo × Quantità` using the existing Crédit Agricole price convention: bonds per 100 nominal, funds per unit.

The plugin preserves each succession row faithfully instead of deduplicating or aggregating: if the bank reports multiple legs for the same security at different prices/quantities, LibreFolio emits multiple BUY+DEPOSIT pairs. Descriptions keep the source causale, e.g. `[GIRO ALTRO DOSSIER — successione] ...`, so provenance remains visible in the import wizard.

Coupons (`CEDOLA`) remain direct INTEREST rows with no automatic counter-entry, because they are actual cash income in the securities report.

## Source files
| Role | Path |
|------|------|
| Implementation | `backend/app/services/brim_providers/broker_credit_agricole.py` |
| Tests | `backend/test_scripts/test_external/test_brim_providers.py` |
| User docs | `mkdocs_src/docs/user/transactions/import/credit_agricole.en.md` |
