---
title: "Phase 0 / 48 — UI polish before the tag (workstream I): the broker icon, the import mismatch modal, the security details, the copy buttons, the Spanish toolbar"
category: source
source_type: plan
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/Phase_0/48_uiPolish/plan-phase00UiPolish.prompt.md
tags: [phase0, release2, workstream-i, frontend, ui, polish, broker-icon, clipboard, connection-security, layout, i18n]
related:
  - problems/late-img-error-marked-the-visible-icon-failed
  - decisions/clipboard-through-one-helper-with-a-gate
  - decisions/security-details-close-after-30-seconds
  - problems/toolbar-measurements-differed-by-the-scrollbar-gutter
  - problems/broker-icon-race-condition
  - problems/copy-buttons-without-http-fallback
  - concepts/responsive-4mode-layout
---

# Source: plan 48, the UI polish of workstream I

## Summary

Five fixes asked by the developer and the coordinator on 2026-10-12, before the 1.2 tag, each proved red before and
green after, and integrated in train 72 (2026-10-12, `0071b9703`). The work stopped with the developer's STOP at 18:26
and resumed at 19:24.

## Key takeaways

- **The broker icon** (`2412c3fe4`): a late `error` event from a replaced `<img>` marked the visible plugin icon as
  failed — [[problems/late-img-error-marked-the-visible-icon-failed]]. C-56 and C-57 stay in the backlog
  ([[problems/broker-icon-race-condition]]).
- **The wrong-broker modal of the import** (`0a69eb007`): the developer, verbatim, «i bottoni hanno i testi che vanno
  a capo e restano larghi, magari il rimuovi può essere accorciato, e anche lo sposta può diventare senza il nome del
  broker» ("the buttons' texts wrap and stay wide; maybe 'remove' can be shortened, and 'move' can lose the broker's
  name"). The buttons now read Remove and Move in the four languages, never wrap inside, and the footer wraps as a
  whole at 375 px. Written against the old catalogue paths, the change reached `base/` through U-2's pure rename
  ([[decisions/plugin-folders-and-split-i18n]]). The import guide that quotes the old labels goes to workstream M.
- **The security details** (`5e9eff52d`) close by themselves after 30 s —
  [[decisions/security-details-close-after-30-seconds]].
- **The copy buttons** (`65d20910e`, M-20 and C-63) go through one helper, kept there by a gate —
  [[decisions/clipboard-through-one-helper-with-a-gate]].
- **The Spanish toolbar** (`7f8febd9d`, V-19): the thresholds compare the bar's width, and a 15 px gap between two
  measurements was the scrollbar gutter — [[problems/toolbar-measurements-differed-by-the-scrollbar-gutter]].

## Not ingested

- A counter race found in `asset-detail.spec.ts`, which the coordinator split off: «(a), ma come lotto 49 separato,
  subito dopo il checkpoint del lotto 48» ("(a), but as a separate lot 49, right after lot 48's checkpoint") — ingested at train 78:
  [[problems/request-counter-read-before-the-handler-counted]].
- Backlog 48-1 (the AI Export button padded wider than its neighbours), left for after 1.2.

## Source files

| Role | Path |
|------|------|
| Plan 48 | `LibreFolio_developer_journal/Release_2/Phase_0/48_uiPolish/plan-phase00UiPolish.prompt.md` |
| The wrong-broker modal | `frontend/src/lib/features/transactions/import/ImportBrokerMismatchModal.svelte` |
| Its E2E | `frontend/e2e/transactions/tx-import-broker-mismatch.spec.ts` |
| Backlog (48-1, C-56, C-57, C-63) | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
