---
title: "Beta testing 2026-08-05 — the tester report and its taxonomy"
category: source
source_type: journal
date_ingested: 2026-08-31
original_path: LibreFolio_developer_journal/Release_2/Phase_0/06_betaTestingReportAndFixing/
tags: [beta-testing, brim, credit-agricole, import, reconciliation, product-defect, bonds]
related:
  - concepts/characterisation-test-latch
  - concepts/discard-the-answer-not-the-question
---

# Source: the 2026-08-05 beta testing session

## Summary

The first external beta session: one tester (Marco), three Crédit Agricole XLSX
exports, one working day. The output was a report, a taxonomy of **34 findings**,
and a full reconciliation of one real portfolio against the bank's own figures.

The verdicts are the reason this material matters: **30 confirmed, 2 partially
confirmed, 2 disproved, 3 discovered during analysis**. A beta report that is
merely believed produces churn; one that is adjudicated produces a plan.

## The root cause, and its cost

**B1 — the `COMPRAVENDITA TITOLI` causale was not handled.**

`broker_credit_agricole.py` assumed the securities leg of a trade would *always*
arrive from the *Deposito Titoli* file. When a user imports only account
statements — or statements covering periods the securities file does not — the
trade **disappears**: the position is never opened and the cash is deducted as if
it were an external withdrawal.

The tester found it before the analysis did:

> *"I have verified that if they are not present it takes them as deposit and
> withdrawal, and that is why it went negative!!!"*

**Four rows out of four lost**, including a **~50 000 hole** on
`BTP 01/03/35 3,35 %` — the one of the four the tester had *not* corrected by
hand.

## B5 — the enabler nobody had looked for

Discovered during the analysis, and it changed the quality of the whole fix.

The name in a purchase row **matches by prefix** the name on the coupons of the
same security, and coupon rows carry **ISIN + `NOMINALE`**:

| purchase (truncated by the export) | coupon | ISIN | nominal |
|---|---|---|---:|
| `BTP 1/3/32 1,65%` | `BTP 1/3/32 1,65%` | IT0005094088 | 50 000 |
| `BTP 01/03/35 3,35%` | `BTP 01/03/35 3,35%` | IT0005358806 | 50 000 |
| `BTP PIU 25-2-33 CU` | `BTP PIU 25-2-33 CUM` | IT0005634792 | 15 000 |

So for bonds the plugin can resolve **quantity and ISIN automatically**, asking
the user nothing.

And the mechanism **already existed**: `_parse_account_movements` builds
`income_identity_by_date` to recover ISIN and nominal from coupons for
maturities, already covered by a test. The fix is to generalise that index
**from per-date to per-name**, not to design something new.

> The best finding in the report was not a defect. It was noticing that the
> repair for the worst defect was already half-written for a different purpose.

## B2 and B3 — the limits that must be declared

**B2 — accrued interest and fees are baked into the purchase price.** The
statement exposes a single amount conflating clean price, accrued interest and
commission:

| security | cash out | book value | difference |
|---|---:|---:|---:|
| BTP 1/3/32 1,65 % | 46 603,73 | 46 177,79 | **425,94** |
| BTP 01/03/35 3,35 % | 50 683,13 | 50 018,11 | **665,02** |
| BTP PIU 25-2-33 | 15 000,00 | 15 000,00 | 0,00 *(issued at par)* |

Booking everything into the purchase makes our cost basis **higher** than the
bank's by the accrued interest. Acceptable as a fallback — but it has to be
**declared**, or the next reconciliation fails again for a different reason.

**B3 — quantity is genuinely absent for funds/SICAV.** For
`SOTTOSC SICAV … AMUNDI PIO GLOB EQ G` there is no coupon to infer from, and the
description carries neither units nor NAV. B5 does not apply; the data is not
there. The only honest answer is to ask the user.

## Key Takeaways

- **Adjudicate every finding.** 30/2/2/3 is a more useful artefact than 34 items
  on a list, because it tells the next reader which ones were *checked*.
- **Distinguish "we mis-handle it" from "the data does not contain it".** B1 is
  ours; B3 is the file's. They get different fixes and different UX.
- **Declare the fallback.** An acceptable approximation that goes unrecorded
  becomes the next reconciliation failure.
- **A real portfolio finds what mock data cannot.** Every one of these depends on
  the specific shape of one bank's export over one real year.

## Not ingested from this folder

The ten `plan-phase00*.prompt.md` files are execution plans derived from the
findings above. Two are already covered
(`phase00-ai-export-backend-snapshot`, `phase00-risk-analysis-backend`), and the
remainder are step-by-step operational documents whose durable content is either
already in the taxonomy or belongs to the feature pages. They are listed in
`INDEX.md` with their P1-P8 status table.

## Source files

| Role | Path |
|------|------|
| Tester report | `LibreFolio_developer_journal/Release_2/Phase_0/06_betaTestingReportAndFixing/00_20260805_betaTester_report.md` |
| Taxonomy of findings | `.../01_tassonomia_findings.md` |
| Reconciliation | `.../02_riconciliazione_credit_agricole.md` |
| Index and P1-P8 status | `.../INDEX.md` |
| BRIM provider | `backend/app/services/brim_providers/broker_credit_agricole.py` |
| Provider tests | `backend/test_scripts/test_external/test_brim_providers.py` |
| mkdocs | `mkdocs_src/docs/developer/backend/brim/` |
