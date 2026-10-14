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
*Update (2026-10-13)*: the content check of the plans is below.

## Drift check (2026-10-12, historical folder H6)

The folder moved from `Release_2/Phase_0/` to `Release_2/phases/06_betaTestingReportAndFixing/` (`91e88b8d1`); the
three reports ingested here moved without changes, the folder's `INDEX.md` was edited. Eleven files were never
ingested: the F1–F17 feedback classification and ten plans (asset identity and identifiers, asset lifecycle, Crédit
Agricole trades, engine accounting and signals, frontend coverage, i18n and docs assets, the import flow and wizard,
the test-runner migration, transactions UX). Their topics already have pages — for example
[[decisions/credit-agricole-securities-only-cash-neutral-brim]] — and their delivery is mostly `0e07359b4`; a
content-level check of each plan was not done in this step.

## Content check of the plans (2026-10-13, C-64 last part)

The ten plans and the F1–F17 classification were read in full against the wiki, and every gap was re-checked on
today's code and on git history. Three pages contradicted the code and were corrected: [[features/F-083]] (parsing
is concurrent, not sequential), [[concepts/txstore-pattern]] (a clone keeps its date) and
[[entities/portfolio-engine]] (the blob cache key). The gaps worth a page:

| Plan | Gap | Page |
|---|---|---|
| Asset identity (P3) | D1–D11: one asset per security, the quoted code leads, unify before repairing, merge | [[decisions/asset-identity-quoted-code-leads]] |
| Asset identity (P3) | the merge's two foreign-key ordering traps | [[problems/asset-merge-cascade-deleted-the-migrated-events]] |
| Crédit Agricole trades | B5-lite: the legs of a split add up to the row | [[decisions/import-row-split-legs-sum-to-the-row]] |
| Engine accounting and signals | the quadratic FX error dedup under a full-history load | [[problems/fx-error-dedup-went-quadratic-under-full-history]] |
| F1–F17 classification | F2: the caches ignored role and share; the first share fix | [[problems/portfolio-cache-ignored-role-and-share]] |
| F1–F17 classification | F13: the 2 GB image | [[features/F-062]] |
| Test-runner migration | D-3.3, «chi committa, ripulisce» | [[concepts/transaction-hygiene-fixture]] |
| Test-runner migration | detour 15, a skipped category counted as passed | [[concepts/derived-test-inventory]] |

The merge and the inactive-asset rule were added to [[features/F-024]], the two decisions linked from
[[features/F-049]].

**Recorded in the plans, not paged** — smaller findings, listed so they can be found; they were not re-verified here:

- *import wizard*: the repair step limited to the fields that matter for duplicates (a WAC blocker kept «Next»
  disabled); the duplicates step opening on database collisions too; the parse counters (W1, W3) and the
  re-selection of importable rows (W7);
- *Crédit Agricole trades, detours*: `/assets/all` returning only active assets (three lookups moved to
  `/assets/query`, the FX pair page left as it was); the asymmetric sign rules; a reopened decided row that vanished;
  fund redemptions arriving as bank transfers;
- *i18n and docs assets*: the asset-download script failing the build on a hard failure; the gallery kept out of the
  Docker build; the provider-error resolver;
- *transactions UX*: the tooltip opening delay;
- *F1–F17*: the date inputs exempted from the iOS zoom guard (F17); the changelog modal trapped by a `transform` on
  the sidebar's `<nav>` (F12);
- *test-runner migration*: setup once per scope; a half-dead server and a `fetch` without a timeout in
  `globalSetup`; the scheduler's serial/parallel fixed point; `external_all` running 28 tests twice; the coverage
  noise floor of the network providers; `.DS_Store` blocking a cleanup;
- *frontend coverage*: the coverage arguments normalisation; a modal reopened on stale data; `not.toContain` on a
  list of objects, true by construction.

## Source files

| Role | Path |
|------|------|
| Tester report | `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/00_20260805_betaTester_report.md` |
| Taxonomy of findings | `.../01_tassonomia_findings.md` |
| Reconciliation | `.../02_riconciliazione_credit_agricole.md` |
| Index and P1-P8 status | `.../INDEX.md` |
| BRIM provider | `backend/app/services/brim_providers/broker_credit_agricole/plugin.py` |
| Provider tests | `backend/test_scripts/test_external/test_brim_providers.py` |
| mkdocs | `mkdocs_src/docs/developer/backend/brim/` |
| Plans and F1–F17 classification | `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/` |
