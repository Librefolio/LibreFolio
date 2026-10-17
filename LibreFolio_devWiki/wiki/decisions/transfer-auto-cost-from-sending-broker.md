---
title: "A transfer's receiving side in Auto takes the sending broker's average cost when the units left"
category: decision
status: resolved
date: 2026-10-09
updated: 2026-10-10
tags: [backend, wac, average-cost, cost-basis, transfer, promote, auto, transactions, workstream-p, release-1.2]
related:
  - problems/promote-skipped-cost-basis-check
  - decisions/financial-math-single-average-cost
  - decisions/auto-cost-basis-zero-without-position
  - decisions/wac-inline-validate-commit
  - entities/transaction-batch-pipeline
  - features/F-097
  - sources/phase00-transfer-cost-basis-2026-10
---

# Decision: the receiving side of a transfer averages the sending broker, as the units left

## Context

Workstream Q, reading the code, reported defects in the average cost that it had not tried. On 2026-10-09 workstream P
proved them with red tests, on `083ed26dc`; all of them were already in v1.1.0. Two share one cause — where a TRANSFER's
receiving side in Auto takes its cost from:

1. **A whole position moved in Auto got a cost of 0.** The source was the partner's broker, but the facade read that
   broker's rows up to the date *including the outgoing leg of the same transfer*: the pool was empty, the average 0,
   and the 0 was written (red P30 at validate, P31 at commit). A partial transfer was right, since a reduction does not
   move the unit cost.
2. **An existing transfer switched to Auto averaged the receiving broker.** An update item has no `link_uuid`, so the
   source was the row's own broker (red P32: 200 instead of 100). The same cause had a second path: a promote of a
   saved row with a new row in Auto, whose `link_uuid` found no partner among the creations (red P33: 0 instead of 100).

The third defect — a promote skipped the cost check — is [[problems/promote-skipped-cost-basis-check]].

## Options Considered

The developer first asked: «chat il punto 1 mi pareva che avvenisse già, gli altri 2 riguardano dati modificati dopo
il salvataggio, quindi più che altro la ui deve ricordarlo e chiedere di metterlo, o sbaglio?» ("I thought point 1
already happened; the other two concern data changed after saving, so isn't it rather the UI that should remind and
ask for it?"). After the explanation he chose: **«Correggere 1 e 2 nel backend con una sola cura, e 3 facendo chiedere
il costo anche col promote (Consigliato)»** ("fix 1 and 2 in the backend with one cure, and 3 by asking for the cost on
a promote too").

On the date of the average, for a transfer whose legs are days apart — BUY 10 at 100, the units out on 1 April, BUY 5
at 300 on 3 April, the receiving side on 5 April:

1. the old rule gave **200**;
2. leaving out only the outgoing leg would give **166.67**;
3. the sending pool as it was when the units left gives **100**, the real cost of the units moved — chosen, and
   confirmed by the developer: «Alla data in cui le quote escono dal broker d'origine (Consigliato)» ("at the date the
   units leave the sending broker").

## Decision

`_auto_cost_source()` (`transaction_service.py`, commit `d7c148564`, train 28) chooses the pool an Auto cost averages:

- the receiving side of a TRANSFER with `related_transaction_id` averages **its partner's broker, up to the partner's
  date, without the partner's outgoing leg and without itself**. The partner comes from the same batch, from the
  database or from a promote: the create, promote and link stages all run before the WAC stage, so one criterion is
  enough;
- any other row averages its own broker, without itself, up to its own date;
- `_resolve_source_broker_from_link`, the old `link_uuid` lookup, was removed with its unit test. The single
  average-cost function itself did not change ([[decisions/financial-math-single-average-cost]]).

## Consequences

- Red tests turned green: P30–P34 and P35 (written after the code, for the in-transit case) in
  `test_wac_inline.py`; no regression in the WAC, promote, portfolio-WAC, transaction and broker suites, nor in six
  E2E specs on WAC and promotes.
- Unchanged: Auto with no position stays 0, by decision P-1 ([[decisions/auto-cost-basis-zero-without-position]]);
  the facade's other callers (`POST /portfolio/wac`, the PAC); the frontend.
- The docs were aligned: `developer/backend/transactions/wac.md`, `developer/backend/transactions/split_promote.md`,
  and `developer/architecture/database/brokers_transactions.md`, where an older error was corrected too —
  `_compute_wac_for_auto_items()` writes the cost, `compute_wac_iterative()` only reads it. The theory page says it in
  all four languages: the sending position when the units left, before the outgoing leg.
- CHANGELOG 1.2.0, 🐛 Fixed: «An asset transfer in *Auto* keeps the cost of the shares it moves».

## Links

- [[problems/promote-skipped-cost-basis-check]] — the same lot's third defect
- [[decisions/wac-inline-validate-commit]] — how Auto, validate and commit fit together
- [[entities/transaction-batch-pipeline]] — the stage order the rule relies on
- [[features/F-097]] — the WAC feature
- Source: [[sources/phase00-transfer-cost-basis-2026-10]]

## Source files

| Role | Path |
|------|------|
| `_auto_cost_source`, `_compute_wac_for_auto_items` | `backend/app/services/transactions/auto_cost.py` |
| The facade, `compute_wac_iterative` | `backend/app/services/portfolio_service.py` |
| The average-cost function (unchanged) | `backend/app/services/financial_math/average_cost.py` |
| P30–P35 | `backend/test_scripts/test_api/test_wac_inline.py` |
| Developer doc | `mkdocs_src/docs/developer/backend/transactions/wac.md` |
| Data model doc | `mkdocs_src/docs/developer/architecture/database/brokers_transactions.md` |
| Theory | `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/weighted-average-cost.en.md` |
| Plan 40 | `LibreFolio_developer_journal/Release_2/phases/40_transferCostBasis/plan-phase00TransferCostBasis.prompt.md` |
