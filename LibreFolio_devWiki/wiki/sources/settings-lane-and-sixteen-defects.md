---
title: "The settings lane and the sixteen tracked defects"
category: source
source_type: plan
date_ingested: 2026-08-31
original_path: "LibreFolio_developer_journal/Release_2/phases/07_coverageAndConsolidationCampaign/difetti-aperti-corsia-impostazioni.md + plan-storico-corsia-impostazioni-COMPLETO.md + plan-storico-undici-difetti-COMPLETO.md + plan-storico-scheduler-e-fx-COMPLETO.md"
tags: [settings, brokers, scheduler, fx, transactions, product-decisions, testing]
related:
  - decisions/settings-write-path-contract
  - decisions/broker-last-owner-guard
  - decisions/scheduler-converts-at-decision
  - concepts/absence-sentinel-vs-nullable-type
  - concepts/characterisation-test-latch
  - problems/i18n-key-assertion-false-green
  - problems/shared-component-option-changed-globally
---

# Source: the settings lane, and the sixteen defects it tracked

## Summary

The settings coverage lane found eleven defects it deliberately did **not** fix,
because each was a product question rather than a test gap. Five more were found
afterwards. All sixteen were frozen with characterisation tests
([[concepts/characterisation-test-latch]]), presented to the user with a
recommendation each, and then closed in a following lane.

This is the densest source in the campaign, because it is the one where the
answers are the **user's**, not the implementer's.

## The tracked items and where their answers now live

| group | subject | answer recorded in |
|---|---|---|
| A1, A2 | broker sharing — the last-owner asymmetry | [[decisions/broker-last-owner-guard]] |
| B1, B2, B3 | settings modals, confirm-before-apply | [[decisions/settings-write-path-contract]] |
| C1-C9 | preferences, profile, global settings, FX zero, transactions | [[decisions/settings-write-path-contract]], [[concepts/absence-sentinel-vs-nullable-type]] |
| D1 | scheduler — weekdays stay UTC while times convert | [[decisions/scheduler-converts-at-decision]] |
| D2 | zero used as an FX sentinel across seven consumers | [[concepts/absence-sentinel-vs-nullable-type]] |

## Key Takeaways

- **The user's answers are the artefact.** For A1 the instruction was explicit:
  *the last owner cannot be deleted; the system should ask whether to delete the
  broker together with its transactions, or to promote a new owner*. That is a
  product design, and it would have been lost in chat.
- **B2 was reversed by D1, knowingly.** B2 had concluded *"the timezone is only a
  lens; the absolute instant does not change"*. D1 concluded the opposite — *the
  timezone is part of the definition*. Both are recorded; the reversal is the
  interesting part, and it is documented in
  [[decisions/scheduler-converts-at-decision]].
- **D1 was not a regression introduced by the fix.** Weekday-in-UTC had always
  been there, hidden because times did not convert either. Fixing half made the
  other half visible.
- **Widen the type first and let the compiler enumerate the work** — the FX
  nullable migration, [[concepts/absence-sentinel-vs-nullable-type]].
- Two of the lane's own tests turned out to be unreliable in ways worth their own
  pages: [[problems/i18n-key-assertion-false-green]] and
  [[problems/shared-component-option-changed-globally]].

## Four operational notes closing the lane

The lane finished with four notes that are process, not product: which
characterisation tests must be deleted when a decision lands, which endpoint
already supports the intended repair (`DELETE /api/v1/brokers` with `force`),
which barrel file was dead (`transactions/modals/index.ts`, deleted), and which
helper is right but unwired (`resolveFormItemsFromOps`).

## Source files

| Role | Path |
|------|------|
| Settings UI | `frontend/src/lib/components/settings/` |
| Broker sharing | `frontend/src/lib/components/brokers/BrokerSharingPanel.svelte` |
| Scheduler config | `frontend/src/lib/components/settings/SchedulerConfigModal.svelte` |
| FX service and consumers | `backend/app/services/fx.py` |
| Bulk modal | `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte` |
| Original plans | `LibreFolio_developer_journal/Release_2/phases/07_coverageAndConsolidationCampaign/difetti-aperti-corsia-impostazioni.md` and three companions (untracked) |
