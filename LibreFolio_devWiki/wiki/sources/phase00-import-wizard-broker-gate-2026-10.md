---
title: "Phase 0 / 44 — the import wizard waits for the broker list (workstream I, M-16)"
category: source
source_type: plan
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/Phase_0/44_importWizardBrokerGate/plan-phase00ImportWizardBrokerGate.prompt.md
tags: [phase0, release2, workstream-i, import-wizard, svelte5, testing, m-16]
related:
  - problems/import-wizard-next-before-brokers-loaded
  - problems/playwright-probes-ignore-timeout
  - decisions/native-cash-daily-revaluation
---

# Source: Phase 0 / 44 — the import wizard waits for the broker list

## Summary

Plan 44 of workstream I (220 lines, 2026-10-12) fixed backlog M-16, which M's test author had found while fixing the
gallery probes. On the import wizard's step 1, «Next» worked before the broker list had arrived, so step 2 showed
every broker panel collapsed and the uploaded files hidden. The developer chose to disable the button until the list
arrives. On I's analysis the coordinator approved covering the refresh after a broker created from step 1 as well (B)
and reusing the upload's spinner, and dropped a second E2E. The red tests came first, from `test-author`; the fix
(`3cd25af4f`) entered with train 48. The same lot also carried I's journal work: the F-AI (b) row in section I of the
post-1.2 backlog and the closing notes of plan 41 (`8339b0a06`).

## Key Takeaways

- The defect, the fix and the tests: [[problems/import-wizard-next-before-brokers-loaded]].
- A counter of loads in flight, incremented inside the effect that starts them, must not be `$state` — the rule of
  [[problems/svelte5-effect-read-write-loop]], applied before the code.
- The gallery line that depends on the gate went to M, who was editing `gallery.spec.ts` for M-14
  ([[problems/playwright-probes-ignore-timeout]]).
- F-AI (b) — «FX on cash» by name in the portfolio's AI Export, with a typed code on `OtherPeriodEffect` — is a backlog
  row since this lot ([[decisions/native-cash-daily-revaluation]]).
- The CHANGELOG line (🐛 Fixed): the wizard keeps Next disabled until the brokers have loaded.

## Wiki Pages Updated

- Created: [[problems/import-wizard-next-before-brokers-loaded]].
- Updated: [[problems/playwright-probes-ignore-timeout]], [[problems/svelte5-effect-read-write-loop]],
  [[decisions/import-wizard-default-plugin-check]], [[decisions/native-cash-daily-revaluation]], [[features/F-049]],
  [[entities/import-wizard-modal]].

## Source files

| Role | Path |
|------|------|
| Plan 44 | `LibreFolio_developer_journal/Release_2/Phase_0/44_importWizardBrokerGate/plan-phase00ImportWizardBrokerGate.prompt.md` |
| Post-1.2 backlog, section I (F-AI (b)) | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
| Plan 41, the closing notes | `LibreFolio_developer_journal/Release_2/Phase_0/41_brokerPnlFlows/plan-phase00BrokerPnlFlows.prompt.md` |
| The wizard | `frontend/src/lib/features/transactions/import/ImportWizardModal.svelte` |
