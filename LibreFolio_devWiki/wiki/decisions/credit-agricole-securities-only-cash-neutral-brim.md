---
title: "Crédit Agricole securities-only BRIM cash-neutral model"
category: decision
status: superseded
date: 2026-07-25
superseded_date: 2026-10-28
tags: [backend, brim, broker, credit-agricole, transactions, cash]
related:
  - decisions/brim-report-sets
  - features/F-013
  - features/F-103
---

# Crédit Agricole securities-only BRIM cash-neutral model

> **Superseded on 2026-10-28 (2026-11-07 lint).** Plugin 2.0.0 (`d0be8c7f2`, «Crédit Agricole 2.0.0 as a report-set
> plugin», W5-7) imports the securities export **together with** the account export (`Lista Movimenti Conto`) as a
> report set ([[decisions/brim-report-sets]]): the two files are paired row by row (same kind of fact, same amount to
> the cent, same value date) and the cash comes from what the account states, not from a synthesised DEPOSIT or
> WITHDRAWAL. A file read alone is no longer imported (`BRIMSetRequiredError`). The succession causali
> (`SUCCESSION_CAUSALI` in `_classify.py`) keep their names. The model below is the one of plugin 1.x.

## Summary
Crédit Agricole Italia `Lista Movimenti Deposito Titoli` is a securities-only export: it contains trades and coupons, but not the bank-account cash flows that fund buys or receive sell proceeds. The BRIM plugin therefore imports every BUY with a same-day DEPOSIT before it, and every SELL with a same-day WITHDRAWAL after it.

## Details
Succession causali `GIRO ALTRO DOSSIER` and `VERS.TITOLI` are now modeled as BUY transactions, not ADJUSTMENTs. Because their reported countervalue is zero, the BUY cash amount is derived from `Prezzo × Quantità` using the existing Crédit Agricole price convention: bonds per 100 nominal, funds per unit.

The plugin preserves each succession row faithfully instead of deduplicating or aggregating: if the bank reports multiple legs for the same security at different prices/quantities, LibreFolio emits multiple BUY+DEPOSIT pairs. Descriptions keep the source causale, e.g. `[GIRO ALTRO DOSSIER — successione] ...`, so provenance remains visible in the import wizard.

Coupons (`CEDOLA`) remain direct INTEREST rows with no automatic counter-entry, because they are actual cash income in the securities report.

## Source files
| Role | Path |
|------|------|
| Implementation | `backend/app/services/brim_providers/broker_credit_agricole/plugin.py` |
| Report-set analysis (2.0.0) | `backend/app/services/brim_providers/broker_credit_agricole/_report_set.py` |
| Causale registry | `backend/app/services/brim_providers/broker_credit_agricole/_classify.py` |
| Tests | `backend/test_scripts/test_external/test_brim_providers.py` |
| User docs | `mkdocs_src/docs/user/transactions/import/credit_agricole.en.md` |
