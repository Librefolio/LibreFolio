---
title: "Splitting an imported row: the legs always add up to the row — the user names the charges, the trade leg is the remainder (B5-lite, no generic leg editor)"
category: decision
status: accepted
date: 2026-08-08
tags: [frontend, import, brim, credit-agricole, bonds, accrued-interest, fees, fixed-point, beta-testing, release-1.1]
related:
  - decisions/credit-agricole-securities-only-cash-neutral-brim
  - decisions/asset-identity-quoted-code-leads
  - features/F-049
  - entities/import-wizard-modal
  - sources/beta-testing-2026-08-05
---

# Decision: a split can only move money between its own legs

## Context

A bank statement often gives one amount for something that happened in several pieces. The beta test's Crédit
Agricole export debited a secondary-market bond purchase as a single figure: clean price, accrued interest and
commissions together ([[sources/beta-testing-2026-08-05]], finding B2). The importer cannot invent the breakdown,
but the user has it on the contract note.

The importer already emitted several transactions from one row (fee and tax legs, the counter-entries of the
*Deposito Titoli* layout). What was missing was a split **driven by the user**: the repair step edited one row as one
transaction, with no cash field and no extra leg.

## Decision

**08/08/2026, the developer**: no generic leg editor. Whoever needs to add more does it in the **bulk transaction
editor**, which already exists and is the place for free editing. Instead, **B5-lite**: where the importer sees that
cash and nominal disagree, it offers to split *that* row, and nothing else.

The first reading of B5-lite was wrong. The plan concluded that the split was not feasible, because the measured gap
(cash minus nominal) is not the accrued interest: one bond was bought below par, so its gap was negative. The
developer corrected the premise:

> «lo split se viene fatto è valido solo se la somma degli importi delle transazioni è pari al valore della
> transazione; il fatto che sia sotto o sopra la pari non c'entra»

So the **only invariant is: the sum of the legs equals the row's amount.** The user types the figures they can read on
the contract note, and the trade leg is whatever is left: the residual is zero by construction, and nothing has to be
deduced. The gap only decides when the question is asked.

## What the code does today

- `splitRowCharges.ts` (shipped in `d1e04b2b8`, 12/08/2026; the plan's first form, `splitRowAmount`, had two fixed
  legs): the user lists the charges they can name, and the trade leg is the remainder. The user can only move money
  **between** legs, never into or out of the import. On a purchase the trade leg is smaller than the row; on a sale
  the credit is already net, so the trade leg is larger.
- The repair step (`FixFlaggedStep.svelte`) offers three kinds of charge — fee, tax, accrued interest — and books a tax
  as `TAX` and the other two as `FEE`.
- **Accrued interest is a `FEE`, not an `INTEREST`**: an `INTEREST` row must carry positive cash
  (`backend/app/schemas/transactions/transactions.py`), and accrued interest paid on a purchase is cash out. It is also not part of
  the cost of the security, since it comes back with the first gross coupon, so it must stay out of the FIFO cost
  basis, which is where `FEE` keeps it.
- Amounts are subtracted in **fixed point**: in floating point `50683.13 - 50018.11` is `665.0199999999968`, and a leg
  that does not recompose the statement is exactly what the function exists to prevent.
- The importers give **hints read from the file** (`split_suggestions`, Crédit Agricole and Danske Bank). The most
  important prevents a real error: when the file already records charge rows near the trade date, splitting them out
  of the trade again would count them twice.
- The cash-versus-nominal finding moved from a notice to a **warning on the `BUY`'s cash field**: a finding the user can
  resolve belongs where it is resolved.

## Why not a generic editor

| | Generic leg editor | Charges plus remainder |
|---|---|---|
| Residual to balance by hand | possible | zero by construction |
| Can drift from the statement | yes | no |
| Cost | a new editor inside the wizard | one panel on the repair step |
| Free editing | duplicated | left to the bulk editor |

## Source files

| Role | Path |
|------|------|
| Split arithmetic | `frontend/src/lib/features/transactions/import/splitRowCharges.ts` |
| Split tests | `frontend/src/lib/features/transactions/import/splitRowCharges.test.ts` |
| Repair step | `frontend/src/lib/features/transactions/import/FixFlaggedStep.svelte` |
| Hints, Crédit Agricole | `backend/app/services/brim_providers/broker_credit_agricole/plugin.py` |
| Hints, Danske Bank | `backend/app/services/brim_providers/broker_danske_bank/plugin.py` |
| `INTEREST` cash rule | `backend/app/schemas/transactions/transactions.py` |
| Plan | `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/plan-phase00BrimCreditAgricoleTrades.prompt.md` |
