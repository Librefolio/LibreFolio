---
title: "Phase 0 / 18 — targeted BRIM refinements: Crédit Agricole refactor, eToro withdrawal fees"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/18_brimTargeted/plan-phase00BrimTargeted.prompt.md
tags: [phase0, release2, brim, credit-agricole, etoro, refactor, fees]
related:
  - features/F-013
  - decisions/credit-agricole-securities-only-cash-neutral-brim
---

# Source: Phase 0 / 18 — targeted BRIM refinements

## Summary

One short plan (~220 lines), delivered in `ebba209c5` (merge `5c2a711f3`, 2026-09-10) and archived on 2026-10-09.

## Key takeaways

- **Crédit Agricole — a refactor with byte-identical output**: the account parser was split into named phases; order,
  fake ids, evidence and `tx_index` must not change, and the plugin version stays. The securities layout creates
  `auto_cash` counterparts, the account layout must not ([[decisions/credit-agricole-securities-only-cash-neutral-brim]]).
- **A shared helper only with a second real consumer**: `attach_maturity_notices` moved to `_brim_output.py` because
  Intesa uses it too. Rejected: a generic fake-id allocator, and a campaign against every C901 site.
- **eToro**: a non-zero `Withdrawal Conversion Fee` / `Withdraw Fee` becomes a separate FEE, zero ones are ignored,
  the withdrawal itself is unchanged; every FEE forces quantity 0 before validation (a non-zero `Units` used to trip
  the zero-quantity check). The FEE reading is an assumption from the observed format, not proven semantics: the tests
  make a double count visible. The eToro plugin version was bumped.
- Gotcha kept by the tests: the Crédit Agricole securities XLSX has nine more preamble rows than the CSV, so source
  row numbers differ by 9 — asserted, not forced to match.

## Residuals (backlog 38)

L10 — a stale `TODO(P2-refactor) … nested trade-resolution closures` comment in `broker_credit_agricole.py`; the
closures are gone (verified at `586a4f0ea`).

## Wiki pages updated

- [[features/F-013]] — eToro and Crédit Agricole notes.

## Source files

| Role | Path |
|------|------|
| Plan | `LibreFolio_developer_journal/Release_2/phases/18_brimTargeted/plan-phase00BrimTargeted.prompt.md` |
| Crédit Agricole plugin | `backend/app/services/brim_providers/broker_credit_agricole.py` |
| eToro plugin | `backend/app/services/brim_providers/broker_etoro.py` |
| Shared helper | `backend/app/services/brim_providers/_brim_output.py` |
| Intesa plugin (second consumer) | `backend/app/services/brim_providers/broker_intesa.py` |
