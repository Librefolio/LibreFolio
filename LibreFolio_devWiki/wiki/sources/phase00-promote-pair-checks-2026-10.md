---
title: "Phase 0 / 42 — the checks of promoted pairs (workstream P), with C-46…C-48 and the mini-lot from M's audit"
category: source
source_type: plan
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/Phase_0/42_promotePairChecks/plan-phase00PromotePairChecks.prompt.md
tags: [phase0, release2, workstream-p, promote, transfer, pairs, bulk-editor, i18n, testing]
related:
  - decisions/transfer-pair-same-asset-opposite-quantity
  - decisions/promote-respects-asset-event-link
  - problems/bulk-cost-basis-compared-by-reference
  - concepts/marker-locale-for-catalogue-labels
  - problems/legacy-component-language-untracked
---

# Source: Phase 0 / 42 — the checks of promoted pairs

## Summary

Plan 42 of workstream P (714 lines, 10–11 October) started from findings of workstream S's test author, traced in the
code but not reproduced. P wrote the red tests first, the coordinator decided D1 and D2, and the lot fixed four defects:

- TRANSFER pairs whose quantities did not cancel, or whose assets differed;
- promotes that kept a link to an asset event their new type does not admit;
- the bulk editor comparing costs by reference;
- the 💡 proposing event-linked rows.

The lot entered with train 34 (`7f8233c47`, merge `8ca0d5535`). Three more pieces followed:

- a side task on the distribution editor (`01b967c56`, train 32);
- C-46…C-48 (`bdec709d2`, train 37);
- a mini-lot of localisation fixes from M's audit (`0de730f3b`, train 38), on the coordinator's word: the developer was
  away and had delegated the reasonable choices.

P then finished, and its chat was archived on 2026-10-11.

## Key Takeaways

- **D1**: a TRANSFER pair is one asset in exactly opposite quantities, checked by the backend, the editor's rule, the
  banner and the selection bar — [[decisions/transfer-pair-same-asset-opposite-quantity]].
- **D2**: a promote is refused rather than unlinked when a row's event link does not fit its new type, and the 💡 follows
  the same rule — [[decisions/promote-respects-asset-event-link]].
- **`fieldEq`** compared cost objects by reference since May: [[problems/bulk-cost-basis-compared-by-reference]].
- **C-47**: the *Max Δ days* slider went down to 0 while `/promote-suggest` wanted `tolerance_days ≥ 1` (a 422 that ended
  in a `console.warn`), and moving it did not search again. The coordinator chose (b): the backend accepts 0 — the same
  day only — and the window enters the 💡 search key, so the slider searches again
  ([[decisions/bulk-pairs-new-with-saved]]).
- **C-48**: the empty manual cost warning now says «0 for a stock split, the donor's original cost for a gift», in the
  four languages with the glossary's terms, and so does the form guide.
- **The localisation mini-lot**:
  - percentages localised on the broker card, the broker page and the sharing panel — with a Svelte trap avoided,
    [[problems/legacy-component-language-untracked]];
  - Spanish and French catalogue terms aligned to the glossary («tipo de cambio», «bróker», «téléverser», «Unir» against
    «Combinar», accents);
  - English labels written in the code moved to the catalogue, tested with [[concepts/marker-locale-for-catalogue-labels]].
- **The distribution editor** (M's finding in the gallery): the weight header from the catalogue, totals through
  `formatPercent` with a locale, «Agregar país», French «excès».
- **Left after 1.2**: C-42, the remaining pair constraints and the single-leg update; P-13 (`KpiSection`'s percentages),
  P-14 (Spanish «broker» in 46 more keys), P-15 (more English labels in the code); the grid's `parseFloat` quantity cell.

## Wiki Pages Updated

- Created: the five pages above.
- Updated: [[decisions/bulk-pairs-new-with-saved]], [[decisions/pair-description-tags-validation]],
  [[decisions/cash-transfer-split-promote]], [[entities/transaction-batch-pipeline]],
  [[problems/promote-skipped-cost-basis-check]], [[concepts/svelte5-runes]], [[concepts/assert-on-identity-not-prose]],
  [[features/F-048]].

## Source files

| Role | Path |
|------|------|
| Plan 42 | `LibreFolio_developer_journal/Release_2/Phase_0/42_promotePairChecks/plan-phase00PromotePairChecks.prompt.md` |
| Post-1.2 backlog, section P (P-12…P-15) | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
| The pair and promote rules | `backend/app/services/transactions/transaction_service.py`, `backend/app/services/transactions/transaction_batch_stages.py` |
| The editor's rule | `frontend/src/lib/features/transactions/transactionTypeStore.ts` |
| The suggest endpoint (`tolerance_days`) | `backend/app/api/v1/transactions.py` |
